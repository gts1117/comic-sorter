#!/usr/bin/env bash

# Ensure you are executing from the script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Automatically create or activate virtual environment
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment for the first time..."
    if command -v /opt/homebrew/bin/python3.11 &> /dev/null; then
        PY_BIN="/opt/homebrew/bin/python3.11"
    elif command -v /opt/homebrew/bin/python3.10 &> /dev/null; then
        PY_BIN="/opt/homebrew/bin/python3.10"
    else
        PY_BIN="python3"
    fi
    $PY_BIN -m venv venv
    source venv/bin/activate
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
else
    source venv/bin/activate
fi

# Clear screen for reading
clear

# Run the interactive startup sequence
echo "Starting Comic Sorter CLI Mode..."
python main.py
