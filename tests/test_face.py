"""app/face.py on a temp character: the page lists only media that exists, /state follows set_state,
allowed media is served, anything else (other files, path tricks) is a 404."""
import os
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import face


def get(url):
    """Status and body of a GET, 404s included."""
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def test_face():
    """Serve a character with only idle.mp4 and a secret file; check what the page can and cannot reach."""
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "idle.mp4"), "wb").write(b"fakevideo")
        open(os.path.join(d, "secret.txt"), "w").write("no")
        server = face.serve(port=0, character=d)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            code, page = get(base + "/")
            assert code == 200 and b'["idle.mp4"]' in page and b"<video" in page
            face.set_state("talk")
            assert get(base + "/state") == (200, b"talk")
            face.set_state("dance")  # not a state: ignored
            assert get(base + "/state") == (200, b"talk")
            face.set_state("idle")
            assert get(base + "/media/idle.mp4") == (200, b"fakevideo")
            assert get(base + "/media/secret.txt")[0] == 404
            assert get(base + "/media/../secret.txt")[0] == 404
            assert get(base + "/media/talk.mp4")[0] == 404  # allowed name, not on disk
        finally:
            server.shutdown()


if __name__ == "__main__":
    test_face()
    print("PASS: face window serves only her media and follows her state")
