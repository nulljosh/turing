"""Serve Samantha over the OpenAI chat API shape, so other apps can use her.

Samantha has only ever been reachable by running chat.py in a terminal.
Nimble (and most local-LLM tooling) already speaks one wire format: POST
/v1/chat/completions, read choices[0].message.content. Implementing that
here means Nimble needs no changes at all, it just points its Ollama engine
at this port instead. Anything else that talks to Ollama or OpenAI works the
same way, which is the actual test of whether this model is usable outside
its own repo.

Stdlib http.server on purpose. This is a personal single-user endpoint on
localhost, not a production server; a framework would be a dependency for
nothing.

Run: ./.venv/bin/python serve.py [--port 8127]
Then in Nimble, choose the Ollama engine and set its base URL to
http://localhost:8127

Declines map to "UNKNOWN", which is Nimble's own signal for "this engine
had nothing", so it falls through to another engine instead of showing the
user a refusal sentence.
"""
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import ask
from ask import OUT_OF_SCOPE, LOOKUP_FAILED, NETWORK_DOWN, _CANT_PIN_DOWN

MODEL_NAME = "samantha"
DECLINES = (OUT_OF_SCOPE, LOOKUP_FAILED, NETWORK_DOWN, _CANT_PIN_DOWN)


def answer_for(question):
    """Get an answer from ask(), return UNKNOWN for declines or errors."""
    if not question:
        return "UNKNOWN", None
    answer, sources = ask(question)
    answer = (answer or "").strip()
    if not answer or answer in DECLINES:
        return "UNKNOWN", None
    return answer, sources


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler for the OpenAI chat API compatible server."""
    def _send(self, payload, status=200):
        """Send a JSON response with CORS headers."""
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        # A browser-based caller (Nimble's web build at docs/engine.js) is
        # same-origin-blocked without these, and this only ever listens on
        # localhost. allow-methods is not optional: a POST carrying
        # content-type: application/json triggers a preflight, and Chrome
        # rejects the preflight outright if the response doesn't name the
        # method. Confirmed missing here, which meant the native Nimble
        # build worked over HTTP while the web build could not have called
        # this at all.
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
        self.send_header("access-control-allow-headers", "content-type, authorization")
        self.send_header("access-control-max-age", "86400")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight request."""
        self._send({})

    def do_GET(self):
        """Handle GET /v1/models to list available models."""
        if self.path.rstrip("/") == "/v1/models":
            self._send({"object": "list", "data": [
                {"id": MODEL_NAME, "object": "model", "owned_by": "turing"}]})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        """Handle POST /v1/chat/completions to answer questions."""
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send({"error": "not found"}, 404)
            return
        try:
            raw = self.rfile.read(int(self.headers.get("content-length") or 0))
            payload = json.loads(raw or b"{}")
        except Exception:
            self._send({"error": "bad request"}, 400)
            return

        # the caller's system prompt is ignored on purpose: Samantha has her
        # own SYSTEM persona and a fixed answer pipeline, and pretending to
        # honour an arbitrary one would be a lie about what this serves
        question = ""
        for message in payload.get("messages", []):
            if message.get("role") == "user":
                question = (message.get("content") or "").strip()

        answer, sources = answer_for(question)
        self._send({
            "id": f"samantha-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }],
            "turing_sources": sources or [],
        })

    def log_message(self, fmt, *args):
        """Log HTTP requests to stderr instead of stdout."""
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")


def main():
    """Start the HTTP server on port 8127 (or --port argument)."""
    port = 8127
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Samantha on http://localhost:{port} (OpenAI chat shape)")
    print("Nimble: pick the Ollama engine, set base URL to that address.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
