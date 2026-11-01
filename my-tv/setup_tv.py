#!/usr/bin/env python3
"""One command that does the whole TV job, with no coding assistant needed.

    python3 my-tv/setup_tv.py              find the TV, back it up, debloat, install the new Home, theme, verify
    python3 my-tv/setup_tv.py backup       only take a snapshot of the TV
    python3 my-tv/setup_tv.py verify       only run the checks again
    python3 my-tv/setup_tv.py restore      put the TV back the way the newest snapshot found it
    python3 my-tv/setup_tv.py check-closed check that network debugging is off (port 5555 refuses)

Options: --host <tv ip> (otherwise TV_HOST, otherwise the local network is searched), --yes (don't ask).
On Windows, use `py` instead of `python3`.

It drives the repo's own tools, so their safety checks stay in force: tools/tv.py for every command,
tools/disable.sh (or .ps1) for the debloat, launcher/build-and-install.sh (or .ps1) for the Home handover
with its rollback, tools/theme.sh (or .ps1) for the theme. Packages are disabled, never uninstalled.
Everything it does is recorded under my-tv/backup/<date>/, which `restore` reads.
"""
import argparse
import concurrent.futures
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MYTV = ROOT / "my-tv"
BACKUPS = MYTV / "backup"
LIST = MYTV / "tcl-android-tv-pro.txt"
THEME = ROOT / "themes" / "midnight-blue"
APK = ROOT / "launcher" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
WINDOWS = os.name == "nt"
LAUNCHER = "com.gathin.tvhome"
SETUPWRAITH = "com.google.android.tungsten.setupwraith"

# The owner's apps, in dock order (Zee5 goes in the grid). The first installed name wins.
MY_APPS = [
    ("Netflix", ["com.netflix.ninja"]),
    ("YouTube", ["com.google.android.youtube.tv"]),
    ("Prime Video", ["com.amazon.amazonvideo.livingroom"]),
    ("JioHotstar", ["in.startv.hotstar.dplus.tv", "in.startv.hotstar"]),
    ("Sony LIV", ["com.sonyliv"]),
    ("Zee5", ["com.graymatrix.did"]),
]
DOCK_COUNT = 5

# Never disabled, whatever a list says: the owner's choices and what the TV needs to work.
KEEP = {pkg for _, pkgs in MY_APPS for pkg in pkgs} | {
    "com.google.android.apps.mediashell",                      # Chromecast
    "com.tcl.versionUpdateApp", "com.tcl.rc.ota", "com.tcl.ttvs", "com.tcl.UpdatePeripheral",  # updates
    "com.tcl.tv", "com.tcl.tvinput", "com.mediatek.tis", "com.mediatek.tv.service",            # Live TV
    "com.mediatek.tv.agent", "com.cltv.mal", "com.tvos",
    "com.tcl.channelplus", "com.tcl.tv.tclchannel", "com.tcl.waterfall.overseas", "com.tcl.tv.plus",  # TCL Channel
    "com.google.android.katniss", "com.google.android.tv.assistant", "com.tcl.assistant",       # Assistant
    "com.tcl.micmanager", "com.google.android.tv.remote.service",
    "com.google.android.apps.tv.dreamx", "com.google.android.backdrop",                       # screensaver
    "com.android.tv.settings", "com.tcl.settings", "com.tcl.dashboard",                         # Settings
    "com.tcl.keyhelp", "com.tcl.autopair", "com.tcl.tcl_bt_rcu_service", "com.tcl.suspension",  # remote
    "com.tcl.system.server", "com.tcl.providers.config", "com.tcl.initsetup",
    "com.android.vending", "com.google.android.gms", "com.google.android.gsf",                  # Play
    LAUNCHER,
}


class TvError(Exception):
    pass


def say(text=""):
    print(text, flush=True)


def ask(question, assume_yes):
    if assume_yes:
        say(question + " yes")
        return True
    try:
        answer = input(question + " [Y/n] ").strip().lower()
    except EOFError:
        return False
    return answer in ("", "y", "yes")


def venv_python():
    return ROOT / "tools" / "venv" / ("Scripts/python.exe" if WINDOWS else "bin/python")


