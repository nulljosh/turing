"""ask_claude: the one tool that leaves the Mac. A fake anthropic module stands in, so no test ever calls the real API.

Run: python3 test_claude.py
"""
import os
import sys
import types
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness
import tools
import tools_claude


def fake_anthropic(reply=None, error=None):
    """A stand-in for the anthropic package: its error classes, and a client whose beta.messages.create records the call."""
    m = types.ModuleType("anthropic")
    m.APIError = type("APIError", (Exception,), {})
    m.APIConnectionError = type("APIConnectionError", (m.APIError,), {})
    m.APIStatusError = type("APIStatusError", (m.APIError,), {"status_code": 500})
    for name in ("AuthenticationError", "PermissionDeniedError", "RateLimitError"):  # the SDK's status errors subclass APIStatusError
        setattr(m, name, type(name, (m.APIStatusError,), {}))
    m.calls = []

    def create(**kw):
        """Record the request, then fail or answer as told."""
        m.calls.append(kw)
        if error:
            raise error(m)
        return reply

    client = types.SimpleNamespace(beta=types.SimpleNamespace(messages=types.SimpleNamespace(create=create)))
    m.Anthropic = lambda: client
    return m


def answer(text, stop="end_turn", model="claude-opus-5"):
    """A response shaped like the SDK's: text blocks, a stop reason and the model that served it."""
    blocks = [types.SimpleNamespace(type="thinking", thinking=""), types.SimpleNamespace(type="text", text=text)]
    return types.SimpleNamespace(content=blocks, stop_reason=stop, model=model)


class AskClaude(unittest.TestCase):
    """What she says back, for every way the call can go."""

    def ask(self, question, **fake):
        """Ask through a fake SDK; returns the reply and the fake, to read what was sent."""
        m = fake_anthropic(**fake)
        with mock.patch.dict(sys.modules, {"anthropic": m}):
            return tools_claude.ask_claude(question), m

    def test_an_answer_is_marked_as_claudes(self):
        """The text comes back with where it came from, and the request is the documented shape."""
        reply, m = self.ask("why is the sky blue", reply=answer("Rayleigh scattering."))
        self.assertEqual(reply, "Rayleigh scattering.\n(Answered by Claude, claude-opus-5, not by me.)")
        sent = m.calls[0]
        self.assertEqual(sent["model"], "claude-opus-5")
        self.assertEqual(sent["messages"], [{"role": "user", "content": "why is the sky blue"}])
        self.assertEqual((sent["fallbacks"], sent["betas"]), ("default", ["server-side-fallback-2026-07-01"]))
        self.assertNotIn("thinking", sent)  # adaptive thinking is on by default; never sent disabled

    def test_a_fallback_model_is_named(self):
        """When a fallback served it, the reply names the model that actually answered."""
        reply, _ = self.ask("q", reply=answer("ok", model="claude-opus-4-8"))
        self.assertTrue(reply.endswith("(Answered by Claude, claude-opus-4-8, not by me.)"))

    def test_refusal_cut_and_empty(self):
        """A refusal is said plainly, a cut answer says so, an empty one is not passed off as an answer."""
        self.assertEqual(self.ask("q", reply=answer("", stop="refusal"))[0], "Claude declined to answer that one.")
        self.assertIn("cut short", self.ask("q", reply=answer("partial", stop="max_tokens"))[0])
        self.assertEqual(self.ask("q", reply=answer("   "))[0], "Claude sent back no answer.")

    def test_every_error_is_a_sentence(self):
        """Key, permission, rate limit, server, network, old SDK and no credential: each gets its own honest reply."""
        cases = {
            lambda m: m.AuthenticationError(): "did not accept the API key",
            lambda m: m.PermissionDeniedError(): "not allowed",
            lambda m: m.RateLimitError(): "rate limiting",
            lambda m: m.APIConnectionError(): "could not reach Claude",
            lambda m: TypeError("unexpected keyword argument 'fallbacks'"): "too old",
            lambda m: Exception("Could not resolve authentication method"): "need an Anthropic API key",
            # what the real SDK (1.8.0) raises with no key at all, found by running it: a TypeError, not an API error
            lambda m: TypeError("Could not resolve authentication method. Expected one of api_key, auth_token"): "need an Anthropic API key",
            lambda m: Exception("something odd"): "Asking Claude failed: something odd",
        }
        for make, words in cases.items():
            self.assertIn(words, self.ask("q", error=make)[0])

        def server(m):
            """A 529 from the API."""
            e = m.APIStatusError()
            e.status_code = 529
            return e
        self.assertEqual(self.ask("q", error=server)[0], "Claude could not answer just now (error 529). Try again later.")

    def test_no_sdk_empty_and_huge(self):
        """No anthropic package, nothing asked, and a question over the limit: none of them reach the network."""
        with mock.patch.dict(sys.modules, {"anthropic": None}):
            self.assertIn("pip install anthropic", tools_claude.ask_claude("q"))
        self.assertEqual(tools_claude.ask_claude("   "), 'Ask Claude what? Say it like "ask claude why the sky is blue".')
        reply, m = self.ask("x" * (tools_claude.LIMIT + 1), reply=answer("never"))
        self.assertIn("too long", reply)
        self.assertEqual(m.calls, [])


class OnlyWithAYes(unittest.TestCase):
    """The harness asks before anything leaves the Mac, and no model or MCP client can reach the tool."""

    def test_asks_first_and_a_no_sends_nothing(self):
        """A no sends nothing; a yes sends the question once."""
        m = fake_anthropic(reply=answer("Because."))
        asked = []
        with mock.patch.dict(sys.modules, {"anthropic": m}):
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
        self.assertEqual(tools.do("ask claude"), 'Ask Claude what? Say it like "ask claude why the sky is blue".')
        self.assertEqual(tools.plan("claude shannon invented information theory"), [])


if __name__ == "__main__":
    unittest.main()
