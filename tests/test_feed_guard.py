"""The feed guard (.github/scripts/feed_guard.py, 25 Nov 2026): a killed feed step leaves a held feed, not the last one.

Works on a copy of this repo's datasets, feed and alert log. Cases:
  1. the feed step is SIGKILLed before it writes: the guard publishes the fail-closed feed, carrying the last feed's
     alert-log record and held alerts, and the next clean run publishes a clean feed again (nothing lost, nothing twice)
  2. the feed step wrote its feed this run: the guard leaves it byte for byte
  3. no feed on disk at all: the guard publishes the fail-closed feed
  4. no run start known and no seal: any feed on disk counts as not this run's

    python3 tests/test_feed_guard.py      -> exit 1 if any case fails
"""
import json, os, shutil, signal, subprocess, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import dataclock; NOW = dataclock.pin()  # noqa: E402 -- the repo data's own day, not the wall clock
import feedcheck  # noqa: E402
from reseal import reseal  # noqa: E402 -- the copy stands in for this run's scored datasets

OK = "refresh=success,grade=success,stack=success,cards=success,regress=success,extras=success"
res = []
def check(name, ok, detail=""):
    res.append(bool(ok)); print(f"  {'PASS' if ok else '*** FAIL ***'}  {name}" + ("" if ok else f"  -- {detail}"))


def workdir():
    w = tempfile.mkdtemp()
    shutil.copytree(f"{ROOT}/datasets", f"{w}/datasets"); os.makedirs(f"{w}/feed")
    for f in ("ctzb_feed.json", "alert_log.csv", "alert_log_backup.csv"):
        if os.path.exists(f"{ROOT}/feed/{f}"): shutil.copy(f"{ROOT}/feed/{f}", f"{w}/feed/{f}")
    reseal(f"{w}/datasets")
    return w


def env(started=None, now=NOW):
    e = dict(os.environ, CTZB_STEP_OUTCOMES=OK, CTZB_NOW=now)
    e.pop("CTZB_RUN_STARTED", None)
    if started: e["CTZB_RUN_STARTED"] = started
    return e


def feed_step(w, e, kill_after=None):
    args = [sys.executable, "-I", f"{ROOT}/feed_live.py", "--datasets", f"{w}/datasets", "--out", f"{w}/feed/ctzb_feed.json", "--alert-log", f"{w}/feed/alert_log.csv"]
    p = subprocess.Popen(args, env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if kill_after is not None:
        time.sleep(kill_after); p.send_signal(signal.SIGKILL)
    p.communicate(); return p.returncode


def guard(w, e):
    p = subprocess.run([sys.executable, "-I", f"{ROOT}/.github/scripts/feed_guard.py", "--out", f"{w}/feed/ctzb_feed.json",
                        "--alert-log", f"{w}/feed/alert_log.csv", "--datasets", f"{w}/datasets"], env=e, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


raw = lambda w: open(f"{w}/feed/ctzb_feed.json", "rb").read()
load = lambda w: json.load(open(f"{w}/feed/ctzb_feed.json"))

# 1. killed before writing: the feed on disk is the previous run's (written before this run started)
w = workdir(); prev = load(w); prev_raw = raw(w)
started = "2099-01-01T00:00:00Z"   # this run started after the feed on disk was written
rc = feed_step(w, env(started), kill_after=0.05)
check("the feed step is killed before writing (the feed on disk is still the last run's)", rc == -signal.SIGKILL and raw(w) == prev_raw, f"rc={rc} same={raw(w) == prev_raw}")
rc, out = guard(w, env(started))
f = load(w)
check("guard: publishes the fail-closed feed", rc == 0 and f["cards_withheld"] and f["alerts_withheld"] and f["cards"] == [] and f["open_signals"] == []
      and f.get("feed_error") == "FeedStepKilled" and f["checks"]["all_passed"] is False, out)
check("guard: the fail-closed feed passes the page's strict check (the page says held, not broken)", feedcheck.problems(f) == [], feedcheck.problems(f)[:3])
check("guard: it carries the last feed's alert-log record", f["alert_log"] == prev.get("alert_log"), f"{f['alert_log']} vs {prev.get('alert_log')}")
want_held = [a["alert_id"] for a in prev.get("alerts", []) + prev.get("alerts_held", [])]
check("guard: alerts the last feed was carrying are held for the next clean feed", sorted(a["alert_id"] for a in f["alerts_held"]) == sorted(set(want_held)), f"{[a['alert_id'] for a in f['alerts_held']]} vs {want_held}")
rc = feed_step(w, env(started))
g = load(w)
check("the next clean run publishes a clean feed again", rc == 0 and not g["cards_withheld"] and g["checks"]["all_passed"], f"rc={rc} withheld={g.get('cards_withheld')} failed={g.get('checks', {}).get('failed_steps')}")
logged = {l.split(",")[0] for l in open(f"{ROOT}/feed/alert_log.csv").read().splitlines()[1:]}
fresh = [a["alert_id"] for a in g["alerts"] if a["alert_id"] not in {x["alert_id"] for x in prev.get("alerts", [])}]
check("...sending no alert that was already logged before the kill", not (set(fresh) & logged) and feedcheck.problems(g) == [], f"{set(fresh) & logged} {feedcheck.problems(g)[:2]}")
shutil.rmtree(w)

# 2. the feed step wrote its feed this run (generated_at at or after the start): left byte for byte
w = workdir()
rc = feed_step(w, env("2000-01-01T00:00:00Z"))
before = raw(w)
rc2, out = guard(w, env("2000-01-01T00:00:00Z"))
check("a feed written this run is left as it is", rc == 0 and rc2 == 0 and raw(w) == before and "left as it is" in out, out)
shutil.rmtree(w)

# 3. no feed on disk at all
w = workdir(); os.remove(f"{w}/feed/ctzb_feed.json")
rc, out = guard(w, env("2099-01-01T00:00:00Z"))
f = load(w)
check("no feed on disk: the fail-closed feed is published", rc == 0 and f["cards_withheld"] and f.get("feed_error") == "FeedStepKilled", out)
shutil.rmtree(w)

# 4. no start time and no seal: the feed on disk is not taken as this run's
w = workdir(); os.remove(f"{w}/datasets/manifest.json")
rc, out = guard(w, env(None))
f = load(w)
check("no run start known: the feed on disk is not taken as this run's", rc == 0 and f["cards_withheld"] and f.get("feed_error") == "FeedStepKilled", out)
shutil.rmtree(w)

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
