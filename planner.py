"""She plans before she acts: plan() turns a multi-step job into an ordered list of steps (a real tool
name plus one string argument, and an optional "if" guard), and run() executes it step by step, checking
every result before the next step runs instead of barreling on. This is the frontier gap "she can't plan"
(roadmap.md): today tools.chain() only runs a fixed "X and Y" and tools_agent.agent() lets a model drive one
tool at a time with no check on what came back. Split out for size (law 8); tools.do() is the only caller,
routing here instead of agent() whenever the sentence already looks multi-step (tools._MULTISTEP) and a
sound plan can be built; agent() is still the fallback when it cannot.

Safety, the same shape as law 9/10 in LAWS.md and followup.py's _SAFE_PRODUCERS: a later step may only pull
a value from an earlier one through an explicit "{stepN.field}" placeholder the plan itself declared, and
only when that earlier step's tool is a SAFE producer, one whose result is something she made herself (a
path she found or wrote), never text read from outside. run() never feeds a tool's result back to a model
to decide what happens next: the steps are fixed before anything runs, so an instruction hidden in a page,
a mail or a note cannot add a step or change a later step's tool, whatever it says (eval/laws.py's planner
law drives real injection strings through this and checks the step list a plan runs never changes).
"""
import json
import re
import urllib.error
import urllib.request

import untrusted

MODEL = "qwen3:1.7b"  # same model tools_agent.agent and tools_screen_agent use for multi-step work
OLLAMA_CHAT = "http://localhost:11434/api/chat"
MAX_STEPS = 6

SYSTEM = ('Break the user\'s job into an ordered list of tool calls. Reply with JSON only, nothing else: '
          '{"steps": [{"tool": "<name>", "arg": "<string>", "if": null}, ...]}. Only use a tool name from '
          'the list given to you; never invent one. A step\'s arg may reuse an earlier step\'s own result '
          'with "{stepN.path}" (N is that step\'s number, counting from 1), but only when step N\'s tool is '
          'find_file, write_document or write_code; never any other step. Set "if" to "changed" or "found" '
          'on a step that should only run when the step right before it showed something changed or '
          'something was found, otherwise leave it null.')

# Tools whose result is something she made herself, never text read from outside: the only tools a later
# step may pull a placeholder value from. Same list followup.py trusts for "open it"/"read it".
_SAFE_PRODUCERS = ("find_file", "write_document", "write_code")

_PLACEHOLDER = re.compile(r"\{step(\d+)\.\w+\}")
_PATH = re.compile(r"(~[^\s,]*|/[^\s,]+)")

# A tool's own result reading like an error, an "I can't", or a plain not-found: her tools already say
# this instead of raising (find_file, git_status, read_file, calendar_today and the rest), so a plan stops
# here rather than feeding a bad result into the next step.
_FAIL = re.compile(r"\b(?:no file (?:at|named)|no files? found|no folder|not found|does not exist|doesn'?t exist|"
                    r"could not|couldn'?t|can'?t|cannot|i (?:don'?t|do not) |nothing (?:to|on|found)|failed|"
                    r"is not on this machine|did not answer|no results|no commits found|not on this machine|"
                    r"spotlight is not)\b", re.I)
_CHANGED_NO = re.compile(r"\b(?:nothing (?:to commit|has changed|changed)|no changes|clean|up to date|nothing "
                          r"on the calendar)\b", re.I)
_FOUND_NO = re.compile(r"\b(?:no \S+ (?:found|at)|not found|nothing found|no results)\b", re.I)

_STEP = re.compile(r"\s*(?:,? and then |,? then |,? and |; )\s*", re.I)
_TELL = re.compile(r"^(?:tell|show|give|read) me (?:my |the )?|^(?:also|and) ", re.I)
_IF_GUARD = re.compile(r"^if (?:anything |something )?(changed|found)(?: something)?,?\s*", re.I)


