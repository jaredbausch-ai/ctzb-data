#!/usr/bin/env bash
# build (if needed) and audit one replay date; prints one summary line
cd "$(dirname "$0")"; DAY="$1"
mkdir -p states; ./mkstate.sh $DAY > states/build_$DAY.log 2>&1 || { echo "$DAY BUILD FAILED"; rm -rf states/d$DAY; exit 0; }
a=$(python3 audit_data.py states/d$DAY d$DAY 2>&1 | grep -A200 "^TOTAL")
b=$(python3 page_audit.py states/d$DAY d$DAY 2>&1 | grep -A200 "^PAGE TOTAL")
echo "== $DAY $(python3 -c "
import json;f=json.load(open('states/d$DAY/feed/ctzb_feed.json'))
print('cards', [(c['signal_id'],c['grade'],c['bars_to_confirm']) for c in f['cards']], 'openA+', [(o['signal_id'],o['edge_level_pct'],o['edge_status']) for o in f['open_signals'] if o['grade']=='A+'], 'forming prints', [p['signal_id']+':'+p['note'] for p in f['prints'] if p['state']=='forming'])")"
echo "$a"; echo "$b"
