"""tools_dev.py: the dev family (git status, recent commits, run the repo's own tests, open prs, open in the
editor), with `_repo`, `_shell`, subprocess and gh stood in throughout so nothing real ever runs.

Run: python3 tests/test_dev.py
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools
import tools_dev


class RepoLookup(unittest.TestCase):
    """_repo() resolves a name to a folder under ~/Documents/Code, case-insensitively, and refuses everything
    else, including a name that only looks like it points outside that folder."""

    def setUp(self):
        """A fake ~/Documents/Code with a couple of real repo-shaped folders and one that is not a git repo."""
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        os.makedirs(os.path.join(self.tmp, "Nimble", ".git"))
        os.makedirs(os.path.join(self.tmp, "not-a-repo"))
        self.patch = mock.patch.object(tools_dev, "CODE_DIR", self.tmp)
        self.patch.start()

    def tearDown(self):
        """Undo the CODE_DIR patch and remove the fake folders."""
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_blank_is_this_repo(self):
        """No name given resolves to turing itself, the repo tools_dev.py lives in."""
        path, err = tools_dev._repo("")
        self.assertIsNone(err)
        self.assertEqual(path, tools_dev._THIS_REPO)

    def test_case_insensitive_exact(self):
        """"nimble" finds the folder "Nimble", case-insensitively."""
        path, err = tools_dev._repo("nimble")
        self.assertIsNone(err)
        self.assertEqual(os.path.basename(path), "Nimble")

    def test_substring_match(self):
        """A partial name still finds the one folder it is short for."""
        path, err = tools_dev._repo("nimb")
        self.assertIsNone(err)
        self.assertEqual(os.path.basename(path), "Nimble")

    def test_unknown_name_refused(self):
        """A name matching no folder under ~/Documents/Code is an honest refusal, never a guess."""
        path, err = tools_dev._repo("totally-not-a-repo")
        self.assertIsNone(path)
        self.assertIn("No repo called", err)

    def test_not_a_git_repo_refused(self):
        """A real folder with no .git is refused too, not treated as a repo."""
        path, err = tools_dev._repo("not-a-repo")
        self.assertIsNone(path)
        self.assertIn("not a git repo", err)

    def test_path_traversal_refused(self):
        """A name shaped like a path out of ~/Documents/Code matches nothing there and is refused."""
        path, err = tools_dev._repo("../../etc")
        self.assertIsNone(path)
        self.assertIn("No repo called", err)


class GitStatusAndCommits(unittest.TestCase):
    """Read only: whatever _shell hands back, capped and passed through."""

    def test_git_status_capped_at_15_lines(self):
        """More than 15 lines of status is capped, never all of it."""
        lines = "\n".join(f"line {i}" for i in range(20))
        with mock.patch.object(tools_dev, "_shell", return_value=lines):
            reply = tools_dev.git_status("")
        self.assertEqual(len(reply.splitlines()), 15)

    def test_git_status_unreadable(self):
        """No output from git is an honest sentence."""
        with mock.patch.object(tools_dev, "_shell", return_value=""):
            self.assertIn("Could not read git status", tools_dev.git_status(""))

    def test_recent_commits(self):
        """Whatever git log hands back comes straight through."""
        with mock.patch.object(tools_dev, "_shell", return_value="abc123 fix thing (2 days ago)"):
            self.assertEqual(tools_dev.recent_commits(""), "abc123 fix thing (2 days ago)")

    def test_recent_commits_none(self):
        """No commits is an honest sentence, never invented."""
        with mock.patch.object(tools_dev, "_shell", return_value=""):
            self.assertIn("No commits found", tools_dev.recent_commits(""))

    def test_unknown_repo_refused_before_any_shell_call(self):
        """An unknown repo name is refused before _shell is ever touched."""
        with mock.patch.object(tools_dev, "_shell", side_effect=AssertionError("called")):
            self.assertIn("No repo called", tools_dev.git_status("nope-nope-nope"))


class RunTests(unittest.TestCase):
    """Picks the right test command for each project shape, real subprocess never called."""

    def setUp(self):
        """A fake repo folder, and _repo patched to resolve any name to it."""
        self.tmp = tempfile.mkdtemp()
        self.patch = mock.patch.object(tools_dev, "_repo", return_value=(self.tmp, None))
        self.patch.start()

    def tearDown(self):
        """Undo the _repo patch and remove the fake folder."""
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_npm_test_preferred(self):
        """A package.json with a real test script runs npm test, even if tests/ also exists."""
        with open(os.path.join(self.tmp, "package.json"), "w") as f:
            f.write('{"scripts": {"test": "jest"}}')
        with mock.patch.object(tools_dev, "_run_timed", return_value=(0, "1 passed")) as m:
            reply = tools_dev.run_tests("")
        self.assertIn("passed", reply)
        self.assertEqual(m.call_args[0][0], ["npm", "test"])

    def test_pytest_when_importable(self):
        """A tests/ folder of test_*.py with pytest importable runs pytest -q."""
        os.makedirs(os.path.join(self.tmp, "tests"))
        open(os.path.join(self.tmp, "tests", "test_x.py"), "w").close()
        with mock.patch.object(tools_dev, "_pytest_importable", return_value=True), \
                mock.patch.object(tools_dev, "_run_timed", return_value=(0, "2 passed")) as m:
            reply = tools_dev.run_tests("")
        self.assertIn("passed", reply)
        self.assertEqual(m.call_args[0][0], ["python3", "-m", "pytest", "-q"])

    def test_each_file_when_pytest_missing(self):
        """No pytest on this machine runs each tests/test_*.py with python3 instead."""
        os.makedirs(os.path.join(self.tmp, "tests"))
        open(os.path.join(self.tmp, "tests", "test_a.py"), "w").close()
        open(os.path.join(self.tmp, "tests", "test_b.py"), "w").close()
        with mock.patch.object(tools_dev, "_pytest_importable", return_value=False), \
                mock.patch.object(tools_dev, "_run_timed", return_value=(0, "ok")) as m:
            reply = tools_dev.run_tests("")
        self.assertIn("passed", reply)
        self.assertEqual(m.call_count, 2)

    def test_swift_test(self):
        """A Package.swift with no npm or python tests runs swift test."""
        open(os.path.join(self.tmp, "Package.swift"), "w").close()
        with mock.patch.object(tools_dev, "_run_timed", return_value=(1, "1 failure")) as m:
            reply = tools_dev.run_tests("")
        self.assertIn("failed", reply)
        self.assertEqual(m.call_args[0][0], ["swift", "test"])

    def test_no_test_command(self):
        """An empty project says plainly there is no test command it knows, and never calls subprocess."""
        with mock.patch.object(tools_dev, "_run_timed", side_effect=AssertionError("called")):
            reply = tools_dev.run_tests("")
        self.assertIn("no test command", reply)

    def test_unknown_repo_refused(self):
        """An unknown repo name is refused before any test command is chosen."""
        with mock.patch.object(tools_dev, "_repo", return_value=(None, "No repo called 'nope' under ~/Documents/Code.")):
            reply = tools_dev.run_tests("nope")
        self.assertIn("No repo called", reply)


class OpenPRs(unittest.TestCase):
    """gh pr list, read only, honest when gh is missing or not logged in."""

    def setUp(self):
        """_repo patched to resolve any name to a fake path; nothing on disk is touched."""
        self.patch = mock.patch.object(tools_dev, "_repo", return_value=("/tmp/fake-repo", None))
        self.patch.start()

    def tearDown(self):
        """Undo the _repo patch."""
        self.patch.stop()

    def test_gh_missing(self):
        """No gh on PATH is an honest sentence, subprocess never called."""
        with mock.patch.object(tools_dev.shutil, "which", return_value=None), \
                mock.patch("subprocess.run", side_effect=AssertionError("called")):
            reply = tools_dev.open_prs("")
        self.assertIn("gh CLI is not installed", reply)

    def test_gh_not_logged_in(self):
        """A gh failure naming auth is reported as not logged in, not a raw error dump."""
        fake = mock.Mock(returncode=1, stdout="", stderr="To get started with GitHub CLI, please run: gh auth login")
        with mock.patch.object(tools_dev.shutil, "which", return_value="/usr/local/bin/gh"), \
                mock.patch("subprocess.run", return_value=fake):
            reply = tools_dev.open_prs("")
        self.assertIn("not logged in", reply)

    def test_lists_prs(self):
        """A clean gh run passes its output straight through."""
        fake = mock.Mock(returncode=0, stdout="123  Fix thing  branch-a\n", stderr="")
        with mock.patch.object(tools_dev.shutil, "which", return_value="/usr/local/bin/gh"), \
                mock.patch("subprocess.run", return_value=fake):
            reply = tools_dev.open_prs("")
        self.assertIn("Fix thing", reply)

    def test_no_open_prs(self):
        """No output is an honest "no open pull requests", never invented."""
        fake = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(tools_dev.shutil, "which", return_value="/usr/local/bin/gh"), \
                mock.patch("subprocess.run", return_value=fake):
            reply = tools_dev.open_prs("")
        self.assertIn("No open pull requests", reply)


class OpenInEditor(unittest.TestCase):
    """Classified like open_app: prefers `code`, falls back to VS Code via `open -a`, then Finder; does
    nothing while headless."""

    def setUp(self):
        """_repo patched to resolve any name to a fake path; nothing on disk is touched."""
        self.patch = mock.patch.object(tools_dev, "_repo", return_value=("/tmp/fake-repo", None))
        self.patch.start()

    def tearDown(self):
        """Undo the _repo patch."""
        self.patch.stop()

    def test_prefers_code_on_path(self):
        """`code` on PATH is used directly."""
        with mock.patch.object(tools_dev, "HEADLESS", False), \
                mock.patch.object(tools_dev.shutil, "which", return_value="/usr/local/bin/code"), \
                mock.patch("subprocess.run") as run:
            reply = tools_dev.open_in_editor("")
        self.assertIn("Opened", reply)
        self.assertEqual(run.call_args[0][0][0], "code")

    def test_falls_back_to_vscode_app(self):
        """No `code` on PATH, but VS Code is installed: opens it with `open -a`."""
        with mock.patch.object(tools_dev, "HEADLESS", False), \
                mock.patch.object(tools_dev.shutil, "which", return_value=None), \
                mock.patch("os.path.isdir", return_value=True), \
                mock.patch("subprocess.run") as run:
            tools_dev.open_in_editor("")
        self.assertEqual(run.call_args[0][0][:2], ["open", "-a"])

    def test_falls_back_to_finder(self):
        """Neither `code` nor VS Code: plain `open`, which is Finder for a folder."""
        with mock.patch.object(tools_dev, "HEADLESS", False), \
                mock.patch.object(tools_dev.shutil, "which", return_value=None), \
                mock.patch("os.path.isdir", return_value=False), \
                mock.patch("subprocess.run") as run:
            tools_dev.open_in_editor("")
        self.assertEqual(run.call_args[0][0][0], "open")

    def test_headless_does_nothing_but_still_answers(self):
        """Headless never opens anything, same shape as open_app, but still gives its answer."""
        with mock.patch.object(tools_dev, "HEADLESS", True), \
                mock.patch.object(tools_dev.shutil, "which", return_value="/usr/local/bin/code"), \
                mock.patch("subprocess.run", side_effect=AssertionError("called")):
            reply = tools_dev.open_in_editor("")
        self.assertIn("Opened", reply)


class Routing(unittest.TestCase):
    """Every dev phrasing reaches its tool end to end through tools.do."""

    def test_git_status(self):
        """"git status" routes to git_status."""
        with mock.patch.object(tools, "git_status", return_value="## main"):
            self.assertEqual(tools.do("git status", confirm=lambda n, a: True), "## main")

    def test_git_status_named(self):
        """"git status of nimble" routes to git_status with the repo name."""
        with mock.patch.object(tools, "git_status", return_value="## main") as m:
            tools.do("git status of nimble", confirm=lambda n, a: True)
        m.assert_called_once_with("nimble")

    def test_what_changed(self):
        """"what changed in turing" routes to git_status."""
        with mock.patch.object(tools, "git_status", return_value="## main") as m:
            tools.do("what changed in turing", confirm=lambda n, a: True)
        m.assert_called_once_with("turing")

    def test_recent_commits(self):
        """"recent commits" routes to recent_commits."""
        with mock.patch.object(tools, "recent_commits", return_value="abc123 fix"):
            self.assertEqual(tools.do("recent commits", confirm=lambda n, a: True), "abc123 fix")

    def test_last_commits_named(self):
        """"last commits in cadence" routes to recent_commits with the repo name."""
        with mock.patch.object(tools, "recent_commits", return_value="abc123 fix") as m:
            tools.do("last commits in cadence", confirm=lambda n, a: True)
        m.assert_called_once_with("cadence")

    def test_run_the_tests(self):
        """"run the tests" routes to run_tests on a yes."""
        with mock.patch.object(tools, "run_tests", return_value="Tests passed for turing."):
            self.assertEqual(tools.do("run the tests", confirm=lambda n, a: True), "Tests passed for turing.")

    def test_run_named_tests(self):
        """"run turing's tests" routes to run_tests with the repo name."""
        with mock.patch.object(tools, "run_tests", return_value="Tests passed for turing.") as m:
            tools.do("run turing's tests", confirm=lambda n, a: True)
        m.assert_called_once_with("turing")

    def test_run_tests_asks_first(self):
        """A no through confirm never runs run_tests."""
        with mock.patch.object(tools, "run_tests", side_effect=AssertionError("ran without a yes")):
            self.assertEqual(tools.do("run the tests", confirm=lambda n, a: False), "Okay, I will not.")

    def test_open_prs(self):
        """"open prs" routes to open_prs."""
        with mock.patch.object(tools, "open_prs", return_value="No open pull requests."):
            self.assertEqual(tools.do("open prs", confirm=lambda n, a: True), "No open pull requests.")

    def test_open_prs_named(self):
        """"any open pull requests on sidewise" routes to open_prs with the repo name."""
        with mock.patch.object(tools, "open_prs", return_value="ok") as m:
            tools.do("any open pull requests on sidewise", confirm=lambda n, a: True)
        m.assert_called_once_with("sidewise")

    def test_open_in_editor(self):
        """"open turing in the editor" routes to open_in_editor."""
        with mock.patch.object(tools, "open_in_editor", return_value="Opened turing in the editor.") as m:
            reply = tools.do("open turing in the editor", confirm=lambda n, a: True)
        m.assert_called_once_with("turing")
        self.assertEqual(reply, "Opened turing in the editor.")

    def test_open_repo_in_vscode(self):
        """"open the nimble repo in vs code" routes to open_in_editor with just the repo name."""
        with mock.patch.object(tools, "open_in_editor", return_value="Opened nimble in the editor.") as m:
            tools.do("open the nimble repo in vs code", confirm=lambda n, a: True)
        m.assert_called_once_with("nimble")

    def test_writes_are_classified(self):
        """run_tests asks first, same as quit_app and complete_reminder."""
        self.assertIn("run_tests", tools.WRITES)

    def test_open_chrome_still_opens_the_app(self):
        """"open chrome" must not be stolen by the dev family."""
        with mock.patch.object(tools, "open_app", return_value="Opened Google Chrome."):
            self.assertEqual(tools.do("open chrome", confirm=lambda n, a: True), "Opened Google Chrome.")

    def test_run_shortcut_still_runs_a_shortcut(self):
        """"run shortcut morning" must not be stolen by run_tests."""
        with mock.patch.object(tools, "run_shortcut", return_value="Ran Morning."):
            self.assertEqual(tools.do("run shortcut morning", confirm=lambda n, a: True), "Ran Morning.")

    def test_whats_running_still_lists_apps(self):
        """"what's running" must not be stolen by the dev family."""
        with mock.patch.object(tools, "running_apps", return_value="Finder, Safari"):
            self.assertEqual(tools.do("what's running", confirm=lambda n, a: True), "Finder, Safari")


if __name__ == "__main__":
    unittest.main()
