#!/bin/bash
# Double-click in Finder to set up the TV (macOS). The first run may ask to install Python's command line
# tools and to let Terminal find devices on the local network: allow both.
cd "$(dirname "$0")/.." || exit 1
python3 my-tv/setup_tv.py "$@"
echo
read -r -p "Press Enter to close this window."
