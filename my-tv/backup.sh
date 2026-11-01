#!/usr/bin/env bash
# Snapshot of the TV before anything changes (packages, disabled list, settings, build, Home owner).
# Nothing on the TV is changed. Same as: python3 my-tv/setup_tv.py backup
#
# Usage: TV_HOST=192.168.1.50 my-tv/backup.sh
exec python3 "$(dirname "$0")/setup_tv.py" backup "$@"
