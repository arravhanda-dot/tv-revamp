"""my-tv/setup_tv.py against a simulated TCL Android TV 11: the whole job, the stops and the restore.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_tv", ROOT / "my-tv" / "setup_tv.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

STOCK = "com.google.android.apps.tv.launcherx/com.google.android.apps.tv.launcherx.home.HomeActivity"
SAVER = "com.google.android.apps.tv.dreamx/.service.Backdrop"
IME = "com.tcl.inputmethod.international/.InputMethodService"


class FakeTv:
    """A TV that keeps the state the script changes. Installed packages: a TCL Android TV 11 set."""

    def __init__(self, extra=(), already_disabled=(), wifi_owner="", broken_apps=(), reenable_on_boot=()):
        pkgs = [
            "android", "com.android.systemui", "com.android.tv.settings", "com.android.vending",
            "com.google.android.gms", "com.google.android.apps.tv.launcherx", st.SETUPWRAITH,
            "com.google.android.apps.tv.dreamx", "com.google.android.katniss", "com.google.android.apps.mediashell",
            "com.tcl.tv", "com.tcl.tvinput", "com.tcl.settings", "com.tcl.versionUpdateApp", "com.tcl.channelplus",
            "com.tcl.waterfall.overseas", "com.tcl.inputmethod.international", "com.tcl.dashboard",
            "com.tcl.bi", "com.tcl.logkit", "com.tcl.guard", "com.tcl.esticker", "com.tcl.partnercustomizer",
            "com.tcl.tv.tclhome_passive", "com.tcl.overseasappshow", "com.tcl.messagebox", "com.tcl.notereminder",
            "com.tcl.browser", "com.google.android.feedback", "com.google.android.play.games",
            "com.google.android.videos", "com.google.android.youtube.tvmusic",
            "com.netflix.ninja", "com.google.android.youtube.tv", "com.amazon.amazonvideo.livingroom",
            "in.startv.hotstar.dplus.tv", "com.sonyliv", "com.graymatrix.did",
        ] + list(extra)
        self.enabled = {p: p not in already_disabled for p in pkgs}
        self.home = STOCK
        self.saver = SAVER
        self.wifi_owner = wifi_owner
        self.broken = set(broken_apps)
        self.reenable_on_boot = set(reenable_on_boot)
        self.resumed = "com.google.android.apps.tv.launcherx"
        self.commands = []
        self.reboots = 0

    def listing(self, which):
        return "".join("package:%s\n" % p for p, on in sorted(self.enabled.items())
                       if which == "all" or (which == "d") == (not on))

    def run(self, command, timeout=240):
        self.commands.append(command)
        if command.startswith("pm list packages"):
            flag = command.split()[-1]
            return self.listing("d" if flag == "-d" else "e" if flag == "-e" else "all")
        if command == "pm list features":
            return "feature:android.software.leanback\nfeature:android.hardware.hdmi.cec\n"
        if command == "getprop ro.build.version.sdk":
            return "30\n"
        if command == "getprop sys.boot_completed":
            return "1\n"
        if command.startswith("getprop ro.product"):
            return "TCL\n"
        if command == "getprop":
            return "[ro.build.version.sdk]: [30]\n"
        if command == "settings get secure screensaver_components":
            return self.saver + "\n"
        if command == "settings get secure default_input_method":
            return IME + "\n"
        if command == "settings get secure enabled_accessibility_services":
            return "null\n"
        if command.startswith("settings list"):
            return "a=1\n"
        if command == "dumpsys wifi":
            return "Network: cname=%s\n" % self.wifi_owner if self.wifi_owner else "Network: cname=android\n"
        if "resolve-activity" in command:
            return "priority=0 preferredOrder=0\n%s\n" % self.home
        if "query-activities" in command:
            return self.home + "\n"
        if command.startswith("pm enable --user 0 "):
            pkg = command.split()[-1]
            self.enabled[pkg] = True
            return "Package %s new state: enabled\n" % pkg
        if command.startswith("cmd package set-home-activity"):
            self.home = command.split()[-1]
            return "Success\n"
        if command == "input keyevent KEYCODE_HOME":
            self.resumed = self.home.split("/")[0]
            return ""
        if command.startswith("monkey -p "):
            pkg = command.split()[2]
            if pkg not in self.broken:
                self.resumed = pkg
            return "Events injected: 1\n"
        if command.startswith("dumpsys activity activities"):
            return "  mResumedActivity: ActivityRecord{1 u0 %s/.Main t1}\n" % self.resumed
        if command == "echo alive":
            return "alive\n"
        if command.startswith("settings put global adb"):
            return ""
        return ""

    def probe(self):
        return True, "TCL Smart TV, Android 11 (SDK 30)"

    def screenshot(self, path, *keys):
        Path(path).write_bytes(b"png")
        return True

    def reboot(self):
        self.reboots += 1
        for pkg in self.reenable_on_boot:
            self.enabled[pkg] = True
        self.resumed = self.home.split("/")[0]


class FakeTools:
    """The repo's scripts as they act on the TV: disable the list, hand Home over, push the theme."""

    def __init__(self, tv, disable_fails_at=None, launcher_fails=False):
        self.tv = tv
        self.calls = []
        self.disable_fails_at = disable_fails_at
        self.launcher_fails = launcher_fails
        self.theme_config = None

    def disable(self, path):
        self.calls.append(("disable", Path(path).name))
        if self.disable_fails_at and Path(path).name == "batch-%d.txt" % self.disable_fails_at:
            return 1
        for pkg, _ in st.read_list(path):
            self.tv.enabled[pkg] = False
        return 0

    def install_launcher(self):
        self.calls.append(("launcher",))
        if self.launcher_fails:
            return 1
        self.tv.enabled[st.LAUNCHER] = True
        self.tv.enabled["com.google.android.apps.tv.launcherx"] = False
        self.tv.home = st.LAUNCHER + "/.MainActivity"
        return 0

    def theme(self, folder):
        self.calls.append(("theme",))
        self.theme_config = json.loads((Path(folder) / "config.json").read_text())
        return 0

    def adb_closed(self, py):
        return 0


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.snap = self.tmp / "snap"
        patcher = mock.patch.object(st.time, "sleep", lambda s: None)
        patcher.start()
        self.addCleanup(patcher.stop)
        # An APK in place, so find_apk() does not look in the real Downloads folder.
        apk = self.tmp / "app-release.apk"
        apk.write_bytes(b"apk")
        p = mock.patch.object(st, "APK", apk)
        p.start()
        self.addCleanup(p.stop)

    def run_setup(self, tv, tools, yes=True):
        with mock.patch("builtins.print"):
            return st.setup(tv, tools, None, yes, self.snap)


