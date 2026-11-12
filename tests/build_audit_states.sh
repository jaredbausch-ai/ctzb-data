#!/usr/bin/env bash
# Build the two frozen states an independent audit checks (12 Nov 2026, docs/AUDIT_LOG.md):
#   <out>/replay_0414  this repo's code on the data committed by the 12 Nov 2026 04:14 UTC run
#                      (commit 4aa1208, four forming setups), clock set to that moment (CTZB_NOW)
#   <out>/current      this repo's code and data, real clock
# Each gets the whole pipeline run (rescore .. feed) with every step passing.
# Usage: tests/build_audit_states.sh <out-dir>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:?usage: build_audit_states.sh <out-dir>}"
mkdir -p "$OUT"
for N in replay_0414 current; do
  D="$OUT/$N"; rm -rf "${D:?}"; mkdir -p "$D"
  (cd "$ROOT" && tar --exclude=.git -cf - .) | tar -xf - -C "$D"
done
rm -rf "${OUT:?}/replay_0414/data" "${OUT:?}/replay_0414/datasets" "${OUT:?}/replay_0414/feed"
(cd "$ROOT" && git archive 4aa1208 data datasets feed) | tar -x -C "$OUT/replay_0414"
for N in replay_0414 current; do
  D="$OUT/$N"
  if [ "$N" = replay_0414 ]; then export CTZB_NOW=2026-11-12T04:14:00Z; else unset CTZB_NOW; fi
  ( cd "$D"
    for s in "refresh.py --data data --out datasets" grade_live.py extras_live.py stack_live.py verify_cards.py "tests/regression.py --quiet"; do
      python3 $s > /dev/null 2>&1 || { echo "FAIL $N: $s"; exit 1; }
    done
    CTZB_STEP_OUTCOMES="refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success" python3 feed_live.py > /dev/null
    python3 -c "import json;f=json.load(open('feed/ctzb_feed.json'));print('$N', f['generated_at'], 'withheld' if f['cards_withheld'] else 'ok', len(f['cards']), 'cards')" )
done
