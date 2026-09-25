"""tools_system.py: the system family (dark mode, running apps, quit, do not disturb, bluetooth), with `_app`
and `_shell` mocked throughout so nothing real is ever touched.

Run: python3 tests/test_system.py
"""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools
import tools_system


class DarkMode(unittest.TestCase):
    """Parses on/off/toggle/free text, and reports whatever _app hands back."""

    def test_on(self):
        """"on" sets the true script and reports on."""
        with mock.patch.object(tools_system, "_app", return_value="true") as m:
            self.assertEqual(tools_system.dark_mode("on"), "Dark mode is on.")
        self.assertEqual(m.call_args[0][0], tools_system._DARK_ON)

    def test_off(self):
        """"off" sets the false script and reports off."""
        with mock.patch.object(tools_system, "_app", return_value="false") as m:
            self.assertEqual(tools_system.dark_mode("off"), "Dark mode is off.")
        self.assertEqual(m.call_args[0][0], tools_system._DARK_OFF)

    def test_toggle(self):
        """"toggle" sets the not-dark-mode script and reports whatever it landed on."""
        with mock.patch.object(tools_system, "_app", return_value="true") as m:
            self.assertEqual(tools_system.dark_mode("toggle"), "Dark mode is on.")
        self.assertEqual(m.call_args[0][0], tools_system._DARK_TOGGLE)

    def test_free_text_light(self):
        """"switch to light mode" reads as off."""
        with mock.patch.object(tools_system, "_app", return_value="false") as m:
            self.assertEqual(tools_system.dark_mode("switch to light mode"), "Dark mode is off.")
        self.assertEqual(m.call_args[0][0], tools_system._DARK_OFF)


class RunningApps(unittest.TestCase):
    """Visible apps only, names sorted, read only."""

    def test_sorted_names(self):
        """Whatever System Events hands back comes out sorted."""
        with mock.patch.object(tools_system, "_app", return_value="Safari, Finder, Terminal"):
            self.assertEqual(tools_system.running_apps(), "Finder, Safari, Terminal")

    def test_none_running(self):
        """No visible apps is "No apps running.", never invented."""
        with mock.patch.object(tools_system, "_app", return_value=""):
            self.assertEqual(tools_system.running_apps(), "No apps running.")


class QuitApp(unittest.TestCase):
    """Refuses Finder/Terminal/the running terminal, refuses a not-running app, quits a running one."""

    def test_refuses_finder(self):
        """Finder is refused before any AppleScript runs."""
        with mock.patch.object(tools_system, "_app", side_effect=AssertionError("called")):
            reply = tools_system.quit_app("Finder")
        self.assertIn("I will not quit", reply)

    def test_refuses_terminal(self):
        """Every terminal running her is refused, not just Terminal.app."""
        with mock.patch.object(tools_system, "_app", side_effect=AssertionError("called")):
            for name in ("Terminal", "iTerm2", "Ghostty", "Warp"):
                self.assertIn("I will not quit", tools_system.quit_app(name))

    def test_not_running(self):
        """An app that is not in the running list is refused, and only the read ran."""
        with mock.patch.object(tools_system, "_app", return_value="Finder, Safari") as m:
            self.assertEqual(tools_system.quit_app("Spotify"), "Spotify is not running.")
        m.assert_called_once()

    def test_quits_running_app(self):
        """A running app gets the quit AppleScript, by its exact found name."""
        with mock.patch.object(tools_system, "_app", side_effect=["Finder, Spotify", ""]) as m:
            self.assertEqual(tools_system.quit_app("spotify"), "Quit Spotify.")
        self.assertEqual(m.call_count, 2)
        self.assertEqual(m.call_args[0][1], "Spotify")

    def test_empty_name(self):
        """No name given is an honest ask, AppleScript never called."""
        with mock.patch.object(tools_system, "_app", side_effect=AssertionError("called")):
            self.assertIn("Quit which app", tools_system.quit_app("  "))


class DoNotDisturb(unittest.TestCase):
    """Runs the named Shortcut if it exists; otherwise an honest sentence and nothing else."""

    def test_shortcut_present_on(self):
        """"on" lists Shortcuts, finds the exact match, and runs it."""
        with mock.patch.object(tools_system, "_shell", side_effect=["Turn On Do Not Disturb\nOther Shortcut", ""]) as m:
            reply = tools_system.do_not_disturb("on")
        self.assertEqual(reply, "Ran Turn On Do Not Disturb.")
        self.assertEqual(m.call_count, 2)

    def test_shortcut_present_off(self):
        """"off" looks for the off-named Shortcut, not the on one."""
        with mock.patch.object(tools_system, "_shell", side_effect=["Turn Off Do Not Disturb", ""]) as m:
            reply = tools_system.do_not_disturb("off")
        self.assertEqual(reply, "Ran Turn Off Do Not Disturb.")
        self.assertEqual(m.call_count, 2)

    def test_shortcut_missing(self):
        """No matching Shortcut is an honest sentence naming the Set Focus action, and shortcuts run never fires."""
        with mock.patch.object(tools_system, "_shell", return_value="Some Other Shortcut") as m:
            reply = tools_system.do_not_disturb("on")
        self.assertIn("Set Focus", reply)
        self.assertIn("Turn On Do Not Disturb", reply)
        m.assert_called_once()


