# scratch-picker

A tool picker that is entirely ours. Random-initialized weights, a character vocabulary built from our own training rows, no pretrained model, no borrowed embeddings.

The model is a small character transformer with three heads: one picks the tool (or null, or agent), one says whether the argument is empty, copied from the query, or a fixed canonical value (like "up" or "~/Desktop"), and one marks the start and end characters of a copied argument. The output is turned into JSON and passed through tools._sound(), same as the LLM picker.

Train: `SAMANTHA_HEADLESS=1 ../.venv/bin/python train.py --name exp1 --minutes 14 --per 20 --seeds 4`
Score: `SAMANTHA_HEADLESS=1 ../.venv/bin/python eval.py --name exp1`

eval.py uses hands.cases() and the same correctness rule as eval/hands.py. Note cases() currently yields 1007 rows (79 actions), not 1005.

Training data is only gen_hands_data.build(0, ...) with several seeds, minus anything in the test sets. exp2 adds casing, punctuation, filler and typo augmentation.

Results (measured): exp1 got 248/834 unseen, 389/1007 total, 198 wrong picks past the guard. exp2 (bigger, augmented) got 220/834 unseen, 346/1007. Training loss went to nearly zero, so the model memorizes the training templates and does not generalize to new phrasings like "boot up" or "pop open". Qwen with LoRA gets 692/834 because it already knows language.
