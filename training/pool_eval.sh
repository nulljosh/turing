#!/bin/bash
# Scores one picker over every dev set (the blind sets already read once and now fair game) and prints the pooled totals,
# so two rounds are compared on ~4,400 rows instead of one 500-row set, where a retrain's own noise (a few rows) hides real change.
# Never touches the sealed sets (heldout4, heldout7, heldout12).
# Usage: training/pool_eval.sh MODEL_DIR OUT_DIR     (one hands.py report per set in OUT_DIR, then a pooled line)
set -uo pipefail
MODEL="${1:?model dir}"; OUT="${2:?output dir}"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
for n in "" 2 3 5 6 8 9 10 11; do
  SAMANTHA_HEADLESS=1 SAMANTHA_NO_LLM=1 ./.venv/bin/python eval/hands.py --model "$MODEL" --trained --test "eval/heldout${n}.jsonl" > "$OUT/h${n:-1}.out" 2>&1
done
python3 - "$OUT" <<'PY'
import glob, re, sys
tot = right = wrong = guard = refused = 0
for f in sorted(glob.glob(sys.argv[1] + "/h*.out")):
    m = re.search(r"(\d+)/(\d+) passed, (\d+) picked the wrong tool, (\d+) of those get past the guard in tools.do\(\), (\d+) right picks refused", open(f).read())
    if m:
        r, t, w, g, x = map(int, m.groups()); right += r; tot += t; wrong += w; guard += g; refused += x
print(f"pooled dev: {right}/{tot} right, {wrong} wrong picks, {guard} past the guard, {refused} right picks refused")
PY
