#!/usr/bin/env bash
# usage: run_replays.sh <list file: "name cutdate clockISO" per line>
A=/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit17
mkdir -p $A/out/rp2 $A/replays
while read -r NAME CUT CLOCK; do
  [ -z "$NAME" ] && continue
  [ -f "$A/out/rp2/$NAME.csv" ] && continue
  D=$A/replays/b2_$NAME
  R=$(bash $A/code/replay_any.sh $A/base "$CUT" "$CLOCK" "$D" 2>&1 | tail -1)
  if [[ "$R" != ok* ]]; then echo "$NAME PIPELINE: $R" >> $A/out/rp2/summary.txt; rm -rf "$D"; continue; fi
  (cd $A/code && python3 audit_page.py "$D" "$CLOCK" "$NAME" "$A/out/rp2/$NAME.csv" > "$A/out/rp2/$NAME.log" 2>&1) || echo "$NAME AUDIT CRASH: $(tail -1 $A/out/rp2/$NAME.log)" >> $A/out/rp2/summary.txt
  python3 - "$D" "$NAME" >> $A/out/rp2/summary.txt <<'PY'
import json,sys
f=json.load(open(sys.argv[1]+'/feed/ctzb_feed.json'))
print(sys.argv[2], f['market_regime'], 'cards', [(c['signal_id'],c['grade'],c['bars_to_confirm']) for c in f['cards']], 'openA+', [(o['signal_id'],o['days_elapsed'],o['edge_status'],o['edge_level_pct']) for o in f['open_signals'] if o['grade']=='A+'], 'open', len(f['open_signals']), 'forming prints', [(p['signal_id'],p['note']) for p in f['prints'] if p['state']=='forming'])
PY
  head -1 "$A/out/rp2/$NAME.log" >> $A/out/rp2/summary.txt 2>/dev/null
  mkdir -p $A/out/rp2/feeds; cp "$D/feed/ctzb_feed.json" "$A/out/rp2/feeds/$NAME.json"
  rm -rf "$D"
done < "$1"
