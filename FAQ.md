# FAQ

## What is Turing?

Turing is the project: the pipeline, the repo, this whole effort to build small language models on consumer hardware. It is not a model itself. Turing is fixed as a name, the way Anthropic is fixed as a company name.

## Summarize what Turing is in one sentence.

Turing is a pipeline for building small language models on consumer hardware.

## What is Samantha?

Samantha is the first model Turing produced. It is a LoRA fine-tune of `Qwen2.5-0.5B-Instruct-4bit`, trained mostly on this project's own docs, plus a small capped sample of the wider fleet for house voice. Samantha is not pretrained from scratch, it starts from an already-trained small open model and adjusts it with a small set of trainable weight deltas.

## What is the relationship between Turing and Samantha?

The same relationship as Anthropic and Claude, or Anthropic and one specific Claude model like Haiku or Fable. The project name stays fixed. Each model Turing produces gets its own name, not a version-bumped name like "Samantha-2". The next model will have a different name entirely, chosen for whatever it is actually built for.

## Why doesn't Turing pretrain a model from scratch at full scale?

Needs data-center-scale compute: gigabytes of clean text and enough GPU time to make noise start looking like language. That's a research-lab budget, not a single Mac Mini's. Arthur (see next answer) already proved what happens when you try it anyway on consumer hardware, gibberish, no working checkpoint. Turing's answer is LoRA fine-tuning an already-trained small base model instead, which needs a tiny fraction of the data and compute.

## What went wrong with Arthur?

Arthur was an earlier attempt at this same idea, months before Turing. Arthur tried to pretrain a language model completely from scratch on a single Mac, with no borrowed base weights. After a few days of training it produced gibberish. The project was abandoned. The lesson from Arthur is the reason Turing exists: pretraining from raw text at any useful scale needs gigabytes of clean data and real compute, more than a single consumer machine can provide in a reasonable timeframe. Turing's answer to that lesson is LoRA fine-tuning a small existing base model instead of training one from zero.

## What base model does Samantha use?

`Qwen2.5-0.5B-Instruct-4bit`, downloaded from Hugging Face via the `mlx-community` org, run through Apple's MLX framework on-device.

## Was another base model tried?

Yes. `Qwen3.5-0.8B-4bit` was tried as a Phase 3 comparison, to see if a bigger base earns its extra cost before committing to one. It caused three crashes in a row on this machine (two plain out-of-memory crashes, then a Metal/GPU out-of-memory error mid-backprop even with plenty of free system RAM). That comparison is paused, not abandoned, `ada-1b-adapter/` holds its unfinished state. It would need a smaller batch size or different hardware to revisit properly, not a blind retry.

## What's the difference between LoRA and full fine-tuning?

LoRA (Low-Rank Adaptation) trains a small set of weight deltas on top of a frozen, already-trained base model, cheaper, faster, and it never touches or retrains the base model's own weights. Full fine-tuning retrains all of a model's weights directly, which needs far more memory, compute, and data to avoid destroying what the base model already knew. Samantha uses LoRA.

## Is Samantha fine-tuned or pretrained from scratch?

Fine-tuned. LoRA (Low-Rank Adaptation) trains a small set of weight deltas on top of a frozen, already-trained base model. It never retrains the base model's own weights from zero. The from-scratch idea (what Arthur tried, and what failed) lives on in this repo as a separate, deliberately small experiment, see the next answer.

## What is scratch/ in this repo?

A second, independent track alongside the main LoRA pipeline: a genuine from-scratch character-level transformer, built and trained with zero borrowed weights. Its own tiny architecture (`scratch/model.py`), its own training loop (`scratch/train.py`). It will not be fluent, that is expected and intentional, it is small on purpose. The point of `scratch/` is proving Turing can build a model from nothing without repeating Arthur's failure (gibberish for days with no working checkpoint), not proving it can compete with the LoRA path.

## What data was Samantha trained on?

