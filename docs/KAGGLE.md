# Training a bigger picker for free

This Mac cannot train a base bigger than about 0.5B (the 0.8B crashed it twice). A free Kaggle GPU can train a 1.5B, and the Mac only has to run the result. Kaggle gives about 30 GPU-hours a week with no card; Colab's free T4 is the backup.

## On Kaggle
1. On the Mac, zip `hands-data/train.jsonl` and `hands-data/valid.jsonl` (run `python3 training/gen_hands_data.py` first if they are old). They are made-up template rows, nothing private. If you add real feedback rows (`training/feedback_to_data.py`), read them before uploading: they are your own words.
2. kaggle.com, Datasets, New Dataset, upload the zip, name it `samantha-hands`.
3. Code, New Notebook, Add Input (your dataset), Settings, Accelerator: GPU T4 x2 or P100.
4. Paste `training/kaggle_train.py` into one cell and run it. About an hour for 2 epochs. Change the base with the BASE variable (default `Qwen/Qwen2.5-1.5B-Instruct`).
5. When it prints `saved`, zip `/kaggle/working/hands-merged` and download it.

## Back on the Mac
```
./.venv/bin/mlx_lm.convert --hf-path hands-merged --mlx-path hands-merged-mlx -q
./.venv/bin/python eval/hands.py --model hands-merged-mlx --trained
./.venv/bin/python eval/hands.py --model hands-merged-mlx --trained --test eval/heldout2.jsonl
```
Compare with the numbers for the shipped picker in `eval/picker-rounds.log` (standard: 1307 right, 7 past the guard, 0 refused). The bar for 5.0 is under 10 past the guard and 0 refused on the sealed set. Read the sealed set only for a real final candidate.

## Not done yet
The merged model is scored, not wired in: the app loads the picker as the 0.5B base plus an adapter, so using a merged model means a small loader change. Do that only if the scores are worth it. The exact router also still answers first; 5.0 needs it out of the live path.
