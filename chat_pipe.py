"""A line-delimited JSON front door onto her real answer chain, for a native GUI (or any other host process) to
drive instead of a terminal. Same shape as serve.py and mcp_server.py: a different door, the exact same
harness.Session and chat.safe_turn underneath, so a native window app needs zero copy of her logic.

Protocol, one JSON object per line, unbuffered stdin/stdout:
    host -> her:  {"ask": "what you typed"}
    her -> host:  {"working": "tool_name(args)"}      zero or more, as each tool call is found
    her -> host:  {"confirm": {"name": "...", "args": [...]}}   only before a write; blocks for a reply
    host -> her:  {"yes": true}                        or {"yes": false}
    her -> host:  {"answer": "the final reply"}         exactly one per turn, always last

    python3 chat_pipe.py            # runs the protocol over real stdin/stdout
    python3 chat_pipe.py --check    # a fake terminal drives one full turn and one confirm, no model needed
"""
import json
import sys

import feedback


def run(read_line, write, ask_fn):
    """The protocol loop: one {"ask": ...} in, {"working"}*, an optional {"confirm"}/{"yes"} round trip, then
    exactly one {"answer": ...}. read_line() returns the next input line or None at EOF; write(obj) sends one
    reply. ask_fn(question, log, confirm) answers one turn, same signature as harness.Session.ask.

    A fresh harness.Session is made per turn (see _real_ask), so there is no Session history to rate against.
    `last` tracks the one turn this process just answered instead, updated after every real turn, so "good"/
    "wrong" here is caught the same way as harness.Session.ask: before ask_fn, before any tool runs."""
    last = {"q": None, "tool": "answer", "args": (), "reply": None}
    while True:
        line = read_line()
        if line is None:
            return
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            question = msg["ask"]
        except (ValueError, KeyError, TypeError):
            write({"answer": "That did not look like a question."})
            continue

        bare = question.strip()
        if feedback.is_summary(bare):
            write({"answer": feedback.feedback_summary()})
            continue
        verdict = feedback.match(bare)
        if verdict:
            if last["q"] is None:
                write({"answer": "Nothing to rate yet."})
            else:
                write({"answer": feedback.record(last["q"], last["tool"], last["args"], last["reply"], *verdict)})
            continue

        calls = []

        def log(text):
            """Every tool call, as it is found."""
            calls.append(text.strip())
            write({"working": text.strip()})

        def confirm(name, args):
            """Ask the host, block for exactly one reply line."""
            write({"confirm": {"name": name, "args": list(args)}})
            reply = read_line()
            try:
                return bool(json.loads(reply or "{}").get("yes"))
            except ValueError:
                return False

        answer = ask_fn(question, log=log, confirm=confirm)
        tool, args = feedback.parse_calls(calls)
        last.update(q=question, tool=tool, args=args, reply=answer or "")
        write({"answer": answer if answer is not None else "That is not a command I know."})


def _stdio():
    """read_line/write bound to the real, unbuffered process stdio."""
    def read_line():
        """One line from real stdin, or None at EOF."""
        line = sys.stdin.readline()
        return line if line else None

    def write(obj):
        """One JSON object to real stdout, flushed at once."""
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()
    return read_line, write


def _real_ask(question, log, confirm):
    """The real answer chain: commands through the harness, questions through chat.safe_turn."""
    import chat
    import harness
    session = harness.Session(confirm=confirm, log=log)
    did = session.ask(question, or_none=True)
    if did is not None:
        return did
    answer, _, _ = chat.safe_turn(question, [], False, None)
    return answer


def _check():
    """No model, no harness: a fake host drives one answered turn and one confirmed-then-refused turn."""
    sent = iter([json.dumps({"ask": "hello"}), json.dumps({"ask": "delete everything"}), json.dumps({"yes": False})])
    got = []

    def read_line():
        """The next scripted input line, or None once they run out."""
        return next(sent, None)

    def write(obj):
        """Record what would have been sent."""
        got.append(obj)

    def fake_ask(question, log, confirm):
        """Stand in for the real answer chain: one plain answer, one that needs a confirm."""
        if "delete" in question:
            log("delete_everything()")
            return "Okay, I will not." if not confirm("delete_everything", ()) else "Deleted."
        return "hi yourself"
    run(read_line, write, fake_ask)
    assert got == [{"answer": "hi yourself"}, {"working": "delete_everything()"},
                   {"confirm": {"name": "delete_everything", "args": []}}, {"answer": "Okay, I will not."}], got
    print("chat_pipe ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        _check()
    else:
        run(*_stdio(), _real_ask)
