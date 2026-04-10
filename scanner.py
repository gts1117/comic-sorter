import os
import inference

def scan_library(library_dir):
    print(f"\n[Scanner] Scanning existing library at {library_dir} for context...")
    if not os.path.exists(library_dir):
        return

    learned_mappings = {}

    for root, dirs, files in os.walk(library_dir):
        for f in files:
            if f.lower().endswith(('.cbz', '.cbr')):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, library_dir)
                parts = rel_path.split(os.sep)
                
                # We expect paths like Publisher/IP/Storyline/filename
                # Or at minimum Publisher/IP/filename
                if len(parts) >= 3:
                    # Strip 'Adult/' root if present to find true publisher
                    if parts[0].lower() == 'adult' and len(parts) >= 4:
                        publisher = parts[1]
                        ip = parts[2]
                    else:
                        publisher = parts[0]
                        ip = parts[1]
                    
                    if publisher.lower() not in ["unknown publisher", "adult", "unknown", "comics", "library", "books", "comic", "sort", "manga"]:
                        ip_lower = ip.lower()
                        if ip_lower not in learned_mappings:
                            learned_mappings[ip_lower] = publisher
                        
    if learned_mappings:
        print(f"  [-] Learned {len(learned_mappings)} custom franchise mappings from your folders!")
        inference.update_learned_ips(learned_mappings)
    else:
        print("  [-] No custom mappings found.")
