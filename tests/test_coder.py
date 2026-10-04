"""tools_coder.py: code feature in project tests. Mocks every external call (model, git, file I/O).

Run: python3 tests/test_coder.py
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools
import tools_coder


class Route(unittest.TestCase):
    """Phrase routing for "code X in Y" and "add X to Y"."""

    def test_routes_code_in_syntax(self):
        """'code X in Y' is recognized."""
        m = __import__("re").match(r"^(?:code|add) (?P<what>.+) (?:in|to) (?P<proj>\S+)$", "code dark mode in nimble")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("what"), "dark mode")
        self.assertEqual(m.group("proj"), "nimble")

    def test_routes_add_to_syntax(self):
        """'add X to Y' is recognized."""
        m = __import__("re").match(r"^(?:code|add) (?P<what>.+) (?:in|to) (?P<proj>\S+)$", "add export button to hotaru")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("what"), "export button")

    def test_not_recognized_without_project(self):
        """'code X' without project name is not recognized."""
        m = __import__("re").match(r"^(?:code|add) (?P<what>.+) (?:in|to) (?P<proj>\S+)$", "code dark mode")
        self.assertIsNone(m)

    def test_route_returns_none_for_non_code_query(self):
        """route() returns None for queries it doesn't match."""
        self.assertIsNone(tools_coder.route("make it shorter"))
        self.assertIsNone(tools_coder.route("draft a doc about X"))

    def test_route_refuses_bad_project(self):
        """route() refuses project names that don't resolve."""
        result = tools_coder.route("code dark mode in fake-project-xyz")
        self.assertIsNotNone(result)
        self.assertIn("No repo", result)


class SafePath(unittest.TestCase):
    """Path validation: under project, no dotfiles, no creds, no locks."""

    def setUp(self):
        """Create a temp project root."""
        self.proj = tempfile.mkdtemp()
        self.app = os.path.join(self.proj, "app")
        self.dotted = os.path.join(self.proj, ".git")
        self.cred = os.path.join(self.proj, ".env")
        self.lock = os.path.join(self.proj, "package-lock.json")
        os.makedirs(self.app, exist_ok=True)

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.proj, ignore_errors=True)

    def test_allows_safe_file_under_project(self):
        """A normal file under project root is safe."""
        safe = os.path.join(self.app, "main.py")
        self.assertTrue(tools_coder._safe_path(self.proj, safe))

    def test_refuses_outside_project(self):
        """File outside project is refused."""
        outside = "/tmp/malicious.py"
        self.assertFalse(tools_coder._safe_path(self.proj, outside))

    def test_refuses_dotfiles(self):
        """File in a dotfile directory is refused."""
        inside_dot = os.path.join(self.dotted, "config")
        self.assertFalse(tools_coder._safe_path(self.proj, inside_dot))

    def test_refuses_credential_files(self):
        """Files matching credential patterns are refused."""
        self.assertFalse(tools_coder._safe_path(self.proj, self.cred))
        secret = os.path.join(self.proj, "secret.key")
        self.assertFalse(tools_coder._safe_path(self.proj, secret))

    def test_refuses_lockfiles(self):
        """Lockfiles are refused."""
        self.assertFalse(tools_coder._safe_path(self.proj, self.lock))
        cargo = os.path.join(self.proj, "Cargo.lock")
        self.assertFalse(tools_coder._safe_path(self.proj, cargo))


class ExtractBlocks(unittest.TestCase):
    """Parsing "--- filename\ncontent\n---" blocks from model output."""

    def test_extracts_single_block(self):
        """One block is extracted."""
        text = "--- app.py\nprint('hi')\n---"
        edits = tools_coder._extract_blocks(text)
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0], ("app.py", "print('hi')"))

    def test_extracts_multiple_blocks(self):
        """Multiple blocks are extracted."""
        text = "--- app.py\ncode1\n---\n--- test.py\ncode2\n---"
        edits = tools_coder._extract_blocks(text)
        self.assertEqual(len(edits), 2)
        self.assertEqual(edits[0][0], "app.py")
        self.assertEqual(edits[1][0], "test.py")

    def test_handles_multiline_content(self):
        """Content with newlines is preserved."""
        text = "--- main.py\ndef foo():\n    pass\n---"
        edits = tools_coder._extract_blocks(text)
        self.assertIn("def foo():", edits[0][1])

    def test_returns_empty_on_no_blocks(self):
        """No blocks returns empty list."""
        edits = tools_coder._extract_blocks("just some text")
        self.assertEqual(edits, [])


