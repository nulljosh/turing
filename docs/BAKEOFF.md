# Picker bake-off

Is Qwen the best base for her tool picker, and can a picker be built with nothing borrowed? Measured on 2026-09-21 with `eval/hands.py`, the same 834 unseen phrasings, 79 hand-written commands and 94 questions for every model. Same training data (`hands-data/`, 3958 rows), same recipe (LoRA, 300 iterations, batch 8, 16 layers, learning rate 1e-4). 300 iterations is a third of the shipped picker's 900, so all numbers here are lower than the live one (692 of 834).

| Base model | Unseen | Actions | Questions | Total | Wrong picks past the guard | Right picks refused | Train | Peak memory |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct (baseline) | 671 / 834 | 69 / 79 | 89 / 94 | 829 / 1007 | 10 | 1 | not timed | 2.5 GB |
| Qwen3-0.6B | 683 / 834 | 63 / 79 | 92 / 94 | 838 / 1007 | 15 | 0 | 6 min | 2.5 GB |
| Llama-3.2-1B-Instruct | not scored | | | | | | 14 min (about 3 times slower per step) | 4.4 GB |
| From scratch, 1.8M parameters, no pretrained anything | 248 / 834 | 70 / 79 | 71 / 94 | 389 / 1007 | 198 | 0 | 14 min | small |
| From scratch, 3.2M parameters plus augmentation (casing, typos, fillers) | 220 / 834 | 65 / 79 | 61 / 94 | 346 / 1007 | 209 | 0 | 12 min | small |

## What it says

**Qwen3-0.6B is about 1.4 points better on unseen phrasings and no safer.** It picks the wrong tool less often (77 times against 107), but more of its wrong picks get past the guard (15 against 10). One run each, 300 iterations, so a gap this small could be noise. The live picker's rule is that wrong picks past the guard must not go up, and this fails it. Not worth switching on this evidence.

**Llama 3.2 1B trained but was never scored.** The scoring run was stopped to wrap up. Even before scoring it is a poor fit: about three times slower to train than the 0.5B models and 4.4 GB of memory at peak on a 16 GB machine that also runs everything else. It would need to be clearly better to earn that, and there is no evidence that it is.

**A picker built from nothing does not work yet.** With no pretraining it handles the wordings it was trained on (70 of 79 hand-written commands) and fails new ones (30 percent of unseen phrasings, 198 wrong picks past the guard). Pretraining is what teaches a model that "how late is it in Tokyo" and "time in Tokyo" mean the same thing, and 23,000 synthetic rows do not teach that. A bigger model with augmentation did slightly worse (220 of 834), not better: training loss went to nearly zero in both runs, which is memorizing the templates. The from-scratch code is in `scratch-picker/` (a 3 to 13 MB character transformer with tool, argument-mode and span heads, 1.5 ms a query) if someone wants to try it with far more varied data.

**Where the from-scratch model fails.** Only 41 of its 586 misses on unseen phrasings had the right tool and a wrong argument, so the argument-copying part works and tool choice is the problem. New verbs are the trigger: "boot up" and "pop open" never appeared in its training rows, so "boot up podcasts" came back as no tool, and "boot up stocks" as a web search. Music commands were sent to open_app or web_search, and volume commands to the agent or to say.

## Caveats

- Timings are not comparable. Other jobs shared the machine.
- The unseen set was made by the same generator as the training data, with held-out templates and held-out names, so it measures new wordings, not new kinds of request.
- Nothing here retrains the live picker. `hands-adapter/` is untouched.

## Next

Run the two closest candidates (Qwen2.5 and Qwen3) again at the full 900 iterations, in a quiet machine, before deciding anything. A from-scratch picker needs much more varied training text than templates can make, so the honest options are real paraphrase data or staying with a pretrained base.
