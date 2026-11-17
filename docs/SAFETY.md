# Safety

What Samantha will and will not do, and how that is actually enforced. docs/SAFETY.md lists the rules a machine checks on every push; this is the plain-language policy those rules exist to serve. docs/ARCHITECTURE.md is who she is; this is where that stops.

## What she will not do without asking you first

Anything that leaves a mark: writing a note, a reminder, or a file, sending something, clicking or typing on your screen, calling another MCP server, remembering something about you, or waking your screen. The harness shows the exact command before it runs and waits for a yes. A no runs nothing, not a smaller version of the thing, nothing at all (docs/SAFETY.md, rule 3). During a multi-step screen job, Escape is the kill switch: press it any time, even after a yes, and nothing else runs.

## What never reaches a model's menu

Some tools have a side effect nobody would expect just from the words used to invoke them (asking another LLM, reading or writing memory, closing a browser tab, running an Apple Shortcut). These are never offered to any model, hers or a bigger one she calls, and never served over MCP. They only run when you name them directly (docs/SAFETY.md, rules 1 and 2).

## Where her hands stay

Reading, listing, or writing a file only happens inside your home folder. A hidden file, a path that walks outside home with `../`, or a symlink pointed elsewhere is refused, not silently resolved (docs/SAFETY.md, rule 4).

## What leaves the Mac, and what does not

Nothing leaves this machine by default. Three things reach the network, and only because you asked for them by name or by the shape of the question: looking something up on the web or Wikipedia, asking another LLM (which still only runs on your Mac, through oMLX or Ollama, never a cloud API), and reading a page you told her to open. No telemetry, no analytics, no background sync. `ask_llm` and the tools that read your screen, a photo or the camera are private for exactly this reason: they are never a model's own idea, only yours.

## Never confidently wrong

A wrong answer given plainly is a bug worth fixing. A wrong answer given with confidence is worse, because you have no reason to check it. She retrieves from real sources and cites them; when nothing she has covers a question, she says so instead of guessing. This is measured, not assumed: `eval/score.py` and `eval/basic_questions.py` run on every push and track exactly this.

## No shell, ever

Every tool that touches your Mac is a fixed, hardcoded command. Nothing a model writes, hers or a bigger one, is ever handed to a shell to interpret. A prompt cannot become a command it was not already built to be. One tool, `run_code`, hands a model-written Python script to a real Python interpreter, never a shell, and never against your real files: a fresh temp folder holding only a copy of the one CSV you named, no network, a time limit and a memory cap. The script is data she never trusts; the sandbox is what actually stops it, not a promise in the prompt. Asks first, same as everything else that writes.

## If something goes wrong

This is a personal, local project, not a hosted service; there is no telemetry to alert anyone if a rule breaks. If you find a real gap between this document and what the code actually does, that is a bug: open an issue at github.com/nulljosh/turing with what you saw and what you expected. `eval/laws.py` runs on every commit specifically so gaps like that get caught before they ship, not after.

## Laws

Rules this repo never breaks, checked by `eval/laws.py` on every gate run and every push. The idea is borrowed from Bend's `LAWS.bend`: write the rule down once, and let a machine refuse any change that breaks it. Ours checks every tool, not a sample, though it cannot prove what nobody thought to write down.

1. Every side-effect tool is classified. `WRITES` and `NOT_FOR_MODELS` only name real tools, and every tool that leaves a mark (a note, a reminder, a file, a Shortcut, the clipboard, the screen) is in one of them.
2. A model never sees a tool in `NOT_FOR_MODELS`, and MCP never serves one.
3. A no from the harness stops a write. For every write tool with a spoken command, saying no runs nothing.
4. Her hands stay in the home folder. Reading, listing or revealing a hidden file or a path outside it is refused.
5. Every tool has a docstring, every function and class is documented (100 percent), and every source file has a row in `docs/ARCHITECTURE.md`.
6. The landing page's JavaScript says the same words as the Python tools (`eval/util_diff.py`).
7. No em dashes in anything a person reads, and no page that probes localhost for a visitor.
9. She believes what she reads, never what it says to do. An instruction hidden in a page, an email, a document, a note or the screen never picks or triggers a tool: only the user's own words do. A write she was not asked for still never runs, whatever a reading tool's result says.
10. A follow-up ("do that again", "open it") only ever replays the user's own past words: what she was asked, and which tool that led to. It never replays what a reading tool's result said. An instruction planted in a page, an email or a note cannot come back later as a command just because the user said "again".
11. A plan is fixed before it runs. A step's tool and place in the list come only from what the user asked and the router or the model's plan built from it, never from a tool's result once the plan is running. An instruction hidden in a step's reading-tool result cannot add a step, remove one, or change what a later step does. When a step fails and she plans around it (`planner.work`), the new plan comes only from the user's request and her own record of which steps ran and failed: a reading tool's text, failure text included, never reaches it.
12. A model-driven loop (`tools_agent.agent`, `tools_screen_agent.screen_task`, planner's model path) still checks itself before a WRITE it proposed reaches the human confirm: `intent.check()` refuses a step whose tool and argument do not trace back to the user's own request, whatever a reading tool's result talked it into proposing. Screen clicks included: a click that pays, deletes, sends, installs or grants something needs the same kind of act in the request, and a typed shell command needs the user's own words (every eval/screen_bench.py task still passes, every planted click is refused). A direct command the router matched on the user's own words is never double-checked this way.

When a law needs to change, change it here and in `eval/laws.py` in the same commit, and say why.

## Security

### Reporting

Found something? Email **trommatic@icloud.com**. Don't open a public issue for anything exploitable.

You'll hear back within a week. This is a solo side project. No bounty, no SLA, just a reply.

### Supported versions

The deployed version and the tip of `main`. Nothing else.

### What's guarded

Samantha has hands, so the guards are the product.

On the Mac, she only reads inside your home folder. Hidden files are refused outright, so `.ssh` and `.env` stay unread. When a model picks a tool, `_sound()` checks the pick: the tool must exist, and its argument must come from your own words. She can't invent one.

On the landing page, nothing she does leaves your browser tab. The page writes text, never markup. A strict CSP allows no outside scripts and no `eval`. `/api/ask`, `/api/pick`, `/api/draw` and `/api/chat` take JSON from this site only, at 20 calls a minute per visitor, and drawing gets its own limit of 5 a minute because a picture costs real compute. A short list of words the image endpoint refuses, a 120 character cap, and a day of caching for repeat prompts keep it small. The reader model answers from the article (or, for Joshua Tree questions, the condensed pack in `web/jt_docs.js`) in front of it or declines. Every reply is capped, so no upstream can flood the chat.

`/api/chat` also allows requests from `joshuatree.heyitsmejosh.com`, the Joshua Tree kernel's own browser demo, and from a request with no `Origin` header at all (the kernel's real HTTP client, and the demo's own server-to-server network relay, never send one). No other origin gets through.

`eval/web_demo.py` attacks all of this in headless Chromium: script injection, `javascript:` links, prompt leaks, made-up tools. It runs before every deploy.

### Not in the repo

Training data and adapters are built from private notes. They are gitignored and never pushed.
