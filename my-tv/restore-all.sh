#!/usr/bin/env bash
# Puts the TV back to the snapshot my-tv/backup.sh took: re-enables every package that is disabled now
# but was enabled then, hands Home back to the app that owned it, and removes the Clean Your TV launcher.
# Packages are only ever disabled, never uninstalled, so nothing needs reinstalling.
#
# Usage: TV_HOST=192.168.1.50 my-tv/restore-all.sh [my-tv/backup/<snapshot folder>]
#        (the newest snapshot by default)
set -euo pipefail
cd "$(dirname "$0")/.."
: "${TV_HOST:?set TV_HOST to the IP address of the TV}"
PY=tools/venv/bin/python
[ -x "$PY" ] || PY=python3
SNAP="${1:-$(ls -d my-tv/backup/*/ 2>/dev/null | sort | tail -n 1)}"
SNAP="${SNAP%/}"
if [ -z "$SNAP" ] || [ ! -f "$SNAP/packages-disabled.txt" ]; then
  echo "no snapshot found: run my-tv/backup.sh before changing the TV" >&2
  exit 2
fi
echo "restoring from $SNAP"

now=$(mktemp)
"$PY" tools/tv.py 'pm list packages -d' | sed 's/^package://' | tr -d '\r' | sort > "$now"
was=$(mktemp)
sed 's/^package://' "$SNAP/packages-disabled.txt" | tr -d '\r' | sort > "$was"

# Disabled now, enabled in the snapshot: turn each back on, one shell call per package.
comm -23 "$now" "$was" | while read -r pkg; do
  [ -n "$pkg" ] || continue
  echo "enable $pkg"
  "$PY" tools/tv.py "pm enable --user 0 $pkg" || echo "  could not enable $pkg" >&2
done

# Home back to the component that owned it.
home=$(tr -d '\r' < "$SNAP/home.txt" | grep '/' | tail -n 1 || true)
if [ -n "$home" ]; then
  echo "Home -> $home"
  "$PY" tools/tv.py "cmd package set-home-activity $home" || true
fi

# The Clean Your TV launcher goes last, once the stock Home is back.
"$PY" tools/tv.py 'pm uninstall com.gathin.tvhome' || true

"$PY" tools/tv.py 'sync'
echo "done; reboot the TV (tools/tv.py --reboot) and check that the stock home screen comes up"
rm -f "$now" "$was"
