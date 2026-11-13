#!/usr/bin/env bash
# Gate-off replay (12 Nov 2026 audit #14): cut the candles at 2026-06-11, when the regime gate was off and ten
# lows were forming, and run the pipeline at that moment. With the filter off there must be no member card and
# no forming alert (a gate-off low can never confirm); the lows still show in prints.csv as "regime off".
# Usage: tests/test_gate_off.sh [work dir]      (exit 1 on failure)
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"; D="${1:-$(mktemp -d)/gateoff}"; rm -rf "${D:?}"; mkdir -p "$D"
bash "$SRC/tests/replay_at.sh" 2026-06-11 "$D" > /dev/null || { echo "*** FAIL *** replay did not run"; exit 1; }
cd "$D"
python3 -c "
import json,csv;f=json.load(open('feed/ctzb_feed.json'))
fa=sum(1 for a in f['alerts'] if a.get('event')=='forming')
fp=[r for r in csv.DictReader(open('datasets/prints.csv')) if r['state']=='forming']
ok = len(f['cards'])==0 and fa==0 and len(fp)>=1 and all(r['note'].startswith('regime off') for r in fp) and 'bear' in (f.get('market_regime') or '').lower()
print(('PASS' if ok else '*** FAIL ***'), ' gate off:', len(f['cards']), 'cards,', fa, 'forming alerts,', len(fp), 'forming prints all regime off, regime', f.get('market_regime'))
raise SystemExit(0 if ok else 1)"
