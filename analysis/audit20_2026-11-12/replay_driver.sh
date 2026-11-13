#!/usr/bin/env bash
# usage: replay_driver.sh <list file> <log>
cd "$(dirname "$0")"
while read -r date clock cat; do
  [[ "$date" =~ ^# ]] && continue; [ -z "$date" ] && continue
  if [ "$clock" = "-" ]; then clock="${date}T04:14:00Z"; name="r_${date}"; else name="r_${date}_$(echo $clock | cut -c12-16 | tr -d :)"; fi
  if grep -q "^$name " "$2" 2>/dev/null; then continue; fi
  out=$(bash base/tests/replay_at.sh "$date" "$PWD/rp/$name" "$clock" 2>&1 | grep -E "^(ok|FAIL)" | head -1)
  if [[ "$out" == ok* ]]; then
    res=$(python3 run_state.py "rp/$name" "$clock" "$name" --out replays 2>&1 | tr '\n' ' ' | cut -c1-1500)
    echo "$name | $cat | $res" >> "$2"
    rm -rf "rp/$name"
  else
    msg=$(bash base/tests/replay_at.sh "$date" "$PWD/rp/$name" "$clock" 2>&1 | tail -4 | tr '\n' ' ' | cut -c1-600)
    echo "$name | $cat | PIPELINE-FAIL $msg" >> "$2"
  fi
done < "$1"
echo DONE >> "$2"
