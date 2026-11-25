"""After a failed feed step: make sure this run did not leave the previous run's feed published (25 Nov 2026).

feed_live.py writes a fail-closed feed itself when it crashes. When it is killed instead (the step's `timeout`, a
SIGKILL, the runner losing the machine), its except block never runs, and the previous run's feed used to stay
published beside this run's new datasets: honest about its own time, stale after 5 hours, and its charts refused
for the price mismatch (audit round 48, recorded and not counted). This runs only when the feed step failed.

  - The feed on disk was written by this run (generated_at at or after the run's start): leave it. That covers a
    feed_live.py crash (it already wrote the fail-closed feed) and "feed published, but the alert log could not be
    written", where the published feed must stay so the next run can rebuild the log from it.
  - Otherwise (an older feed, none at all, or one that cannot be read): write the fail-closed feed, as a crash would.

The run's start comes from CTZB_RUN_STARTED (the workflow records it before fetching), else the run seal's
started_at. Exit 0 either way: the workflow already fails the run on the feed step's failure.

    python3 .github/scripts/feed_guard.py [--out feed/ctzb_feed.json] [--alert-log feed/alert_log.csv] [--datasets datasets]
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import feed_live as FL  # noqa: E402


class FeedStepKilled(Exception):
    """The feed step ended without writing a feed (killed or timed out)."""


def run_started(datasets):
    v = os.environ.get("CTZB_RUN_STARTED", "").strip()
    if v:
        return v
    try:
        return json.load(open(os.path.join(datasets, "manifest.json")))["started_at"]
    except Exception:  # noqa: BLE001 -- no start time: treat any feed on disk as not this run's
        return None


def written_this_run(out, started):
    try:
        g = json.load(open(out)).get("generated_at")
    except Exception:  # noqa: BLE001 -- unreadable or missing: not a feed this run published
        return False
    return isinstance(g, str) and started is not None and g >= started


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="feed/ctzb_feed.json")
    ap.add_argument("--alert-log", default="feed/alert_log.csv")
    ap.add_argument("--datasets", default="datasets")
    a = ap.parse_args(argv)
    started = run_started(a.datasets)
    if written_this_run(a.out, started):
        print(f"feed guard: the feed was written by this run (at or after {started}); left as it is")
        return 0
    FL.fail_closed(a.out, FeedStepKilled("the feed step ended without writing a feed"), a.alert_log)
    try:
        if FL.step_outcomes().get("extras", "success") != "success":
            FL.remove_extras_files(a.datasets)   # as feed_live.py does on a crash
    except Exception:  # noqa: BLE001 -- the fail-closed feed is already written
        pass
    print(f"feed guard: the feed step ended without writing a feed (run started {started}); wrote a fail-closed feed to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
