#!/usr/bin/env bash
# Put the TV back the way the newest snapshot in my-tv/backup/ found it: re-enables what was enabled then
# and hands Home back to the stock launcher. Same as: python3 my-tv/setup_tv.py restore [snapshot folder]
#
# Usage: TV_HOST=192.168.1.50 my-tv/restore-all.sh [my-tv/backup/<snapshot folder>]
exec python3 "$(dirname "$0")/setup_tv.py" restore "$@"
