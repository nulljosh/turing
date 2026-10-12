"""app/tools_shortcut.py with the Shortcuts tool stood in: nothing real is signed, saved or opened.

Run: python3 tests/test_shortcut.py
"""
import os
import plistlib
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools  # noqa: E402
import tools_shortcut  # noqa: E402


class ShortcutWriter(unittest.TestCase):
    """The four actions, the refusals, the file she would build, and that it always asks first."""

    def test_four_actions_parse(self):
        """Say, notify, open a link and set the volume turn into steps; "then" chains them; a name is optional."""
        name, steps = tools_shortcut.parse("make a shortcut called Morning that says hello and then sets the volume to 30")
        self.assertEqual(name, "Morning")
        self.assertEqual([s[0] for s in steps], ["is.workflow.actions.speaktext", "is.workflow.actions.setvolume"])
        _, steps = tools_shortcut.parse("make a shortcut that shows a notification saying stand up")
        self.assertEqual(steps[0][1]["WFNotificationActionBody"], "stand up")
        _, steps = tools_shortcut.parse("make a shortcut that opens https://example.com")
        self.assertEqual([s[0] for s in steps], ["is.workflow.actions.url", "is.workflow.actions.openurl"])

    def test_anything_else_is_declined(self):
        """No delete, no send, no shell, a volume past 100, and a request with no step all build nothing."""
        for ask in ("make a shortcut that deletes my files", "make a shortcut that sets the volume to 300",
                    "make a shortcut that runs rm -rf", "make a shortcut that emails my boss"):
            self.assertIsNone(tools_shortcut.parse(ask), ask)
        self.assertIn("I can build a Shortcut", tools_shortcut.make_shortcut("make a shortcut that does a backflip"))

    def test_the_file_has_no_triggers(self):
        """The workflow is a plain list of actions: no automation type, no schedule, and it survives a plist round trip."""
        _, steps = tools_shortcut.parse("make a shortcut that says hi")
        wf = plistlib.loads(plistlib.dumps(tools_shortcut.workflow(steps), fmt=plistlib.FMT_BINARY))
        self.assertEqual(wf["WFWorkflowTypes"], [])
        self.assertEqual(len(wf["WFWorkflowActions"]), 1)

    def test_routes_and_asking_first(self):
        """The words route to make_shortcut, it is a write, and no model can pick it."""
        self.assertEqual(tools.plan("make a shortcut that says good morning"), [("make_shortcut", ("make a shortcut that says good morning",))])
        self.assertIn("make_shortcut", tools.WRITES)
        self.assertIn("make_shortcut", tools.NOT_FOR_MODELS)

    def test_headless_writes_nothing(self):
        """Under SAMANTHA_HEADLESS the Shortcut is described and nothing is signed or opened; live, a failed sign says so."""
        with mock.patch("subprocess.run") as run:
            said = tools_shortcut.make_shortcut("make a shortcut that says hi")
        run.assert_not_called()
        self.assertTrue(said.startswith('Shortcut "Samantha says hi" would do:'), said)
        os.environ.pop("SAMANTHA_HEADLESS")
        try:
            with mock.patch("subprocess.run", return_value=mock.Mock(returncode=1)) as run:
                said = tools_shortcut.make_shortcut("make a shortcut that says hi")
            self.assertIn("would not sign it", said)
            self.assertEqual(run.call_count, 1)   # signed (and failed), never opened
        finally:
            os.environ["SAMANTHA_HEADLESS"] = "1"


if __name__ == "__main__":
    unittest.main()
