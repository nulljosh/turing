# Turing Technical Whitepaper

**v3.0.0** | September 2026

Turing builds small language models on one Mac. Its first model, Samantha, is a 0.5B model trained on your own writing. She will never out-think a frontier model. She does not try to. She runs on your Mac, costs nothing per question, keeps everything on the machine, and gets real work done with 90 exact tools. When a question is too hard for her, she borrows a bigger brain that also lives on the Mac. You can type to her or talk to her. She can see your screen, click in your apps, and research a topic with sources. She asks before anything that changes something.

## The core idea

A small model cannot hold facts without making them up. So Samantha does not try to remember. She looks things up and she uses tools.

Every request goes down the same ladder, and the first rung that holds wins:

1. **Exact routes.** "Set the volume to 30", "what's 15% of 80", "click Sign in". A recognisable command has one right answer, so no model is involved. Instant, and never wrong.
2. **Her own picker.** A second 0.5B model, trained to turn loose wording into a tool call. A guard refuses any pick whose argument is not in your sentence.
3. **Her FAQ and your notes.** Questions about the project are answered from its own docs and from your notes (the brain RAG service).
4. **The web, then her library.** Wikipedia and DuckDuckGo first. When the web has nothing or is down, her offline library: the lead of all 10,000 of Wikipedia's vital articles, plus your fieldbook of every science.
5. **Her own words.** Only now does Samantha write an answer herself, and only from passages she was handed. If they do not hold the answer, she says "My notes don't cover that."

Anything too hard goes to the biggest model on the Mac by name ("ask qwen", "ask llama", "ask claude" for the biggest): Qwen3.5-9B through oMLX, or qwen3:8b through Ollama.

## How she is trained

She starts from Qwen2.5-0.5B-Instruct, which already knows language. LoRA adds a small layer of trainable weights on top, trained with Apple's MLX on the Mac itself. No cloud GPU, no API bill.

Her material is everything: your wiki, every project README, whitepaper and roadmap, and the journal. That is 5,680 chunks, six times what she had before.

Then a teacher. Claude writes practice questions and answers from real passages of your docs. A local 9B model reads every pair and throws out answers that miss their question. Each lesson is wrapped in exactly the prompt she sees in real use. A tenth of the passages never reach training, so progress is measured on questions she has never seen. Round two taught her to decline: when her notes lack the answer, she now says so 16 times out of 16 (it was 3).

## What she can do

- **Talk.** `python3 chat.py --voice`. Whisper on the Mac turns speech into text, she answers, and she says it out loud.
- **See.** "Look at my screen and tell me what's wrong with this chart." A 3B vision model on the Mac looks and answers.
- **Act on screen.** "Click Sign in", "type hello", "press return". She reads the screen to find what you named, and asks before every step.
- **Research.** "Research the history of the printing press." She reads several sources and writes a short brief with a source after every sentence. A sentence she cannot back up is cut.
- **Everything else.** Her Mac, pictures and painting, math and time, documents, memory across sessions, Chrome tabs, Apple Shortcuts, and MCP in both directions.

## Promises she keeps

Rules live in LAWS.md and are checked against every tool on every push. Anything that writes, sends or looks at your screen asks first. Private tools never reach a model's menu. Her hands stay in your home folder. On the 65-question knowledge check she gets 58 right and 0 confidently wrong; the rest she declines.

## Limits, stated plainly

She cannot reason, do hard math, or write code like a frontier model. That gap is size, and it stays. On unseen questions about your own projects she answers 19 of 43 right; that is the next thing to train. Her eyes get the gist and miss details (she called the Dock a taskbar). The 9B helper takes about four minutes to load off the external drive. Voice, eyes, hands and research need the Mac; the web page is a stand-in.

---
Apache License 2.0, 2026 Joshua Trommel.
