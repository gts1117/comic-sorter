import re
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import os
import app_paths

RULES_FILE = app_paths.user_data("rules.json")

DEFAULT_RULES = {
  "CORE_IPS": {
    "batman": "DC",
    "superman": "DC",
    "wonder woman": "DC",
    "flash": "DC",
    "green lantern": "DC",
    "aquaman": "DC",
    "justice league": "DC",
    "teen titans": "DC",
    "nightwing": "DC",
    "robin": "DC",
    "joker": "DC",
    "harley quinn": "DC",
    "supergirl": "DC",
    "superboy": "DC",
    "resurrection man": "DC",
    "ressurection man": "DC",
    "swamp thing": "Vertigo",
    "constantine": "Vertigo",
    "hellblazer": "Vertigo",
    "sandman": "Vertigo",
    "spider-man": "Marvel",
    "x-men": "Marvel",
    "avengers": "Marvel",
    "iron man": "Marvel",
    "captain america": "Marvel",
    "thor": "Marvel",
    "hulk": "Marvel",
    "black widow": "Marvel",
    "doctor strange": "Marvel",
    "daredevil": "Marvel",
    "wolverine": "Marvel",
    "deadpool": "Marvel",
    "fantastic four": "Marvel",
    "doctor doom": "Marvel",
    "dr doom": "Marvel",
    "punisher": "Marvel",
    "venom": "Marvel",
    "miles morales": "Marvel",
    "black panther": "Marvel",
    "hellboy": "Dark Horse",
    "bprd": "Dark Horse",
    "b.p.r.d.": "Dark Horse",
    "abe sapien": "Dark Horse",
    "sir edward grey": "Dark Horse",
    "lobster johnson": "Dark Horse",
    "witchfinder": "Dark Horse",
    "spawn": "Image",
    "invincible": "Image",
    "saga": "Image",
    "the walking dead": "Image",
    "we're taking everyone down with us": "Image",
    "machine girl": "Alien Books"
  },
  "ALIAS_IPS": {
    "bprd": "Hellboy",
    "b.p.r.d.": "Hellboy",
    "abe sapien": "Hellboy",
    "sir edward grey": "Hellboy",
    "lobster johnson": "Hellboy",
    "witchfinder": "Hellboy",
    "dr doom": "Doctor Doom",
    "ressurection man": "Resurrection Man"
  },
  "EVENT_MAPPINGS": {
    "one world under doom": {"publisher": "Marvel", "ip": "Doctor Doom", "storyline": "One World Under Doom"}
  },
  "FILENAME_OVERRIDES": [
    {
      "_comment": "Match any filename containing this substring (case-insensitive)",
      "match": "Plastic 001 (2017) (Digital) (Zone-Empire)",
      "publisher": "Image",
      "ip": "Plastic",
      "storyline": ""
    },
    {
      "match": "Plastic 002 (2017) (Digital) (Zone-Empire)",
      "publisher": "Image",
      "ip": "Plastic",
      "storyline": ""
    },
    {
      "match": "Plastic 003 (2017) (Digital) (Zone-Empire)",
      "publisher": "Image",
      "ip": "Plastic",
      "storyline": ""
    },
    {
      "match": "Plastic 004 (2017) (Digital) (Zone-Empire)",
      "publisher": "Image",
      "ip": "Plastic",
      "storyline": ""
    },
    {
      "match": "Plastic 005 (2017) (Digital) (Zone-Empire)",
      "publisher": "Image",
      "ip": "Plastic",
      "storyline": ""
    }
  ]
}

def load_rules():
    if not os.path.exists(RULES_FILE):
        try:
            with open(RULES_FILE, 'w') as f:
                json.dump(DEFAULT_RULES, f, indent=4)
        except Exception as e:
            # Failing to write default rules is okay, just use defaults
            pass
        return DEFAULT_RULES

    try:
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        return DEFAULT_RULES

