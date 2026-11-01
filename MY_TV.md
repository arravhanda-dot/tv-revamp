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
   git clone https://github.com/arravhanda-dot/tv-revamp && cd tv-revamp
   ```

3. Start `claude` in that folder and paste [`PROMPT.md`](PROMPT.md) (the part between the `---` lines),
   with your TV model filled in. Add this:

   > Use the `themes/midnight-blue` theme (`tools/theme.sh themes/midnight-blue`). My answers are in
   > MY_TV.md under "My choices". Keep Google Assistant, the Google TV / Ambient screensaver and the
   > photos it currently uses, Chromecast, Play Store, the TV's update service and all HDMI/Live TV
   > services. Replace the theme's screenshot.jpg with a real capture from the TV.

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

## My choices (fill in before you start)

- TV model (Settings → System → About → Model):
- Apps to keep (everything else from TCL/preloads can go):
  - [ ] YouTube   - [ ] Netflix   - [ ] Prime Video   - [ ] Disney+ Hotstar   - [ ] JioCinema
  - [ ] Spotify   - [ ] Apple TV  - [ ] Zee5          - [ ] SonyLIV           - [ ] other:
- Dock (4–7 apps, in order):
- Keep: Google Assistant ✔ · screensaver ✔ · Chromecast ? · firmware updates ? · Live TV / tuner ?
- When the TV turns on, open: Home / Live TV / last HDMI input

## Testing

`python3 -m unittest discover -s tests` runs the repo's checks (2,700+ tests, including the safety rules in
`tools/disable.sh`, theme validation and the launcher config). The real test is on the TV: the prompt makes
Claude press remote keys over ADB and screenshot each step, then reboot and check that every kept app opens,
HDMI and Live TV switch, the Assistant answers and the screensaver starts.

To regenerate the wallpaper: `python3 themes/midnight-blue/make_wallpaper.py` (needs Pillow).
