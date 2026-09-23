"""ask_claude: hands a hard question to the biggest local model. A fake urlopen stands in, so no test needs Ollama.

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


class FakeOllama:
    """Stands in for urlopen: records each request body, then answers or fails as told."""

    def __init__(self, reply=None, error=None):
        """What to answer with, or what to raise."""
        self.reply, self.error, self.calls = reply, error, []

    def __call__(self, req, timeout=None):
        """One request: record its body, then fail or answer."""
        self.calls.append(json.loads(req.data))
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.reply).encode())


def answer(text, done="stop"):
    """A reply shaped like Ollama's /api/chat."""
    return {"message": {"role": "assistant", "content": text}, "done_reason": done}


class AskClaude(unittest.TestCase):
    """What she says back, for every way the call can go."""

    def ask(self, question, **fake):
        """Ask through a fake Ollama; returns the reply and the fake, to read what was sent."""
        f = FakeOllama(**fake)
        with mock.patch("urllib.request.urlopen", f):
            return tools_claude.ask_claude(question), f

    def test_an_answer_is_marked_as_the_local_models(self):
        """The text comes back with where it came from, and the request stays on this Mac."""
        reply, f = self.ask("why is the sky blue", reply=answer("<think>hmm</think>Rayleigh scattering."))
        self.assertEqual(reply, f"Rayleigh scattering.\n(Answered by {tools_claude.MODEL} on this Mac, not by me.)")
        self.assertEqual(f.calls[0]["model"], tools_claude.MODEL)
        self.assertEqual(f.calls[0]["messages"][-1], {"role": "user", "content": "why is the sky blue"})
        self.assertTrue(tools_claude.OLLAMA_CHAT.startswith("http://localhost:"))

    def test_cut_and_empty(self):
        """A cut answer says so, an empty one is not passed off as an answer."""
        self.assertIn("cut short", self.ask("q", reply=answer("partial", done="length"))[0])
        self.assertEqual(self.ask("q", reply=answer("   "))[0], f"{tools_claude.MODEL} sent back no answer.")

    def test_every_error_is_a_sentence(self):
        """Model missing, server error, Ollama not running: each gets its own honest reply."""
        http = lambda code: urllib.error.HTTPError(tools_claude.OLLAMA_CHAT, code, "", {}, None)
        self.assertIn("ollama pull", self.ask("q", error=http(404))[0])
        self.assertIn("error 500", self.ask("q", error=http(500))[0])
        self.assertIn("could not reach Ollama", self.ask("q", error=urllib.error.URLError("refused"))[0])
        self.assertIn("could not reach Ollama", self.ask("q", error=TimeoutError())[0])

    def test_empty_and_huge(self):
        """Nothing asked, and a question over the limit: neither reaches the model."""
        self.assertEqual(tools_claude.ask_claude("   "), 'Ask what? Say it like "ask claude why the sky is blue".')
        reply, f = self.ask("x" * (tools_claude.LIMIT + 1), reply=answer("never"))
        self.assertIn("too long", reply)
        self.assertEqual(f.calls, [])


class OnlyWithAYes(unittest.TestCase):
    """The harness asks before handing it over, and no model or MCP client can reach the tool."""

    def test_asks_first_and_a_no_sends_nothing(self):
        """A no sends nothing; a yes sends the question once."""
        m = FakeOllama(reply=answer("Because."))
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
