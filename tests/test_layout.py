"""Relocated code still finds repository resources and launches outside the checkout."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO / 'app'), str(REPO / 'scripts')]
os.environ['SAMANTHA_HEADLESS'] = '1'


class Layout(unittest.TestCase):
    """Keep code moves from silently dropping resources or coverage."""

    def test_resources_and_entry_point(self):
        """Model/cache paths stay put, the FAQ loads, and the pipe works from another cwd."""
        import ask
        import ask_faq
        import ask_web
        import stats
        import tools_agent
        import tools_badge
        import tools_dev
        import tools_gui
        import tools_logo

        for path in (ask.REPO, ask_faq.REPO, ask_web.REPO, tools_badge.HERE,
                     tools_gui.HERE, tools_dev._THIS_REPO):
            self.assertEqual(Path(path), REPO)
        self.assertEqual(Path(ask.ADAPTER), REPO / 'ada-1-adapter')
        self.assertEqual(Path(tools_agent.HANDS_ADAPTER), REPO / 'hands-adapter')
        self.assertEqual(Path(tools_agent.HANDS_GGUF), REPO / 'models/samantha-hands.gguf')
        self.assertEqual(Path(ask_faq.FAQ_PATH), REPO / 'docs/FAQ.md')
        self.assertTrue(ask_faq.load_faq())
        self.assertTrue(Path(tools_logo.PXM).is_file())
        self.assertTrue(Path(tools_badge.OCR_SCRIPT).is_file())
        coverage, percent = stats.collect_coverage()
        self.assertEqual(percent, 100)
        for path in ('app/chat.py', 'scripts/stats.py', 'tests/test_chat.py', 'training/distill.py'):
            self.assertIn(path, coverage)
        with tempfile.TemporaryDirectory() as other:
            result = subprocess.run([sys.executable, str(REPO / 'app/chat_pipe.py'), '--check'],
                                    cwd=other, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
