import os
import re
import shutil
import json
import threading

from metadata import extract_metadata
from injector import inject_metadata_into_archive
import scanner

HAS_SEND2TRASH = False
try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    pass

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            print(f"[!] Warning: Failed to load config: {e}")
    return {}

def save_config(conf):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(conf, f, indent=4)
    except (OSError, ValueError) as e:
        print(f"[!] Warning: Failed to save config: {e}")

def load_library_cache(dest_dir):
    cache_path = os.path.join(dest_dir, ".comic_sorter_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            print(f"[!] Warning: Failed to load library cache: {e}")
    return {}

def save_library_cache(dest_dir, cache):
    cache_path = os.path.join(dest_dir, ".comic_sorter_cache.json")
    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=4)
    except (OSError, ValueError) as e:
        print(f"[!] Warning: Failed to save library cache: {e}")


class ComicSorterEngine:
    def __init__(self, callbacks):
        self.callbacks = callbacks
        self.aborted = False

    def log(self, msg):
        if 'log' in self.callbacks:
            self.callbacks['log'](msg)
        else:
            print(msg)

    def _safe_log(self, msg, lock):
        with lock:
            self.log(msg)

    def _handle_api_rate_limit(self, file_path, filename, custom_regexes, safe_log):
        safe_log("\n=================================================================")
        safe_log("!!! FATAL ERROR: COMICVINE API RATE LIMIT EXCEEDED !!!")
        safe_log("ComicVine's API officially restricts accounts to 200 requests per hour.")
        safe_log("=================================================================")
        
        continue_offline = False
        if 'on_rate_limit' in self.callbacks:
            continue_offline = self.callbacks['on_rate_limit']()
            
        if continue_offline:
            safe_log("\nContinuing strictly offline. Future API hits skipped.")
            try:
                publisher, ip, storyline, issue, volume = extract_metadata(file_path, None, custom_regexes)
                return True, None, publisher, ip, storyline, issue, volume
            except Exception as offline_e:
                ctx = f"Offline data extraction for '{filename}'"
                should_continue = False
                if 'on_failure' in self.callbacks:
                    should_continue = self.callbacks['on_failure'](str(offline_e), ctx)
                else:
                    safe_log(f"\n[!] Offline metadata extraction failed: {offline_e}")
                    should_continue = True
                    
                if not should_continue:
                    safe_log(f"\n[!] Aborting execution due to offline metadata crash: {offline_e}")
                    self.aborted = True
                    return False, None, None, None, None, None, None
                else:
                    return True, None, "Unknown Publisher", "Unknown IP", "Unknown Storyline", "", ""
        else:
            safe_log("\nAborting sort.")
            self.aborted = True
            return False, None, None, None, None, None, None

    def _handle_missing_api_key(self, file_path, custom_regexes, safe_log, config):
        if 'on_missing_api_key' in self.callbacks:
            new_key = self.callbacks['on_missing_api_key']()
            if new_key:
                config['comicvine_api_key'] = new_key
                save_config(config)
                safe_log("  Retrying with ComicVine API...")
                try:
                    return extract_metadata(file_path, new_key, custom_regexes), new_key
                except Exception:
                    pass
        return None, None

    def _process_single_file(self, file_path, res, context):
        filename = os.path.basename(file_path)
        safe_log = context['safe_log']
        custom_regexes = context['custom_regexes']
        api_key = context['api_key']
        config = context['config']
        library_cache = context['library_cache']
        dest_dir = context['dest_dir']
        dry_run = context['dry_run']
        is_move_operation = context['is_move_operation']
        activity_log = context['activity_log']
        ambiguous_files = context['ambiguous_files']
        processed_originals = context['processed_originals']

        _, is_cached, publisher, ip, storyline, issue, volume, err = res
        
        if err:
            if str(err) == "API_RATE_LIMIT":
                cont, new_key, publisher, ip, storyline, issue, volume = self._handle_api_rate_limit(file_path, filename, custom_regexes, safe_log)
                if not cont:
                    return
                api_key = new_key
                context['api_key'] = api_key
            else:
                ctx = f"Metadata extraction for '{filename}'"
                should_continue = False
                if 'on_failure' in self.callbacks:
                    should_continue = self.callbacks['on_failure'](str(err), ctx)
                else:
                    safe_log(f"\n[!] Unexpected Error during extraction: {err}")
                    should_continue = True
                
                if not should_continue:
                    activity_log.append(f"[FATAL_ERROR] Aborted on metadata extraction : {filename}")
                    self.aborted = True
                    return
                else:
                    publisher, ip, storyline, issue, volume = "Unknown Publisher", "Unknown IP", "Unknown Storyline", "", ""
                
        if (publisher == "Unknown Publisher" or ip == "Unknown IP") and not api_key:
            safe_log(f"  [!] Missing metadata for {filename}")
            ret_metadata, new_key = self._handle_missing_api_key(file_path, custom_regexes, safe_log, config)
            if ret_metadata:
                publisher, ip, storyline, issue, volume = ret_metadata
                api_key = new_key
                context['api_key'] = api_key

        publisher = re.sub(r'[\\/*?:"<>|]', "", publisher or "Unknown Publisher").strip()
        ip = re.sub(r'[\\/*?:"<>|]', "", ip or "Unknown IP").strip()
        storyline = re.sub(r'[\\/*?:"<>|]', "", storyline or "Unknown Storyline").strip()
        issue = issue or ""
        volume = volume or ""
        
        if publisher == "Unknown Publisher" or storyline == "Unknown Storyline":
            ambiguous_files.append(f"[{publisher}] / [{ip}] / [{storyline}] -> {filename}")

        if "ADULT" in filename.upper():
            target_dir = os.path.join(dest_dir, "Adult", publisher, ip, storyline)
        else:
            target_dir = os.path.join(dest_dir, publisher, ip, storyline)
            
        target_file = os.path.join(target_dir, filename)
        needs_move = True
        
        if os.path.exists(target_file) and os.path.abspath(target_file) != os.path.abspath(file_path):
            target_size = os.path.getsize(target_file)
            source_size = os.path.getsize(file_path)
            target_cache_key = f"{filename}_{target_size}"
            
            if target_size == source_size or (is_cached and target_cache_key in library_cache):
                safe_log("  [!] Target exists natively matching source footprints. Assumed Duplicate.")
                activity_log.append(f"[DUPLICATE] Trashed         : {filename}")
                needs_move = False
                if not dry_run:
                    if 'on_trash_prompt' in self.callbacks and self.callbacks['on_trash_prompt'](-1): 
                        if HAS_SEND2TRASH:
                            try:
                                send2trash(file_path)
                            except Exception:
                                os.remove(file_path)
                        else:
                            os.remove(file_path)
                return

        if is_move_operation and os.path.abspath(target_file) == os.path.abspath(file_path):
            safe_log("  [=] File already perfectly sorted.")
            activity_log.append(f"[SKIPPED] Perfectly sorted  : {filename}")
            needs_move = False
            
        if not dry_run:
            os.makedirs(target_dir, exist_ok=True)
        
        source_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        try:
            if needs_move:
                if is_move_operation:
                    if not dry_run: shutil.move(file_path, target_file)
                    safe_log("  [>] Moved to proper library location.")
                else:
                    if not dry_run: shutil.copy2(file_path, target_file)
                    safe_log("  [>] Copied to library.")
            
            if not is_cached or needs_move:
                if not dry_run:
                    target_file = inject_metadata_into_archive(target_file, publisher, ip, storyline, issue, volume)
                    new_size = os.path.getsize(target_file)
                else:
                    new_size = source_size
                    
                new_cache_key = f"{filename}_{new_size}"
                source_cache_key = f"{filename}_{source_size}"
                
                library_cache[new_cache_key] = {"publisher": publisher, "ip": ip, "storyline": storyline, "issue": issue, "volume": volume}
                library_cache[source_cache_key] = library_cache[new_cache_key]
                context['cache_updated'] = True
            
            activity_log.append(f"[SUCCESS] Sorted to         : {target_file}")
            if not is_move_operation:
                processed_originals.append(file_path)
                
        except Exception as e:
            context_msg = f"Processing disk operation for '{filename}'"
            should_continue = False
            if 'on_failure' in self.callbacks:
                should_continue = self.callbacks['on_failure'](str(e), context_msg)
            else:
                safe_log(f"\n[!] Disk operation failed: {e}")
                should_continue = True 
                
            if not should_continue:
                safe_log("\n[!] Aborting sort process immediately due to disk error.")
                activity_log.append(f"[FATAL_ERROR] Aborted on disk writing : {filename}")
                self.aborted = True
                return
            activity_log.append(f"[ERROR] Failed disk writing : {filename}")

    def process_comics(self, source_dir, dest_dir, api_key=None, is_move_operation=False, mode=1, dry_run=False):
        config = load_config()
        custom_regexes = config.get('custom_regexes', [])
        library_cache = load_library_cache(dest_dir)
        
        source_files = []
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                if f.lower().endswith(('.cbz', '.cbr')):
                    source_files.append(os.path.join(root, f))
                    
        if not source_files:
            self.log(f"No .cbz or .cbr files found logically under {source_dir}")
            if 'on_finish' in self.callbacks: self.callbacks['on_finish']()
            return

        processed_originals = []
        ambiguous_files = []
        activity_log = []
        self.aborted = False
        
        cb_lock = threading.Lock()
        def safe_log(m):
            self._safe_log(m, cb_lock)

        pre_processed = {}
        def _extract(file_path):
            try:
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                cache_key = f"{filename}_{file_size}"
                
                if cache_key in library_cache:
                    c = library_cache[cache_key]
                    return (file_path, True, c.get('publisher'), c.get('ip'), c.get('storyline'), c.get('issue'), c.get('volume'), None)
                
                publisher, ip, storyline, issue, volume = extract_metadata(file_path, api_key, custom_regexes)
                return (file_path, False, publisher, ip, storyline, issue, volume, None)
            except Exception as e:
                return (file_path, False, None, None, None, None, None, e)

        from concurrent.futures import ThreadPoolExecutor, as_completed
        safe_log(f"Phase 1: Scanning metadata for {len(source_files)} valid archives...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_path = {executor.submit(_extract, p): p for p in source_files}
            completed_count = 0
            for future in as_completed(future_to_path):
                if self.aborted:
                    break
                path = future_to_path[future]
                res = future.result()
                pre_processed[path] = res
                
                completed_count += 1
                if 'on_progress' in self.callbacks:
                    with cb_lock:
                        self.callbacks['on_progress'](completed_count, len(source_files))

        safe_log(f"\nPhase 2: Executing library injection & filesystem mapping...")
        if 'on_progress' in self.callbacks:
            with cb_lock:
                self.callbacks['on_progress'](0, 1)

        context = {
            'safe_log': safe_log,
            'custom_regexes': custom_regexes,
            'api_key': api_key,
            'config': config,
            'library_cache': library_cache,
            'dest_dir': dest_dir,
            'dry_run': dry_run,
            'is_move_operation': is_move_operation,
            'activity_log': activity_log,
            'ambiguous_files': ambiguous_files,
            'processed_originals': processed_originals,
            'cache_updated': False
        }
                
        for count, file_path in enumerate(source_files, 1):
            if self.aborted:
                break
                
            filename = os.path.basename(file_path)
            safe_log(f"[{count}/{len(source_files)}] Processing: {filename}")
            
            res = pre_processed.get(file_path)
            if not res: continue

            self._process_single_file(file_path, res, context)
                
            if 'on_progress' in self.callbacks:
                with cb_lock:
                    self.callbacks['on_progress'](count, len(source_files))

        if context['cache_updated'] and not dry_run:
            save_library_cache(dest_dir, library_cache)

        safe_log("\n--- Sorting Ended ---")
        if dry_run: safe_log("[SIMULATION ONLY] No files were permanently moved.")
        
        if is_move_operation and not dry_run:
            try:
                for root, dirs, files in os.walk(source_dir, topdown=False):
                    for d in dirs:
                        dir_path = os.path.join(root, d)
                        if not os.listdir(dir_path):
                            try:
                                os.rmdir(dir_path)
                            except Exception:
                                pass
            except Exception:
                pass
        elif not is_move_operation:
            safe_log(f"Successfully evaluated {len(processed_originals)} out of {len(source_files)} files.")
            
        safe_log(f"Check your destination directory at: {dest_dir}")
        
        if mode == 1:
            log_filename = "newSort_log.txt"
        elif mode == 2:
            log_filename = "reSort_log.txt"
        else:
            log_filename = "mergeSort_log.txt"
            
        if dry_run:
            log_filename = "DRY_RUN_" + log_filename
            
        if mode in [2, 3]:
            activity_log = [line for line in activity_log if "[SKIPPED]" not in line]
            
        if activity_log or ambiguous_files:
            report_path = os.path.join(dest_dir, log_filename)
            try:
                with open(report_path, 'w') as f:
                    f.write("=== Comic Sorter Execution Log ===\n")
                    if dry_run:
                        f.write("[!] DRY RUN MODE - SIMULATED RESULTS [!]\n")
                    if self.aborted:
                        f.write("\n[!] WARNING: Run was manually aborted. Log is incomplete!\n")
                    
                    f.write("\n--- Files Processed ---\n")
                    for line in activity_log:
                        f.write(line + "\n")
                        
                    if ambiguous_files:
                        f.write("\n--- Ambiguous Identifications (Manual check suggested) ---\n")
                        for line in ambiguous_files:
                            f.write(line + "\n")
                safe_log(f"\n[REPORT] An execution log has been saved natively to: {report_path}")
            except Exception:
                pass
        
        if processed_originals and not is_move_operation and not self.aborted and not dry_run:
            if 'on_trash_prompt' in self.callbacks:
                trash_it = self.callbacks['on_trash_prompt'](len(processed_originals))
                if trash_it:
                    if HAS_SEND2TRASH:
                        try:
                            for f in processed_originals:
                                if os.path.exists(f):
                                    send2trash(f)
                            safe_log("Original files moved to Trash.")
                        except Exception as e:
                            safe_log(f"Failed to trash files: {e}")
                    else:
                        for f in processed_originals:
                            if os.path.exists(f):
                                os.remove(f)
                        safe_log("Original files deleted (Trash not available).")
                else:
                    safe_log("Original files kept.")
                    
        if 'on_finish' in self.callbacks:
            self.callbacks['on_finish']()
