#!/usr/bin/env python3
"""
build_dmg.py — Build script for Comic Sorter macOS distribution.

Usage:
    python build_dmg.py

What this does:
    1. Runs PyInstaller to produce dist/Comic Sorter.app
    2. Ad-hoc code-signs the .app so Gatekeeper does not quarantine it
       on the machine it was built on. Other machines will still see the
       "unidentified developer" prompt on first launch (right-click > Open).
    3. Uses create-dmg to wrap the .app in a drag-to-install DMG.

Requirements:
    pip install pyinstaller
    brew install create-dmg

Output:
    dist/Comic Sorter.dmg
"""

import os
import sys
import shutil
import subprocess

# ---------------------------------------------------------------------------
# Configuration — edit these if needed
# ---------------------------------------------------------------------------
APP_NAME        = "Comic Sorter"
BUNDLE_ID       = "com.gts.comicsorter"
VERSION         = "1.1.0"
SPEC_FILE       = "Comic Sorter.spec"
DIST_DIR        = "dist"
BUILD_DIR       = "build"
APP_PATH        = os.path.join(DIST_DIR, f"{APP_NAME}.app")
DMG_PATH        = os.path.join(DIST_DIR, f"{APP_NAME}.dmg")
ICON_PATH       = "icon.icns"
DMG_WINDOW_W    = 600
DMG_WINDOW_H    = 400
DMG_ICON_SIZE   = 128
# ---------------------------------------------------------------------------


def run(cmd, **kwargs):
    print(f"\n[>] {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"[!] Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result


def find_tool(name):
    """Find a tool on PATH or in common Homebrew locations."""
    found = shutil.which(name)
    if found:
        return found
    for prefix in ["/opt/homebrew/bin", "/usr/local/bin"]:
        candidate = os.path.join(prefix, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def check_tool(name, install_hint):
    if not find_tool(name):
        print(f"[!] Required tool '{name}' not found.")
        print(f"    Install with: {install_hint}")
        sys.exit(1)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # ------------------------------------------------------------------
    # Pre-flight checks
    # ------------------------------------------------------------------
    check_tool("pyinstaller", "pip install pyinstaller")
    check_tool("create-dmg",  "brew install create-dmg")
    check_tool("codesign",    "Install Xcode Command Line Tools: xcode-select --install")

    # ------------------------------------------------------------------
    # Clean previous build artefacts
    # ------------------------------------------------------------------
    for stale in [APP_PATH, DMG_PATH]:
        if os.path.exists(stale):
            print(f"[>] Removing stale: {stale}")
            if os.path.isdir(stale):
                shutil.rmtree(stale)
            else:
                os.remove(stale)

    # ------------------------------------------------------------------
    # Step 1: PyInstaller
    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print("  Step 1 of 3 — Building .app with PyInstaller")
    print("="*60)
    run([find_tool("pyinstaller"), "--noconfirm", "--clean", SPEC_FILE])

    if not os.path.exists(APP_PATH):
        print(f"[!] PyInstaller did not produce {APP_PATH}. Check the output above.")
        sys.exit(1)

    print(f"[OK] .app built: {APP_PATH}")

    # ------------------------------------------------------------------
    # Step 2: Ad-hoc code sign
    # Ad-hoc signing (-) avoids requiring a paid Apple Developer cert.
    # The app will still trigger Gatekeeper on OTHER machines
    # (right-click > Open bypasses it). On THIS machine it runs cleanly.
    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print("  Step 2 of 3 — Ad-hoc code signing")
    print("="*60)
    run([
        find_tool("codesign"),
        "--force",
        "--deep",
        "--sign", "-",   # "-" means ad-hoc (no Developer ID required)
        APP_PATH,
    ])
    print(f"[OK] Ad-hoc signed: {APP_PATH}")

    # ------------------------------------------------------------------
    # Step 3: create-dmg
    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print("  Step 3 of 3 — Creating DMG")
    print("="*60)

    run([
        find_tool("create-dmg"),
        "--volname",            f"{APP_NAME}",
        "--volicon",            ICON_PATH,
        "--window-size",        str(DMG_WINDOW_W), str(DMG_WINDOW_H),
        "--icon-size",          str(DMG_ICON_SIZE),
        "--icon",               f"{APP_NAME}.app", "160", "185",
        "--hide-extension",     f"{APP_NAME}.app",
        "--app-drop-link",      "430", "185",
        "--no-internet-enable",
        DMG_PATH,
        APP_PATH,
    ])

    print("\n" + "="*60)
    dmg_size = os.path.getsize(DMG_PATH) // (1024 * 1024)
    print(f"  Done! DMG written to: {DMG_PATH} ({dmg_size} MB)")
    print("="*60)
    print()
    print("  To install: open the DMG and drag Comic Sorter into Applications.")
    print()
    print("  User config files (config.json, rules.json) are stored at:")
    print("  ~/Library/Application Support/Comic Sorter/")
    print("  Open that folder in Finder to edit them.")
    print("="*60)


if __name__ == "__main__":
    main()
