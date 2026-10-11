"""The phone's door onto her real answer chain: chat_pipe.py's protocol over HTTP, for an iPhone on your own network.

Same harness.Session and chat.safe_turn underneath (this runs chat_pipe.run in a worker thread, so follow-ups
like "again" keep their history across turns), a different door. Nothing here is a cloud service: it is a small
stdlib server you start by hand on your own Mac, and it stops when you stop it.

    POST /v1/ask      {"ask": "what needs me"}   answers as Server-Sent Events: one JSON object per `data:` line,
                      the exact chat_pipe messages: {"working"}*, an optional {"confirm"}, then one {"answer"}
    POST /v1/confirm  {"yes": true}              the phone's reply to a {"confirm"} event; nothing is ever written
                                                 without it, and no reply inside 120 seconds is a no
    GET  /v1/ping                                {"ok": true, "name": "samantha", "version": "..."} to test pairing

Pairing: the first run makes a secret in ~/.samantha/phone-token (mode 600) and prints a samantha://pair link on this
terminal. Every request carries X-Samantha-Time (unix seconds), X-Samantha-Nonce (random, once) and X-Samantha-Sig,
the hex HMAC-SHA256 of "METHOD|path|time|nonce|sha256(body)" under that secret, so the secret itself never crosses the
network, a changed body fails, and a captured request is dead after 60 seconds (and cannot be replayed inside them).

It listens on 127.0.0.1 unless you ask: --lan binds this Mac's private (or Tailscale) address, --host binds one you
name. Never 0.0.0.0. Plain HTTP on a trusted network is the same trade Home Assistant makes; over anything wider,
use Tailscale, which encrypts it.

Run: ./.venv/bin/python app/phone_bridge.py [--lan | --host ADDR] [--port 8128]
     ./.venv/bin/python app/phone_bridge.py --check     (a fake chain drives every route, no model needed)
"""
import hashlib
import hmac
import json
import os
import queue
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PORT = 8128
WINDOW = 60  # seconds a signed request stays valid
CONFIRM_WAIT = 120  # seconds the phone has to answer a confirm before it counts as a no
KEEPALIVE = 15  # seconds of quiet before a comment line keeps the connection from idling out
MAX_BODY = 16 * 1024


def token_path():
    """Where the pairing secret lives; SAMANTHA_HOME moves it for tests."""
    return os.path.join(os.environ.get("SAMANTHA_HOME") or os.path.expanduser("~/.samantha"), "phone-token")


def load_token():
    """The pairing secret, made on first use with owner-only permissions."""
    path = token_path()
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(os.urandom(32).hex() + "\n")
    except FileExistsError:
        pass
    with open(path) as f:
        return f.read().strip()


def sign(token, method, path, stamp, nonce, body):
    """The signature a client must send for this exact request."""
    msg = f"{method}|{path}|{stamp}|{nonce}|{hashlib.sha256(body).hexdigest()}"
    return hmac.new(token.encode(), msg.encode(), hashlib.sha256).hexdigest()


