# Prompt for Claude Code on the laptop

Paste everything below the line into Claude Code running on a laptop on the same Wi-Fi as the TV.
First, on the TV: Settings → Device Preferences → About → press OK on "Build" 7 times, then
Developer options → turn on USB debugging (and Network/Wireless debugging if it is there). Keep the TV on.

---

Turn my TCL Android TV into a clean, ad-free, Apple TV style home screen. Work on the real TV over ADB
from this laptop (same Wi-Fi), step by step, and check every step with screenshots pulled from the TV.

**Setup**
1. Clone my repo and work from it:
   `git clone -b claude/relaxed-babbage-lrexd7 https://github.com/arravhanda-dot/tv-revamp && cd tv-revamp`.
   It is the Clean Your TV toolkit plus my theme. Read `AGENTS.md`, `PROMPT.md` (the part between the
   `---` lines) and `MY_TV.md`, then follow `PROMPT.md` exactly. Use `tools/` and `launcher/` instead of
   writing your own.
2. Set up the Python venv for the tools (`tools/requirements.txt`). The launcher build needs JDK 17 and
   Android SDK platform 34 with build-tools 34.0.0: install them if they are missing, or use
   `tools/docker-build.sh` if Docker is available. On Windows use the `.ps1` twins of the scripts, and Git
   Bash for `my-tv/*.sh`.
3. Find my TV on the network (or ask me for its IP) and connect on port 5555. Tell me exactly when to
   accept "Allow USB debugging?" on the TV.

**My TV**
- TCL "Android TV Pro", Android TV 11, India. Read the exact model and build with `tools/tv.py --probe`.
  No folder in `examples/` matches it yet: use the closest TCL Android TV 11 lists (`tcl-55p638`,
  `tcl-55c815`, `tcl-50p615` and others) as a guide only, and build my list from what is actually installed.

**My answers (treat these checklist questions as already answered)**
- Apps I use, all kept: JioHotstar, YouTube, Netflix, Prime Video, Sony LIV, Zee5.
- Dock, in this order: Netflix, YouTube, Prime Video, JioHotstar, Sony LIV. Every other app goes in the
  grid below, which scrolls up when I press Down.
- Keep: Chromecast, firmware updates, Live TV and the antenna tuner, TCL Channel, Google Assistant, the
  screensaver with the photos it shows now, Play Store and Settings. The full never-disable list is in
  `MY_TV.md`.
- Disable: TCL telemetry and analytics, ad and promo services, recommendation rows, content feeds, and
  preloaded apps I don't use. Ask me about any package whose purpose is unclear.
- When the TV turns on: Home with the dock, not Live TV.
- Don't change any system settings. Only the home screen changes. Skip the Private DNS extra.
- Look: `themes/midnight-blue` (black-to-blue gradient, frosted-glass dock, clock and date top left).

**Order of work**
1. Back up before changing anything: `TV_HOST=<tv ip> my-tv/backup.sh`, plus anything else `PROMPT.md`
   asks for. Note the current screensaver (`settings get secure screensaver_components`) and keep it.
2. Show me the debloat list, then disable it in small batches with `tools/disable.sh`, taking a screenshot
   between batches.
3. Build and install the launcher (`launcher/build-and-install.sh`) and make it Home. Confirm with
   `dumpsys activity activities | grep mFocusedApp`. Then push the theme with
   `tools/theme.sh themes/midnight-blue`. In `dock_apps`, keep only the JioHotstar package name that is
   installed.
4. Reboot, then check: Home comes up with the dock in my order; each of my six apps opens and plays; Live TV
   and HDMI switch from Inputs; TCL Channel opens; the screensaver still shows my photos (don't change its
   timeout). Ask me to press the real remote buttons (Home, Back, Settings, Input, the mic for Assistant,
   and the Netflix/YouTube/Prime buttons) and to cast from my phone. If a button needs a key helper, tell
   me what it costs before turning it on.
5. Replace `themes/midnight-blue/screenshot.jpg` with a real 1280x720 capture with the focus on the dock,
   and no Wi-Fi name visible.
6. Close ADB at the end as `PROMPT.md` says, and give me a short summary: what was disabled, how to undo it
   (`my-tv/restore-all.sh`, `tools/restore.sh`) and how to change the dock order.
7. Commit the theme config, the real screenshot and my TV's list to the branch, then push. Never commit
   backups, the ADB key, or anything showing my network name, IP or account.

Ask me before anything this prompt doesn't cover.
