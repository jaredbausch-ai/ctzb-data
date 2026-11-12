#!/usr/bin/env bash
# Gate-off replay (12 Nov 2026 audit #14): cut the candles at 2026-06-11, when the regime gate was off and ten
# lows were forming, and run the pipeline at that moment. With the filter off there must be no member card and
# no forming alert (a gate-off low can never confirm); the lows still show in prints.csv as "regime off".
# Usage: tests/test_gate_off.sh [work dir]      (exit 1 on failure)
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"; D="${1:-$(mktemp -d)/gateoff}"; rm -rf "${D:?}"; mkdir -p "$D"
(cd "$SRC" && tar --exclude=.git --exclude='analysis/audit*' -cf - .) | tar -xf - -C "$D"
python3 - "$D" <<'PY'
import csv, sys, glob, datetime as dt
cut = dt.datetime(2026,6,12,tzinfo=dt.timezone.utc).timestamp()
for p in glob.glob(sys.argv[1]+'/data/*_*.csv'):
    rows=list(csv.reader(open(p))); h=rows[0]; ti=h.index('time')
    keep=[r for r in rows[1:] if float(r[ti]) < cut]
    csv.writer(open(p,'w',newline='')).writerows([h]+keep)
PY
export CTZB_NOW=2026-06-11T04:14:00Z
cd "$D"
for s in "refresh.py --data data --out datasets" grade_live.py extras_live.py stack_live.py verify_cards.py; do
  python3 $s > /dev/null 2>&1 || { echo "FAIL: $s"; python3 $s 2>&1 | tail -3; exit 1; }
done
CTZB_STEP_OUTCOMES="refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success" python3 feed_live.py | tail -1
python3 -c "
import json,csv;f=json.load(open('feed/ctzb_feed.json'))
fa=sum(1 for a in f['alerts'] if a.get('event')=='forming')
fp=[r for r in csv.DictReader(open('datasets/prints.csv')) if r['state']=='forming']
ok = len(f['cards'])==0 and fa==0 and len(fp)>=1 and all(r['note'].startswith('regime off') for r in fp) and 'bear' in (f.get('market_regime') or '').lower()
print(('PASS' if ok else '*** FAIL ***'), ' gate off:', len(f['cards']), 'cards,', fa, 'forming alerts,', len(fp), 'forming prints all regime off, regime', f.get('market_regime'))
raise SystemExit(0 if ok else 1)"
