"""ask_llm: hands a hard question to another LLM on this Mac. A fake urlopen stands in, so no test needs oMLX or Ollama.

Run: python3 tests/test_llm.py
"""
import io
import json
import os
import sys
import urllib.error
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness
import tools
import tools_llm

OMLX_MODELS = {"data": [{"id": "Qwen3.5-9B-OptiQ-4bit"}, {"id": "mlx-community--Llama-3.2-1B-Instruct-4bit"}]}
OLLAMA_MODELS = {"models": [{"name": "qwen3:8b"}, {"name": "llama3.1:8b"}, {"name": "nomic-embed-text:latest"}]}


class FakeServers:
    """Stands in for urlopen: each local server answers or fails as told, and every request is recorded."""

    def __init__(self, omlx=None, ollama=None, omlx_models=OMLX_MODELS, ollama_models=OLLAMA_MODELS):
        """What each chat answers with (a dict) or raises (an exception), and what each server lists. None means not running."""
        self.by_url = {tools_llm.OMLX_CHAT: omlx, tools_llm.OLLAMA_CHAT: ollama,
                       tools_llm.OMLX + "/v1/models": omlx_models, tools_llm.OLLAMA + "/api/tags": ollama_models}
        self.calls = []

    def __call__(self, req, timeout=None):
        """One request: record the address and body, then fail or answer."""
        url = req if isinstance(req, str) else req.full_url
        self.calls.append((url, None if isinstance(req, str) else json.loads(req.data)))
        got = self.by_url[url]
        if got is None:
            raise urllib.error.URLError("refused")
        if isinstance(got, Exception):
            raise got
        return io.BytesIO(json.dumps(got).encode())

    def chats(self):
        """The chat requests only, as (address, model)."""
        return [(u, b["model"]) for u, b in self.calls if b]


def omlx(text, finish="stop"):
    """A reply shaped like oMLX's OpenAI-style chat."""
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}


def ollama(text, done="stop"):
    """A reply shaped like Ollama's /api/chat."""
    return {"message": {"role": "assistant", "content": text}, "done_reason": done}


def http(code):
    """An HTTP error from a local server."""
    return urllib.error.HTTPError("http://localhost", code, "", {}, None)


