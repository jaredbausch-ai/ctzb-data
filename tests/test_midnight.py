"""Family 5 (timing): a run whose scoring finishes before 00:00 UTC and whose feed is written after it
(14 Nov 2026 audit #31). The data describes a daily bar that has closed, so the feed must not be published as clean:
feed_live fails closed (the strict check refuses a feed that is not withheld whose scored_as_of is before its own
day). The same data written a few seconds before midnight publishes clean.

Quiet market (no cards, no open signals), because that is the state that got through: with open signals the
days_elapsed cross-check already failed the run closed.

    python3 tests/test_midnight.py      -- exits 1 if any case fails
Entry quality only: computed signals, not fills.
"""
import csv, datetime as dt, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, ROOT)
from reseal import reseal  # noqa: E402
import feedcheck  # noqa: E402
results = []


def ok(label, cond, detail=""):
    results.append(bool(cond)); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f"  -- {detail}" if not cond and detail else ""))


def status_day(ds):
    return next(r["value"] for r in csv.DictReader(open(f"{ds}/status.csv")) if r["item"] == "Scored as of")


def run(clock):
    """A quiet run whose scoring is sealed at `clock` minus 20 s and whose feed is written at `clock`."""
    w = tempfile.mkdtemp(); ds = f"{w}/datasets"
    shutil.copytree(f"{ROOT}/datasets", ds)
    with open(f"{ds}/open.csv") as f: head = f.readline()
    open(f"{ds}/open.csv", "w").write(head)                      # quiet: no open signals
    with open(f"{ds}/cards.csv") as f: head = f.readline()
    open(f"{ds}/cards.csv", "w").write(head)                     # and no live or forming card
    sealed = (dt.datetime.fromisoformat(clock.replace("Z", "+00:00")) - dt.timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    reseal(ds, started_at=sealed)
    env = dict(os.environ, CTZB_NOW=clock, CTZB_SEED_ALERT_LOG="1",
               CTZB_STEP_OUTCOMES="refresh=success,grade=success,extras=success,stack=success,cards=success,regress=success")
    os.makedirs(f"{w}/feed")
    p = subprocess.run([sys.executable, "-I", f"{ROOT}/feed_live.py", "--datasets", ds, "--out", f"{w}/feed/ctzb_feed.json",
                        "--alert-log", f"{w}/feed/alert_log.csv"], env=env, capture_output=True, text=True)
    f = json.load(open(f"{w}/feed/ctzb_feed.json")) if os.path.exists(f"{w}/feed/ctzb_feed.json") else None
    shutil.rmtree(w)
    return p, f


day = status_day(f"{ROOT}/datasets")
nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()

p, f = run(f"{day}T23:59:55Z")
ok("quiet run, scored and written before 00:00 UTC: published clean", p.returncode == 0 and f and not f["cards_withheld"] and f["scored_as_of"] == day,
   (p.stderr or "")[-300:])

p, f = run(f"{nxt}T00:00:05Z")
ok("quiet run, scored before 00:00 UTC and written after it: not published as clean (fails closed)",
   p.returncode != 0 and f is not None and f["cards_withheld"] and f["scored_as_of"] is None and not f["cards"] and not f["open_signals"],
   f"rc {p.returncode}; withheld {f and f['cards_withheld']}; scored {f and f['scored_as_of']}")
ok("...and the reason given is the scored day", "scored_as_of: before" in (p.stderr or ""), (p.stderr or "")[-300:])

# the strict check itself, the one the page and the pipeline share
g = json.load(open(f"{ROOT}/feed/ctzb_feed.json"))
if not g["cards_withheld"]:
    g2 = json.loads(json.dumps(g)); g2["scored_as_of"] = (dt.date.fromisoformat(g["generated_at"][:10]) - dt.timedelta(days=1)).isoformat()
    ok("strict check: a feed that is not withheld, scored the day before it was written, is refused",
       any("scored_as_of" in x for x in feedcheck.problems(g2)), str(feedcheck.problems(g2)[:3]))
    ok("strict check: the same feed scored on its own day passes", not feedcheck.problems(g), str(feedcheck.problems(g)[:3]))

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
