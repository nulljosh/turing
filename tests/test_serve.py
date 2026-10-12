"""serve.py: the OpenAI-shaped endpoint other apps use, against a real HTTPServer on a free port with ask() stood in.

Run: python3 tests/test_serve.py
"""
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import serve  # noqa: E402


class Endpoint(unittest.TestCase):
    """One server for the class, one request per test."""

    @classmethod
    def setUpClass(cls):
        """A real server on 127.0.0.1 and a free port, logging silenced."""
        serve.Handler.log_message = lambda *a, **k: None
        cls.server = HTTPServer(("127.0.0.1", 0), serve.Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        """Stop serving."""
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, path, body=None, method=None):
        """(status, headers, parsed body) for one request; a 4xx comes back the same way, never raised."""
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request(self.base + path, data=data, method=method or ("POST" if data else "GET"),
                                     headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.headers, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, json.loads(e.read() or b"{}")

    def test_models_lists_samantha(self):
        """GET /v1/models names her as the one model; any other GET is a 404."""
        status, _, body = self.call("/v1/models")
        self.assertEqual(status, 200)
        self.assertEqual([m["id"] for m in body["data"]], ["samantha"])
        self.assertEqual(self.call("/v1/other")[0], 404)

    def test_preflight_names_post(self):
        """OPTIONS answers 200 with the CORS headers a browser needs, POST included."""
        status, headers, _ = self.call("/v1/chat/completions", method="OPTIONS")
        self.assertEqual(status, 200)
        self.assertEqual(headers["access-control-allow-origin"], "*")
        self.assertIn("POST", headers["access-control-allow-methods"])

    def test_completion_answers_the_last_user_message(self):
        """The last user turn is what she is asked, the system prompt is ignored, sources ride along."""
        with mock.patch.object(serve, "ask", return_value=("Paris.", ["wiki:Paris"])) as ask:
            status, _, body = self.call("/v1/chat/completions", {"messages": [
                {"role": "system", "content": "You are a pirate."},
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "..."},
                {"role": "user", "content": "capital of France?"}]})
        self.assertEqual(status, 200)
        ask.assert_called_once_with("capital of France?")
        self.assertEqual(body["choices"][0]["message"]["content"], "Paris.")
        self.assertEqual(body["turing_sources"], ["wiki:Paris"])
        self.assertEqual(body["model"], "samantha")

    def test_declines_empty_and_errors_are_unknown(self):
        """A decline sentence, an empty answer, no question at all, and a crash inside ask() all read UNKNOWN."""
        for ret in [(serve.OUT_OF_SCOPE, None), ("", None), ("   ", [])]:
            with mock.patch.object(serve, "ask", return_value=ret):
                self.assertEqual(self.call("/v1/chat/completions", {"messages": [{"role": "user", "content": "x"}]})[2]
                                 ["choices"][0]["message"]["content"], "UNKNOWN")
        with mock.patch.object(serve, "ask", side_effect=RuntimeError("model gone")):
            status, _, body = self.call("/v1/chat/completions", {"messages": [{"role": "user", "content": "x"}]})
        self.assertEqual((status, body["choices"][0]["message"]["content"]), (200, "UNKNOWN"))
        with mock.patch.object(serve, "ask", side_effect=AssertionError("asked with no question")):
            self.assertEqual(self.call("/v1/chat/completions", {"messages": []})[2]["choices"][0]["message"]["content"], "UNKNOWN")

    def test_bad_json_and_wrong_path(self):
        """Broken JSON is a 400, a POST anywhere else a 404, neither a crash."""
        self.assertEqual(self.call("/v1/chat/completions", b"{not json")[0], 400)
        self.assertEqual(self.call("/v1/embeddings", {"input": "x"})[0], 404)


class Main(unittest.TestCase):
    """main(): the port flag and a clean stop on Ctrl-C, with the server stood in."""

    def test_port_flag_and_keyboard_interrupt(self):
        """--port reaches HTTPServer; KeyboardInterrupt from serve_forever ends main() quietly."""
        fake = mock.Mock()
        fake.serve_forever.side_effect = KeyboardInterrupt
        with mock.patch.object(serve, "HTTPServer", return_value=fake) as cls, \
                mock.patch.object(serve.sys, "argv", ["serve.py", "--port", "9999"]), \
                mock.patch("builtins.print"):
            serve.main()
        cls.assert_called_once_with(("127.0.0.1", 9999), serve.Handler)


class PiAnswerTest(unittest.TestCase):
    """pi_answer(): a Joshua Tree Pi's save request gets code plus [[save NAME]], its result report ends the loop."""

    def test_save_request(self):
        """The 8.3 name comes out uppercased after the code; no model or no fence means nothing is saved."""
        code = ("Here it is.\n```c\nint main(void) { return 0; }\n```\nCompile with cc.", "Qwen")
        with mock.patch("tools_llm.fallback", return_value=code) as fb:
            got = serve.pi_answer("write hello world in C and save it as hello.c")
        self.assertTrue(got.endswith("\n[[save HELLO.C]]") and "```c" in got, got)
        self.assertNotIn("hello.c", fb.call_args[0][0])
        with mock.patch("tools_llm.fallback", return_value=None):
            self.assertIn("nothing was saved", serve.pi_answer("write a python script, save it to fib.py"))
        self.assertIsNone(serve.pi_answer("what is joshua tree"))
        self.assertIsNone(serve.pi_answer("save it as a surprise"))
        self.assertEqual(serve.pi_answer("make a file called todo.txt that says buy milk"),
                         "Here is todo.txt.\n```\nbuy milk\n```\n[[save TODO.TXT]]")

    def test_pi_results_end_the_loop(self):
        """What the Pi's actions printed comes back as a turn; she answers it in one word, with no new action."""
        self.assertEqual(serve.pi_answer("The Pi ran your actions. Results:\nsave HELLO.C: saved\n"), "Saved.")
        self.assertEqual(serve.pi_answer("The Pi ran your actions. Results:\nstatus: ip 1.2.3.4\n"), "Done.")


if __name__ == "__main__":
    unittest.main()