def plan(request, max_steps=MAX_STEPS):
    """An ordered, validated list of steps for a multi-step job, or [] when nothing sound could be built.
    Asks the local model first, the same Ollama flow tools_agent.agent uses, constrained to real tool names
    (tools.TOOLS minus NOT_FOR_MODELS) and checked by _validate: an invented tool, a bad arg, an unsupported
    "if", or a placeholder pointing at a step that has not run yet or is not a SAFE producer throws the
    whole plan out, never a partial one. With Ollama down, or an unsound model reply, falls back to
    splitting the request on "and"/"then" (no model at all) through the existing router: kept only when
    every piece routes to exactly one real tool on its own. [] either way means this is agent() work."""
    if untrusted.is_untrusted(request):
        return []
    import tools
    tool_names = set(tools.model_tools())
    raw = _query_model(request, tool_names)
    if raw is not None:
        steps = _validate(raw, tool_names)
        if steps and len(steps) <= max_steps:
            return steps
    return _fallback_split(request)


def _query_model(request, tool_names):
    """Ask MODEL for a JSON plan over tool_names. Returns the model's raw "steps" list (not yet validated),
    or None when Ollama is down, times out, or the reply is not JSON with a "steps" list at all."""
    body = json.dumps({"model": MODEL, "stream": False, "think": False, "format": "json", "messages": [
        {"role": "system", "content": SYSTEM + " Tools: " + ", ".join(sorted(tool_names)) + "."},
        {"role": "user", "content": request}]}).encode()
    req = urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            msg = json.load(r)["message"]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return None
    text = re.sub(r"(?s)<think>.*?</think>", "", msg.get("content", "")).strip()
    try:
        found = re.search(r"\{.*\}", text, re.S)
        steps = json.loads(found.group(0)).get("steps") if found else None
    except (json.JSONDecodeError, AttributeError):
        return None
    return steps if isinstance(steps, list) else None


def _validate(raw_steps, tool_names):
    """The model's raw JSON steps turned into a clean plan, or [] when any one of them is unsound: not a
    real tool, an arg that is not a string, an "if" that is not "changed"/"found"/null, or a placeholder
    naming a step index that has not happened yet by that point in the list or whose tool is not a SAFE
    producer. One bad step throws out the whole plan, so a model can never sneak in a step it invented
    alongside otherwise-real ones."""
    if not isinstance(raw_steps, list) or not raw_steps:
        return []
    steps = []
    for i, raw in enumerate(raw_steps, start=1):
        if not isinstance(raw, dict):
            return []
        tool, arg, cond = raw.get("tool"), raw.get("arg", ""), raw.get("if")
        if tool not in tool_names or not isinstance(arg, str) or cond not in (None, "changed", "found"):
            return []
        for m in _PLACEHOLDER.finditer(arg):
            idx = int(m.group(1))
            if idx < 1 or idx >= i or steps[idx - 1]["tool"] not in _SAFE_PRODUCERS:
                return []
        steps.append({"tool": tool, "arg": arg, "if": cond})
    return steps


def _fallback_split(request):
    """No model needed: split the request on "and"/"then" the way tools.chain() already does, with one
    addition, a leading "if changed"/"if found" on a piece becomes that step's guard. Kept only when every
    piece routes to exactly one real tool on its own (tools.plan, which runs nothing): anything that does
    not split that cleanly is [] (agent() work), never a guess at a step."""
    import tools
    whole = tools._bare(request.splitlines()[-1])
    parts = [_TELL.sub("", p).strip() for p in _STEP.split(whole)]
    if len(parts) < 2 or not all(parts):
        return []
    steps = []
    for part in parts:
        cond = None
        m = _IF_GUARD.match(part)
        if m:
            cond, part = m.group(1), part[m.end():].strip()
        calls = tools.plan(part)
        if len(calls) != 1:
            return []
        name, args = calls[0]
        steps.append({"tool": name, "arg": args[0] if args else "", "if": cond})
    return steps


def _describe(i, step):
    """One line of the plan preview shown to the user before it runs: "1. find_file(resume.docx)", with
    " if changed"/" if found" appended when the step only runs conditionally."""
    tail = f" if {step['if']}" if step.get("if") else ""
    return f"{i}. {step['tool']}({step['arg']}){tail}."