class TheList(unittest.TestCase):
    def test_list_never_names_a_kept_or_core_package(self):
        items = st.read_list(st.LIST)
        self.assertGreater(len(items), 15)
        for pkg, _ in items:
            self.assertNotIn(pkg, st.KEEP, pkg)
            self.assertFalse(pkg.startswith(("com.android.", "com.mediatek.", "com.cltv.")), pkg)
            self.assertNotIn(pkg, ("com.google.android.gms", "com.android.vending", "com.tcl.tv"), pkg)

    def test_keep_list_covers_the_owners_choices(self):
        for pkg in ("com.google.android.apps.mediashell", "com.tcl.versionUpdateApp", "com.tcl.tv",
                    "com.tcl.channelplus", "com.google.android.katniss", "com.google.android.apps.tv.dreamx",
                    "com.android.tv.settings", "com.graymatrix.did", "com.sonyliv", "in.startv.hotstar"):
            self.assertIn(pkg, st.KEEP)

    def test_the_repo_tools_accept_the_list(self):
        # tools/disable.sh refuses a list with anything but bare package names and comments (#165).
        for line in st.LIST.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                self.assertRegex(line.split("#")[0].strip(), r"^[A-Za-z][\w]*(\.[\w]+)+$")


class Parsing(unittest.TestCase):
    def test_package_lines_with_paths_and_uids(self):
        text = ("package:/system/app/A/A.apk=com.a uid:1000\r\npackage:com.b\n"
                "package:/data/app/x==/base.apk=com.c uid:10123\nnot a package\n")
        self.assertEqual(st.parse_packages(text), {"com.a", "com.b", "com.c"})

    def test_component_lists(self):
        self.assertEqual(st.component_packages("a.b/.X,c.d/e.F"), {"a.b", "c.d"})
        self.assertEqual(st.component_packages("null"), set())
        self.assertEqual(st.component_packages("x.y/.S:z.w/.T"), {"x.y", "z.w"})


class Plan(Base):
    def test_only_installed_enabled_unprotected_packages(self):
        tv = FakeTv(already_disabled={"com.tcl.bi"})
        candidates = [("com.tcl.bi", ""), ("com.tcl.logkit", "logs"), ("com.not.installed", ""),
                      ("com.tcl.inputmethod.international", "keyboard in use"),
                      ("com.google.android.apps.tv.dreamx", "screensaver in use"), (st.SETUPWRAITH, "")]
        items, notes = st.plan(tv, candidates)
        self.assertEqual([p for p, _ in items], ["com.tcl.logkit", st.SETUPWRAITH])
        self.assertEqual(len(notes), 2)

    def test_setupwraith_stays_when_it_owns_the_wifi(self):
        tv = FakeTv(wifi_owner=st.SETUPWRAITH)
        items, notes = st.plan(tv, [(st.SETUPWRAITH, "")])
        self.assertEqual(items, [])
        self.assertIn("Wi-Fi", notes[0])

    def test_a_screensaver_from_another_package_is_protected(self):
        tv = FakeTv()
        tv.saver = "com.tcl.esticker/.Dream"
        items, _ = st.plan(tv, [("com.tcl.esticker", "")])
        self.assertEqual(items, [])


