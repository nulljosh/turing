"""Sentences an adversarial review found slipping past loosened guard cues (2026-10-04). Each must stay stopped,
and the right picks the cues were added for must still run."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
os.environ["SAMANTHA_HEADLESS"] = "1"
import tools_registry as R  # noqa: E402

STOPPED = [("rename_file", "photo.heic\tjpg", "change photo.heic to jpg"), ("roll_dice", "", "toss a coin"),
           ("move_file", "file.pdf\tfolder", "put the file to my folder")]
RUNS = [("roll_dice", "", "Give me a dice roll"), ("move_file", "photo.jpg\tPictures", "Put photo.jpg in Pictures for me"),
        ("rename_file", "file.txt\tupdated_file.txt", "Change file.txt to updated_file.txt"), ("wifi_name", "", "Tell me the SSID")]


class GuardProbes(unittest.TestCase):
    """The review's leaks and the picks they were loosened for."""
    def test_review_leaks_stay_stopped(self):
        """Every leak the review confirmed is refused."""
        for tool, arg, q in STOPPED:
            self.assertFalse(R._sound(tool, R.repair(tool, arg, q), q), q)

    def test_right_picks_still_run(self):
        """The commands the cues were loosened for still run."""
        for tool, arg, q in RUNS:
            self.assertTrue(R._sound(tool, R.repair(tool, arg, q), q), q)


if __name__ == "__main__":
    unittest.main()
