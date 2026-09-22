# Picker bake-off

Is Qwen the best base for her tool picker, and can a picker be built with nothing borrowed? Measured on 2026-09-21 with `eval/hands.py`, the same 834 unseen phrasings, 79 hand-written commands and 94 questions for every model. Same training data (`hands-data/`, 3958 rows), same recipe (LoRA, 300 iterations, batch 8, 16 layers, learning rate 1e-4). 300 iterations is a third of the shipped picker's 900, so all numbers here are lower than the live one (692 of 834).

| Base model | Unseen | Actions | Questions | Total | Wrong picks past the guard | Right picks refused | Train | Peak memory |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct (baseline) | 671 / 834 | 69 / 79 | 89 / 94 | 829 / 1007 | 10 | 1 | not timed | 2.5 GB |
| Qwen3-0.6B | 683 / 834 | 63 / 79 | 92 / 94 | 838 / 1007 | 15 | 0 | 6 min | 2.5 GB |
| Llama-3.2-1B-Instruct | pending | | | | | | | 4.4 GB |
| From scratch, 1.8M parameters, no pretrained anything | 248 / 834 | 70 / 79 | 71 / 94 | 389 / 1007 | 198 | 0 | 14 min | small |

## What it says

**Qwen3-0.6B is about 1.4 points better on unseen phrasings and no safer.** It picks the wrong tool less often (77 times against 107), but more of its wrong picks get past the guard (15 against 10). One run each, 300 iterations, so a gap this small could be noise. The live picker's rule is that wrong picks past the guard must not go up, and this fails it. Not worth switching on this evidence.

**A picker built from nothing does not work yet.** With no pretraining it handles the wordings it was trained on (70 of 79 hand-written commands) and fails new ones (30 percent of unseen phrasings, 198 wrong picks past the guard). Pretraining is what teaches a model that "how late is it in Tokyo" and "time in Tokyo" mean the same thing, and 23,000 synthetic rows do not teach that. A bigger from-scratch model is still being tried, and this row will be updated if it changes the picture.

## Caveats

- Timings are not comparable. Other jobs shared the machine.
- The unseen set was made by the same generator as the training data, with held-out templates and held-out names, so it measures new wordings, not new kinds of request.
- Nothing here retrains the live picker. `hands-adapter/` is untouched.

## Next

Run the two closest candidates (Qwen2.5 and Qwen3) again at the full 900 iterations, in a quiet machine, before deciding anything. Try a model 10 to 30 times bigger than the from-scratch one only if a from-scratch picker is still worth the effort.