class WholeJob(Base):
    def test_backs_up_first_then_debloats_then_home_then_theme_and_checks(self):
        tv = FakeTv()
        tools = FakeTools(tv)
        self.assertTrue(self.run_setup(tv, tools))
        # Backup taken before the first change.
        first_change = next(i for i, c in enumerate(tv.commands) if c.startswith(("pm disable", "pm enable")))\
            if any(c.startswith(("pm disable", "pm enable")) for c in tv.commands) else len(tv.commands)
        self.assertTrue((self.snap / "state.json").exists())
        state = json.loads((self.snap / "state.json").read_text())
        self.assertEqual(state["home"], STOCK)
        self.assertEqual(state["screensaver"], SAVER)
        self.assertLessEqual(first_change, len(tv.commands))
        kinds = [c[0] for c in tools.calls]
        self.assertEqual(kinds[-2:], ["launcher", "theme"])
        self.assertTrue(all(k == "disable" for k in kinds[:-2]))
        self.assertGreater(kinds.count("disable"), 1, "small batches, not one big run")
        self.assertEqual(tv.reboots, 1)
        # What the owner asked to keep is still on; the bloat is off.
        for pkg in ("com.tcl.channelplus", "com.tcl.waterfall.overseas", "com.google.android.katniss",
                    "com.google.android.apps.mediashell", "com.tcl.versionUpdateApp", "com.tcl.tv",
                    "com.google.android.apps.tv.dreamx", "com.tcl.dashboard", "com.graymatrix.did"):
            self.assertTrue(tv.enabled[pkg], pkg)
        for pkg in ("com.tcl.bi", "com.tcl.esticker", "com.tcl.partnercustomizer", st.SETUPWRAITH):
            self.assertFalse(tv.enabled[pkg], pkg)
        self.assertEqual(tv.home.split("/")[0], st.LAUNCHER)
        self.assertIn("[ok] Home opens the new home screen", (self.snap / "report.txt").read_text())
        self.assertNotIn("[!!]", (self.snap / "report.txt").read_text())
        self.assertFalse(any("uninstall" in c for c in tv.commands))

    def test_dock_is_in_the_owners_order_with_the_installed_hotstar(self):
        tv = FakeTv()
        tools = FakeTools(tv)
        self.run_setup(tv, tools)
        self.assertEqual(tools.theme_config["dock_apps"], [
            "com.netflix.ninja", "com.google.android.youtube.tv", "com.amazon.amazonvideo.livingroom",
            "in.startv.hotstar.dplus.tv", "com.sonyliv"])
        self.assertEqual(tools.theme_config["columns"], 5)
        # The repo's theme itself is untouched.
        repo = json.loads((st.THEME / "config.json").read_text())
        self.assertIn("in.startv.hotstar", repo["dock_apps"])

    def test_a_failed_batch_stops_before_the_launcher(self):
        tv = FakeTv()
        tools = FakeTools(tv, disable_fails_at=2)
        self.assertFalse(self.run_setup(tv, tools))
        self.assertNotIn(("launcher",), tools.calls)
        self.assertEqual(tv.home, STOCK)
        self.assertEqual(tv.reboots, 0)

    def test_a_failed_launcher_install_leaves_the_stock_home(self):
        tv = FakeTv()
        tools = FakeTools(tv, launcher_fails=True)
        self.assertFalse(self.run_setup(tv, tools))
        self.assertNotIn(("theme",), tools.calls)
        self.assertEqual(tv.home, STOCK)

    def test_saying_no_changes_nothing(self):
        tv = FakeTv()
        tools = FakeTools(tv)
        with mock.patch("builtins.input", return_value="n"):
            self.assertFalse(self.run_setup(tv, tools, yes=False))
        self.assertEqual(tools.calls, [])
        self.assertTrue(all(tv.enabled.values()))

    def test_missing_apk_stops_before_anything_changes(self):
        tv = FakeTv()
        tools = FakeTools(tv)
        empty = self.tmp / "empty"
        empty.mkdir()
        with mock.patch.object(st, "APK", empty / "none.apk"), \
                mock.patch.object(st, "MYTV", empty), mock.patch.object(st, "ROOT", empty), \
                mock.patch.object(st.Path, "home", return_value=empty):
            self.assertFalse(self.run_setup(tv, tools))
        self.assertEqual(tools.calls, [])
        self.assertEqual(tv.commands, [])
        self.assertTrue(all(tv.enabled.values()))


