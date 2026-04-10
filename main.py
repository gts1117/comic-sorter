import os
import sys

from core import load_config, save_config, ComicSorterEngine
import scanner

def choose_folder(prompt_msg):
    import subprocess
    script = f'POSIX path of (choose folder with prompt "{prompt_msg}")'
    res = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return None

if __name__ == "__main__":
    print("\n=== Welcome to Comic Sorter! ===")
    print("Select an operation mode:")
    print("[1] Sort New Library (Start a fresh sorted folder from scratch)")
    print("[2] Resort Existing Library (Fix misplacements in your library safely in-place)")
    print("[3] Smart-Merge (Add new files and dynamically adopt an existing library's categorization)")
    print("")
    
    try:
        mode = input("Enter choice (1/2/3): ").strip()
    except EOFError:
        sys.exit(0)
    
    source_dir = None
    dest_dir = None
    is_move_operation = False
    
    if mode == '1':
        print("\n1. Select the location of your UNSORTED comic files from the popup window...")
        source_dir = choose_folder("Select your UNSORTED comic files")
        if not source_dir:
            print("Action canceled. Exiting.")
            sys.exit(0)
            
        print("2. Select the location for your NEW SORTED library from the popup window...")
        dest_dir = choose_folder("Select your NEW SORTED library destination")
        if not dest_dir:
            print("Action canceled. Exiting.")
            sys.exit(0)
        
    elif mode == '2':
        print("\n1. Select the location of your EXISTING comic library to safely re-sort...")
        dest_dir = choose_folder("Select your EXISTING comic library to re-sort")
        if not dest_dir:
            print("Action canceled. Exiting.")
            sys.exit(0)
            
        source_dir = dest_dir 
        is_move_operation = True
        print("  [!] Notice: This mode strictly MOVES your files around inside this folder hierarchy.")
        
    elif mode == '3':
        print("\n1. Select the location of your UNSORTED comic files from the popup window...")
        source_dir = choose_folder("Select your UNSORTED comic files")
        if not source_dir:
            print("Action canceled. Exiting.")
            sys.exit(0)
            
        print("2. Select the location of your EXISTING library to strictly adopt rules from...")
        dest_dir = choose_folder("Select your EXISTING library to adopt rules from")
        if not dest_dir:
            print("Action canceled. Exiting.")
            sys.exit(0)
            
    else:
        print("Invalid selection. Exiting.")
        sys.exit(1)
        
    config = load_config()
    api_key = config.get('comicvine_api_key')
    
    if api_key is None:
        try:
            api_key = input("\n3. (Optional) Enter your ComicVine API Key, or press Enter to skip: ").strip()
            if api_key == "":
                api_key = None
            else:
                config['comicvine_api_key'] = api_key
                save_config(config)
                print("  [>] API Key securely cached for future runs!")
        except EOFError:
            pass
            
    print("\n--- Review ---")
    print(f"Source : {os.path.abspath(source_dir)}")
    print(f"Target : {os.path.abspath(dest_dir)}")
    print(f"Mode   : {'Move In-Place (NO DELETE)' if is_move_operation else 'Copy Files safely'}")
    
    try:
        confirm = input("\nReady to process your files? (Y)es, (N)o, or (D)ry-Run Simulation: ").strip().lower()
    except EOFError:
        confirm = 'n'
        
    if confirm in ['y', 'yes', 'go', 'run', 'd', 'dry', 'dry-run']:
        dry_run = confirm in ['d', 'dry', 'dry-run']
        if dry_run:
            print("\n[!] STARTING IN DRY-RUN SIMULATION MODE... NO FILES WILL BE MOVED [!]\n")
        else:
            print("\nStarting process...\n")
        
        if mode in ['2', '3']:
            scanner.scan_library(dest_dir)
            
        def on_missing_api_key():
            try:
                k = input("Enter ComicVine API key for online lookup (or hit Enter to skip): ").strip()
                return k if k else None
            except:
                return None
                
        def on_rate_limit():
            try:
                choice = input("\nDo you want to (A)bort the run, or (C)ontinue the run using ONLY offline guessing? (A/C): ").strip().lower()
                return choice in ['c', 'continue']
            except:
                return False
                
        def on_trash_prompt(num_files):
            if num_files == -1:
                return True
            try:
                choice = input(f"\nDo you want to move the {num_files} original sorted files to the Trash? (y/N): ").strip().lower()
                return choice in ['y', 'yes']
            except:
                return False

        def on_failure(err, context):
            print(f"\n[ERROR] An error occurred - {context}: {err}")
            return True # Try to continue
            
        callbacks = {
            'log': print,
            'on_progress': lambda cur, total: None,
            'on_missing_api_key': on_missing_api_key,
            'on_rate_limit': on_rate_limit,
            'on_trash_prompt': on_trash_prompt,
            'on_failure': on_failure,
            'on_finish': lambda: None
        }
        
        engine = ComicSorterEngine(callbacks)
        engine.process_comics(source_dir, dest_dir, api_key, is_move_operation, mode=int(mode), dry_run=dry_run)
        
    else:
        print("\nAction aborted. Have a great day!")
