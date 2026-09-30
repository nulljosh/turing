# Turing loop handoff (2026-09-30)

## What the loop is

Work the Turing roadmap toward v5.0.0: her own tool-calling head, better picker accuracy, and research beyond Wikipedia. One round at a time, measured against held-out sets. Watch usage and taper on overage; hard stop at 90% session usage. This checkpoint saves the resume point; it does not restart training or the loop.

## Where things stand

v4.17.0 (2026-09-27): the guard refuses fewer right picks (heldout2 dev set 16 refused down to 7, standard set wrong-past-guard held at 9). Computer use is this week's focus: screen jobs look at the frontmost app after every action (accessibility tree, OCR fallback), click by accessibility first, run up to 25 steps, stop when stuck, and nudge a narrated step into a real call. eval/screen_bench.py drives a simulated app with the real qwen3:1.7b: all injection and failure scenarios pass; most tasks failed on the first run because of bugs it found (calls written as text, misnamed arguments), which are fixed, so rerun it for the new number. define_word reads the Mac dictionary offline. The landing page follows the Astra layout system. Headless runs never write to the Desktop. Name snapping was tried and dropped. GitHub issues went from 47 open to 27.

Voice and face (2026-09-27, afternoon): she speaks with ElevenLabs (Sarah) whenever a key is in the environment or in ~/.config/fish/secrets.fish, `say` only when there is none. Every line she says is cached in ~/.samantha/voice-cache, so repeats cost nothing. `--face` (or /face in chat, or the Face button in the Mac app) shows her face; it talks while her voice plays and freezes in the gaps between words. Ask her to change her voice or look (v4.17.0: list_voices, set_voice, restyle, keep_look, each priced before it runs). Default look: the twee one, strawberry blonde, round tortoiseshell glasses, mustard cardigan. The worker's /api/speak voices text for Joshua Tree, which now speaks her Chat replies through its own sound card. Next: her face inside Joshua Tree's Chat (in progress), then the landing demo.

## Next, in order

1. Improve guard refusals and wrong tool picks using training examples and development cases. Do not tune on the blind held-out cases or copy them into training.
2. Recheck the held-out sets after changes. The v5.0 gate remains fewer than ten wrong past the guard and zero right picks refused; the existing numbers do not meet it.
3. Run `python3 eval/bench.py` after each release and keep the reported measurements current.
4. Use `python3 app/chat.py`, `python3 app/tools.py`, and `python3 scripts/stats.py` from the repo root. Tests and eval commands keep their existing paths. Read `CLAUDE.md` for the full pre-push checks.

## Needs Joshua (the Mac)

- `training/picker_round.sh 14`: trains round fourteen (about 20 minutes), compares with the shipped adapter, reads heldout3 once if it is no less safe. Commit eval/picker-rounds.log after. 5.0 cannot be measured anywhere else.
- `python3 eval/screen_bench.py` (needs qwen3:1.7b in Ollama), and press Escape once during a screen job.

## Next, in order (this week)

1. Rerun `eval/screen_bench.py` on the Mac (needs qwen3:1.7b) and fix what it finds until every task passes. Done 2026-09-30: Escape kill switch (v4.17.1); law 12 own-words check for consequential screen clicks (v4.17.2). Try Escape on the real Mac once: it reads key state through Quartz via ctypes, untestable in the cloud.
2. Keep closing GitHub issues (27 open): each one shipped, merged into a duplicate, or moved to the roadmap with a reason.
3. Picker: v5.0 still needs fewer than ten wrong past the guard and zero refused on the blind third set. Round fourteen is prepared (v4.17.3); split training/gen_hands_data.py (658 lines) next: its filler pools into their own module.

## Restart prompt

```
/loop work the Turing roadmap until the next major version (5.0.0), one round at a time, watching Claude usage and tapering on overage; hard stop at 90% session usage.
```
