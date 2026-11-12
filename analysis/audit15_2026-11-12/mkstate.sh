#!/usr/bin/env bash
# Audit 15: replay the CURRENT code at another date, on a copy. Usage: mkstate.sh <YYYY-MM-DD> [HH:MM]
# Cuts the 1D candles after that day, rebuilds 2D/3D/5D/8D from them by fetch.py's rule (so the last bar of
# each chart is as partial as it would have been), cuts 4H/12H, sets CTZB_NOW and runs the pipeline.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; SRC="$HERE/../a15/current"; DAY="$1"; HM="${2:-04:14}"; D="$HERE/states/d$DAY"
rm -rf "${D:?}"; mkdir -p "$D"
(cd "$SRC" && tar --exclude=.git --exclude='analysis/audit*' --exclude='__pycache__' -cf - .) | tar -xf - -C "$D"
python3 - "$D" "$DAY" <<'PY'
import csv, sys, glob, datetime as dt
D, day = sys.argv[1], dt.date.fromisoformat(sys.argv[2])
cut = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(), dt.timezone.utc).timestamp()
for a in ('ETH', 'BTC'):
    rows = list(csv.reader(open(f'{D}/data/{a}_1D.csv'))); h = rows[0]
    keep = [r for r in rows[1:] if float(r[0]) < cut]
    csv.writer(open(f'{D}/data/{a}_1D.csv', 'w', newline='')).writerows([h] + keep)
    by = {dt.datetime.fromtimestamp(int(r[0]), dt.timezone.utc).date(): r for r in keep}
    for tf in (2, 3, 5, 8):
        g = {}
        for d in sorted(by): g.setdefault((d.year, (d - dt.date(d.year, 1, 1)).days // tf), []).append(d)
        out = []
        for k in sorted(g):
            ds = g[k]
            out.append([by[ds[0]][0], by[ds[0]][1], max((float(by[x][2]), by[x][2]) for x in ds)[1], min((float(by[x][3]), by[x][3]) for x in ds)[1], by[ds[-1]][4],
                        repr(sum(float(by[x][5]) for x in ds))])
        csv.writer(open(f'{D}/data/{a}_{tf}D.csv', 'w', newline='')).writerows([h] + out)
    for hh in ('4H', '12H'):
        rows = list(csv.reader(open(f'{D}/data/{a}_{hh}.csv'))); keep = [r for r in rows[1:] if float(r[0]) < cut]
        csv.writer(open(f'{D}/data/{a}_{hh}.csv', 'w', newline='')).writerows([rows[0]] + keep)
PY
export CTZB_NOW="${DAY}T${HM}:00Z"
cd "$D"
for s in "refresh.py --data data --out datasets" grade_live.py extras_live.py stack_live.py verify_cards.py; do
  python3 $s > /dev/null 2>&1 || { echo "FAIL $DAY: $s"; python3 $s 2>&1 | tail -3; exit 1; }
done
CTZB_STEP_OUTCOMES="refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success" python3 feed_live.py | tail -1
