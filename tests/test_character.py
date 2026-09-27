"""tools_character.py: her voice and look, changed by asking. ElevenLabs and the Higgsfield scripts are faked
throughout, so nothing here spends a cent or touches the real character folder.

Run: python3 tests/test_character.py
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import chat_pipe
import harness
import tools
import tools_character as tc

VOICES = {"voices": [
    {"voice_id": "sarahid", "name": "Sarah - Mature, Reassuring", "category": "premade", "labels": {"gender": "female", "accent": "american"}},
    {"voice_id": "georgeid", "name": "George", "category": "premade", "description": "Warm British storyteller"},
    {"voice_id": "mineid", "name": "My Clone", "category": "cloned"},
]}


def _read(path):
    """A file's bytes, closed straight away."""
    with open(path, "rb") as f:
        return f.read()


class Character(unittest.TestCase):
    """Each test gets its own empty character folder and a fake key."""

    def setUp(self):
        """A temp character with a look and Sarah's voice; a fake ElevenLabs key; no real ELEVENLABS_VOICE."""
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"SAMANTHA_CHARACTER": self.dir, "ELEVENLABS_API_KEY": "k"})
        self.env.start()
        os.environ.pop("ELEVENLABS_VOICE", None)
        with open(os.path.join(self.dir, "character.json"), "w") as f:
            json.dump({"name": "Samantha", "look": "a woman with red hair", "voice_id": "sarahid"}, f)
        with open(os.path.join(self.dir, "portrait.png"), "wb") as f:
            f.write(b"old")

    def tearDown(self):
        """Put the environment back."""
        self.env.stop()

    def data(self):
        """character.json as it is on disk now."""
        with open(os.path.join(self.dir, "character.json")) as f:
            return json.load(f)

    def test_list_voices_no_key(self):
        """No key is an honest sentence, and the network is never tried."""
        os.environ.pop("ELEVENLABS_API_KEY")
        with mock.patch.object(tc, "_fetch", side_effect=AssertionError("fetched")):
            self.assertIn("don't have an ElevenLabs key", tc.list_voices())

    def test_list_voices_premade_only(self):
        """Premade voices only, short names, a description each, the current one marked."""
        with mock.patch.object(tc, "_fetch", return_value=VOICES):
            got = tc.list_voices()
        self.assertIn("Sarah (now): female, american", got)
        self.assertIn("George: Warm British storyteller", got)
        self.assertNotIn("Clone", got)

    def test_headless_never_fetches(self):
        """Headless, the real _fetch returns nothing without opening a connection."""
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            self.assertIn("couldn't reach", tc.list_voices())

    def test_set_voice(self):
        """A known name writes its id into character.json and keeps everything else."""
        with mock.patch.object(tc, "_fetch", return_value=VOICES):
            self.assertEqual(tc.set_voice("george"), "Okay, I'm George now.")
        self.assertEqual(self.data()["voice_id"], "georgeid")
        self.assertEqual(self.data()["look"], "a woman with red hair")

    def test_set_voice_unknown(self):
        """An unknown name changes nothing and names the close ones."""
        with mock.patch.object(tc, "_fetch", return_value=VOICES):
            got = tc.set_voice("Georgie")
        self.assertIn("George", got)
        self.assertIn("don't have a voice called Georgie", got)
        self.assertEqual(self.data()["voice_id"], "sarahid")

    def test_restyle_stages_and_names_the_cost(self):
        """The new portrait lands in staged/, the live one is untouched, the reply names the cost."""
        seen = []

        def fake(argv):
            """portrait.sh stand-in: writes a portrait and its url into the folder it was given."""
            seen.append(argv)
            for name, body in (("portrait.png", b"new"), ("portrait.url", b"https://x/p.png")):
                with open(os.path.join(argv[1], name), "wb") as f:
                    f.write(body)
            return True, "portrait ok"
        with mock.patch.object(tc, "_run", side_effect=fake):
            got = tc.restyle("ginger with glasses")
        self.assertIn("5 cents", got)
        self.assertTrue(seen[0][0].endswith("portrait.sh"))
        self.assertIn("a woman with red hair. Change only this: ginger with glasses.", seen[0][2])
        self.assertEqual(_read(os.path.join(self.dir, "portrait.png")), b"old")
        self.assertEqual(_read(os.path.join(self.dir, "staged", "portrait.png")), b"new")

    def test_restyle_failure_changes_nothing(self):
        """A failed render leaves no staging folder and says nothing changed."""
        with mock.patch.object(tc, "_run", return_value=(False, "portrait failed")):
            self.assertIn("Nothing changed", tc.restyle("ginger"))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "staged")))

    def test_headless_never_renders(self):
        """Headless, the real _run never starts a script."""
        with mock.patch("subprocess.run", side_effect=AssertionError("ran")):
            self.assertIn("Nothing changed", tc.restyle("ginger"))

    def test_keep_look(self):
        """Both loops render into staging, then the staged look goes live and the old one is kept."""
        stage = os.path.join(self.dir, "staged")
        os.makedirs(stage)
        for name, body in (("portrait.png", b"new"), ("portrait.url", b"u"), ("look.txt", b"ginger look\n")):
            with open(os.path.join(stage, name), "wb") as f:
                f.write(body)
        kinds = []

        def fake(argv):
            """loop.sh stand-in: writes <kind>.mp4 into the staging folder."""
            kinds.append(argv[2])
            with open(os.path.join(argv[1], argv[2] + ".mp4"), "wb") as f:
                f.write(b"mp4")
            return True, "ok"
        with mock.patch.object(tc, "_run", side_effect=fake):
            got = tc.keep_look()
        self.assertEqual(kinds, ["idle", "talk"])
        self.assertIn("$1.40", got)
        self.assertEqual(_read(os.path.join(self.dir, "portrait.png")), b"new")
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "talk.mp4")))
        self.assertFalse(os.path.exists(stage))
        self.assertEqual(self.data()["look"], "ginger look")
        backups = os.listdir(os.path.join(self.dir, "old"))
        self.assertEqual(_read(os.path.join(self.dir, "old", backups[0], "portrait.png")), b"old")

    def test_keep_look_without_staging(self):
        """Nothing staged: says so and never renders."""
        with mock.patch.object(tc, "_run", side_effect=AssertionError("ran")):
            self.assertIn("no new look waiting", tc.keep_look())

    def test_keep_look_failed_loop_keeps_old(self):
        """A loop that fails leaves the live look alone."""
        stage = os.path.join(self.dir, "staged")
        os.makedirs(stage)
        for name in ("portrait.png", "portrait.url"):
            open(os.path.join(stage, name), "wb").close()
        with mock.patch.object(tc, "_run", return_value=(False, "idle failed")):
            self.assertIn("old look stays", tc.keep_look())
        self.assertEqual(_read(os.path.join(self.dir, "portrait.png")), b"old")


