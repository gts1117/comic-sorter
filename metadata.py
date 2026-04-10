import zipfile
import xml.etree.ElementTree as ET
import os
import re
from inference import infer_metadata

try:
    import rarfile
except ImportError:
    rarfile = None

def guess_metadata_from_filename(filename, custom_regexes=None):
    basename = os.path.basename(filename)
    name, ext = os.path.splitext(basename)
    
    publisher = "Unknown Publisher"
    ip = "Unknown IP"
    storyline = "Unknown Storyline"
    issue = ""
    volume = ""
    
    if custom_regexes:
        for r in custom_regexes:
            try:
                match = re.search(r, name, re.IGNORECASE)
                if match:
                    d = match.groupdict()
                    if 'publisher' in d and d['publisher']: publisher = d['publisher'].strip()
                    if 'ip' in d and d['ip']: ip = d['ip'].strip()
                    if 'storyline' in d and d['storyline']: storyline = d['storyline'].strip()
                    if 'issue' in d and d['issue']: issue = d['issue'].strip()
                    if 'volume' in d and d['volume']: volume = d['volume'].strip()
                    return publisher, ip, storyline, issue, volume
            except re.error:
                continue
                
    # Fallback default matching
    match = re.match(r"^([a-zA-Z\s\-\'\.\_]+?)(?=\s*(?:#|\b(?:v|vol|volume)\b\.?|\d{1,4}(?:\s|$|\()|\())", name, re.IGNORECASE)
    
    if match:
        ip = match.group(1).strip()
        ip = re.sub(r'[\-\_\.]$', '', ip).strip()
        
    vol_match = re.search(r'\b(?:v|vol|volume)\.?\s*(\d+)\b', name, re.IGNORECASE)
    if vol_match:
        volume = vol_match.group(1)
        
    issue_match = re.search(r'#\s*(\d+(?:\.\d+)?)\b', name)
    if issue_match:
        issue = issue_match.group(1)
    else:
        if ip != "Unknown IP":
            after_ip = name[len(ip):]
            loose = re.search(r'^\s*[\-\_]?\s*(\d+(?:\.\d+)?(?:[a-zA-Z])?)\b', after_ip)
            if loose:
                issue = loose.group(1)
                
    return publisher, ip, storyline, issue, volume

def extract_metadata(file_path, api_key=None, custom_regexes=None):
    publisher = None
    ip = None
    storyline = None
    issue = ""
    volume = ""

    def parse_xml_node(root):
        nonlocal publisher, ip, storyline, issue, volume
        def get_text(tag):
            elem = root.find(tag)
            return elem.text.strip() if elem is not None and elem.text else None
            
        publisher = get_text('Publisher') or publisher
        ip = get_text('Series') or ip
        storyline = get_text('StoryArc') or storyline
        issue = get_text('Number') or issue
        volume = get_text('Volume') or volume

    try:
        if file_path.lower().endswith('.cbz'):
            with zipfile.ZipFile(file_path, 'r') as zf:
                if 'ComicInfo.xml' in zf.namelist():
                    with zf.open('ComicInfo.xml') as f:
                        tree = ET.parse(f)
                        parse_xml_node(tree.getroot())
                        
                elif 'comicinfo.xml' in [name.lower() for name in zf.namelist()]:
                    real_name = next(name for name in zf.namelist() if name.lower() == 'comicinfo.xml')
                    with zf.open(real_name) as f:
                        tree = ET.parse(f)
                        parse_xml_node(tree.getroot())
                        
        elif file_path.lower().endswith('.cbr') and rarfile is not None:
            with rarfile.RarFile(file_path, 'r') as rf:
                if 'ComicInfo.xml' in rf.namelist():
                    with rf.open('ComicInfo.xml') as f:
                        tree = ET.parse(f)
                        parse_xml_node(tree.getroot())
                        
                elif 'comicinfo.xml' in [name.lower() for name in rf.namelist()]:
                    real_name = next(name for name in rf.namelist() if name.lower() == 'comicinfo.xml')
                    with rf.open(real_name) as f:
                        tree = ET.parse(f)
                        parse_xml_node(tree.getroot())
    except Exception as e:
        print(f"  [!] Ignored unreadable archive '{os.path.basename(file_path)}' metadata. Reason: {e}")

    # Fallback logic
    fb_pub, fb_ip, fb_story, fb_issue, fb_vol = guess_metadata_from_filename(file_path, custom_regexes)
    
    if not publisher: publisher = fb_pub
    if not ip: ip = fb_ip
    if not storyline: storyline = fb_story
    if not issue: issue = fb_issue
    if not volume: volume = fb_vol
        
    if not publisher: publisher = "Unknown Publisher"
    if not ip: ip = "Unknown IP"
    if not storyline: storyline = "Unknown Storyline"

    filename = os.path.basename(file_path)
    # inference only modifies pub/ip/storyline
    publisher, ip, storyline = infer_metadata(publisher, ip, storyline, filename, api_key)
    
    return publisher, ip, storyline, issue, volume

if __name__ == '__main__':
    print(guess_metadata_from_filename("Batman v2 #13 (2020).cbz"))
