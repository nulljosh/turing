"""ElevenLabs voice: key set and call works -> afplay the mp3; no key or a failed call -> macOS say."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import voice


def test_speaker():
    os.environ.pop("ELEVENLABS_API_KEY", None)
    assert voice.speaker("hi") == ["say", "hi"]
    os.environ["ELEVENLABS_API_KEY"] = "k"
    seen = {}
    def ok(req):
        seen["key"] = req.get_header("Xi-api-key")
        return b"ID3fake"
    cmd = voice.speaker("hi", fetch=ok)
    assert cmd[0] == "afplay" and open(cmd[1], "rb").read() == b"ID3fake" and seen["key"] == "k"
    os.remove(cmd[1])
    def boom(req):
        raise OSError("down")
    assert voice.speaker("hi", fetch=boom) == ["say", "hi"]
    os.environ.pop("ELEVENLABS_API_KEY")


if __name__ == "__main__":
    test_speaker()
    print("PASS: ElevenLabs voice with say fallback")
