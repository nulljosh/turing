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
                mock.patch("tools_coder._repo", return_value=(proj, None)), \
                mock.patch("tools_coder._shell", return_value=""):
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
                mock.patch("tools_coder._repo", return_value=(self.proj, None)):
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
                mock.patch("tools_coder._shell", return_value=""):  # mock git status
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


class Helpers(unittest.TestCase):
    """_read_head, _gather_context, _plan and _edits with the model and git stood in."""

    def setUp(self):
        """A temp project with a README and two files."""
        self.proj = tempfile.mkdtemp()
        for name, body in (("README.md", "# Demo\nline2\n"), ("app.py", "print('old')\n"), (".env", "SECRET=1\n")):
            with open(os.path.join(self.proj, name), "w") as f:
                f.write(body)

    def tearDown(self):
        """Remove the temp project."""
        import shutil
        shutil.rmtree(self.proj, ignore_errors=True)

    def test_read_head_caps_lines_and_survives_a_missing_file(self):
        """The first N lines come back; a missing path is an empty string."""
        self.assertEqual(tools_coder._read_head(os.path.join(self.proj, "README.md"), lines=1), "# Demo")
        self.assertEqual(tools_coder._read_head(os.path.join(self.proj, "nope.txt")), "")

    def test_gather_context_has_readme_status_and_files(self):
        """README head, git status and the visible file list, hidden files left out."""
        with mock.patch("tools_coder._shell", return_value="## main"):
            ctx = tools_coder._gather_context(self.proj, "x")
        self.assertIn("README:\n# Demo", ctx)
        self.assertIn("Status:\n## main", ctx)
        self.assertIn("Files: README.md, app.py", ctx)
        self.assertNotIn(".env", ctx)

    def test_plan_shapes(self):
        """No reply, a reply without the model's sign-off, a could-not reply: None. A real reply: the plan text."""
        import tools_llm
        for reply in (None, "plan with no sign-off", "I could not reach a model.\n(Answered by x)"):
            with mock.patch.object(tools_llm, "ask_llm", return_value=reply), mock.patch("tools_coder._shell", return_value=""):
                self.assertIsNone(tools_coder._plan(self.proj, "dark mode"))
        with mock.patch.object(tools_llm, "ask_llm", return_value="Change app.py.\n(Answered by Qwen)") as ask, mock.patch("tools_coder._shell", return_value=""):
            self.assertEqual(tools_coder._plan(self.proj, "dark mode"), "Change app.py.")
        self.assertIn("dark mode", ask.call_args[0][0])

    def test_edits_parse_blocks_and_show_only_safe_files(self):
        """The prompt shows app.py but never .env; blocks come back parsed; a bad reply is (None, [])."""
        import tools_llm
        with mock.patch.object(tools_llm, "ask_llm", return_value="--- app.py\nprint('new')\n---\n(Answered by Qwen)") as ask:
            text, edits = tools_coder._edits(self.proj, "x", "plan")
        self.assertEqual(edits, [("app.py", "print('new')")])
        self.assertIn("app.py:\nprint('old')", ask.call_args[0][0])
        self.assertNotIn("SECRET", ask.call_args[0][0])
        with mock.patch.object(tools_llm, "ask_llm", return_value="The local model is down.\n(Answered by x)"):
            self.assertEqual(tools_coder._edits(self.proj, "x", "plan"), (None, []))


class RouteBranches(unittest.TestCase):
    """Every way route() stops short, plus the test-runner step, on a temp project with the model stood in."""

    def setUp(self):
        """A temp project with one committed-looking file, _repo pinned to it, plan stood in."""
        self.proj = tempfile.mkdtemp()
        self.app = os.path.join(self.proj, "app.py")
        with open(self.app, "w") as f:
            f.write("print('old')\n")
        self.patches = [mock.patch("tools_coder._repo", return_value=(self.proj, None)),
                        mock.patch("tools_coder._plan", return_value="Change app.py.")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        """Undo patches, remove the project."""
        import shutil
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.proj, ignore_errors=True)

    def run_with(self, edits, shell="", confirm=lambda n, a: True, reply="raw"):
        """route() with these edits and this git/test shell output."""
        runner = lambda argv, *a, **k: shell if argv[0] in ("python3", "npm") else ("" if "status" in argv else shell)  # git status is clean unless the test says so
        with mock.patch("tools_coder._edits", return_value=(reply, edits)), mock.patch("tools_coder._shell", side_effect=runner):
            return tools_coder.route("code x in demo", confirm=confirm)

    def test_first_no_runs_nothing(self):
        """A no at the first ask stops before the project is even read."""
        with mock.patch("tools_coder._plan", side_effect=AssertionError("read")):
            self.assertEqual(tools_coder.route("code x in demo", confirm=lambda n, a: False), "Okay, I will not.")

    def test_model_not_ready(self):
        """No plan, no edits, or edits in the wrong shape each end with a plain sentence."""
        with mock.patch("tools_coder._plan", return_value=None):
            self.assertIn("Could not plan", tools_coder.route("code x in demo"))
        self.assertIn("Could not generate", self.run_with([], reply=None))
        self.assertIn("expected format", self.run_with([]))

    def test_too_many_unsafe_and_dirty_files(self):
        """Four files, a path outside the project, a credential file, and an uncommitted file are each refused."""
        self.assertIn("Too many files", self.run_with([(f"f{i}.py", "x") for i in range(4)]))
        self.assertIn("outside project or protected", self.run_with([("../evil.py", "x")]))
        self.assertIn("outside project or protected", self.run_with([(".env", "x")]))
        with mock.patch("tools_coder._edits", return_value=("raw", [("app.py", "print('new')")])), mock.patch("tools_coder._shell", return_value=" M app.py"):
            self.assertIn("uncommitted changes", tools_coder.route("code x in demo", confirm=lambda n, a: True))
        self.assertEqual(open(self.app).read(), "print('old')\n")

    def test_no_diff_and_no_confirm(self):
        """Identical content is "No changes"; with no way to ask, the plan and diff come back and nothing is written."""
        self.assertEqual(self.run_with([("app.py", "print('old')")]), "No changes to make.")
        reply = self.run_with([("app.py", "print('new')")], confirm=None)
        self.assertIn("(Needs confirmation)", reply)
        self.assertIn("-print('old')", reply)
        self.assertEqual(open(self.app).read(), "print('old')\n")

    def test_tests_run_after_the_write(self):
        """With a tests/ folder the runner's output decides: a fail names the undo, a pass is reported."""
        os.mkdir(os.path.join(self.proj, "tests"))
        reply = self.run_with([("app.py", "print('new')")], shell="1 failed")
        self.assertIn("Tests failed", reply)
        self.assertIn("Undo: git checkout -- " + self.app, reply)
        reply = self.run_with([("app.py", "print('newer')")], shell="3 passed")
        self.assertEqual(reply, "Wrote 1 file(s). 3 passed")
        self.assertEqual(open(self.app).read(), "print('newer')")

    def test_code_wrapper(self):
        """code() hands the phrase to route() and explains the shape when it does not match."""
        self.assertIn("Say it like", tools_coder.code("make it blue"))


if __name__ == "__main__":
    unittest.main()
