"""Her face while you talk: a small local page that loops the character's idle video and switches to the
talking video while her voice plays (the listening video while the mic is open). The videos are rendered
once by the character-creator skill into ~/.samantha/characters/<name>/; nothing is generated per reply.

    python3 app/chat.py --voice --face   # talk to her and watch her answer
    python3 app/face.py                  # just the window, for checking the loops

Serves on localhost only. voice.py calls set_state(); with no window open that is a harmless no-op.
"""
import http.server
import os
import sys
import threading
import webbrowser

CHARACTER = os.path.expanduser(os.environ.get("SAMANTHA_CHARACTER", "~/.samantha/characters/samantha"))
PORT = int(os.environ.get("SAMANTHA_FACE_PORT", "8766"))
MEDIA = {"idle.mp4", "listen.mp4", "talk.mp4", "portrait.png"}  # the only files the page may fetch
STATES = {"idle", "listen", "talk"}
_state = "idle"

PAGE = """<!doctype html><meta charset="utf-8"><title>Samantha</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{margin:0;height:100%;background:#faf8f4;display:grid;place-items:center}
video,img{max-width:100vw;max-height:100vh;aspect-ratio:1;object-fit:cover;border-radius:24px}
@media (prefers-color-scheme:dark){html,body{background:#141311}}</style>
<video id="v" muted loop autoplay playsinline poster="/media/portrait.png"></video>
<script>
const v = document.getElementById("v"); let shown = "";
const have = new Set(__MEDIA__);
function pick(s) { if (s === "listen" && !have.has("listen.mp4")) s = "idle"; return have.has(s + ".mp4") ? s + ".mp4" : ""; }
async function tick() {
  try {
    const s = (await (await fetch("/state", {cache: "no-store"})).text()).trim();
    const f = pick(s);
    if (f && f !== shown) { shown = f; v.src = "/media/" + f; v.play().catch(() => {}); }
  } catch (e) {}
  setTimeout(tick, 120);
}
tick();
</script>"""


def set_state(state):
    """What her face shows now: idle, listen or talk. Anything else is ignored."""
    global _state
    if state in STATES:
        _state = state


def available(character=CHARACTER):
    """The media files this character actually has on disk, from the allowed set."""
    return sorted(n for n in MEDIA if os.path.isfile(os.path.join(character, n)))


class Handler(http.server.BaseHTTPRequestHandler):
    """The page, the current state, and the character's media, nothing else."""
    character = CHARACTER

    def log_message(self, *args):
        """Quiet: the chat prints what matters."""

    def _send(self, code, body, ctype):
        """One response with a body and no caching."""
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """/ is the page, /state is idle|listen|talk, /media/<name> is one allowed file."""
        path = self.path.split("?")[0]
        if path == "/":
            import json
            return self._send(200, PAGE.replace("__MEDIA__", json.dumps(available(self.character))).encode(), "text/html; charset=utf-8")
        if path == "/state":
            return self._send(200, _state.encode(), "text/plain")
        name = path[len("/media/"):] if path.startswith("/media/") else ""
        if name in MEDIA and os.path.isfile(os.path.join(self.character, name)):
            with open(os.path.join(self.character, name), "rb") as f:
                return self._send(200, f.read(), "video/mp4" if name.endswith(".mp4") else "image/png")
        self._send(404, b"not found", "text/plain")


def serve(port=PORT, character=CHARACTER):
    """Start the face server on localhost in a background thread and return it."""
    handler = type("FaceHandler", (Handler,), {"character": character})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def start(open_window=True):
    """Serve her face and open it in the browser (never when SAMANTHA_HEADLESS=1). Returns the server or None."""
    if not available():
        print(f"No face yet: make one with the character-creator skill into {CHARACTER}.")
        return None
    try:
        server = serve()
    except OSError:
        return None  # already running from another chat, that window keeps working
    if open_window and os.environ.get("SAMANTHA_HEADLESS") != "1":
        webbrowser.open(f"http://127.0.0.1:{server.server_address[1]}/")
    return server


if __name__ == "__main__":
    if start():
        print(f"Face on http://127.0.0.1:{PORT}/  (Ctrl+C to stop)")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            sys.exit(0)