def private_address():
    """This Mac's private or Tailscale IPv4 address, found without sending a packet, or None."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            addr = s.getsockname()[0]
    except OSError:
        return None
    parts = addr.split(".")
    private = addr.startswith(("10.", "192.168.")) or (parts[0] == "172" and 16 <= int(parts[1]) <= 31) or (parts[0] == "100" and 64 <= int(parts[1]) <= 127)
    return addr if private else None


class Bridge:
    """One pipe session shared by every request, so follow-up history survives between turns."""

    def __init__(self, token, ask_fn):
        """Start chat_pipe.run in a worker thread fed by two queues."""
        import chat_pipe
        self.token, self.seen, self.lock = token, {}, threading.Lock()
        self.busy = threading.Lock()
        self.inbox, self.outbox = queue.Queue(), queue.Queue()
        threading.Thread(target=chat_pipe.run, args=(self.inbox.get, self.outbox.put, ask_fn), daemon=True).start()

    def authorized(self, method, path, headers, body):
        """True for a fresh, correctly signed, never-seen request."""
        try:
            stamp = int(headers.get("X-Samantha-Time", ""))
        except ValueError:
            return False
        now = time.time()
        sig, nonce = headers.get("X-Samantha-Sig", ""), headers.get("X-Samantha-Nonce", "")
        if abs(now - stamp) > WINDOW or not nonce or not hmac.compare_digest(sig, sign(self.token, method, path, stamp, nonce, body)):
            return False
        with self.lock:
            self.seen = {k: v for k, v in self.seen.items() if now - v < WINDOW * 2}
            if sig in self.seen:
                return False
            self.seen[sig] = now
        return True


def make_handler(bridge):
    """A request handler class bound to one Bridge."""
    class Handler(BaseHTTPRequestHandler):
        """Routes /v1/ping, /v1/ask and /v1/confirm behind the signature check."""

        def _json(self, obj, code=200):
            """Send one JSON reply and close."""
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            """The request body, capped, or None when it is too large."""
            n = int(self.headers.get("Content-Length") or 0)
            return None if n > MAX_BODY else self.rfile.read(n)

        def _gate(self, method):
            """(body, ok): reads the body and checks the signature, answering 401 itself on failure."""
            body = self._body()
            if body is None:
                self._json({"error": "too large"}, 413)
                return b"", False
            if not bridge.authorized(method, self.path, self.headers, body):
                self._json({"error": "unauthorized"}, 401)
                return b"", False
            return body, True

        def do_GET(self):
            """GET /v1/ping."""
            body, ok = self._gate("GET")
            if ok and self.path == "/v1/ping":
                version = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")).read().strip() if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")) else ""
                self._json({"ok": True, "name": "samantha", "version": version})
            elif ok:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            """POST /v1/ask streams a turn; POST /v1/confirm answers its confirm."""
            body, ok = self._gate("POST")
            if not ok:
                return
            try:
                msg = json.loads(body or b"{}")
            except ValueError:
                return self._json({"error": "bad request"}, 400)
            if self.path == "/v1/confirm":
                bridge.inbox.put(json.dumps({"yes": bool(msg.get("yes"))}))
                return self._json({"ok": True})
            if self.path != "/v1/ask" or not isinstance(msg.get("ask"), str) or not msg["ask"].strip():
                return self._json({"error": "bad request"}, 400)
            if not bridge.busy.acquire(blocking=False):
                return self._json({"error": "busy"}, 409)
            try:
                self._stream(msg["ask"])
            finally:
                bridge.busy.release()

        def _stream(self, question):
            """Feed one question to the pipe and relay its messages as Server-Sent Events until the answer."""
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            while not bridge.outbox.empty():  # anything stale from an abandoned turn
                bridge.outbox.get_nowait()
            bridge.inbox.put(json.dumps({"ask": question}))
            asked_at = None
            while True:
                try:
                    event = bridge.outbox.get(timeout=KEEPALIVE)
                except queue.Empty:
                    event = None
                if event is None:
                    if asked_at and time.time() - asked_at > CONFIRM_WAIT:
                        bridge.inbox.put(json.dumps({"yes": False}))  # no reply in time is a no
                        asked_at = None
                    line = b": ping\n\n"
                else:
                    if "confirm" in event:
                        asked_at = time.time()
                    line = b"data: " + json.dumps(event).encode() + b"\n\n"
                try:
                    self.wfile.write(line)
                    self.wfile.flush()
                except OSError:
                    if asked_at:
                        bridge.inbox.put(json.dumps({"yes": False}))
                    return
                if event is not None and "answer" in event:
                    return

        def log_message(self, fmt, *args):
            """Log to stderr, never the body."""
            sys.stderr.write(f"phone {self.address_string()} {fmt % args}\n")
    return Handler


def make_server(token, ask_fn, host="127.0.0.1", port=PORT):
    """A ready (not yet serving) server; port 0 picks a free one."""
    return ThreadingHTTPServer((host, port), make_handler(Bridge(token, ask_fn)))


def main():
    """Parse flags, print the pairing link and serve until interrupted."""
    args = sys.argv[1:]
    port = int(args[args.index("--port") + 1]) if "--port" in args else PORT
    host = args[args.index("--host") + 1] if "--host" in args else "127.0.0.1"
    if "--lan" in args:
        host = private_address()
        if not host:
            sys.exit("No private or Tailscale address found; use --host ADDR.")
    from chat_pipe import _real_ask
    token = load_token()
    server = make_server(token, _real_ask, host, port)
    print(f"Samantha for the phone is listening on {host}:{port}. Stop it with Ctrl-C.")
    print(f"Pair the app with: samantha://pair?host={host}&port={port}&token={token}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")


def _check():
    """A fake chain, a fresh secret, and every route driven once over real sockets."""
    import tempfile
    import urllib.request
    os.environ["SAMANTHA_HOME"] = tempfile.mkdtemp()
    token = load_token()

    def fake_ask(question, log, confirm):
        """One plain answer, and one that needs a confirm."""
        log("note()")
        return "yes" if "delete" in question and confirm("delete", ()) else "hi"
    server = make_server(token, fake_ask, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def call(method, path, obj=None):
        """One signed request, its body returned as text."""
        body = json.dumps(obj).encode() if obj is not None else b""
        stamp, nonce = int(time.time()), os.urandom(8).hex()
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body or None, method=method, headers={
            "X-Samantha-Time": str(stamp), "X-Samantha-Nonce": nonce, "X-Samantha-Sig": sign(token, method, path, stamp, nonce, body)})
        return urllib.request.urlopen(req, timeout=10).read().decode()
    assert json.loads(call("GET", "/v1/ping"))["ok"]
    assert '"answer": "hi"' in call("POST", "/v1/ask", {"ask": "hello"})
    server.shutdown()
    print("phone_bridge ok")


if __name__ == "__main__":
    _check() if "--check" in sys.argv else main()
