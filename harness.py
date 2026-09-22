#!/usr/bin/env python3
"""Samantha's harness: one conversation around her hands.

Three jobs the bare tools cannot do. It remembers: every turn's command, tool calls and
result are kept, so "what did you just do" is answered from the record and a multi-step
ask starts with what already happened. It shows its work: every tool call prints as it is
found, before anything runs. And it asks first: anything in tools.WRITES (a note, a
reminder, a file on the Desktop, a Shortcut, the clipboard) waits for a yes.

Run: python3 harness.py        (a chat in the terminal)
"""
import re
import subprocess
import sys

import tools
import tools_util

_RECALL = re.compile(r"^(?:what did you (?:just )?do|what have you done|show (?:me )?(?:the )?(?:tool )?(?:log|history)|history)$", re.I)

# "read it", "what does that page say", "open it": the page she last opened or searched
_READ_IT = re.compile(r"^(?:read|summari[sz]e|what does|what's on|what is on) (?:it|that|this|that page|this page|the page|that site|that link)(?: say| for me| to me)?$", re.I)
_OPEN_IT = re.compile(r"^(?:open|show|pull up|go to|go back to) (?:it|that|that page|that site|that link|there)(?: again)?$|^go there$", re.I)
_PAGE_CALL = re.compile(r"^\[(open_url|web_search|read_page)\((.+)\)\]$")
_AGAIN = re.compile(r"^(?:again|do (?:that|it) again|one more time|repeat that|same again|once more)$", re.I)


class Session:
    """One conversation. confirm(name, args) -> bool decides writes; log(line) shows the tool log."""

    def __init__(self, confirm=None, log=print):
        """A conversation. confirm decides writes (no by default), log shows the tool log."""
        self.confirm, self.log, self.history = confirm or (lambda name, args: False), log, []

    def ask(self, query, or_none=False):
        """Answer one command. Returns the reply and records the turn. With or_none, a sentence that is not a command
        returns None and is not recorded, so a chat can hand it to the question chain."""
        q = query.strip()
        if not q:
            return None if or_none else "Say something, or tell me what to do."
        if _RECALL.match(tools._bare(q)):
            return self.recall()
        pointer = self.point_back(tools._bare(q))
        if pointer:
            q = pointer
        elif _AGAIN.match(tools._bare(q)):
            # the same command once more, through the same asking: a write still waits for a yes
            return self.ask(self.history[-1]["q"]) if self.history else "Nothing to do again yet."
        calls = []

        def log(line):
            """Record a tool call in this turn and show it."""
            calls.append(line.strip())
            self.log(line)

        # a multi-step ask starts knowing what was just done
        context = "".join(f"Earlier: {h['q']} -> {h['result'][:120]}\n" for h in self.history[-3:])
        # what she was told to remember about this ask rides along with a multi-step task, never over MCP
        context += "".join(f"Remembered: {f}\n" for f in tools_util.recall_lines(q))
        try:
            result = tools.do((context + q) if context and tools._MULTISTEP.search(tools._bare(q)) else q, log=log, confirm=self.confirm)
        except Exception as e:
            # one tool breaking (a missing command, a hung app) is a reply, never the end of the conversation
            result = failed(calls, e)
        if result is None and or_none:
            return None
        result = result or "That is not a command I know. Ask me a question, or tell me to do something."
        self.history.append({"q": q, "calls": calls, "result": result})
        return result

    def last_page(self):
        """The address of the page she last opened, searched or read in this conversation, or None."""
        for h in reversed(self.history):
            for call in reversed(h["calls"]):
                m = _PAGE_CALL.match(call)
                if m and m.group(1) == "web_search":
                    return tools.search_url(m.group(2))
                if m and tools._url(m.group(2)):
                    return tools._url(m.group(2))
        return None

    def point_back(self, bare):
        """ "read it" or "open that" as the command it points at, or None when it points at nothing."""
        page = (_READ_IT.match(bare) or _OPEN_IT.match(bare)) and self.last_page()
        if not page:
            return None
        return f"read {page}" if _READ_IT.match(bare) else f"go to {page}"

    def recall(self):
        """What was done so far, from the record, no model involved."""
        if not self.history:
            return "Nothing yet."
        return "\n".join(f"{h['q']}: " + (", ".join(h["calls"]) or "answered directly") for h in self.history[-5:])


def failed(calls, e):
    """Say plainly which tool broke and why, instead of claiming it worked or crashing."""
    what = calls[-1].strip("[] ") if calls else "that"
    if isinstance(e, FileNotFoundError):
        why = f"{e.filename or 'a command it needs'} is not on this machine"
    elif isinstance(e, subprocess.TimeoutExpired):
        why = f"it took longer than {e.timeout:g} seconds"
    else:
        why = str(e) or type(e).__name__
    return f"I tried {what}, but it did not work: {why}."


def _ask_yes(name, args):
    """Ask on the terminal whether to run a tool that writes or sends."""
    return input(f"  Run {name}({', '.join(args)})? [y/N] ").strip().lower() in ("y", "yes")


def main():
    """A chat in the terminal."""
    s = Session(confirm=_ask_yes)
    print("Samantha. Say what to do. Ctrl-D to leave.")
    for line in sys.stdin if not sys.stdin.isatty() else iter(lambda: input("> "), None):
        if line.strip():
            print(s.ask(line))


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print()
