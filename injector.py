import os
import zipfile
import shutil
import tempfile
import xml.etree.ElementTree as ET
import subprocess
from xml.dom import minidom

try:
    import rarfile
except ImportError:
    rarfile = None

def render_xml(root):
    rough_string = ET.tostring(root, 'utf-8')
    try:
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding="utf-8")
    except Exception:
        return rough_string

def build_comic_info(publisher, ip, storyline, issue="", volume="", existing_xml_bytes=None):
    root = None
    if existing_xml_bytes:
        try:
            root = ET.fromstring(existing_xml_bytes)
        except Exception:
            pass 
            
    if root is None:
        root = ET.Element('ComicInfo', {
            'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        })
        
    def _set_or_update(tag, value):
        if not value or value.startswith("Unknown"):
            return
        el = root.find(tag)
        if el is None:
            el = ET.SubElement(root, tag)
        el.text = value

    _set_or_update('Publisher', publisher)
    _set_or_update('Series', ip)
    _set_or_update('StoryArc', storyline)
    
    if issue: _set_or_update('Number', issue)
    if volume: _set_or_update('Volume', volume)
    
    return render_xml(root)

def inject_cbz(target_file, publisher, ip, storyline, issue="", volume=""):
    temp_fd, temp_path = tempfile.mkstemp(suffix='.cbz')
    os.close(temp_fd)
    
    existing_xml = None
    
    try:
        with zipfile.ZipFile(target_file, 'r') as zf_in:
            if 'ComicInfo.xml' in zf_in.namelist():
                existing_xml = zf_in.read('ComicInfo.xml')
            elif 'comicinfo.xml' in [name.lower() for name in zf_in.namelist()]:
                real_name = next(name for name in zf_in.namelist() if name.lower() == 'comicinfo.xml')
                existing_xml = zf_in.read(real_name)
                
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                for item in zf_in.infolist():
                    if item.filename.lower() != 'comicinfo.xml':
                        zf_out.writestr(item, zf_in.read(item.filename))
                
                new_xml = build_comic_info(publisher, ip, storyline, issue, volume, existing_xml)
                zf_out.writestr('ComicInfo.xml', new_xml)
                
        shutil.move(temp_path, target_file)
        return target_file
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise RuntimeError(f"Injection Failed: {e}")

def convert_cbr_to_cbz_and_inject(target_file, publisher, ip, storyline, issue="", volume=""):
    new_target_file = target_file[:-4] + ".cbz"
    existing_xml_bytes = None
    
    try:
        with tempfile.TemporaryDirectory() as extract_dir:
            dest_path = os.path.join(extract_dir, "")  
            try:
                res = subprocess.run(['unar', '-f', '-D', '-o', extract_dir, target_file], capture_output=True, text=True)
                if res.returncode != 0:
                    from utils import handle_failure
                    handle_failure(f"Native unar failed with code {res.returncode}", context=f"Extracting {os.path.basename(target_file)}")
                    return target_file
            except FileNotFoundError:
                from utils import handle_failure
                handle_failure("Missing the 'unar' binary. Run: brew install unar", context="CBR file format conversion")
                return target_file
                
            xml_path = None
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.lower() == 'comicinfo.xml':
                        xml_path = os.path.join(root, f)
                        break
                if xml_path: break
                
            if xml_path:
                with open(xml_path, 'rb') as xf:
                    existing_xml_bytes = xf.read()
                os.remove(xml_path) 
                
            new_xml = build_comic_info(publisher, ip, storyline, issue, volume, existing_xml_bytes)
            
            with open(os.path.join(extract_dir, 'ComicInfo.xml'), 'wb') as xf:
                if isinstance(new_xml, str):
                    xf.write(new_xml.encode('utf-8'))
                else:
                    xf.write(new_xml)
                
            temp_fd, temp_path = tempfile.mkstemp(suffix='.cbz')
            os.close(temp_fd)
            
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, extract_dir)
                        zf_out.write(full_path, arcname=rel_path)
                        
        os.remove(target_file)
        shutil.move(temp_path, new_target_file)
        print(f"  [->] Converted successfully to {os.path.basename(new_target_file)}")
        return new_target_file
    except Exception as e:
        from utils import handle_failure
        handle_failure(str(e), context=f"Converting and Injecting {os.path.basename(target_file)}")
        return target_file

def inject_metadata_into_archive(target_file, publisher, ip, storyline, issue="", volume=""):
    if target_file.lower().endswith('.cbz'):
        return inject_cbz(target_file, publisher, ip, storyline, issue, volume)
    elif target_file.lower().endswith('.cbr'):
        print(f"  [cbr] Converting proprietary file to standard .cbz...")
        return convert_cbr_to_cbz_and_inject(target_file, publisher, ip, storyline, issue, volume)
    return target_file