class Checks(Base):
    def setUp(self):
        super().setUp()
        self.tv = FakeTv(reenable_on_boot={"com.tcl.bi"}, broken_apps={"com.sonyliv"})
        self.tools = FakeTools(self.tv)
        self.assertFalse(self.run_setup(self.tv, self.tools))
        self.text = (self.snap / "report.txt").read_text()

    def test_a_package_the_firmware_turns_back_on_is_reported(self):
        self.assertIn("[!!] Disabled packages stayed disabled after reboot: re-enabled by the firmware: com.tcl.bi",
                      self.text)

    def test_an_app_that_does_not_open_is_reported(self):
        self.assertIn("[!!] Sony LIV opens", self.text)
        self.assertIn("[ok] Netflix opens", self.text)

    def test_a_changed_screensaver_is_reported(self):
        self.tv.saver = "com.android.dreams.basic/.Colors"
        with mock.patch("builtins.print"):
            results = st.verify(self.tv, self.snap, st.read_list(self.snap / "applied-list.txt"), pause=0)
        self.assertIn((False, "Screensaver unchanged and enabled", "com.android.dreams.basic/.Colors"), results)


class Restore(Base):
    def test_restore_puts_back_only_what_was_on_and_the_stock_home(self):
        tv = FakeTv(already_disabled={"com.tcl.logkit"})
        tools = FakeTools(tv)
        self.run_setup(tv, tools)
        self.assertFalse(tv.enabled["com.tcl.bi"])
        with mock.patch("builtins.print"):
            failed = st.restore(tv, self.snap)
        self.assertEqual(failed, [])
        self.assertTrue(tv.enabled["com.tcl.bi"])
        self.assertTrue(tv.enabled["com.google.android.apps.tv.launcherx"])
        self.assertFalse(tv.enabled["com.tcl.logkit"], "was already off before the setup")
        self.assertEqual(tv.home, STOCK)
        self.assertFalse(any("uninstall" in c for c in tv.commands))


class FindApk(Base):
    def test_picks_up_the_apk_from_downloads(self):
        target = self.tmp / "build" / "app-release.apk"
        downloads = self.tmp / "Downloads"
        downloads.mkdir()
        (downloads / "tvhome-midnight-blue.apk").write_bytes(b"apk!")
        with mock.patch.object(st, "APK", target), mock.patch.object(st, "MYTV", self.tmp / "x"), \
                mock.patch.object(st, "ROOT", self.tmp / "y"), \
                mock.patch.object(st.Path, "home", return_value=self.tmp), mock.patch("builtins.print"):
            self.assertEqual(st.find_apk(), target)
        self.assertEqual(target.read_bytes(), b"apk!")


class CommandLine(unittest.TestCase):
    """main() through the real Tv class, with a fake interpreter standing in for tools/tv.py."""

    def test_backup_through_tv_py(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        fake = base / "fake_tv.py"
        fake.write_text(
            "import sys\n"
            "cmd = sys.argv[-1]\n"
            "if cmd == '--probe': print('TCL Smart TV, Android 11'); sys.exit(0)\n"
            "answers = {'getprop ro.build.version.sdk': '30', 'pm list features': 'feature:android.software.leanback',\n"
            "  'getprop ro.product.brand': 'TCL', 'getprop ro.product.manufacturer': 'TCL',\n"
            "  'settings get secure screensaver_components': '%s',\n"
            "  'pm list packages -d': 'package:com.x.off'}\n"
            "if 'resolve-activity' in cmd: print('%s'); sys.exit(0)\n"
            "print(answers.get(cmd, 'package:com.tcl.tv'))\n" % (SAVER, STOCK))
        if os.name != "posix":
            raise unittest.SkipTest("the stand-in interpreter is a shell script")
        py = base / "python"
        py.write_text('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, fake))
        py.chmod(0o755)
        backups = base / "backups"
        with mock.patch.object(st, "ensure_venv", return_value=py), mock.patch.object(st, "BACKUPS", backups), \
                mock.patch("builtins.print"):
            code = st.main(["backup", "--host", "192.168.1.50", "--yes"])
        self.assertEqual(code, 0)
        snap = next(backups.iterdir())
        state = json.loads((snap / "state.json").read_text())
        self.assertEqual(state, {"home": STOCK, "screensaver": SAVER, "disabled": ["com.x.off"]})
        self.assertTrue((snap / "settings-secure.txt").exists())

    def test_help_needs_no_tv(self):
        out = subprocess.run([sys.executable, str(ROOT / "my-tv" / "setup_tv.py"), "--help"],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0)
        self.assertIn("restore", out.stdout)


if __name__ == "__main__":
    unittest.main()
