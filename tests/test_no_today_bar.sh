#!/usr/bin/env bash
# A run whose daily candles lack today's bar must not publish cards (12 Nov 2026 audit #17). Candles are cut
# at 11 Nov 2026 and the clock is set to 12 Nov 00:05 UTC: just after midnight, before the new day's candle
# exists. stack_live.py must fail closed, and the feed must withhold cards and open signals.
# (In a real run fetch.py builds today's bar from the hourly candles and check_fresh.py refuses a run without it.)
# Usage: tests/test_no_today_bar.sh [work dir]      (exit 1 on failure)
set -uo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"; D="${1:-$(mktemp -d)/notoday}"
bash "$SRC/tests/replay_at.sh" 2026-11-11 "$D" 2026-11-12T00:05:00Z --keep-going > /dev/null 2>&1
cd "$D" || { echo "*** FAIL *** replay did not run"; exit 1; }
python3 -c "
import json
f=json.load(open('feed/ctzb_feed.json')); st=open('datasets/stack_status.txt').read()
ok = f.get('cards_withheld') is True and f['cards']==[] and f['open_signals']==[] and 'FAILED' in st and \"today's bar is missing\" in st
print(('PASS' if ok else '*** FAIL ***'), ' no today bar: cards withheld', f.get('cards_withheld'), '| cards', len(f['cards']), '| open signals', len(f['open_signals']), '|', st.strip()[:110])
raise SystemExit(0 if ok else 1)"