class AskLLM(unittest.TestCase):
    """What she says back, for every model named and every way the call can go."""

    def ask(self, request, **servers):
        """Ask through fake local servers; returns the reply and the fake, to read what was sent."""
        f = FakeServers(**servers)
        with mock.patch("urllib.request.urlopen", f):
            return tools_llm.ask_llm(request), f

    def test_any_big_model_goes_to_the_biggest(self):
        """claude, gpt, an llm or no name: oMLX's default first, named in the answer, and the request stays on this Mac."""
        for name in ("claude\t", "gpt-4o\t", "an llm\t", ""):
            reply, f = self.ask(name + "why is the sky blue", omlx=omlx("<think>hmm</think>Rayleigh scattering."), ollama=ollama("never"))
            self.assertEqual(reply, f"Rayleigh scattering.\n(Answered by {tools_llm.MODEL} on this Mac, not by me.)")
            self.assertEqual(f.chats(), [(tools_llm.OMLX_CHAT, tools_llm.MODEL)])
        self.assertTrue(all(u.startswith("http://localhost:") for u in (tools_llm.OMLX, tools_llm.OLLAMA)))

    def test_a_named_model_is_found_on_either_server(self):
        """qwen finds oMLX's Qwen first, llama3.1 finds Ollama's, a full id finds exactly that one."""
        reply, f = self.ask("qwen\tq", omlx=omlx("A."), ollama=ollama("B."))
        self.assertEqual(f.chats(), [(tools_llm.OMLX_CHAT, "Qwen3.5-9B-OptiQ-4bit")])
        reply, f = self.ask("llama3.1\tq", omlx=omlx("A."), ollama=ollama("B."))
        self.assertEqual((reply, f.chats()), ("B.\n(Answered by llama3.1:8b on this Mac, not by me.)", [(tools_llm.OLLAMA_CHAT, "llama3.1:8b")]))
        _, f = self.ask("qwen3:8b\tq", omlx=omlx("A."), ollama=ollama("B."))
        self.assertEqual(f.chats(), [(tools_llm.OLLAMA_CHAT, "qwen3:8b")])

    def test_a_named_model_falls_through_to_its_next_copy(self):
        """oMLX's llama erroring: Ollama's llama answers."""
        reply, _ = self.ask("llama\tq", omlx=http(500), ollama=ollama("B."))
        self.assertEqual(reply, "B.\n(Answered by llama3.1:8b on this Mac, not by me.)")

    def test_a_model_that_is_not_here_lists_what_is(self):
        """No gemma: she says so and names what is running, never the embedding model, and asks nothing."""
        reply, f = self.ask("gemma\tq", omlx=omlx("A."), ollama=ollama("B."))
        self.assertIn("I do not have a gemma model on this Mac.", reply)
        self.assertIn("qwen3:8b", reply)
        self.assertNotIn("embed", reply)
        self.assertEqual(f.chats(), [])
        reply, _ = self.ask("gemma\tq", omlx_models=None, ollama_models=None)
        self.assertIn("Start oMLX or Ollama first", reply)

    def test_ollama_when_omlx_is_down(self):
        """No oMLX, or oMLX erroring: Ollama's default answers and is named."""
        for down in (None, http(500)):
            reply, f = self.ask("claude\tq", omlx=down, ollama=ollama("Because."))
            self.assertEqual(reply, f"Because.\n(Answered by {tools_llm.OLLAMA_MODEL} on this Mac, not by me.)")

    def test_cut_and_empty(self):
        """A cut answer says so, an empty one is not passed off as an answer."""
        self.assertIn("cut short", self.ask("q", omlx=omlx("partial", finish="length"))[0])
        self.assertIn("cut short", self.ask("q", ollama=ollama("partial", done="length"))[0])
        self.assertEqual(self.ask("q", omlx=omlx("   "))[0], f"{tools_llm.MODEL} sent back no answer.")

    def test_every_error_is_a_sentence(self):
        """Nothing running, model missing, server error, still loading, a garbled reply: each gets an honest reply."""
        self.assertIn("could not reach a local model", self.ask("q")[0])
        self.assertIn("ollama pull", self.ask("q", ollama=http(404))[0])
        self.assertIn("error 500", self.ask("q", omlx=http(500), ollama=http(500))[0])
        self.assertIn("still loading", self.ask("q", omlx=TimeoutError())[0])
        self.assertIn("could not reach a local model", self.ask("q", omlx={"weird": 1})[0])

    def test_empty_and_huge(self):
        """Nothing asked, and a question over the limit: neither reaches a model."""
        for empty in ("   ", "qwen\t  "):
            self.assertEqual(tools_llm.ask_llm(empty), 'Ask what? Say it like "ask qwen why the sky is blue".')
        reply, f = self.ask("qwen\t" + "x" * (tools_llm.LIMIT + 1), omlx=omlx("never"))
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
        self.assertEqual(asked, [("ask_llm", ("claude\twhy is the sky blue",))])
        self.assertTrue(yes.startswith("Because.") and len(m.calls) == 1)

    def test_hidden_from_models_and_mcp(self):
        """Only by name: never on a model's menu, never served over MCP, always a write."""
        import mcp_server
        self.assertIn("ask_llm", tools.WRITES & tools.NOT_FOR_MODELS)
        self.assertNotIn("ask_llm", tools.model_tools())
        self.assertNotIn("ask_llm", {t["name"] for t in mcp_server._tools()})

    def test_routes(self):
        """The ways people name a model, and the sentences that only mention one."""
        self.assertEqual(tools.plan("ask claude why is the sky blue"), [("ask_llm", ("claude\twhy is the sky blue",))])
        self.assertEqual(tools.plan("have llama write a haiku"), [("ask_llm", ("llama\twrite a haiku",))])
        self.assertEqual(tools.plan("qwen: what is a monad"), [("ask_llm", ("qwen\twhat is a monad",))])
        self.assertEqual(tools.plan("ask the llm what is a monad"), [("ask_llm", ("the llm\twhat is a monad",))])
        for bare in ("ask claude", "ask qwen", "hey llama", "gemma,"):
            self.assertEqual(tools.plan(bare), [])  # nothing to ask, so nothing is sent
        self.assertEqual(tools.do("ask qwen"), 'Ask what? Say it like "ask qwen why the sky is blue".')
        for mention in ("claude shannon invented information theory", "llamas live in the andes", "ask me a question"):
            self.assertEqual(tools.plan(mention), [])


if __name__ == "__main__":
    unittest.main()
