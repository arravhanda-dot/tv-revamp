# My TCL TV: Apple TV style revamp

This repo is [Clean Your TV](https://github.com/Gathin23/cleanyourtv) (MIT), imported as-is, plus a theme
made for this TV: [`themes/midnight-blue/`](themes/midnight-blue/). Everything here is reversible.

## Do it yourself in three steps (no Claude needed)

You need a Windows PC or a Mac on the same Wi-Fi as the TV, and about 15 minutes.

1. **On the TV:** Settings → Device Preferences → About → press OK on "Build" 7 times. Go back to
   Developer options and turn on **USB debugging** (and **Network debugging** if it is listed).
2. **On the computer:**
   - Install Python from [python.org](https://www.python.org/downloads/). On Windows, tick "Add python.exe to
     PATH" in the installer. Macs ask to install it the first time it is needed.
   - Download this repo: on GitHub, open the `claude/relaxed-babbage-lrexd7` branch → **Code** →
     **Download ZIP**, then unzip it.
   - Put `app-release.apk` (the launcher app, sent separately) into the unzipped `my-tv` folder or leave it
     in Downloads. The repo holds no built apps, by its own rules.
3. **Run it:** double-click `my-tv/setup-tv.bat` (Windows) or `my-tv/setup-tv.command` (Mac), or type
   `python3 my-tv/setup_tv.py` in a terminal. When the TV shows **"Allow USB debugging?"**, tick
   "Always allow" and press OK.

[`my-tv/setup_tv.py`](my-tv/setup_tv.py) then works on its own:

1. finds the TV on your Wi-Fi (or asks for its IP);
2. backs up everything to `my-tv/backup/<date>/`;
3. shows what it will switch off ([`my-tv/tcl-android-tv-pro.txt`](my-tv/tcl-android-tv-pro.txt), filtered to
   what your TV has) and asks once;
4. switches it off in small batches, checking the TV after each;
5. installs the new home screen. The old one is switched off only after the new one has started, and is
   put back if Home doesn't come up;
6. applies the midnight-blue look with your dock;
7. restarts the TV and checks it: Home, every app on the keep list, the screensaver, Assistant, Chromecast,
   Live TV, and that each of your six apps opens. The results go to `report.txt` in the backup folder;
8. offers to switch network debugging off again.

Afterwards, try the remote's mic, Settings and Input buttons and cast from your phone once: a script can't
press real buttons. Problems show as `[!!]` in the report.

### Or let Claude Code do it

If you can run Claude Code on that computer, paste [`my-tv/LOCAL_PROMPT.md`](my-tv/LOCAL_PROMPT.md) instead.
It does the same job and can deal with surprises a script can't.

## Backup and undo

- Every run saves a snapshot to `my-tv/backup/<date>/` before anything changes: every package, the disabled
  list, all settings, build properties and the original Home app. Keep that folder. It stays out of git
  because settings can include your network names.
- Apps are only ever **disabled**, never uninstalled, so the original software stays on the TV.
- To put the TV back exactly as it was, turn USB debugging on again and run `python3 my-tv/setup_tv.py restore`
  (or `my-tv/restore-all.sh`). It re-enables everything that was enabled in the snapshot and hands Home
  back to the stock launcher. The new launcher stays installed but unused; remove it in Settings → Apps
  if you like.
- To undo only one batch, `tools/restore.sh my-tv/backup/<date>/batch-1.txt` also works.

## What you get

- **Home screen:** pitch black fading to deep blue, a large thin clock and date, a frosted-glass dock,
  one glass highlight that springs from tile to tile, the app's name in large type above the dock,
  and glass pill buttons for Inputs, Wi-Fi and Settings.
- **No ads:** the stock Google TV / TCL home screen and its recommendation rows are replaced, and TCL's
  telemetry and ad services are disabled. Optional extra: ad-blocking Private DNS (it doesn't block
  YouTube ads).
- **Nothing important breaks:** the debloat tool (`tools/disable.sh`) refuses lists that touch core
  Android, the TV middleware, the keyboard, remote, Bluetooth, Play Store or Play Services. Anything
  disabled is reversible with `tools/restore.sh`.
- **Screensaver:** the theme leaves the launcher's own clock screensaver off, so the TV's screensaver
  keeps the photos you already use. Don't disable `com.google.android.backdrop` (Ambient mode) or the
  Google TV photo services.
- **Google Assistant:** stays. Keep `com.google.android.katniss` (the Assistant) and TCL's remote and
  voice services, such as `com.tcl.keyhelp` and `com.tcl.tcl_bt_rcu_service` on some models. The
  `examples/tcl-*` folder for your model lists what to keep. Some TCL builds need a key helper so the
  remote's buttons still work after the stock launcher is gone, and on TCL G09 sets that helper stops
  held volume from repeating. The prompt makes Claude ask before it turns the helper on.
- **Screensaver on TCL:** some TCL sets run their screensaver from a TCL package (`dreamx` on several
  models) instead of Ambient mode. Before disabling anything, check which one is set:
  `settings get secure screensaver_components`.

### About "glass"

On a real Apple TV, the frosted look comes from live blur on a strong GPU. Most TCL sets have 1.5–2.5 GB of RAM
and a small GPU, and live blur makes the whole UI stutter. So the launcher draws its glass as translucent
layers with a sheen and a rim, without blur. It looks frosted and stays smooth. If your TV has 2 GB or more,
add `"wallpaper_true_color": true` to the theme for an even smoother gradient.

## My choices

- **TV:** TCL "Android TV Pro", Android TV OS 11 (India). Read the exact model and build off the TV with
  `tools/tv.py --probe` first. No recorded entry matches it yet; the closest are the TCL Android TV 11 sets
  in `examples/` (`tcl-55p638`, `tcl-55c815`, `tcl-50p615` …). Use them as a guide, not a list to apply.
- **Dock, in this order** (already in `themes/midnight-blue/config.json`):
  Netflix → YouTube → Prime Video → JioHotstar → Sony LIV.
  JioHotstar ships as `in.startv.hotstar.dplus.tv` on most TVs and `in.startv.hotstar` on some; both are
  listed and the launcher skips the one that isn't installed. Once on the TV, keep only the installed one.
- **Below the dock:** every other app (Zee5 first among them) in a 5-column grid that scrolls up on Down.
- **Top-left corner:** greeting, clock and date.
- **Power on:** Home with the dock. If the TV boots into Live TV on its own, set `power_on_home`
  (needs `HOME_KEY_SERVICE=1`, see `PROMPT.md`).
- **Settings:** leave every system setting as it is. Only the home screen changes. After the stock
  launcher is off, press the remote's Settings, Input and app buttons and remap any that stop working.
- **No ads:** stock home screen and its promo rows gone, TCL ad/analytics/content-feed services disabled.

### Never disable (on top of what `tools/disable.sh` already protects)

| What | Packages |
|---|---|
| Apps I use | `com.netflix.ninja`, `com.google.android.youtube.tv`, `com.amazon.amazonvideo.livingroom`, `in.startv.hotstar.dplus.tv` / `in.startv.hotstar`, `com.sonyliv`, `com.graymatrix.did` (Zee5) |
| Chromecast | `com.google.android.apps.mediashell` |
| Firmware updates | `com.tcl.versionUpdateApp`, `com.tcl.rc.ota`, `com.tcl.ttvs` (holds the updater on some TCL builds) |
| Live TV / antenna | `com.tcl.tv`, `com.tcl.tvinput`, `com.mediatek.*` TV services, `com.cltv.mal` |
| TCL Channel | `com.tcl.channelplus`, `com.tcl.tv.tclchannel`, `com.tcl.waterfall.overseas` if it is what the TCL Channel button opens |
| Google Assistant | `com.google.android.katniss` and TCL's remote/voice services |
| Screensaver | `com.google.android.apps.tv.dreamx`, `com.google.android.backdrop`; check `settings get secure screensaver_components` and keep whatever it names |
| Settings | `com.android.tv.settings`, `com.tcl.settings` |

Two of these choices pull against "no ads", and both are kept as asked:
- **TCL Channel** is free, ad-supported live channels. Its streams carry their own ads.
- **The screensaver** can mix in Google promos. To turn them off: Settings → System → Ambient mode,
  then switch off anything that isn't your photos.

## Testing

- `python3 -m unittest discover -s tests` runs the repo's 2,764 checks. That includes the safety rules in
  `tools/disable.sh`, the theme, and `tests/test_my_tv_setup.py`, which runs `setup_tv.py` against a
  simulated TCL Android TV 11. Those 21 tests cover the backup coming first, the batches, the stops when a
  step fails, the dock order, the checks and the restore.
- `setup_tv.py` was also run through the repo's real `disable.sh`, `build-and-install.sh` and `theme.sh`
  against a simulated TV, and all three succeeded. The Windows (PowerShell) path has not been run.
- The launcher was built from source with its 308 unit tests and lint passing. The release APK is
  587,065 bytes, under the 576 KB size limit.
- Not yet tried on this TV. The first real run is the real test, and the report says what passed.

To regenerate the wallpaper: `python3 themes/midnight-blue/make_wallpaper.py` (needs Pillow).
