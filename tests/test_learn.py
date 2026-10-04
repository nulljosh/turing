"""tools_learn.py: explain a codebase and teach a lesson.

Run: python3 tests/test_learn.py
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools
import tools_learn


class ExplainCodebase(unittest.TestCase):
    """Explain a codebase by reading README and CLAUDE.md."""

    def test_no_repo_error(self):
        """An unknown repo name is refused."""
        result = tools_learn.explain_codebase("nonexistent-repo-xyz")
        self.assertIn("No repo", result)

    def test_turing_repo(self):
        """Explaining the turing repo (this one) works with the local model mocked."""
        with mock.patch("tools_llm.ask_llm") as mock_llm:
            mock_llm.return_value = "This is a codebase.\n(Answered by Qwen3.5-9B on this Mac, not by me.)"
            result = tools_learn.explain_codebase("turing")
            self.assertIn("This is a codebase", result)
            self.assertNotIn("(Answered by", result)  # attribution stripped

    def test_empty_repo(self):
        """A repo with no README or CLAUDE.md still gets a fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal git repo
            git_dir = os.path.join(tmpdir, "test-repo")
            os.makedirs(git_dir)
            os.makedirs(os.path.join(git_dir, ".git"))
            # Mock _repo to return this temp path
            with mock.patch("tools_learn._repo") as mock_repo:
                mock_repo.return_value = (git_dir, None)
                result = tools_learn.explain_codebase("test-repo")
                # Should return a message about not being able to read the structure
                self.assertIn("Could not read", result)

    def test_model_unavailable(self):
        """When the local model is unavailable, a graceful error is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal git repo with a folder but no README or CLAUDE.md
            git_dir = os.path.join(tmpdir, "test-repo")
            os.makedirs(git_dir)
            os.makedirs(os.path.join(git_dir, ".git"))
            os.makedirs(os.path.join(git_dir, "src"))  # Add a visible folder
            with mock.patch("tools_learn._repo") as mock_repo:
                mock_repo.return_value = (git_dir, None)
                with mock.patch("tools_llm.ask_llm") as mock_llm:
                    mock_llm.return_value = "I could not reach a local model."  # No attribution marker
                    result = tools_learn.explain_codebase("test-repo")
                    # Should mention local model unavailability
                    self.assertIn("local model", result.lower())

    def test_routes(self):
        """The explain_codebase routes match expected phrasings."""
        with mock.patch.object(tools, "explain_codebase") as mock_fn:
            mock_fn.return_value = "ok"
            # "explain this codebase to me" should hit the first route
            result = tools.do("explain this codebase to me")
            mock_fn.assert_called()
            # Reset and test another phrasing
            mock_fn.reset_mock()
            result = tools.do("explain the turing codebase")
            mock_fn.assert_called()


class TeachMe(unittest.TestCase):
    """Teach a lesson on a topic with quiz questions."""

    def test_empty_topic(self):
        """An empty topic is refused."""
        result = tools_learn.teach_me("")
        self.assertIn("Teach you about what", result)

    def test_teach_with_sources(self):
        """Teaching with sources and a working model returns the lesson and questions."""
        with mock.patch("tools_research.sources") as mock_sources, \
             mock.patch("tools_llm.ask_llm") as mock_llm:
            mock_sources.return_value = [
                ("Wikipedia: Example", "This is an example topic with facts."),
                ("Library: Guide", "A guide to understanding examples.")
            ]
            mock_llm.return_value = (
                "An example is something you can point at.\n"
                "\n"
                "Quiz question 1: What is an example?\n"
                "a) A mistake\n"
                "b) A case you can point to [b]\n"
                "c) A question\n"
                "d) A title\n"
                "\n"
                "Quiz question 2: Why do we use examples?\n"
                "a) To confuse people\n"
                "b) To make things clearer [b]\n"
                "c) To fill time\n"
                "d) To practice typing\n"
                "\n"
                "(Answered by Qwen3.5-9B on this Mac, not by me.)"
            )
            result = tools_learn.teach_me("examples")
            self.assertIn("example", result.lower())
            self.assertIn("Quiz", result)
            self.assertNotIn("(Answered by", result)

    def test_teach_no_sources(self):
        """Teaching when no sources are found returns an honest refusal."""
        with mock.patch("tools_research.sources") as mock_sources:
            mock_sources.return_value = []
            result = tools_learn.teach_me("something obscure xyz")
            self.assertIn("could not find sources", result)

    def test_teach_model_unavailable(self):
        """Teaching when the model is unavailable falls back gracefully."""
        with mock.patch("tools_research.sources") as mock_sources, \
             mock.patch("tools_llm.ask_llm") as mock_llm:
            mock_sources.return_value = [("Wikipedia: Test", "Test content")]
            mock_llm.return_value = "I could not reach the model."  # No attribution
            result = tools_learn.teach_me("test")
            self.assertIn("local model", result.lower())

    def test_teach_route(self):
        """The teach_me route matches expected phrasings."""
        with mock.patch.object(tools, "teach_me") as mock_fn:
            mock_fn.return_value = "Lesson here."
            # "teach me X" should route
            result = tools.do("teach me quantum mechanics")
            mock_fn.assert_called()
            # Reset and test another phrasing
            mock_fn.reset_mock()
            result = tools.do("give me a lesson on history")
            mock_fn.assert_called()


class Classification(unittest.TestCase):
    """Tools are properly classified."""

    def test_not_in_writes(self):
        """The new tools are not in WRITES."""
        self.assertNotIn("explain_codebase", tools.WRITES)
        self.assertNotIn("teach_me", tools.WRITES)

    def test_tools_registered(self):
        """The new tools are in tools.TOOLS."""
        self.assertIn("explain_codebase", tools.TOOLS)
        self.assertIn("teach_me", tools.TOOLS)

    def test_in_reading(self):
        """teach_me is in untrusted.READING (it pulls from Wikipedia)."""
        import untrusted
        self.assertIn("teach_me", untrusted.READING)


if __name__ == "__main__":
    unittest.main()
