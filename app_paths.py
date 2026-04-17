"""
app_paths.py — Central path resolver for Comic Sorter.

When running as a PyInstaller .app bundle, the source files live inside a
read-only directory inside the .app. All user-editable files (config.json,
rules.json, comicvine_cache.json) are stored in:

    ~/Library/Application Support/Comic Sorter/

This makes them easy to find in Finder and safe to edit with a text editor.
To open that folder: Finder > Go > Go to Folder > paste the path above.

When running from source (development), the same files are read from the
project root directory as before, so nothing changes for development.
"""

import os
import sys
import shutil

# -----------------------------------------------------------------------
# Detect bundle vs. dev mode
# -----------------------------------------------------------------------
_FROZEN = getattr(sys, "frozen", False)

# Root of bundled resources (read-only inside .app)
if _FROZEN:
    _BUNDLE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

# User-writable data directory
if _FROZEN:
    _USER_DATA_DIR = os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", "Comic Sorter"
    )
else:
    _USER_DATA_DIR = _BUNDLE_DIR

os.makedirs(_USER_DATA_DIR, exist_ok=True)


def bundle_resource(filename: str) -> str:
    """Absolute path to a read-only bundled resource (e.g. default rule files)."""
    return os.path.join(_BUNDLE_DIR, filename)


def user_data(filename: str) -> str:
    """
    Absolute path to a user-editable file in Application Support.

    If the file does not exist yet and a bundled default exists, the default
    is copied there automatically so the user starts with sensible defaults.
    """
    dest = os.path.join(_USER_DATA_DIR, filename)
    if not os.path.exists(dest):
        src = os.path.join(_BUNDLE_DIR, filename)
        if os.path.exists(src):
            shutil.copy2(src, dest)
    return dest


def user_data_dir() -> str:
    """The Application Support folder itself — open this in Finder to edit configs."""
    return _USER_DATA_DIR
