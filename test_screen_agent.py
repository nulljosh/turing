"""tools_screen_agent.py: multi-step screen jobs. A fake urlopen and fake screen tools stand in, so no test clicks
anything or reaches Ollama.

Run: python3 test_screen_agent.py
"""
import io
import json
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools
import tools_screen_agent


class FakeOllama:
    """Stands in for urlopen: hands back one scripted assistant message per call, in order."""

    def __init__(self, *messages):
        """Queue up the assistant messages to hand back, in order."""
        self.queue = list(messages)
        self.calls = []

    def __call__(self, req, timeout=None):
        """One request: record its body, then hand back the next queued message."""
        body = json.loads(req.data)
        self.calls.append(body)
        return io.BytesIO(json.dumps({"message": self.queue.pop(0)}).encode())


def call(name, **args):
    """One tool_calls entry, shaped like Ollama's function-calling reply."""
    return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}


def say(text):
    """A plain closing answer, no tool call."""
    return {"role": "assistant", "content": text}


class ScreenTask(unittest.TestCase):
    """The plan-act loop: every step confirmed, a no stops the whole job, and the tools it may ever touch are fixed."""

    def run_task(self, messages, confirm=lambda n, a: True, max_steps=tools_screen_agent.MAX_STEPS, **fakes):
        """Run screen_task through a fake Ollama and fake screen tools; returns (result, ollama, log lines)."""
        fake_llm = FakeOllama(*messages)
        log = []
        with mock.patch("urllib.request.urlopen", fake_llm), \
                mock.patch.object(tools_screen_agent, "_tools", return_value={
                    "click_text": fakes.get("click_text", lambda target: f"Clicked {target}."),
                    "type_text": fakes.get("type_text", lambda text: f"Typed {text}."),
                    "press_key": fakes.get("press_key", lambda key: f"Pressed {key}."),
                    "see_screen": fakes.get("see_screen", lambda question="": "A login form."),
                }):
            result = tools_screen_agent.screen_task("log me into gmail", max_steps=max_steps, log=log.append, confirm=confirm)
            return result, fake_llm, log

    def test_a_multi_step_plan_runs_click_by_click(self):
        """Click, type, click again, then a plain closing answer: every real step logged, none skipped."""
        result, fake_llm, log = self.run_task([call("click_text", target="Sign in"), call("type_text", text="me@x.com"),
                                               call("click_text", target="Next"), say("Signed in.")])
        self.assertEqual(result, "Signed in.")
        self.assertEqual(log, ["  [click_text(Sign in)]", "  [type_text(me@x.com)]", "  [click_text(Next)]"])
        self.assertEqual(len(fake_llm.calls), 4)

    def test_a_no_stops_the_whole_job_not_just_that_step(self):
        """Refusing one step ends the job outright, and no later step is even attempted."""
        asked = []
        result, fake_llm, log = self.run_task(
            [call("click_text", target="Sign in"), call("type_text", text="me@x.com"), say("never reached")],
            confirm=lambda n, a: (asked.append((n, a)) or n != "type_text"))
        self.assertEqual(result, "Okay, I stopped there.")
        self.assertEqual(asked, [("click_text", ("Sign in",)), ("type_text", ("me@x.com",))])
        self.assertEqual(len(fake_llm.calls), 2)  # the model was never asked for a third step

    def test_she_can_look_before_acting(self):
        """see_screen is a real step too, confirmed like any other, used to find what to click."""
        result, _, log = self.run_task([call("see_screen"), call("click_text", target="Sign in"), say("Done.")],
                                       see_screen=lambda question="": "A page with a Sign in button.")
        self.assertEqual(result, "Done.")
        self.assertIn("  [see_screen()]", log)

    def test_an_unknown_tool_is_an_honest_result_not_a_crash(self):
        """A tool name the model invents is reported back to it, not run."""
        result, _, _ = self.run_task([call("delete_everything"), say("Could not do that.")])
        self.assertEqual(result, "Could not do that.")

    def test_a_broken_tool_is_reported_not_raised(self):
        """A tool that raises comes back as text, so one bad step does not kill the job."""
        result, _, _ = self.run_task([call("click_text", target="Sign in"), say("It failed, trying something else.")],
                                     click_text=lambda target: (_ for _ in ()).throw(RuntimeError("no such window")))
        self.assertEqual(result, "It failed, trying something else.")

    def test_ollama_down_is_a_sentence(self):
        """No Ollama running: an honest reply, never a crash."""
        import urllib.error
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            result = tools_screen_agent.screen_task("log me into gmail", confirm=lambda n, a: True)
        self.assertIn("need Ollama running", result)

    def test_runs_out_of_steps(self):
        """A job that never stops itself ends honestly at the step cap, not forever."""
        result, fake_llm, _ = self.run_task([call("click_text", target="Next")] * 3, max_steps=3)
        self.assertIn("ran out of steps", result)
        self.assertEqual(len(fake_llm.calls), 3)  # never a fourth request past the cap


class OnlyByName(unittest.TestCase):
    """Screen jobs route only when named as one, never confused with a single click or research."""

    def test_routes(self):
        """Explicit multi-step phrasing goes to no exact tool: it is left for the screen agent."""
        self.assertEqual(tools.act("log me into gmail"), None)
        self.assertEqual(tools.act("log into gmail and check my email"), None)
        self.assertEqual(tools.act("walk me through checkout"), None)
        self.assertEqual(tools.act("step me through the signup form"), None)

    def test_a_single_click_still_goes_through_the_exact_route(self):
        """"click Sign in" alone is not a job: the instant router still fires, no model involved."""
        self.assertEqual(tools.plan("click Sign in"), [("click_text", ("Sign in",))])

    def test_the_screen_agent_never_reaches_the_general_model_menu(self):
        """click_text, type_text, press_key and see_screen stay off model_tools(): only screen_task's own fixed
        dict ever hands them to a model, and that dict is exactly these four, nothing more."""
        self.assertTrue({"click_text", "type_text", "press_key", "see_screen"} & tools.NOT_FOR_MODELS)
        self.assertFalse({"click_text", "type_text", "press_key", "see_screen"} & set(tools.model_tools()))
        names = set(tools_screen_agent._tools())
        self.assertEqual(names, {"click_text", "type_text", "press_key", "see_screen"})


if __name__ == "__main__":
    unittest.main()
