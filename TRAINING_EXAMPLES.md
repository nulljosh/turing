# Training examples

Real instruction/response pairs, not FAQ facts. `prep_data.py` reads this
file separately from FAQ.md so Samantha sees actual examples of task-style
output (a commit message, a changelog line) instead of only ever seeing
"tell me about X" -> FAQ-doc-voice pairs. Added 2026-09-13 after a retrain
regressed on "write a one-line commit message", the model blended FAQ-doc
structure into what should have been a terse, plain line. Every response
here is a real commit message from this repo's own git history, not
invented, so the style is genuinely this project's own voice.

## Write a one-line commit message for fixing an MLX memory leak during training.

Fix a real hang in prep_data.py, own-doc chunks 28 -> 55

## Write a one-line commit message for adding a new FAQ entry.

FAQ.md: fill two real content gaps the eval exposed

## Write a one-line commit message for fixing a bug in the retrieval fallback.

Fix a real crash: no brain/.env.local = unhandled traceback

## Write a one-line commit message for adding automated tests.

Real QA infra: automated pass/fail scoring instead of eyeballing

## Write a one-line commit message for updating stale documentation.

WHITEPAPER.md was stale: still v0.1, described RAG as a future plan

## Write a one-line commit message for fixing a false-positive matching bug.

Fix faq_match false positive the officeholder fix exposed

## Write a one-line commit message for wiring a feature into a second file that was missing it.

Wire general_knowledge into chat.py, it never had it

## Write a one-line commit message for adding version tracking to a project that never had one.

Add real semver, this project never had one

## Write a one-line commit message for confirming a hardware limitation and stopping further retries.

Qwen3.5-0.8B: confirmed real hardware limit, stopping retries

## Write a one-line commit message for adding CI to a repo that had tests but no pipeline.

Add CI: run test_chat.py on push/PR

## Write a short journal entry about fixing a stubborn bug that turned out to be a false alarm.

Spent a while convinced a script was hung forever, killed it twice before realizing the elapsed time I was reading was cumulative across hundreds of files, not stuck on one. The real fix (a hard timeout per file) was right the first time, I just didn't trust it long enough to see it finish.

## Write a short journal entry about a retrain that mostly worked but had one honest regression.

Doubled the training data and the loss dropped like it should, but one generation task came out worse, not better. Kept the new weights anyway since everything else improved and the one miss is well understood, not going to chase a clean scoreboard over an honest result.