rules_db = load_rules()
CORE_IPS = rules_db.get("CORE_IPS", {})
# Keep a frozen copy of user-defined rules so scanner-learned mappings can never overwrite them
_LOCKED_CORE_IPS = set(CORE_IPS.keys())
ALIAS_IPS = rules_db.get("ALIAS_IPS", {})
EVENT_MAPPINGS = rules_db.get("EVENT_MAPPINGS", {})
FILENAME_OVERRIDES = rules_db.get("FILENAME_OVERRIDES", [])

def update_learned_ips(mappings):
    """Register contextual folders learned by scanning an existing library.
    Never overwrites keys that were explicitly defined by the user in rules.json.
    """
    global CORE_IPS
    for key, value in mappings.items():
        if key not in _LOCKED_CORE_IPS:  # user rules are immutable
            CORE_IPS.setdefault(key, value)

CACHE_FILE = app_paths.user_data("comicvine_cache.json")
_CV_CACHE = None
_LAST_CV_REQ_TIME = 0

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache_data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=4)
    except Exception as e:
        print(f"Failed to save temporary ComicVine cache: {e}")

import threading
CV_LOCK = threading.Lock()

def query_comicvine(query, api_key):
    global _CV_CACHE, _LAST_CV_REQ_TIME
    
    with CV_LOCK:
        if _CV_CACHE is None:
            _CV_CACHE = load_cache()
            
        # Strip extension from query
        query = re.sub(r'\.(cbz|cbr|zip|rar)$', '', query, flags=re.IGNORECASE)
        
        cache_key = query.lower()
        if cache_key in _CV_CACHE:
            print(f"  [CACHE] Loaded ComicVine data from cache for: {query}")
            return _CV_CACHE[cache_key].get('publisher'), _CV_CACHE[cache_key].get('ip')
            
        # Velocity check: minimum 1 second between requests to respect rate limit
        time_since = time.time() - _LAST_CV_REQ_TIME
        if time_since < 1.0:
            time.sleep(1.0 - time_since)
            
        url = f"https://comicvine.gamespot.com/api/search/?api_key={api_key}&format=json&resources=volume&query={urllib.parse.quote(query)}"
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'User-Agent': 'ComicSorterApp/1.0'
            }
        )
        
        # PREEMPTIVELY update the timestamp before the HTTP call releases the GIL or halts
        _LAST_CV_REQ_TIME = time.time()
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data['results']:
                    first_result = data['results'][0]
                    pub = first_result.get('publisher', {}).get('name', "Unknown Publisher") if first_result.get('publisher') else "Unknown Publisher"
                    ip = first_result.get('name', "Unknown IP")
                    
                    # Commit to cache
                    _CV_CACHE[cache_key] = {"publisher": pub, "ip": ip}
                    save_cache(_CV_CACHE)
                    
                    return pub, ip
        except urllib.error.HTTPError as e:
            if e.code in [420, 429]:
                raise RuntimeError("API_RATE_LIMIT")
            raise RuntimeError(f"HTTP {e.code} - {e.reason}")
        except Exception as e:
            raise RuntimeError(str(e))
        return None, None