class Wiring(unittest.TestCase):
    """Routes, classification, and the price in every confirm."""

    def test_routes(self):
        """Each phrasing lands on its tool with the right argument."""
        self.assertEqual(tools.plan("what voices do you have"), [("list_voices", ())])
        self.assertEqual(tools.plan("change your voice to George"), [("set_voice", ("George",))])
        self.assertEqual(tools.plan("change your look: ginger with glasses"), [("restyle", ("ginger with glasses",))])
        self.assertEqual(tools.plan("make yourself ginger"), [("restyle", ("ginger",))])
        self.assertEqual(tools.plan("keep that look"), [("keep_look", ())])

    def test_classified(self):
        """Every write asks first; the paid ones never reach a model or MCP."""
        self.assertTrue({"set_voice", "restyle", "keep_look"} <= tools.WRITES)
        self.assertTrue({"restyle", "keep_look"} <= tools.NOT_FOR_MODELS)
        self.assertNotIn("list_voices", tools.WRITES)

    def test_confirm_names_the_cost(self):
        """The terminal line and the GUI confirm both carry the price; a free write carries none."""
        self.assertIn("5 cents", harness.confirm_line("restyle", ("ginger",)))
        self.assertIn("$1.40", harness.confirm_line("keep_look", ()))
        self.assertEqual(harness.confirm_line("new_note", ("milk",)), "Run new_note(milk)?")
        lines = iter([json.dumps({"ask": "make yourself ginger"}), json.dumps({"yes": False})])
        got = []
        chat_pipe.run(lambda: next(lines, None), got.append,
                      lambda q, log, confirm: "Okay, I will not." if not confirm("restyle", ("ginger",)) else "done")
        self.assertIn("5 cents", got[0]["confirm"]["note"])

    def test_gui_switches(self):
        """/voice and /face never reach the harness: a mode line, then her one-line answer, each time."""
        import face
        lines = iter([json.dumps({"ask": "/voice"}), json.dumps({"ask": "/face"}), json.dumps({"ask": "voice off"})])
        got = []
        with mock.patch.object(face, "available", return_value=[]):
            chat_pipe.run(lambda: next(lines, None), got.append, lambda q, log, confirm: self.fail("reached the harness"))
        self.assertEqual(got[0], {"mode": {"voice": True, "face": False}})
        self.assertIn("Voice on", got[1]["answer"])
        self.assertIn("No face yet", got[3]["answer"])
        self.assertEqual(got[4], {"mode": {"voice": False, "face": False}})

    def test_saying_no_renders_nothing(self):
        """No to the confirm: no script, no fetch, the polite refusal."""
        with mock.patch.object(tc, "_run", side_effect=AssertionError("ran")), mock.patch.object(tc, "_fetch", side_effect=AssertionError("fetched")):
            for q in ("make yourself ginger", "keep that look", "change your voice to george"):
                self.assertEqual(harness.Session(confirm=lambda n, a: False, log=lambda l: None).ask(q), "Okay, I will not.")


if __name__ == "__main__":
    unittest.main()
