#!/usr/bin/env bash

# Ensure you are executing from the script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Automatically create or activate virtual environment
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment for the first time..."
    python3 -m venv venv
    source venv/bin/activate
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
else
    source venv/bin/activate
fi

# Run the interactive desktop GUI application
echo "Starting Comic Sorter Desktop GUI..."
python app.py