class BluetoothStatus(unittest.TestCase):
    """Read only: on/off and connected device names from system_profiler."""

    def test_on_with_device(self):
        """On, with a connected device named and a not-connected one left out."""
        sample = "Bluetooth:\n\n    Hardware Settings:\n        State: On\n\n    Connected:\n        AirPods Pro:\n            Address: aa\n\n    Not Connected:\n        Magic Mouse:\n"
        with mock.patch.object(tools_system, "_shell", return_value=sample):
            reply = tools_system.bluetooth_status()
        self.assertIn("Bluetooth is on", reply)
        self.assertIn("AirPods Pro", reply)
        self.assertNotIn("Magic Mouse", reply)

    def test_off(self):
        """Off is one plain sentence, no device list."""
        sample = "Bluetooth:\n\n    Hardware Settings:\n        State: Off\n"
        with mock.patch.object(tools_system, "_shell", return_value=sample):
            self.assertEqual(tools_system.bluetooth_status(), "Bluetooth is off.")

    def test_no_reading(self):
        """No output from system_profiler is an honest refusal, never a guess."""
        with mock.patch.object(tools_system, "_shell", return_value=""):
            self.assertEqual(tools_system.bluetooth_status(), "Could not read Bluetooth status.")


class Routing(unittest.TestCase):
    """Every system phrasing reaches its tool end to end through tools.do."""

    def test_dark_mode(self):
        """"Turn on dark mode" routes to dark_mode."""
        with mock.patch.object(tools, "dark_mode", return_value="Dark mode is on."):
            self.assertEqual(tools.do("turn on dark mode", confirm=lambda n, a: True), "Dark mode is on.")

    def test_running_apps(self):
        """"What apps are running" routes to running_apps."""
        with mock.patch.object(tools, "running_apps", return_value="Finder, Safari"):
            self.assertEqual(tools.do("what apps are running", confirm=lambda n, a: True), "Finder, Safari")

    def test_quit_app(self):
        """"Quit spotify" routes to quit_app on a yes."""
        with mock.patch.object(tools, "quit_app", return_value="Quit Spotify."):
            self.assertEqual(tools.do("quit spotify", confirm=lambda n, a: True), "Quit Spotify.")

    def test_quit_app_alt_phrasing(self):
        """"Close the app slack" also routes to quit_app."""
        with mock.patch.object(tools, "quit_app", return_value="Quit Slack."):
            self.assertEqual(tools.do("close the app slack", confirm=lambda n, a: True), "Quit Slack.")

    def test_quit_app_asks_first(self):
        """A no through confirm never runs quit_app."""
        with mock.patch.object(tools, "quit_app", side_effect=AssertionError("ran without a yes")):
            self.assertEqual(tools.do("quit spotify", confirm=lambda n, a: False), "Okay, I will not.")

    def test_do_not_disturb(self):
        """"Turn on do not disturb" routes to do_not_disturb on a yes."""
        with mock.patch.object(tools, "do_not_disturb", return_value="Ran Turn On Do Not Disturb."):
            self.assertEqual(tools.do("turn on do not disturb", confirm=lambda n, a: True), "Ran Turn On Do Not Disturb.")

    def test_bluetooth_status(self):
        """"Bluetooth status" routes to bluetooth_status."""
        with mock.patch.object(tools, "bluetooth_status", return_value="Bluetooth is on."):
            self.assertEqual(tools.do("bluetooth status", confirm=lambda n, a: True), "Bluetooth is on.")

    def test_close_the_github_tab_still_closes_a_tab(self):
        """The new "close the app X" phrasing must not steal "close the github tab" from close_tab."""
        with mock.patch.object(tools, "close_tab", return_value="Closed."):
            self.assertEqual(tools.do("close the github tab", confirm=lambda n, a: True), "Closed.")

    def test_open_spotify_still_opens_the_app(self):
        """"Open spotify" must not be stolen by the quit_app family."""
        with mock.patch.object(tools, "open_app", return_value="Opened Spotify."):
            self.assertEqual(tools.do("open spotify", confirm=lambda n, a: True), "Opened Spotify.")

    def test_set_the_volume_still_sets_volume(self):
        """"Set the volume to 30" must not be stolen by the dark_mode family."""
        with mock.patch.object(tools, "set_volume", return_value="Volume at 30."):
            self.assertEqual(tools.do("set the volume to 30", confirm=lambda n, a: True), "Volume at 30.")

    def test_writes_are_classified(self):
        """quit_app and do_not_disturb ask first, same as complete_reminder and add_event."""
        self.assertTrue({"quit_app", "do_not_disturb"} <= tools.WRITES)



class QuitGuard(unittest.TestCase):
    """The protected list is checked on the app actually matched, not just the words typed."""

    def test_partial_name_never_reaches_finder_or_cmux(self):
        """"quit find" and "quit cmu" match Finder and cmux, and both are refused without quitting anything."""
        import tools_system
        calls = []
        def fake(script, *args):
            """Running apps are Finder, cmux, Spotify; record any quit."""
            if args:
                calls.append(args)
            return "Finder, cmux, Spotify"
        with mock.patch.object(tools_system, "_app", side_effect=fake):
            self.assertIn("will not quit Finder", tools_system.quit_app("find"))
            self.assertIn("will not quit cmux", tools_system.quit_app("cmu"))
            self.assertEqual(calls, [])
            self.assertEqual(tools_system.quit_app("spot"), "Quit Spotify.")

if __name__ == "__main__":
    unittest.main()
