import os
import plistlib
import stat
import shutil
import sys

APP_NAME = "Comic Sorter.app"
CONTENTS_DIR = os.path.join(APP_NAME, "Contents")
MACOS_DIR = os.path.join(CONTENTS_DIR, "MacOS")
RES_DIR = os.path.join(CONTENTS_DIR, "Resources")

os.makedirs(MACOS_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

# Copy icon
if os.path.exists("icon.icns"):
    shutil.copy2("icon.icns", os.path.join(RES_DIR, "icon.icns"))

# Create Info.plist
info = {
    "CFBundleExecutable": "launcher",
    "CFBundleIconFile": "icon",
    "CFBundleIdentifier": "com.gts.comicsorter",
    "CFBundleName": "Comic Sorter",
    "CFBundlePackageType": "APPL",
    "CFBundleShortVersionString": "1.0",
    "LSMinimumSystemVersion": "10.10.0",
    "NSHighResolutionCapable": True,
}

with open(os.path.join(CONTENTS_DIR, "Info.plist"), "wb") as f:
    plistlib.dump(info, f)

# Create launcher
launcher_path = os.path.join(MACOS_DIR, "launcher")
with open(launcher_path, "w") as f:
    f.write("#!/bin/bash\n")
    f.write(f'cd "{os.path.abspath(os.getcwd())}"\n')
    f.write(f'{sys.executable} app.py\n')

# Make executable
st = os.stat(launcher_path)
os.chmod(launcher_path, st.st_mode | stat.S_IEXEC)
print(f"Created {APP_NAME} successfully!")
