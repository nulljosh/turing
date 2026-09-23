# Safety

What Samantha will and will not do, and how that is actually enforced. LAWS.md lists the rules a machine checks on every push; this is the plain-language policy those rules exist to serve. SOUL.md is who she is; this is where that stops.

## What she will not do without asking you first

Anything that leaves a mark: writing a note, a reminder, or a file, sending something, clicking or typing on your screen, calling another MCP server, remembering something about you, or waking your screen. The harness shows the exact command before it runs and waits for a yes. A no runs nothing, not a smaller version of the thing, nothing at all (LAWS.md, rule 3).

## What never reaches a model's menu

Some tools have a side effect nobody would expect just from the words used to invoke them (asking another LLM, reading or writing memory, closing a browser tab, running an Apple Shortcut). These are never offered to any model, hers or a bigger one she calls, and never served over MCP. They only run when you name them directly (LAWS.md, rules 1 and 2).

## Where her hands stay

Reading, listing, or writing a file only happens inside your home folder. A hidden file, a path that walks outside home with `../`, or a symlink pointed elsewhere is refused, not silently resolved (LAWS.md, rule 4).

## What leaves the Mac, and what does not

Nothing leaves this machine by default. Three things reach the network, and only because you asked for them by name or by the shape of the question: looking something up on the web or Wikipedia, asking another LLM (which still only runs on your Mac, through oMLX or Ollama, never a cloud API), and reading a page you told her to open. No telemetry, no analytics, no background sync. `ask_llm` and the tools that read your screen or a photo are private for exactly this reason: they are never a model's own idea, only yours.

## Never confidently wrong

A wrong answer given plainly is a bug worth fixing. A wrong answer given with confidence is worse, because you have no reason to check it. She retrieves from real sources and cites them; when nothing she has covers a question, she says so instead of guessing. This is measured, not assumed: `eval/score.py` and `eval/basic_questions.py` run on every push and track exactly this.

## No shell, ever

Every tool that touches your Mac is a fixed, hardcoded command. Nothing a model writes, hers or a bigger one, is ever handed to a shell to interpret. A prompt cannot become a command it was not already built to be.

## If something goes wrong

This is a personal, local project, not a hosted service; there is no telemetry to alert anyone if a rule breaks. If you find a real gap between this document and what the code actually does, that is a bug: open an issue at github.com/nulljosh/turing with what you saw and what you expected. `eval/laws.py` runs on every commit specifically so gaps like that get caught before they ship, not after.
