#!/usr/bin/env bash
# Re-run a failed pipeline workflow with a cooldown that grows with the failure streak.
# Added 4 Nov 2026 (Jared: "our data flow needs to be repushed immediately on failures.
# Unless there is a succession of failures ... a cooldown ... retried for 15 or 30 minutes").
#
#   streak 1-2  -> re-run after 1 minute   (a one-off blip: try again straight away)
#   streak 3-5  -> re-run after 15 minutes (the source may be having issues: cool down)
#   streak 6+   -> re-run every 30 minutes, forever, until it succeeds
#
# The streak counts this run plus the consecutive FAILED runs before it (cancelled runs are
# ignored; any successful run, including a gate skip, ends a streak). From the 3rd failure
# in a row a GitHub issue labelled pipeline-alert is opened (GitHub emails the owner) and
# commented on at the 3rd failure and every 6th after; the next successful run closes it.
#
# Usage: retry_after_failure.sh <workflow file, e.g. daily.yml> <label for the alert>
# Needs GH_TOKEN (actions: write, issues: write) and GITHUB_REPOSITORY, GITHUB_RUN_ID.
set -u
WF="$1"; WHAT="$2"; REPO="$GITHUB_REPOSITORY"

prior=$(gh api "repos/$REPO/actions/workflows/$WF/runs?per_page=50&status=completed" \
  --jq "[.workflow_runs[] | select(.id != $GITHUB_RUN_ID) | select(.conclusion != \"cancelled\" and .conclusion != \"skipped\") | .conclusion]" \
  2>/dev/null || echo '[]')
streak=$(( 1 + $(python3 -c "import json,sys; c=json.loads(sys.argv[1]); n=0
for x in c:
    if x in ('failure', 'timed_out'): n+=1
    else: break
print(n)" "$prior") ))

if   [ "$streak" -le 2 ]; then wait=60
elif [ "$streak" -le 5 ]; then wait=900
else                            wait=1800
fi
echo "$WHAT failed. Failure streak: $streak. Re-running in $((wait / 60)) minute(s)."

if [ "$streak" -ge 3 ]; then
  log="https://github.com/$REPO/actions/runs/$GITHUB_RUN_ID"
  body="**$WHAT has failed $streak runs in a row.** Latest: $log. Cooling down: next automatic re-run in $((wait / 60)) minutes, and every 30 minutes from the 6th failure until it succeeds. This issue closes itself on the next successful run."
  gh label create pipeline-alert -R "$REPO" --color B60205 --description "Data pipeline failing or stale" 2>/dev/null || true
  open=$(gh issue list -R "$REPO" --label pipeline-alert --state open --json number,title \
         --jq "[.[] | select(.title | startswith(\"$WHAT\"))][0].number // empty" 2>/dev/null || true)
  if [ -z "$open" ]; then
    gh issue create -R "$REPO" --label pipeline-alert --title "$WHAT failing: $streak runs in a row" --body "$body" || true
  elif [ "$streak" -eq 3 ] || [ $(( (streak - 3) % 6 )) -eq 0 ]; then
    gh issue comment "$open" -R "$REPO" --body "$body" || true
  fi
fi

sleep "$wait"
for i in 1 2 3 4 5; do
  if gh api -X POST "repos/$REPO/actions/workflows/$WF/dispatches" -f ref=main; then
    echo "re-run dispatched $(date -u '+%H:%M UTC')"; exit 0
  fi
  sleep $((i * 20))
done
echo "COULD NOT DISPATCH the re-run"; exit 1
