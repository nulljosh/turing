"""ElevenLabs voice: key set and call works -> afplay the mp3; no key or a failed call -> macOS say."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import tempfile
import voice
voice.SECRETS = "/nonexistent/secrets.fish"  # tests never read the real key
voice.CACHE_DIR = tempfile.mkdtemp()  # never touch the real cache
os.environ["SAMANTHA_CHARACTER"] = tempfile.mkdtemp()  # never read the real character either


def test_current_voice():
    """The env var wins, then the character's voice_id, then Sarah when there is no file or it is broken."""
    import json
    os.environ.pop("ELEVENLABS_VOICE", None)
    path = os.path.join(os.environ["SAMANTHA_CHARACTER"], "character.json")
    assert voice.current_voice() == voice.ELEVEN_VOICE  # no character.json yet
    with open(path, "w") as f:
        f.write("{not json")
    assert voice.current_voice() == voice.ELEVEN_VOICE
    with open(path, "w") as f:
        json.dump({"voice_id": "georgeid"}, f)
    assert voice.current_voice() == "georgeid"
    os.environ["ELEVENLABS_VOICE"] = "envid"
    assert voice.current_voice() == "envid"
    os.environ.pop("ELEVENLABS_VOICE")
    os.remove(path)


def test_speaker():
    """No key says it with say; a key and a good call plays the mp3; a failed call falls back to say."""
    os.environ.pop("ELEVENLABS_API_KEY", None)
    assert voice.speaker("hi") == ["say", "hi"]
    os.environ["ELEVENLABS_API_KEY"] = "k"
    seen = {}
    def ok(req):
        """A fake ElevenLabs that answers with mp3 bytes and records the key header."""
        seen["key"] = req.get_header("Xi-api-key")
        return b"ID3fake"
    cmd = voice.speaker("hi", fetch=ok)
    assert cmd[0] == "afplay" and open(cmd[1], "rb").read() == b"ID3fake" and seen["key"] == "k"
    def never(req):
        """A second call for the same line must never reach the network."""
        raise AssertionError("cached line fetched again")
    assert voice.speaker("hi", fetch=never) == cmd  # same line: replayed from the cache
    os.remove(cmd[1])
    def boom(req):
        """A fake ElevenLabs that is down."""
        raise OSError("down")
    assert voice.speaker("hi", fetch=boom) == ["say", "hi"]
    os.environ.pop("ELEVENLABS_API_KEY")


def test_key_from_secrets():
    """No key in the environment: the fish secrets line is read instead; a missing file or line means no key."""
    os.environ.pop("ELEVENLABS_API_KEY", None)
    d = tempfile.mkdtemp()
    f = os.path.join(d, "secrets.fish")
    open(f, "w").write("set -gx OTHER 'x'\nset -gx ELEVENLABS_API_KEY 'sk_test123'\n")
    assert voice.eleven_key(f) == "sk_test123"
    open(f, "w").write("set -gx OTHER 'x'\n")
    assert voice.eleven_key(f) is None
    assert voice.eleven_key(os.path.join(d, "missing")) is None
    os.environ["ELEVENLABS_API_KEY"] = "env"
    assert voice.eleven_key(f) == "env"
    os.environ.pop("ELEVENLABS_API_KEY")


if __name__ == "__main__":
    test_key_from_secrets()
    test_current_voice()
    test_speaker()
    print("PASS: ElevenLabs voice with say fallback")
