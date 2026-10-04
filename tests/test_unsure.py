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


if __name__ == "__main__":
    unittest.main()
