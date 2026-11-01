#!/usr/bin/env bash
# Snapshot of the TV before anything changes: every package, which ones are disabled, all settings,
# the build properties, the app that owns Home and a screenshot of the stock home screen.
# Nothing on the TV is changed. my-tv/restore-all.sh reads the newest snapshot to put the TV back.
#
# Usage: TV_HOST=192.168.1.50 my-tv/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${TV_HOST:?set TV_HOST to the IP address of the TV}"
PY=tools/venv/bin/python
[ -x "$PY" ] || PY=python3
OUT="my-tv/backup/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

run() {  # one shell call per command: chained pm commands can stop after the first on some firmware
  "$PY" tools/tv.py "$1" > "$OUT/$2"
  echo "saved $OUT/$2 ($(wc -l < "$OUT/$2") lines)"
}

run 'getprop' getprop.txt
run 'pm list packages -f -U' packages-all.txt
run 'pm list packages -d' packages-disabled.txt
run 'pm list packages -e' packages-enabled.txt
run 'pm list packages -3' packages-third-party.txt
run 'settings list system' settings-system.txt
run 'settings list secure' settings-secure.txt
run 'settings list global' settings-global.txt
run 'cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME' home.txt
run 'cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME' home-candidates.txt
run 'wm size' display-size.txt
run 'wm density' display-density.txt
"$PY" tools/tv.py --screenshot "$OUT/home-before.png" HOME || echo "no screenshot (Live TV and some apps capture empty)"

grep -c '^package:' "$OUT/packages-all.txt" | xargs -I{} echo "backed up {} packages to $OUT"