def ensure_venv():
    """tools/venv with tools/requirements.txt: what every tool in the repo runs on."""
    py = venv_python()
    if py.exists():
        return py
    say("Setting up the tools (one time, about a minute)...")
    subprocess.run([sys.executable, "-m", "venv", str(ROOT / "tools" / "venv")], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "-q", "-r", str(ROOT / "tools" / "requirements.txt")],
                   check=True)
    return py


class Tv:
    """tools/tv.py, one shell command per call (chained pm commands can stop after the first)."""

    def __init__(self, host, py):
        self.host = host
        self.py = str(py)
        self.env = dict(os.environ, TV_HOST=host)

    def _tvpy(self, args, timeout=240):
        try:
            return subprocess.run([self.py, "-I", str(ROOT / "tools" / "tv.py")] + args, env=self.env,
                                  capture_output=True, text=True, errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TvError("the TV did not answer in time")

    def run(self, command, timeout=240):
        result = self._tvpy([command], timeout)
        if result.returncode != 0:
            raise TvError((result.stderr or result.stdout).strip() or "tv.py exit %d" % result.returncode)
        return result.stdout.replace("\r", "")

    def probe(self):
        result = self._tvpy(["--probe"], timeout=150)
        return result.returncode == 0, (result.stdout + result.stderr).strip()

    def screenshot(self, path, *keys):
        result = self._tvpy(["--screenshot", str(path)] + list(keys), timeout=120)
        return result.returncode == 0

    def reboot(self):
        self._tvpy(["--reboot"], timeout=60)


class Tools:
    """The repo's scripts: the .sh versions on macOS and Linux, the PowerShell twins on Windows."""

    def __init__(self, host):
        self.host = host
        self.env = dict(os.environ, TV_HOST=host)

    def _run(self, posix, windows, cwd=ROOT, extra_env=None):
        env = dict(self.env, **(extra_env or {}))
        if WINDOWS:
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"] + windows
        else:
            cmd = ["bash"] + posix
        say("  $ " + " ".join(cmd))
        return subprocess.run(cmd, cwd=str(cwd), env=env).returncode

    def disable(self, list_path):
        return self._run([str(ROOT / "tools" / "disable.sh"), str(list_path)],
                         [str(ROOT / "tools" / "disable.ps1"), "-TvHost", self.host, str(list_path)])

    def install_launcher(self):
        return self._run([str(ROOT / "launcher" / "build-and-install.sh")],
                         [str(ROOT / "launcher" / "build-and-install.ps1"), "-TvHost", self.host],
                         cwd=ROOT / "launcher", extra_env={"SKIP_BUILD": "1"})

    def theme(self, folder):
        return self._run([str(ROOT / "tools" / "theme.sh"), str(folder)],
                         [str(ROOT / "tools" / "theme.ps1"), "-TvHost", self.host, str(folder)])

    def adb_closed(self, py):
        return subprocess.run([str(py), "-I", str(ROOT / "tools" / "adb-closed.py"), self.host]).returncode


# ---------------------------------------------------------------- reading what the TV says

def parse_packages(text):
    """Package names from `pm list packages` output, with or without -f / -U."""
    names = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("package:"):
            continue
        word = line[len("package:"):].split()[0] if line[len("package:"):].split() else ""
        names.add(word.rsplit("=", 1)[-1])
    names.discard("")
    return names


def read_list(path):
    """(package, reason) for every package line of a debloat list."""
    items = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^\s*([A-Za-z][\w]*(?:\.[\w]+)+)\s*(?:#\s*(.*))?$", line)
        if m:
            items.append((m.group(1), (m.group(2) or "").strip()))
    return items


def component_packages(value):
    """Packages named in a component list such as screensaver_components or an IME id."""
    value = (value or "").strip()
    if value in ("", "null"):
        return set()
    return {part.split("/")[0].strip() for part in re.split(r"[,:]", value) if "/" in part}


def resumed_packages(tv):
    out = tv.run("dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity|mFocusedApp'")
    return set(re.findall(r"\s([A-Za-z][\w]*(?:\.[\w]+)+)/", out))


def installed_app(installed, candidates):
    for pkg in candidates:
        if pkg in installed:
            return pkg
    return None


# ---------------------------------------------------------------- backup and restore

def backup(tv, snap):
    """Everything needed to put the TV back. Nothing on the TV changes."""
    snap.mkdir(parents=True, exist_ok=True)
    files = [
        ("getprop", "getprop.txt"),
        ("pm list packages -f -U", "packages-all.txt"),
        ("pm list packages -d", "packages-disabled.txt"),
        ("pm list packages -e", "packages-enabled.txt"),
        ("pm list packages -3", "packages-third-party.txt"),
        ("settings list system", "settings-system.txt"),
        ("settings list secure", "settings-secure.txt"),
        ("settings list global", "settings-global.txt"),
        ("cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME",
         "home.txt"),
        ("cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME",
         "home-candidates.txt"),
        ("wm size", "display-size.txt"),
        ("wm density", "display-density.txt"),
    ]
    for command, name in files:
        (snap / name).write_text(tv.run(command), encoding="utf-8")
        say("  saved %s" % name)
    state = {
        "home": stock_home(tv.run(files[8][0])),
        "screensaver": tv.run("settings get secure screensaver_components").strip(),
        "disabled": sorted(parse_packages((snap / "packages-disabled.txt").read_text(encoding="utf-8"))),
    }
    (snap / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def stock_home(resolve_output):
    lines = [l.strip() for l in resolve_output.splitlines() if "/" in l]
    return lines[-1] if lines else ""


def newest_snapshot():
    snaps = sorted(p for p in BACKUPS.glob("*") if (p / "state.json").exists())
    return snaps[-1] if snaps else None


def restore(tv, snap):
    """Re-enable what the snapshot had enabled and give Home back to the stock launcher."""
    state = json.loads((snap / "state.json").read_text(encoding="utf-8"))
    was_disabled = set(state["disabled"])
    now_disabled = parse_packages(tv.run("pm list packages -d"))
    failed = []
    for pkg in sorted(now_disabled - was_disabled):
        say("  enable %s" % pkg)
        out = tv.run("pm enable --user 0 %s" % pkg)
        if "enabled" not in out.lower() or "error" in out.lower():
            failed.append(pkg)
    if state.get("home"):
        say("  Home -> %s" % state["home"])
        tv.run("cmd package set-home-activity --user 0 %s" % state["home"])
    tv.run("sync")
    return failed


# ---------------------------------------------------------------- the plan

def plan(tv, candidates):
    """What to disable on this TV: listed, installed, enabled and not protected. Returns (items, notes)."""
    installed = parse_packages(tv.run("pm list packages"))
    disabled = parse_packages(tv.run("pm list packages -d"))
    protected = set(KEEP)
    protected |= component_packages(tv.run("settings get secure screensaver_components"))
    protected |= component_packages(tv.run("settings get secure default_input_method"))
    protected |= component_packages(tv.run("settings get secure enabled_accessibility_services"))
    wifi_owner = "cname=" + SETUPWRAITH in tv.run("dumpsys wifi")
    items, notes = [], []
    for pkg, reason in candidates:
        if pkg not in installed or pkg in disabled:
            continue
        if pkg in protected:
            notes.append("kept %s: it is in use or on the keep list" % pkg)
        elif pkg == SETUPWRAITH and wifi_owner:
            notes.append("kept %s: it owns the saved Wi-Fi network, and disabling it would delete that network"
                         % pkg)
        else:
            items.append((pkg, reason))
    return items, notes


def write_list(path, items, title):
    lines = ["# %s" % title, "# Written by my-tv/setup_tv.py from my-tv/tcl-android-tv-pro.txt.", ""]
    lines += ["%s%s" % (pkg, "  # " + reason if reason else "") for pkg, reason in items]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def batches(items, size=6):
    return [items[i:i + size] for i in range(0, len(items), size)]


def theme_for_tv(installed, dest):
    """A copy of the theme whose dock names only the JioHotstar package this TV has (if it has one)."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(THEME, dest, ignore=shutil.ignore_patterns("*.py", "screenshot.jpg"))
    config_path = dest / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    dock = []
    for _, pkgs in MY_APPS[:DOCK_COUNT]:
        have = installed_app(installed, pkgs)
        dock += [have] if have else pkgs  # a missing app stays listed: installed later, it joins the dock
    config["dock_apps"] = dock
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return dock


def find_apk():
    """The launcher APK: already built here, or downloaded next to this script or into Downloads."""
    if APK.exists():
        return APK
    places = [MYTV, ROOT, Path.home() / "Downloads", Path.home() / "Desktop"]
    for place in places:
        for pattern in ("tvhome*.apk", "*tvhome*.apk", "app-release*.apk"):
            found = sorted(place.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            if found:
                APK.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(found[0], APK)
                say("  using %s" % found[0])
                return APK
    return None


# ---------------------------------------------------------------- checks

def wait_for_boot(tv, limit=300, step=10):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        time.sleep(step)
        try:
            if tv.run("getprop sys.boot_completed", timeout=30).strip() == "1":
                time.sleep(15)  # let Home and the services settle
                return True
        except TvError:
            pass
    return False


def verify(tv, snap, applied, pause=6):
    """Checks after the reboot. Returns [(ok, label, detail)]."""
    results = []
    state = json.loads((snap / "state.json").read_text(encoding="utf-8"))
    installed = parse_packages(tv.run("pm list packages"))
    disabled = parse_packages(tv.run("pm list packages -d"))

    boot_app = resumed_packages(tv)
    tv.run("input keyevent KEYCODE_HOME")
    time.sleep(3)
    home = resumed_packages(tv)
    results.append((LAUNCHER in home, "Home opens the new home screen", ", ".join(sorted(home)) or "nothing"))
    if "com.tcl.tv" in boot_app and LAUNCHER not in boot_app:
        results.append((False, "Power-on lands on Home",
                        "the TV opened Live TV by itself; see MY_TV.md, 'Power on'"))

    back_on = sorted(pkg for pkg, _ in applied if pkg not in disabled)
    results.append((not back_on, "Disabled packages stayed disabled after reboot",
                    "re-enabled by the firmware: " + ", ".join(back_on) if back_on else "all %d" % len(applied)))

    was_enabled = set(installed) - set(state["disabled"])
    lost = sorted(pkg for pkg in KEEP & was_enabled if pkg in disabled)
    results.append((not lost, "Everything on the keep list is still enabled", ", ".join(lost) or "yes"))

    saver_now = tv.run("settings get secure screensaver_components").strip()
    saver_pkgs = component_packages(saver_now)
    saver_ok = saver_now == state["screensaver"] and not (saver_pkgs & disabled)
    results.append((saver_ok, "Screensaver unchanged and enabled", saver_now or "not set"))

    for pkg, label in (("com.google.android.katniss", "Google Assistant enabled"),
                       ("com.google.android.apps.mediashell", "Chromecast enabled"),
                       ("com.tcl.tv", "Live TV app enabled")):
        if pkg in installed:
            results.append((pkg not in disabled, label, pkg))

    for name, pkgs in MY_APPS:
        pkg = installed_app(installed, pkgs)
        if not pkg:
            results.append((True, "%s opens" % name, "not installed on this TV; install it from Play Store"))
            continue
        tv.run("monkey -p %s -c android.intent.category.LEANBACK_LAUNCHER 1" % pkg)
        opened = False
        for _ in range(4):
            time.sleep(pause / 2 if pause else 0)
            if pkg in resumed_packages(tv):
                opened = True
                break
        results.append((opened, "%s opens" % name, pkg))
        tv.run("input keyevent KEYCODE_HOME")
        time.sleep(2 if pause else 0)
    tv.screenshot(snap / "home-after.png", "HOME")
    return results


def report(snap, results, notes):
    lines = ["Checks:"] + ["  [%s] %s: %s" % ("ok" if ok else "!!", label, detail) for ok, label, detail in results]
    if notes:
        lines += ["", "Notes:"] + ["  - " + n for n in notes]
    text = "\n".join(lines)
    (snap / "report.txt").write_text(text + "\n", encoding="utf-8")
    say(text)
    return all(ok for ok, _, _ in results)


# ---------------------------------------------------------------- finding the TV

def local_networks():
    nets = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # no packet is sent; this only picks the outgoing interface
        nets.add(ipaddress.ip_network(s.getsockname()[0] + "/24", strict=False))
        s.close()
    except OSError:
        pass
    return sorted(nets, key=str)


def port_open(ip, port=5555, timeout=0.6):
    try:
        with socket.create_connection((str(ip), port), timeout=timeout):
            return True
    except OSError:
        return False


def find_host(given, assume_yes):
    if given:
        return given
    if os.environ.get("TV_HOST"):
        return os.environ["TV_HOST"]
    for net in local_networks():
        say("Looking for the TV on %s ..." % net)
        with concurrent.futures.ThreadPoolExecutor(64) as pool:
            hosts = list(net.hosts())
            found = [str(ip) for ip, ok in zip(hosts, pool.map(port_open, hosts)) if ok]
        if len(found) == 1:
            say("Found it at %s" % found[0])
            return found[0]
        if len(found) > 1:
            say("More than one device answers: " + ", ".join(found))
            break
    say("Couldn't find the TV automatically. On the TV: Settings > Network & Internet > your network shows its IP.")
    if assume_yes:
        sys.exit("Run again with --host <tv ip>.")
    return input("Type the TV's IP address: ").strip()


def connect(tv, assume_yes):
    say("")
    say("Look at the TV now. A box 'Allow USB debugging?' appears:")
    say("tick 'Always allow from this computer' and press OK with the remote.")
    for attempt in range(3):
        ok, text = tv.probe()
        if ok:
            say(text)
            return True
        say(text)
        if attempt < 2 and not assume_yes:
            input("Not connected yet. Accept the box on the TV, then press Enter here to try again...")
    return False


def check_tv(tv):
    """Stop early on a TV this job does not fit."""
    sdk = tv.run("getprop ro.build.version.sdk").strip()
    if not sdk.isdigit() or int(sdk) < 26:
        raise TvError("this TV runs SDK %s; the launcher needs 26 (Android 8) or newer" % (sdk or "unknown"))
    if "android.software.leanback" not in tv.run("pm list features"):
        raise TvError("this does not look like an Android TV (no leanback feature)")
    brand = (tv.run("getprop ro.product.brand") + tv.run("getprop ro.product.manufacturer")).lower()
    return "tcl" in brand


# ---------------------------------------------------------------- the whole job

def setup(tv, tools, py, assume_yes, snap):
    if not find_apk():
        say("The launcher app (app-release.apk) is missing. Put the one you were sent into the my-tv folder")
        say("or your Downloads folder and run this again. Nothing on the TV was changed.")
        return False
    say("\n1/7  Backing up the TV to %s" % snap)
    backup(tv, snap)

    say("\n2/7  Working out what to switch off")
    items, notes = plan(tv, read_list(LIST))
    write_list(snap / "applied-list.txt", items, "Disabled on this TV by my-tv/setup_tv.py")
    for pkg, reason in items:
        say("  - %s  %s" % (pkg, reason))
    for note in notes:
        say("  (%s)" % note)
    if items and not ask("Switch these %d off? Nothing is uninstalled, and restore puts them back." % len(items),
                         assume_yes):
        return False

    say("\n3/7  Switching them off in small batches")
    for n, batch in enumerate(batches(items), 1):
        path = snap / ("batch-%d.txt" % n)
        write_list(path, batch, "Batch %d" % n)
        if tools.disable(path) != 0:
            say("The debloat tool stopped (see above). Nothing after batch %d was touched." % n)
            say("To undo: python3 my-tv/setup_tv.py restore")
            return False
        if tv.run("echo alive").strip() != "alive":
            say("The TV stopped answering after batch %d. To undo: python3 my-tv/setup_tv.py restore" % n)
            return False
        tv.screenshot(snap / ("after-batch-%d.png" % n), "HOME")

    say("\n4/7  Installing the new home screen")
    if tools.install_launcher() != 0:
        say("The install stopped; the stock home screen was left in place (see above).")
        return False

    say("\n5/7  Applying the midnight-blue look and your dock")
    installed = parse_packages(tv.run("pm list packages"))
    folder = snap / "midnight-blue"
    dock = theme_for_tv(installed, folder)
    say("  dock: " + ", ".join(dock))
    if tools.theme(folder) != 0:
        say("The theme push stopped (see above). The home screen works; run this again to retry.")
        return False

    say("\n6/7  Restarting the TV (about a minute)")
    tv.run("sync")
    time.sleep(15)  # Android writes package state about ten seconds after a change
    tv.reboot()
    if not wait_for_boot(tv):
        say("The TV did not come back within 5 minutes. Turn it on with the remote, then run:")
        say("  python3 my-tv/setup_tv.py verify")
        return False

    say("\n7/7  Checking everything")
    ok = report(snap, verify(tv, snap, read_list(snap / "applied-list.txt")), notes)
    say("")
    say("Saved: %s (backup, report, screenshots)" % snap)
    return ok


def close_adb(tv, tools, py, assume_yes):
    if not ask("Switch network debugging off now? (Recommended: anyone on your Wi-Fi could control the TV.)",
               assume_yes):
        return
    for command in ("settings put global adb_wifi_enabled 0", "settings put global adb_enabled 0"):
        try:
            tv.run(command, timeout=20)
        except TvError:
            pass  # the connection drops as debugging goes off
    time.sleep(5)
    if tools.adb_closed(py) == 0:
        say("Network debugging is off.")
    else:
        say("Turn the TV off and on with the remote, then run: python3 my-tv/setup_tv.py check-closed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("action", nargs="?", default="setup",
                        choices=["setup", "backup", "verify", "restore", "check-closed"])
    parser.add_argument("snapshot", nargs="?", help="restore/verify: the backup folder (newest by default)")
    parser.add_argument("--host", help="the TV's IP address")
    parser.add_argument("--yes", action="store_true", help="answer yes to every question")
    args = parser.parse_args(argv)

    py = ensure_venv()
    host = find_host(args.host, args.yes)
    tv, tools = Tv(host, py), Tools(host)
    if args.action == "check-closed":
        return tools.adb_closed(py)
    if not connect(tv, args.yes):
        say("Could not connect. Check that USB debugging (and Network debugging, if listed) is on, and that")
        say("this computer is on the same Wi-Fi as the TV. On a Mac, allow Local Network for the Terminal app.")
        return 1
    try:
        if not check_tv(tv) and not ask("This TV doesn't say TCL. Carry on anyway?", args.yes):
            return 1
        stamp = time.strftime("%Y%m%d-%H%M%S")
        if args.action == "backup":
            backup(tv, BACKUPS / stamp)
            say("Backed up to %s" % (BACKUPS / stamp))
            return 0
        snap = Path(args.snapshot) if args.snapshot else newest_snapshot()
        if args.action == "restore":
            if not snap:
                say("No backup found in %s." % BACKUPS)
                return 2
            say("Putting the TV back the way %s found it" % snap)
            failed = restore(tv, snap)
            say("Could not re-enable: " + ", ".join(failed) if failed else "All packages are back.")
            tv.reboot()
            say("The TV is restarting with its original home screen. The new launcher stays installed but")
            say("unused; remove it in Settings > Apps if you like.")
            return 1 if failed else 0
        if args.action == "verify":
            if not snap:
                say("No backup found; run the setup first.")
                return 2
            return 0 if report(snap, verify(tv, snap, read_list(snap / "applied-list.txt")), []) else 1
        ok = setup(tv, tools, py, args.yes, BACKUPS / stamp)
        close_adb(tv, tools, py, args.yes)
        say("\nAll done." if ok else "\nFinished with problems; read the messages above.")
        return 0 if ok else 1
    except TvError as e:
        say("Stopped: %s" % e)
        say("Nothing more was changed. To undo what was done: python3 my-tv/setup_tv.py restore")
        return 1


if __name__ == "__main__":
    sys.exit(main())