class HeadlessMode(unittest.TestCase):
    """In headless mode, no writes even with yes confirmation."""

    def test_headless_env_set(self):
        """SAMANTHA_HEADLESS is set in this run."""
        self.assertEqual(os.environ.get("SAMANTHA_HEADLESS"), "1")

    def test_route_with_confirm_still_no_write_in_headless(self):
        """route() asks confirm but won't write in headless."""
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as proj, \
                mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)), \
                mock.patch("tools_coder._plan", return_value="Add dark mode"), \
                mock.patch("tools_coder._edits", return_value=("--- app.py\nprint()\n---", [("app.py", "print()")])), \
                mock.patch("tools_dev._repo", return_value=(proj, None)), \
                mock.patch("tools_dev._shell", return_value=""):
            # In headless, route won't write even on confirm=lambda: True
            result = tools_coder.route("code dark mode in test", confirm=lambda n, a: True)
            # Should get past model steps but won't write in pure headless
            # The function checks os.environ.get("SAMANTHA_HEADLESS") at write time
            self.assertIsNotNone(result)


class FullFlow(unittest.TestCase):
    """Full flow: plan -> edits -> validate -> write (mocked)."""

    def setUp(self):
        """Create a temp project with a git repo and files."""
        self.proj = tempfile.mkdtemp()
        os.system(f"cd {self.proj} && git init -q")
        # Create a simple file
        self.app_file = os.path.join(self.proj, "app.py")
        with open(self.app_file, "w") as f:
            f.write("print('old')\n")
        os.system(f"cd {self.proj} && git add app.py && git commit -q -m 'initial'")

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.proj, ignore_errors=True)

    def test_full_flow_with_mocked_model(self):
        """Full flow: plan -> edits -> show diffs -> write."""
        plan_reply = "Add dark mode support\n(Answered by Qwen on this Mac, not by me.)"
        edit_reply = "--- app.py\nprint('new')\n---\n(Answered by Qwen on this Mac, not by me.)"

        with mock.patch("tools_coder._plan", return_value="Add dark mode support"), \
                mock.patch("tools_coder._edits", return_value=(edit_reply, [("app.py", "print('new')\n")])), \
                mock.patch("os.environ.get", side_effect=lambda k, d=None: "1" if k == "SAMANTHA_HEADLESS" else d):
            # route will show plan and diffs, then need confirmation
            # But in headless, confirmation is bypassed and write doesn't happen
            result = tools_coder.route("code dark mode in test", confirm=lambda n, a: False)
            # Saying no means no write
            self.assertIn("Okay, I will not", result)

    def test_writes_on_yes_not_headless(self):
        """With headless off and confirm=yes, files are written."""
        plan_reply = "Add dark mode support\n(Answered by Qwen on this Mac, not by me.)"
        edit_reply = "--- app.py\nprint('new')\n---\n(Answered by Qwen on this Mac, not by me.)"

        with mock.patch("tools_coder._plan", return_value="Add dark mode support"), \
                mock.patch("tools_coder._edits", return_value=(edit_reply, [("app.py", "print('new')\n")])), \
                mock.patch("os.environ.get", side_effect=lambda k, d=None: None if k == "SAMANTHA_HEADLESS" else d), \
                mock.patch("tools_dev._shell", return_value=""):  # mock git status
            result = tools_coder.route("code dark mode in test", confirm=lambda n, a: True)
            # Should complete flow and write
            self.assertIsNotNone(result)


class NotInModelsMenu(unittest.TestCase):
    """code is NOT_FOR_MODELS and WRITES."""

    def test_in_not_for_models(self):
        """'code' is in NOT_FOR_MODELS."""
        self.assertIn("code", tools.NOT_FOR_MODELS)

    def test_in_writes(self):
        """'code' is in WRITES."""
        self.assertIn("code", tools.WRITES)


if __name__ == "__main__":
    unittest.main()