def infer_metadata(publisher, ip, storyline, original_filename="", api_key=None):
    # -1. Filename override check — highest priority, checked before anything else.
    # Add entries to the FILENAME_OVERRIDES list in rules.json to pin specific
    # ambiguously-named files to the correct publisher/IP/storyline.
    filename_lower = original_filename.lower()
    for override in FILENAME_OVERRIDES:
        match_str = override.get("match", "")
        if match_str and match_str.lower() in filename_lower:
            pub_o  = override.get("publisher") or publisher
            ip_o   = override.get("ip") or ip
            sl_o   = override.get("storyline") or storyline
            return pub_o, ip_o, sl_o

    # 0. Handle manually joined IPs (e.g., "Resurrection Man/ Quantum Karma", "Supergirl: Rebirth")
    if storyline == "Unknown Storyline":
        split_match = re.split(r'\s*(?:/|:| - )\s*', ip, maxsplit=1)
        if len(split_match) == 2:
            ip, storyline = split_match

    # 1. Event Check
    for event, mapping in EVENT_MAPPINGS.items():
        if event in ip.lower() or event in storyline.lower() or event in original_filename.lower():
            publisher = publisher if publisher != "Unknown Publisher" else mapping["publisher"]
            ip = mapping["ip"]
            storyline = mapping["storyline"]
            return publisher, ip, storyline

    # 2. Base IP extraction check
    ip_lower = ip.lower()
    file_lower = original_filename.lower()
    
    sorted_cores = sorted(CORE_IPS.keys(), key=len, reverse=True)
    
    found_core = None
    remainder = ""
    
    # First check extracted IP
    for core in sorted_cores:
        if re.search(r'\b' + re.escape(core) + r'\b', ip_lower):
            found_core = core
            
            # If the IP starts with the core (e.g., Wonder Woman Black and Gold), strip the core text
            if ip_lower.startswith(core):
                remainder = ip[len(core):].strip()
            else:
                # If the core is located inside the IP (e.g., "Absolute Batman" or "The Amazing Spider-Man"),
                # the entire extracted IP makes a great storyline name.
                remainder = ip
            break
            
    # Then try filename if IP is still unknown
    if not found_core and ip == "Unknown IP":
        for core in sorted_cores:
            if re.search(r'\b' + re.escape(core) + r'\b', file_lower):
                found_core = core
                remainder = "" # Too hard to extract remainder from filename reliably
                break

    if found_core:
        # Resolve to base IP
        base_ip = ALIAS_IPS.get(found_core, found_core.title())
        
        # Clean remainder
        remainder = re.sub(r'^[\-\:]\s*', '', remainder).strip()
        
        ip = base_ip
        if remainder and storyline == "Unknown Storyline":
            # If original remainder already has proper casing (because we took it from 'ip' directly), 
            # we should avoid ruining it with .title() which lowercases acronyms.
            if remainder == remainder.lower():
                 storyline = remainder.title()
            else:
                 storyline = remainder
                
        # 3. Publisher Inference
        if publisher == "Unknown Publisher" or publisher.lower() == "unknown publisher":
            publisher = CORE_IPS[found_core]

    # Optional Comicvine Fallback
    if api_key and (publisher == "Unknown Publisher" or ip == "Unknown IP"):
        print(f"  [API] Falling back to ComicVine for: {original_filename}")
        cv_pub, cv_ip = query_comicvine(original_filename, api_key)
        if cv_pub and cv_pub != "Unknown Publisher": 
            publisher = cv_pub
        if cv_ip and cv_ip != "Unknown IP": 
            ip = cv_ip

    # Normalize publisher names robustly across ALL sources (including ComicVine)
    BAD_PUBLISHERS = {"unsorted", "unsorted comics", "unsorted files", "comics", "library", "books", "comic", "sort", "manga", "temporary"}
    if publisher and publisher.lower().strip() in BAD_PUBLISHERS:
        publisher = "Unknown Publisher"

    if publisher != "Unknown Publisher":
        while True:
            stripped = re.sub(r'(?i)\s+(comics|comic|books|publishing|entertainment|productions|press|studios|incorporated|inc\.?|llc|group)$', '', publisher)
            if stripped == publisher:
                break
            publisher = stripped
            
        acronyms = {"dc": "DC", "idw": "IDW", "marvel": "Marvel", "image": "Image", "dark horse": "Dark Horse", "boom!": "BOOM!"}
        normalized_pub = acronyms.get(publisher.lower())
        if normalized_pub:
            publisher = normalized_pub
        elif publisher.islower() or publisher.isupper():
            publisher = publisher.title()

    return publisher, ip, storyline
