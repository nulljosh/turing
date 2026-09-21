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
import sys

import tools

_RECALL = re.compile(r"^(?:what did you (?:just )?do|what have you done|show (?:me )?(?:the )?(?:tool )?(?:log|history)|history)$", re.I)


class Session:
    """One conversation. confirm(name, args) -> bool decides writes; log(line) shows the tool log."""

    def __init__(self, confirm=None, log=print):
        """A conversation. confirm decides writes (no by default), log shows the tool log."""
        self.confirm, self.log, self.history = confirm or (lambda name, args: False), log, []

    def ask(self, query):
        """Answer one command. Returns the reply and records the turn."""
        q = query.strip()
        if _RECALL.match(tools._bare(q)):
            return self.recall()
        calls = []

        def log(line):
            """Record a tool call in this turn and show it."""
            calls.append(line.strip())
            self.log(line)

        # a multi-step ask starts knowing what was just done
        context = "".join(f"Earlier: {h['q']} -> {h['result'][:120]}\n" for h in self.history[-3:])
        result = tools.do((context + q) if context and tools._MULTISTEP.search(tools._bare(q)) else q, log=log, confirm=self.confirm)
        result = result or "That is not a command I know. Ask me a question, or tell me to do something."
        self.history.append({"q": q, "calls": calls, "result": result})
        return result

    def recall(self):
        """What was done so far, from the record, no model involved."""
        if not self.history:
            return "Nothing yet."
        return "\n".join(f"{h['q']}: " + (", ".join(h["calls"]) or "answered directly") for h in self.history[-5:])


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
