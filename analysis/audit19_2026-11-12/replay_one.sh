#!/usr/bin/env bash
# usage: replay_one.sh <date> <clock|-> <suffix|->   -> replays the pipeline as of <date> on a copy, audits it, deletes the copy
H=/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit19
D="$1"; CL="$2"; [ "$CL" = "-" ] && CL="${D}T04:14:00Z"; SUF="$3"; [ "$SUF" = "-" ] && SUF=""; LBL="replay_${D}${SUF}"
export A19_OUT=replays2
if ! bash $H/base/tests/replay_at.sh "$D" "$H/rp/$LBL" "$CL" > $H/replays2/$LBL.log 2>&1; then
  echo "PIPELINE FAIL $D: $(tail -4 $H/replays2/$LBL.log | tr '\n' ' ' | cut -c1-400)"
  bash $H/base/tests/replay_at.sh "$D" "$H/rp/$LBL" "$CL" --keep-going >> $H/replays2/$LBL.log 2>&1
fi
python3 $H/replay_audit.py "$H/rp/$LBL" "$CL" "$LBL" 2>&1 | tail -1
rm -rf "$H/rp/$LBL"