Primarily this repo's own docs (README, WHITEPAPER, roadmap.md, TROUBLESHOOTING.md, this FAQ, and eval result writeups), repeated a few times so they are not drowned out. A capped sample of the wider ~50-repo fleet's READMEs, roadmap.md files, and CLAUDE.md files, and a slice of the personal Obsidian wiki, is mixed in for house voice and variety, but capped so it cannot dominate the training data the way it did in an earlier run (see roadmap.md's progress log, run 3).

## Why does Samantha hallucinate, or sometimes make things up?

Not enough real, distinct training content yet to override the base model's habit of answering "what is X" questions with a plausible-sounding, generic, confident answer. Five training runs on 2026-09-13 confirmed this is the actual bottleneck, not the training format (fixed in run 2), not which fleet projects were included (fixed in run 3), not how aggressively existing content was repeated (tuned in runs 4 and 5). More genuinely distinct real content, like this FAQ, is the real fix, not another resampling trick.

## Should Samantha try to beat Claude or GPT?

No. Samantha's base model is Qwen2.5-0.5B, so a LoRA fine-tune of it cannot outperform Qwen in general, only on the narrow thing it was actually fine-tuned for. The real benchmark is whether the fine-tuned version answers questions about this project better than the stock base model does, not whether it beats a frontier lab's model. Beating a frontier model was never the goal, see roadmap.md's "What we will never do on this budget" section.

## What is the honest win condition?

Ask Samantha to draft something in house voice, or answer a real question about one of these projects, and have the answer be good enough to use without rewriting it. Not "beat GPT."

## What is house voice?

Plain, short sentences. No em dashes anywhere, in code, UI, or prose. No emojis. No AI-brochure language like "leverage", "seamlessly", or "robust" used as filler. Say the problem, then the thing, then stop. This rule applies fleet-wide across every project, not just Turing.

## What tool actually runs training?

`mlx_lm.lora`, run through Apple's MLX framework, entirely on-device on this Mac Mini. No cloud GPU, no API cost. Always invoked through `run_lora_capped.py`, a thin wrapper that sets a Metal cache limit and memory limit before calling `mlx_lm.lora`'s own unmodified entry point, see TROUBLESHOOTING.md for why that wrapper exists.

## Why was run_lora_capped.py written?

MLX's lazy-evaluation graph caches intermediate Metal (GPU) buffers, and on a memory-constrained machine during a long sustained training loop, that cache can grow without bound and eventually cause an out-of-memory crash mid-run, even with a small batch size and gradient checkpointing already enabled. This happened three times during Phase 3's base-model comparison before the cause was found. `run_lora_capped.py` calls `mx.set_cache_limit()` and `mx.set_memory_limit()` before training starts, capping both explicitly. It does not patch the `mlx-lm` package itself, so it survives package upgrades.

## What is train_resilient.sh?

A wrapper around `run_lora_capped.py` for long unattended runs: it checks free memory before each attempt, auto-restarts on crash with a backoff delay, resumes from the last saved checkpoint instead of starting over, and gives up after a capped number of retries. It is not a daemon, it runs once when invoked and exits when the training finishes or the retries run out.

## How does the landing page get its loss chart data?

`parse_log.py` parses the most recent training run's log (previously `train.log`, now `ada-1-adapter.resilient.log` since training moved to the resilient wrapper) into `web/status.json`. The landing page fetches that file and renders the loss curve and roadmap-phase markers on a canvas, no charting library.

## What license is this project under?

MIT.

## Who maintains this project?

Joshua Trommel, listed as the author in `LICENSE` and `WHITEPAPER.md`.

## What's blocked or paused right now?

The `Qwen3.5-0.8B` base comparison (Phase 3) is paused after three crashes, the last being a real Metal/GPU memory-fit problem rather than a background-process conflict. Phase 2 (real eval prompts) is active but the model still scores poorly, see the eval/ folder's run-by-run results for the honest numbers.

## What does Phase 4 of the roadmap involve?

Retrieval instead of memorization: wiring Samantha to `brain` (the existing RAG-over-notes project) so it answers from live retrieved documents instead of trying to recall facts from its own trained weights. Confirmed working on 2026-09-13, this whole FAQ is part of what makes that retrieval accurate.

## Does Turing use a paid API or cloud service to train?

No. Training runs entirely on-device via Apple's MLX framework, no cloud GPU, no API cost. The only paid-adjacent thing involved is `brain`'s Cloudflare Workers AI usage for retrieval embeddings, which is separate infrastructure, not part of training itself.

## Can I add my own FAQ entries?

Yes. `FAQ.md` is a plain markdown file, `faq_match()` in `ask.py` re-parses it fresh on every question, no rebuild step. Add a new `## Your question here` header followed by a paragraph answer, in the same style as every existing entry, and it's immediately queryable.

## What happens if a question isn't in FAQ.md and isn't covered by the project docs either?

It falls through to retrieval plus generation, brain's index is searched for the closest real passages it has, then the base model generates an answer from that context. Quality varies at that point, that's the honest ceiling this whole project has been documenting, not a special error case.

## Can Samantha answer general-knowledge questions, not just project facts?

Yes, for clean factual/definitional queries ("what's the capital of France"), via a DuckDuckGo-instant-answer-then-Wikipedia-summary fallback (`general_knowledge()` in ask.py, reusing nimble's existing pattern). It's genuinely unreliable for ambiguous subjects (picked Tchaikovsky's overture over Shakespeare's play for "who wrote Romeo and Juliet" on one search, a different wrong answer on the next, Wikipedia's own search ranking is what varies here, not this code). It never fires on project questions, an explicit keyword gate keeps "Turing" (also Alan Turing's name) from getting hijacked by unrelated Wikipedia articles. It also never fires on a task instruction ("write a commit message for X"), only on something actually shaped like a question, `is_question()` gates it after a task prompt once got hijacked into Wikipedia's Git article.

## Can it answer "who's the president" or "who's the prime minister of X" correctly?

Yes, as of 2026-09-13. DDG and a plain Wikipedia summary both describe the office, never today's actual holder, that was a real limitation for months. Fixed with `current_officeholder()`: for a "who is/who's the X" question, it looks up the office in Wikidata and reads its officeholder claim directly, picking whichever claim Wikidata's own editors marked `rank: preferred`, that is literally how Wikidata flags which value is current among several historical ones (a fixed-term office like the presidency pre-fills an expected end-of-term date even on the sitting holder, so "no end date" alone isn't a safe signal, only the rank is). Tested against "who is the president of the united states" (correctly returns the sitting president) and "who's the prime minister of canada" (correctly returns Mark Carney). Facts like this can go stale after the next election, that's an accepted limitation of any live lookup, not a bug, Wikidata's own edits are what keep it current.

## What would Phase 5 let Samantha actually do for someone?

In-voice drafting (journal entries, commit messages, README sections in house style), answering project-status questions from real data via retrieval instead of memorized weights, local autocomplete that never touches the network, or acting as a cheap first-pass judge/filter model on every commit or PR before anything reaches a bigger model.

## What should Samantha be used for eventually, and what will Turing never do on this hardware?

Eventually: in-voice drafting, project Q&A from real data via retrieval, local autocomplete, or acting as a cheap first-pass judge/filter model, not competing with frontier models. Never, on this Mac Mini: pretrain a foundation model from raw text at frontier scale, that needs data-center-scale compute and a research team's budget, not a personal project's. Beating Claude or GPT was never the goal.

## What is chat.py?

A multi-turn conversation loop on top of ask.py's retrieval. Same underlying model and same FAQ-matching/general-knowledge/retrieval/generation chain, but it carries the last few exchanges as short-term memory, so a follow-up question like "what's its first model called" correctly resolves "its" to whatever was discussed a turn earlier, instead of needing every question spelled out standalone. Until 2026-09-13 it only had FAQ-matching and retrieval, not general-knowledge, so it couldn't answer "who's the president" even though ask.py could, that gap is now closed.

## What's the actual difference between ask.py and chat.py?

ask.py is the one-shot core: a single question in, one grounded answer out, no memory of anything before it. chat.py wraps ask.py's exact same answer logic (FAQ-match, officeholder lookup, retrieval, generation) in a loop that also remembers recent turns, so it handles follow-ups and feels like a real conversation instead of restarting from zero every question. Neither is a separate model, both call the same Samantha.

## What is the FAQ-matcher?

`faq_match()` in ask.py: parses this file's own `## Question` headers and answer paragraphs, fuzzy-matches an incoming question against them, and returns the real answer verbatim when confident, skipping retrieval and generation entirely. Added 2026-09-13 after hand-writing one-off fixes for failing eval questions turned into whack-a-mole. Jumped the eval score from about 10 out of 28 correct to about 24 out of 28 in one change, the single biggest win of that session. The lesson: a well-maintained FAQ beats fancier retrieval or training tricks for the questions people actually ask most.

## Why is there no live chat demo on the landing page?

The model runs locally via MLX on this Mac Mini, it isn't servable from a static Cloudflare Worker page without real hosting infrastructure (a running inference server, not just static files). Building that is real, separate infrastructure work, not attempted yet. Run `chat.py` locally instead for a real session.

## What's the current eval score?

As of 2026-09-14 there are four separate harnesses, because one number was hiding too much. `eval/score.py` scores 29 out of 29 on the hand-written set and 18 out of 18 on the held-out set. `test_chat.py` passes 18 out of 18 pure-function tests. `eval/faq_paraphrase.py` scores 13 out of 16 on natural rephrasings of questions the FAQ genuinely answers, a number that was 3 out of 16 before semantic matching landed. `eval/basic_questions.py` scores 16 out of 19 on general questions a child could answer, up from a 9 out of 19 baseline. The first two look perfect because their prompts are worded the way the FAQ words things; the last two exist precisely because that flattered the matcher. See `eval/` for every run's actual numbers and honest writeup, including the failed attempts that got there.

## How long does a question actually take to answer, and how much memory does it use?

Measured directly on this Mac Mini: an FAQ-matched question (no model load at all) answers in about 0.04 seconds using about 26MB. A question that falls through to retrieval plus generation takes about 2 seconds and peaks around 570MB, mostly the base model loading into memory. Neither is slow enough to need a persistent server process, that's why `ask.py` is invoked fresh each time instead of running as a daemon.

## How does ask.py decide when to trust a FAQ match versus generate an answer?

A similarity score (Python's difflib, comparing the question to every FAQ question) has to clear a threshold (0.55) before the FAQ answer is used. Below that, it falls through to retrieval plus generation instead, so a genuinely novel question doesn't get force-matched to an unrelated FAQ entry.

## How do I boot into Samantha and chat with her?

Run `./samantha` from the turing repo root. It activates the venv and launches `chat.py`'s plain text loop, type a question, get an answer, `exit` or Ctrl+C to quit.

## Is there a TUI, not just a plain CLI?

Yes. `./samantha --tui` launches a full-screen curses interface (`chat.py`'s `tui()` function, stdlib `curses`, no new dependency), same conversation logic as the plain CLI, just a scrolling full-screen view instead of line-by-line prints. `./samantha` with no flag stays plain-text.

## What happens if I run ./samantha with no flags at all?

Plain-text mode, the default. No flag means the ordinary line-by-line CLI (`chat.py`'s `chat()` function), not the TUI. Only `--tui` changes that.

## Can Samantha be used from other apps, not just the terminal?

Yes. `./.venv/bin/python serve.py` serves her over the OpenAI chat API shape on port 8127 (`POST /v1/chat/completions`, `GET /v1/models`), which is the one wire format most local-LLM tooling already speaks. Nimble needs no code changes at all: pick its Ollama engine and set the base URL to `http://localhost:8127`. A question Samantha declines comes back as the literal string `UNKNOWN`, which is Nimble's own signal to fall through to another engine rather than showing a refusal as if it were an answer. Run `./.venv/bin/python test_nimble.py` to check the pipe still works; it starts the server itself, sends the exact request Nimble builds, and parses the reply the way Nimble does.
