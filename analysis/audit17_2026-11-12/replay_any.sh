#!/usr/bin/env bash
# Audit 17 harness: like the repo's tests/replay_at.sh (candles cut at the end of <date>, 2D-8D bars rebuilt
# from the cut daily candles with fetch.py's rule), but with any clock, so a run just after midnight UTC
# (before the new day's candle exists) can be replayed.  Usage: replay_any.sh <base> <cut date> <clock ISO> <out dir>
set -euo pipefail
SRC="$1"; DATE="$2"; CLOCK="$3"; D="$4"; rm -rf "${D:?}"; mkdir -p "$D"
(cd "$SRC" && tar --exclude=.git --exclude='analysis/audit*' -cf - .) | tar -xf - -C "$D"
python3 - "$D" "$DATE" <<'PY'
import csv, sys, glob, os, datetime as dt
D = sys.argv[1]
cut = (dt.datetime.fromisoformat(sys.argv[2]).replace(tzinfo=dt.timezone.utc) + dt.timedelta(days=1)).timestamp()
for p in glob.glob(D + '/data/*_*.csv'):
    rows = list(csv.reader(open(p))); h = rows[0]; ti = h.index('time')
    csv.writer(open(p, 'w', newline='')).writerows([h] + [r for r in rows[1:] if float(r[ti]) < cut])
sys.path.insert(0, D)
import fetch
for a in ('ETH', 'BTC'):
    p1 = f'{D}/data/{a}_1D.csv'
    rows = list(csv.DictReader(open(p1)))
    daily = {dt.datetime.fromtimestamp(float(r['time']), dt.timezone.utc).date(): tuple(float(r[k]) for k in ('open', 'high', 'low', 'close', 'volume')) for r in rows}
    first = {tf: float(next(csv.DictReader(open(f'{D}/data/{a}_{tf}D.csv')))['time']) for tf in (2, 3, 5, 8)}
    for tf, t0 in first.items():
        out = fetch.resample(daily, tf)
        d0 = dt.datetime.fromtimestamp(t0, dt.timezone.utc).date()
        fetch.write(f'{D}/data/{a}_{tf}D.csv', {d: v for d, v in out.items() if d >= d0})
PY
export CTZB_NOW="$CLOCK"
cd "$D"
for s in "refresh.py --data data --out datasets" grade_live.py extras_live.py stack_live.py verify_cards.py; do
  python3 $s > /dev/null 2>&1 || { echo "FAIL $DATE $CLOCK: $s: $(python3 $s 2>&1 | tail -1)"; exit 1; }
done
CTZB_STEP_OUTCOMES="refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success" python3 feed_live.py > /dev/null
echo "ok $DATE $CLOCK"
