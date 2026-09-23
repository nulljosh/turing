"""ask_claude: hands a hard question to the biggest local model. A fake urlopen stands in, so no test needs oMLX or Ollama.

Run: python3 test_claude.py
"""
import io
import json
import os
import sys
import urllib.error
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness
import tools
import tools_claude


class FakeServers:
    """Stands in for urlopen: each local server (oMLX, Ollama) answers or fails as told, and every request is recorded."""

    def __init__(self, omlx=None, ollama=None):
        """What each server answers with (a dict) or raises (an exception). None means it is not running."""
        self.by_url = {tools_claude.OMLX_CHAT: omlx, tools_claude.OLLAMA_CHAT: ollama}
        self.calls = []

    def __call__(self, req, timeout=None):
        """One request: record which server and body, then fail or answer."""
        self.calls.append((req.full_url, json.loads(req.data)))
        got = self.by_url[req.full_url]
        if got is None:
            raise urllib.error.URLError("refused")
        if isinstance(got, Exception):
            raise got
        return io.BytesIO(json.dumps(got).encode())


def omlx(text, finish="stop"):
    """A reply shaped like oMLX's OpenAI-style chat."""
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}


def ollama(text, done="stop"):
    """A reply shaped like Ollama's /api/chat."""
    return {"message": {"role": "assistant", "content": text}, "done_reason": done}


def http(code):
    """An HTTP error from a local server."""
    return urllib.error.HTTPError("http://localhost", code, "", {}, None)


class AskClaude(unittest.TestCase):
    """What she says back, for every way the call can go."""

    def ask(self, question, **servers):
        """Ask through fake local servers; returns the reply and the fake, to read what was sent."""
        f = FakeServers(**servers)
        with mock.patch("urllib.request.urlopen", f):
            return tools_claude.ask_claude(question), f

    def test_omlx_answers_first_and_is_named(self):
        """oMLX is asked first, the answer names its model, and the request stays on this Mac."""
        reply, f = self.ask("why is the sky blue", omlx=omlx("<think>hmm</think>Rayleigh scattering."), ollama=ollama("never"))
        self.assertEqual(reply, f"Rayleigh scattering.\n(Answered by {tools_claude.MODEL} on this Mac, not by me.)")
        self.assertEqual([u for u, _ in f.calls], [tools_claude.OMLX_CHAT])
        self.assertEqual(f.calls[0][1]["messages"][-1], {"role": "user", "content": "why is the sky blue"})
        self.assertTrue(all(u.startswith("http://localhost:") for u in (tools_claude.OMLX_CHAT, tools_claude.OLLAMA_CHAT)))

    def test_ollama_when_omlx_is_down(self):
        """No oMLX, or oMLX erroring: Ollama answers and is named."""
        for down in (None, http(500)):
            reply, f = self.ask("q", omlx=down, ollama=ollama("Because."))
            self.assertEqual(reply, f"Because.\n(Answered by {tools_claude.OLLAMA_MODEL} on this Mac, not by me.)")
            self.assertEqual(f.calls[-1][1]["model"], tools_claude.OLLAMA_MODEL)

    def test_cut_and_empty(self):
        """A cut answer says so, an empty one is not passed off as an answer."""
        self.assertIn("cut short", self.ask("q", omlx=omlx("partial", finish="length"))[0])
        self.assertIn("cut short", self.ask("q", ollama=ollama("partial", done="length"))[0])
        self.assertEqual(self.ask("q", omlx=omlx("   "))[0], f"{tools_claude.MODEL} sent back no answer.")

    def test_every_error_is_a_sentence(self):
        """Nothing running, model missing, server error, still loading, a garbled reply: each gets an honest reply."""
        self.assertIn("could not reach a local model", self.ask("q")[0])
        self.assertIn("ollama pull", self.ask("q", ollama=http(404))[0])
        self.assertIn("error 500", self.ask("q", omlx=http(500), ollama=http(500))[0])
        self.assertIn("still loading", self.ask("q", omlx=TimeoutError())[0])
        self.assertIn("could not reach a local model", self.ask("q", omlx={"weird": 1})[0])

    def test_empty_and_huge(self):
        """Nothing asked, and a question over the limit: neither reaches a model."""
        self.assertEqual(tools_claude.ask_claude("   "), 'Ask what? Say it like "ask claude why the sky is blue".')
        reply, f = self.ask("x" * (tools_claude.LIMIT + 1), omlx=omlx("never"))
        self.assertIn("too long", reply)
        self.assertEqual(f.calls, [])


class OnlyWithAYes(unittest.TestCase):
    """The harness asks before handing it over, and no model or MCP client can reach the tool."""

    def test_asks_first_and_a_no_sends_nothing(self):
        """A no sends nothing; a yes sends the question once."""
        m = FakeServers(omlx=omlx("Because."))
        asked = []
        with mock.patch("urllib.request.urlopen", m):
            no = harness.Session(confirm=lambda n, a: asked.append((n, a)) or False, log=lambda l: None).ask("ask claude why is the sky blue")
            self.assertEqual((no, m.calls), ("Okay, I will not.", []))
            yes = harness.Session(confirm=lambda n, a: True, log=lambda l: None).ask("claude, why is the sky blue")
        self.assertEqual(asked, [("ask_claude", ("why is the sky blue",))])
        self.assertTrue(yes.startswith("Because.") and len(m.calls) == 1)

    def test_hidden_from_models_and_mcp(self):
        """Only by name: never on a model's menu, never served over MCP, always a write."""
        import mcp_server
        self.assertIn("ask_claude", tools.WRITES & tools.NOT_FOR_MODELS)
        self.assertNotIn("ask_claude", tools.model_tools())
        self.assertNotIn("ask_claude", {t["name"] for t in mcp_server._tools()})

    def test_routes(self):
        """The ways people name her, and the sentences that only mention Claude."""
        self.assertEqual(tools.plan("ask claude why is the sky blue"), [("ask_claude", ("why is the sky blue",))])
        self.assertEqual(tools.plan("have claude write a haiku"), [("ask_claude", ("write a haiku",))])
        self.assertEqual(tools.plan("claude: what is a monad"), [("ask_claude", ("what is a monad",))])
        self.assertEqual(tools.plan("ask claude"), [])  # nothing to ask, so nothing is sent
        self.assertEqual(tools.do("ask claude"), 'Ask what? Say it like "ask claude why the sky is blue".')
        self.assertEqual(tools.plan("claude shannon invented information theory"), [])


if __name__ == "__main__":
    unittest.main()