def _condition_holds(cond, prior_result):
    """True when the step right before a conditional step showed something changed (cond "changed") or
    something was found (cond "found"), decided from that step's own result text, never from model free
    text. An empty or missing prior result never holds."""
    text = str(prior_result or "").strip()
    if not text:
        return False
    if cond == "changed":
        return not _CHANGED_NO.search(text)
    if cond == "found":
        return not _FOUND_NO.search(text)
    return True


def _looks_failed(result):
    """True when a tool's own result reads like an error, a refusal, or a plain not-found: the wording her
    tools already use instead of raising. A plan stops right there rather than feeding a bad result, or a
    made-up one, into the step after it."""
    return bool(_FAIL.search(str(result or "")))


def _fill(arg, steps, results):
    """Substitute every "{stepN.field}" placeholder in one step's argument with the value an earlier SAFE
    producer step's own result names, never text a reading tool produced. Raises ValueError, with a plain
    reason, when a placeholder cannot be filled that way; run() turns that into an honest stop, not a crash
    and not a guess."""
    def repl(m):
        """One placeholder match, turned into the value it stands for, or a raised ValueError."""
        idx = int(m.group(1))
        if idx < 1 or idx > len(steps) or steps[idx - 1]["tool"] not in _SAFE_PRODUCERS:
            raise ValueError(f"step {idx} is not one I can pull a value from")
        result = results.get(idx)
        if result is None:
            raise ValueError(f"step {idx} has not run yet")
        if untrusted.is_untrusted(result):
            raise ValueError(f"step {idx}'s result came from something she read, not something she made")
        found = _PATH.search(str(result))
        if not found:
            raise ValueError(f"step {idx}'s result has no path in it to fill in")
        return found.group(1).rstrip(".,:;)")
    return _PLACEHOLDER.sub(repl, arg)


def run(steps, log=None, confirm=None):
    """Execute a validated plan (from plan()) step by step, in order. With 2 or more steps, shows the whole
    plan and asks once, through confirm, before anything runs; a no there stops before a single step runs.
    A step whose "if" guard does not hold against the step before it is skipped, not run. After every step
    that does run, its result is checked (_looks_failed): a bad result stops the whole run right there with
    a plain explanation instead of continuing into the next step. A later step's "{stepN.field}" is filled
    only from an earlier SAFE-producer step's own result (_fill), never from a reading tool's text, and any
    step whose tool is in tools.WRITES still asks for its own yes, exactly like tools.do(). Returns the
    final reply, or where and why the run stopped."""
    if not steps:
        return None
    import tools
    if len(steps) >= 2 and confirm and not confirm("plan", ("Here's my plan: " + " ".join(_describe(i, s) for i, s in enumerate(steps, 1)) + " Go?",)):
        return "Okay, I will not."
    results, last = {}, None
    for i, step in enumerate(steps, start=1):
        if step.get("if") and i > 1 and not _condition_holds(step["if"], results.get(i - 1)):
            if log:
                log(f"  [skipped step {i}: {step['tool']}, {step['if']} did not hold]")
            continue
        try:
            arg = _fill(step["arg"], steps, results)
        except ValueError as e:
            return f"I can't run step {i} ({step['tool']}): {e}."
        name = step["tool"]
        fn = tools.TOOLS.get(name)
        if not fn:
            return f"Step {i} names a tool I don't have: {name}."
        if confirm and name in tools.WRITES and not confirm(name, (arg,)):
            return f"Okay, I will not run step {i} ({name})."
        if log:
            log(f"  [{name}({arg})]")
        try:
            result = fn(arg) if fn.__code__.co_argcount else fn()
        except Exception as e:
            return f"Step {i} ({name}) failed: {e}."
        result = untrusted.wrap(name, result)
        results[i] = result
        if _looks_failed(result):
            return f"Stopped after step {i} ({name}): {result}"
        last = str(result)
    return last
