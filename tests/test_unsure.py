"""Her 1.5B asks before acting when it was not sure of the tool name (tools_agent.UNSURE)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
os.environ["SAMANTHA_HEADLESS"] = "1"
import tools  # noqa: E402
import tools_agent  # noqa: E402


class Unsure(unittest.TestCase):
    """The confidence read and the yes-first path in tools.do."""

    def test_confidence_reads_only_the_tool_name(self):
        """A shaky argument does not count; a shaky tool name does."""
        pieces = [('{"', 1.0), ("tool", 1.0), ('":', 1.0), (' "', 0.99), ("calc", 0.4), ('",', 1.0), (' "arg": "', 1.0), ("2+2", 0.2), ('"}', 1.0)]
        self.assertEqual(tools_agent._tool_confidence(pieces), 0.4)
        self.assertEqual(tools_agent._tool_confidence([("hello", 0.1)]), 1.0)

    def test_unsure_pick_needs_a_yes(self):
        """No one to ask: she does nothing. A no: nothing runs. A yes: it runs once."""
        ran = []
        with mock.patch.object(tools, "pick", return_value=("unsure", "flip_coin", "")), \
                mock.patch.object(tools, "_faq_knows", return_value=False), \
                mock.patch.dict(tools.TOOLS, {"flip_coin": lambda: ran.append(1) or "heads"}):
            self.assertIsNone(tools.do("toss something"))
            self.assertEqual(tools.do("toss something", confirm=lambda *a: False), "Okay, I will not.")
            self.assertEqual(tools.do("toss something", confirm=lambda *a: True), "heads")
        self.assertEqual(ran, [1])



class LoaderTests(unittest.TestCase):
    """The 1.5B loads first and turns on asking when unsure; a broken or missing 1.5B falls back to the 0.5B, which never asks on confidence."""

    def setUp(self):
        """Every case starts with nothing loaded and no confidence threshold."""
        self._before = tools_agent._unsure_at
        tools_agent._unsure_at = 0.0

    def tearDown(self):
        """Put the threshold back."""
        tools_agent._unsure_at = self._before

    def _load(self, big, load):
        """_load_hands with a fake mlx_lm and the 1.5B at `big` (None: not on this Mac)."""
        fake = mock.MagicMock(load=load)
        with mock.patch.dict(sys.modules, {"mlx_lm": fake}), mock.patch.object(tools_agent, "_hands_model", return_value=big), \
                mock.patch.object(tools_agent.os.path, "isdir", return_value=True):
            return tools_agent._load_hands()

    def test_the_big_head_loads_first_and_asks_when_unsure(self):
        """A good 1.5B is the picker, and only then does she ask on confidence."""
        got = self._load("/m/big", lambda path, **kw: ("BIG", "tok") if path == "/m/big" else ("SMALL", "tok"))
        self.assertEqual(got, ("mlx", "BIG", "tok"))
        self.assertEqual(tools_agent._unsure_at, tools_agent.UNSURE)

    def test_a_broken_big_head_falls_back_to_the_small_one(self):
        """A half-downloaded 1.5B never leaves her without hands, and the 0.5B never asks on confidence."""
        def load(path, **kw):
            """The 1.5B fails to load; the 0.5B loads."""
            if path == "/m/big":
                raise ValueError("missing model.safetensors")
            return ("SMALL", "tok")
        self.assertEqual(self._load("/m/big", load), ("mlx", "SMALL", "tok"))
        self.assertEqual(tools_agent._unsure_at, 0.0)

    def test_no_big_head_yet_means_the_small_one(self):
        """Before the first fetch lands, the 0.5B answers."""
        self.assertEqual(self._load(None, lambda path, **kw: ("SMALL", "tok")), ("mlx", "SMALL", "tok"))
        self.assertEqual(tools_agent._unsure_at, 0.0)

    def test_a_half_downloaded_cache_is_not_the_big_head(self):
        """The small files are there but model.safetensors is not: not here yet, and no second fetch starts."""
        import tempfile
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": ""}), \
                mock.patch.object(tools_agent, "_fetching", False), mock.patch.object(tools_agent.os.path, "isdir", return_value=False), \
                mock.patch("huggingface_hub.snapshot_download", return_value=folder), mock.patch("threading.Thread") as thread:
            os.environ.pop("SAMANTHA_HEADLESS")
            self.assertIsNone(tools_agent._hands_model())
            self.assertIsNone(tools_agent._hands_model())
            open(os.path.join(folder, "model.safetensors"), "w").close()
            self.assertEqual(tools_agent._hands_model(), folder)
        self.assertEqual(thread.call_count, 1)

    def test_headless_never_downloads(self):
        """Tests and CI never start a fetch."""
        with mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": "1"}), mock.patch.object(tools_agent.os.path, "isdir", return_value=False), \
                mock.patch("threading.Thread") as thread:
            tools_agent._hands_model()
        thread.assert_not_called()

if __name__ == "__main__":
    unittest.main()
