#!/usr/bin/env bash
# Replay the pipeline as of a past date on a copy of this repo: candles cut at the end of <date>, clock set
# to <date>T04:14Z (CTZB_NOW). Used by tests/test_year_end.py and by audits to reach states that today's data
# doesn't show. Regression is skipped (the ledger is shorter by construction).
# Usage: tests/replay_at.sh <YYYY-MM-DD> <out dir>
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"; DATE="${1:?date}"; D="${2:?out dir}"; rm -rf "${D:?}"; mkdir -p "$D"
(cd "$SRC" && tar --exclude=.git --exclude='analysis/audit*' -cf - .) | tar -xf - -C "$D"
python3 - "$D" "$DATE" <<'PY'
import csv, sys, glob, datetime as dt
cut = (dt.datetime.fromisoformat(sys.argv[2]).replace(tzinfo=dt.timezone.utc) + dt.timedelta(days=1)).timestamp()
for p in glob.glob(sys.argv[1] + '/data/*_*.csv'):
    rows = list(csv.reader(open(p))); h = rows[0]; ti = h.index('time')
    csv.writer(open(p, 'w', newline='')).writerows([h] + [r for r in rows[1:] if float(r[ti]) < cut])
PY
export CTZB_NOW="${DATE}T04:14:00Z"
cd "$D"
for s in "refresh.py --data data --out datasets" grade_live.py extras_live.py stack_live.py verify_cards.py; do
  python3 $s > /dev/null 2>&1 || { echo "FAIL $DATE: $s"; python3 $s 2>&1 | tail -3; exit 1; }
done
CTZB_STEP_OUTCOMES="refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success" python3 feed_live.py > /dev/null
echo "ok $DATE"
