#!/usr/bin/env bash
# Replay the pipeline as of a past date on a copy of this repo: candles cut at the end of <date> (the date's
# own daily bar is kept whole and is "today's open bar"; 2D-8D bars are rebuilt from the cut daily candles),
# clock set to <date>T04:14Z (CTZB_NOW). Used by tests/test_year_end.py and by audits to reach states that today's data
# doesn't show. Regression is skipped (the ledger is shorter by construction).
# Usage: tests/replay_at.sh <YYYY-MM-DD> <out dir>
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"; DATE="${1:?date}"; D="${2:?out dir}"; rm -rf "${D:?}"; mkdir -p "$D"
(cd "$SRC" && tar --exclude=.git --exclude='analysis/audit*' -cf - .) | tar -xf - -C "$D"
python3 - "$D" "$DATE" <<'PY'
import csv, sys, glob, os, datetime as dt
D = sys.argv[1]
cut = (dt.datetime.fromisoformat(sys.argv[2]).replace(tzinfo=dt.timezone.utc) + dt.timedelta(days=1)).timestamp()
for p in glob.glob(D + '/data/*_*.csv'):
    rows = list(csv.reader(open(p))); h = rows[0]; ti = h.index('time')
    csv.writer(open(p, 'w', newline='')).writerows([h] + [r for r in rows[1:] if float(r[ti]) < cut])
# 2D-8D bars are rebuilt from the cut daily candles with fetch.py's own rule, so the open multi-day bar holds
# nothing after <date> (12 Nov 2026 audit #16: cutting the multi-day files by open time kept the whole bar)
sys.path.insert(0, D)
import fetch
for a in ('ETH', 'BTC'):
    p1 = f'{D}/data/{a}_1D.csv'
    if not os.path.exists(p1): continue
    rows = list(csv.DictReader(open(p1)))
    daily = {dt.datetime.fromtimestamp(float(r['time']), dt.timezone.utc).date(): tuple(float(r[k]) for k in ('open', 'high', 'low', 'close', 'volume')) for r in rows}
    first = {tf: float(next(csv.DictReader(open(f'{D}/data/{a}_{tf}D.csv')))['time']) for tf in (2, 3, 5, 8) if os.path.exists(f'{D}/data/{a}_{tf}D.csv')}
    for tf, t0 in first.items():
        out = fetch.resample(daily, tf)
        d0 = dt.datetime.fromtimestamp(t0, dt.timezone.utc).date()
        fetch.write(f'{D}/data/{a}_{tf}D.csv', {d: v for d, v in out.items() if d >= d0})
PY
export CTZB_NOW="${DATE}T04:14:00Z"
cd "$D"
for s in "refresh.py --data data --out datasets" grade_live.py extras_live.py stack_live.py verify_cards.py; do
  python3 $s > /dev/null 2>&1 || { echo "FAIL $DATE: $s"; python3 $s 2>&1 | tail -3; exit 1; }
done
CTZB_STEP_OUTCOMES="refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success" python3 feed_live.py > /dev/null
echo "ok $DATE"
