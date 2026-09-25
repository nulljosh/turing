# Laws

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
11. A plan is fixed before it runs. A step's tool and place in the list come only from what the user asked and the router or the model's plan built from it, never from a tool's result once the plan is running. An instruction hidden in a step's reading-tool result cannot add a step, remove one, or change what a later step does.

When a law needs to change, change it here and in `eval/laws.py` in the same commit, and say why.
