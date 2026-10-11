"""The phone bridge: signed requests, the event stream, and the confirm round trip, all over real sockets.
No model: a scripted answer chain stands in for harness and chat.

Run: python3 tests/test_phone_bridge.py
"""
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

os.environ["SAMANTHA_HEADLESS"] = "1"
os.environ["SAMANTHA_HOME"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import phone_bridge  # noqa: E402


def fake_ask(question, log, confirm):
    """Two kinds of turn: a plain answer, and one that asks before it writes."""
    log("note()")
    if "delete" in question:
        return "Deleted." if confirm("trash_file", ("x",)) else "Left it alone."
    return "hi"


class Bridge(unittest.TestCase):
    """One server for the class, a fresh signature per request."""
    @classmethod
    def setUpClass(cls):
        """Start the bridge on a free localhost port with the scripted chain."""
        cls.token = phone_bridge.load_token()
        cls.server = phone_bridge.make_server(cls.token, fake_ask, port=0)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        """Stop serving."""
        cls.server.shutdown()

    def request(self, method, path, obj=None, stamp=None, nonce=None, sig=None):
        """One request, signed unless a bad signature, stamp or nonce is forced; returns (status, body text)."""
        body = json.dumps(obj).encode() if obj is not None else b""
        stamp = int(time.time()) if stamp is None else stamp
        nonce = os.urandom(8).hex() if nonce is None else nonce
        sig = phone_bridge.sign(self.token, method, path, stamp, nonce, body) if sig is None else sig
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body or None, method=method,
                                     headers={"X-Samantha-Time": str(stamp), "X-Samantha-Nonce": nonce, "X-Samantha-Sig": sig})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read().decode()

    def events(self, text):
        """The JSON objects on the data lines of one event stream, in order."""
        return [json.loads(l[6:]) for l in text.splitlines() if l.startswith("data: ")]

    def test_token_file_is_private(self):
        """The secret is created once, owner-only, and never empty."""
        path = phone_bridge.token_path()
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
        self.assertEqual(len(self.token), 64)
        self.assertEqual(phone_bridge.load_token(), self.token)

    def test_ping_needs_a_good_signature(self):
        """A right signature pings; a wrong one, a stale stamp and a reused one are all 401."""
        status, body = self.request("GET", "/v1/ping")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])
        self.assertEqual(self.request("GET", "/v1/ping", sig="0" * 64)[0], 401)
        self.assertEqual(self.request("GET", "/v1/ping", stamp=int(time.time()) - 600)[0], 401)
        stamp, nonce = int(time.time()), "abc123"
        sig = phone_bridge.sign(self.token, "GET", "/v1/ping", stamp, nonce, b"")
        self.assertEqual(self.request("GET", "/v1/ping", stamp=stamp, nonce=nonce, sig=sig)[0], 200)
        self.assertEqual(self.request("GET", "/v1/ping", stamp=stamp, nonce=nonce, sig=sig)[0], 401)  # replay
        self.assertEqual(self.request("GET", "/v1/ping", stamp=stamp, nonce="", sig=sig)[0], 401)  # no nonce

    def test_signature_covers_the_body(self):
        """A signature made for one body does not pass with another."""
        stamp, nonce = int(time.time()), "n1"
        sig = phone_bridge.sign(self.token, "POST", "/v1/ask", stamp, nonce, json.dumps({"ask": "hello"}).encode())
        self.assertEqual(self.request("POST", "/v1/ask", {"ask": "delete it"}, stamp=stamp, nonce=nonce, sig=sig)[0], 401)

    def test_ask_streams_working_then_answer(self):
        """One turn: the tool step first, the answer last, nothing after it."""
        status, body = self.request("POST", "/v1/ask", {"ask": "hello"})
        self.assertEqual(status, 200)
        self.assertEqual(self.events(body), [{"working": "note()"}, {"answer": "hi"}])

    def test_confirm_round_trip(self):
        """A write waits for the phone's yes; the stream carries the confirm, then the answer."""
        got = {}

        def ask():
            """The streaming request, on its own thread because it blocks on the confirm."""
            got["status"], got["body"] = self.request("POST", "/v1/ask", {"ask": "delete it"})
        t = threading.Thread(target=ask)
        t.start()
        time.sleep(0.5)
        self.assertEqual(self.request("POST", "/v1/confirm", {"yes": True})[0], 200)
        t.join(10)
        self.assertEqual(self.events(got["body"])[-2:], [{"confirm": {"name": "trash_file", "args": ["x"]}}, {"answer": "Deleted."}])
        t = threading.Thread(target=ask)
        t.start()
        time.sleep(0.5)
        self.request("POST", "/v1/confirm", {"yes": False})
        t.join(10)
        self.assertEqual(self.events(got["body"])[-1], {"answer": "Left it alone."})

    def test_bad_asks(self):
        """An empty ask, a non-string ask and an unknown path are 400 or 404, never a crash."""
        self.assertEqual(self.request("POST", "/v1/ask", {"ask": ""})[0], 400)
        self.assertEqual(self.request("POST", "/v1/ask", {"ask": 7})[0], 400)
        self.assertEqual(self.request("GET", "/v1/nope")[0], 404)

    def test_binds_localhost_by_default(self):
        """Without --lan the server only listens on the loopback address."""
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertIn(phone_bridge.private_address(), (None,) + tuple(a for a in [phone_bridge.private_address()] if a and not a.startswith("127.")))

    def test_sha_in_signature_is_body_hash(self):
        """The signed message hashes the body, so the secret never has to cross the wire."""
        body = b'{"ask":"x"}'
        msg = f"GET|/v1/ping|1|n|{hashlib.sha256(body).hexdigest()}"
        self.assertEqual(len(phone_bridge.sign(self.token, "GET", "/v1/ping", 1, "n", body)), 64)
        self.assertIn(hashlib.sha256(body).hexdigest(), msg)


if __name__ == "__main__":
    unittest.main()
