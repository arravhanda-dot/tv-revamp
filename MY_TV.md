# My TCL TV: Apple TV style revamp

This repo is [Clean Your TV](https://github.com/Gathin23/cleanyourtv) (MIT), imported as-is, plus a theme
made for this TV: [`themes/midnight-blue/`](themes/midnight-blue/). Everything here is reversible.

## Why this can't run from a cloud session

The TV is controlled over ADB on your home Wi-Fi. A Claude Code session on claude.ai/code runs in a
cloud container that cannot see your home network, so the work on the TV itself has to run from
**Claude Code on a computer on the same Wi-Fi as the TV** (Mac, Windows or Linux).

## What to run at home

1. On the TV: Settings → System → About → press OK on "Build" (or "Android TV OS build") 7 times.
   Then go to Developer options and turn on USB debugging, plus Network/Wireless debugging if your TV has it.
2. On the computer:

   ```bash
   git clone -b claude/relaxed-babbage-lrexd7 https://github.com/arravhanda-dot/tv-revamp && cd tv-revamp
   ```

3. Start `claude` and paste the prompt in [`my-tv/LOCAL_PROMPT.md`](my-tv/LOCAL_PROMPT.md) (everything below
   its line). It holds all my answers, so the session only asks about what it finds on the TV.

## Backup and undo

- `my-tv/backup.sh` saves a snapshot to `my-tv/backup/<date>/` on the computer before anything changes: every
  package, the disabled list, all settings, build properties, the original Home app and a screenshot.
  Keep that folder. It stays out of git because settings can include your network names.
- Apps are only ever **disabled**, never uninstalled, so the original software stays on the TV.
- To put the TV back exactly as it was: `TV_HOST=<tv ip> my-tv/restore-all.sh`. It re-enables everything
  that was enabled in the snapshot, hands Home back to the TCL launcher and removes the new launcher.
- To undo only the debloat list, `tools/restore.sh <list>` also works.

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

`python3 -m unittest discover -s tests` runs the repo's checks (2,700+ tests, including the safety rules in
`tools/disable.sh`, theme validation and the launcher config). The real test is on the TV: the prompt makes
Claude press remote keys over ADB and screenshot each step, then reboot and check that every kept app opens,
HDMI and Live TV switch, the Assistant answers and the screensaver starts.

To regenerate the wallpaper: `python3 themes/midnight-blue/make_wallpaper.py` (needs Pillow).
