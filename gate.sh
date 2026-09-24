#!/bin/sh
# Gate: run checks and enforce baselines, refusing to pass if any number got worse.
# Usage: ./gate.sh [--full] [--update-baseline]
#   --full: also run eval/hands.py and live web demo
#   --update-baseline: rewrite baselines after all checks pass
#
# Baselines in eval/baseline.json keep scores from getting worse.
# Higher is better for chat, actions, parity, hands_passed.
# Lower is better for hands_past_guard and hands_refused.

set -e
cd "$(dirname "$0")"

BASELINE="eval/baseline.json"

# Run all checks and collect results
echo "=== fast checks ==="

OUT=$(python3 tests/test_chat.py 2>&1 | tail -1)
CHAT=$(echo "$OUT" | cut -d/ -f1)

OUT=$(python3 eval/actions.py 2>&1 | tail -1)
ACTIONS=$(echo "$OUT" | cut -d/ -f1)

OUT=$(python3 eval/web_parity.py 2>&1 | tail -1)
PARITY=$(echo "$OUT" | cut -d/ -f1)

OUT=$(SAMANTHA_HEADLESS=1 python3 tools.py 2>&1 | tail -1)
TOOLS_OK=$([ "$OUT" = "tools ok" ] && echo "1" || echo "0")

# The docs rule: 100 percent of functions and classes documented, or nothing ships.
python3 stats.py --check || { echo "FAIL docs coverage below 100 percent"; exit 1; }

# The laws in LAWS.md, checked against every tool.
python3 eval/laws.py || { echo "FAIL a law in LAWS.md is broken"; exit 1; }

HANDS_PASSED=""
HANDS_PAST=""
HANDS_REFUSED=""
WEB_OK="1"

if [ "$1" = "--full" ]; then
	echo "=== full checks ==="

	if [ -d "hands-adapter" ] && [ -d ".venv" ]; then
		OUT=$(SAMANTHA_HEADLESS=1 .venv/bin/python eval/hands.py --adapter hands-adapter 2>&1 | tail -1)
		HANDS_PASSED=$(echo "$OUT" | cut -d/ -f1 | tr -d ' ')
		HANDS_PAST=$(echo "$OUT" | grep -o "[0-9]* of those get past" | cut -d' ' -f1)
		HANDS_REFUSED=$(echo "$OUT" | grep -o "[0-9]* right picks refused" | cut -d' ' -f1)
	fi

	python3 eval/smoke_images.py 2>&1 | tail -3 || true
	python3 eval/smoke_images.py >/dev/null 2>&1 || { echo "FAIL image tools smoke run"; exit 1; }
	.venv/bin/python eval/a11y.py https://turing.heyitsmejosh.com 2>&1 | tail -5 || true  # shown, and the release reads it
	.venv/bin/python eval/a11y.py https://turing.heyitsmejosh.com >/dev/null 2>&1 || { echo "FAIL accessibility audit"; exit 1; }
	if .venv/bin/python eval/web_demo.py https://turing.heyitsmejosh.com 2>&1 | grep -q "^ok:"; then
		WEB_OK="1"
	else
		WEB_OK="0"
	fi
fi

# Compare with baselines using Python
python3 - "$BASELINE" "$CHAT" "$ACTIONS" "$PARITY" "$TOOLS_OK" "$HANDS_PASSED" "$HANDS_PAST" "$HANDS_REFUSED" "$WEB_OK" "$1" <<'PYTHON'
import json, sys, os

baseline_file = sys.argv[1]
chat = int(sys.argv[2]) if sys.argv[2] else 0
actions = int(sys.argv[3]) if sys.argv[3] else 0
parity = int(sys.argv[4]) if sys.argv[4] else 0
tools_ok = int(sys.argv[5])
hands_passed = sys.argv[6]
hands_past = sys.argv[7]
hands_refused = sys.argv[8]
web_ok = int(sys.argv[9])
mode = sys.argv[10]

failed = 0

# Load baseline
baseline = {}
if os.path.exists(baseline_file):
	with open(baseline_file) as f:
		baseline = json.load(f)

# Check chat
base = baseline.get("chat", 0)
if chat >= base:
	print(f"PASS chat {chat}/{base}")
else:
	print(f"FAIL chat {chat} (baseline {base})")
	failed = 1

# Check actions
base = baseline.get("actions", 0)
if actions >= base:
	print(f"PASS actions {actions}/{base}")
else:
	print(f"FAIL actions {actions} (baseline {base})")
	failed = 1

# Check parity
base = baseline.get("parity", 0)
if parity >= base:
	print(f"PASS parity {parity}/{base}")
else:
	print(f"FAIL parity {parity} (baseline {base})")
	failed = 1

# Check tools
if tools_ok:
	print("PASS tools ok")
else:
	print("FAIL tools")
	failed = 1

# Full mode checks
if mode == "--full":
	if hands_passed:
		hands_passed = int(hands_passed)
		base = baseline.get("hands_passed", 0)
		if hands_passed >= base:
			print(f"PASS hands_passed {hands_passed}/{base}")
		else:
			print(f"FAIL hands_passed {hands_passed} (baseline {base})")
			failed = 1

		hands_past = int(hands_past)
		base = baseline.get("hands_past_guard", 999999)
		if hands_past <= base:
			print(f"PASS hands_past_guard {hands_past}/{base}")
		else:
			print(f"FAIL hands_past_guard {hands_past} (baseline {base})")
			failed = 1

		hands_refused = int(hands_refused)
		base = baseline.get("hands_refused", 999999)
		if hands_refused <= base:
			print(f"PASS hands_refused {hands_refused}/{base}")
		else:
			print(f"FAIL hands_refused {hands_refused} (baseline {base})")
			failed = 1

	if web_ok:
		print("PASS web_demo live")
	else:
		print("FAIL web_demo live")
		failed = 1

# Update baseline if requested and all passed
if mode == "--update-baseline" and failed == 0:
	print("=== updating baseline ===")
	new_baseline = {
		"chat": chat,
		"actions": actions,
		"parity": parity,
	}
	if hands_passed:
		new_baseline["hands_passed"] = int(hands_passed)
	if hands_past:
		new_baseline["hands_past_guard"] = int(hands_past)
	if hands_refused:
		new_baseline["hands_refused"] = int(hands_refused)

	with open(baseline_file, "w") as f:
		json.dump(new_baseline, f, indent=2)
	print("baseline updated")

sys.exit(failed)
PYTHON
