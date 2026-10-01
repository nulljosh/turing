"""training/gen_hands_data.py: the picker's training set never holds a held-out phrasing, and every tool row it
teaches is one the guard would let through, so she is never trained into a pick tools.do() then refuses.

Run: python3 tests/test_hands_data.py
"""
import json
import os
import sys
import tempfile
import unittest

os.environ["SAMANTHA_HEADLESS"] = "1"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "app"))
sys.path.insert(0, os.path.join(REPO, "training"))
import gen_hands_data
import tools


class HandsData(unittest.TestCase):
    """Build the real set once, in a temp folder, and check it."""

    @classmethod
    def setUpClass(cls):
        """Run gen_hands_data.main() in a temp folder and load train.jsonl."""
        here, cls.tmp = os.getcwd(), tempfile.mkdtemp()
        try:
            os.chdir(cls.tmp)
            gen_hands_data.main()
            with open("hands-data/train.jsonl") as f:
                cls.rows = [json.loads(line)["messages"] for line in f]
        finally:
            os.chdir(here)

    def test_no_held_out_phrasing_in_training(self):
        """Not one row of heldout, heldout2, heldout3 or heldout4 appears in training, however it is punctuated."""
        seen = {m[1]["content"].lower().rstrip(".?!") for m in self.rows}
        for name in ("heldout.jsonl", "heldout2.jsonl", "heldout3.jsonl", "heldout4.jsonl"):
            with open(os.path.join(REPO, "eval", name)) as f:
                texts = {json.loads(line)["text"].lower().rstrip(".?!") for line in f if line.strip()}
            self.assertFalse(seen & texts, name)

    def test_every_taught_pick_passes_the_guard(self):
        """A training row the guard would refuse teaches a pick that can never run: none allowed."""
        refused = []
        for m in self.rows:
            call = json.loads(m[2]["content"])
            if call["tool"] and call["tool"] != "agent" and not tools._sound(call["tool"], call["arg"], m[1]["content"]):
                refused.append((m[1]["content"], call))
        self.assertEqual(refused[:10], [], f"{len(refused)} rows the guard refuses")


if __name__ == "__main__":
    unittest.main()
