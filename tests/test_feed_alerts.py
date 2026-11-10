"""Tests for the alert guard in feed_live.py (item 17d). Runs feed_live.py as the
pipeline does, on a copy of datasets/, across a sequence of simulated runs.

Run: python tests/test_feed_alerts.py   -- exits 1 if any case fails.
"""
import csv, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = tempfile.mkdtemp()
DS, FEED, LOG = f"{W}/datasets", f"{W}/feed/ctzb_feed.json", f"{W}/feed/alert_log.csv"
shutil.copytree(f"{ROOT}/datasets", DS)
CARD_COLS = open(f"{DS}/cards.csv").readline().strip().split(",")
results = []


def set_cards(cards):
    with open(f"{DS}/cards.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CARD_COLS); w.writeheader()
        for chart, confirms in cards:
            r = {k: "" for k in CARD_COLS}
            r.update(chart=chart, asset=chart.split()[0], tf=chart.split()[1], trough="2026-11-07",
                     confirms=confirms, grade="A", confluences="[]")
            w.writerow(r)


def add_print(chart, confirms):
    with open(f"{DS}/prints.csv", "a", newline="") as f:
        csv.writer(f).writerow([chart, "confirmed", "2026-11-07", confirms, "2100", "A", "regime on"])


def run(outcomes="refresh=success,grade=success,stack=success,cards=success,regress=success"):
    env = dict(os.environ)
    env.pop("CTZB_STEP_OUTCOMES", None)
    if outcomes is not None:
        env["CTZB_STEP_OUTCOMES"] = outcomes
    p = subprocess.run([sys.executable, "-I", f"{ROOT}/feed_live.py", "--datasets", DS, "--out", FEED,
                        "--alert-log", LOG], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.load(open(FEED))


def log_n():
    return sum(1 for _ in open(LOG)) - 1 if os.path.exists(LOG) else 0


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else '*** FAIL ***'}  {name}{('  -- ' + detail) if detail else ''}")


set_cards([])
f = run()
check("first run seeds the log and sends nothing", f["alerts_seeded"] and f["alerts"] == [] and log_n() > 0,
      f"seeded {log_n()} existing signals")
check("schema version is 4", f["schema_version"] == 4)
check("every print and open signal carries a signal_id",
      all(x.get("signal_id") for x in f["prints"] + f["open_signals"]))
n0 = log_n()

f = run()
check("second identical run: no alerts, log unchanged", f["alerts"] == [] and log_n() == n0)

set_cards([("ETH 2D", "2026-11-12")])
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("new forming card -> one 'forming' alert", ev == [("forming", "ETH-2D-2026-11-12")], str(ev))
check("card and alert share the signal_id", f["cards"][0]["signal_id"] == "ETH-2D-2026-11-12")

dups = sum(len(run()["alerts"]) for _ in range(36))
check("36 back-to-back runs on the same state (10 Nov) -> zero duplicates", dups == 0, f"{dups} alerts")

set_cards([]); add_print("ETH 2D", "2026-11-12")
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("card confirms -> 'confirmed', not 'vanished'", ev == [("confirmed", "ETH-2D-2026-11-12")], str(ev))

set_cards([("BTC 1D", "2026-11-13")]); run()
set_cards([])
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("forming card disappears unconfirmed -> 'vanished' once", ev == [("vanished", "BTC-1D-2026-11-13")], str(ev))
check("...and not again next run", run()["alerts"] == [])

set_cards([("ETH 3D", "2026-11-15")]); n1 = log_n()
f = run("refresh=success,grade=success,stack=success,cards=success,regress=failure")
check("regression guard failed -> alerts AND cards withheld, log untouched",
      f["alerts_withheld"] and f["cards_withheld"] and f["alerts"] == [] and f["cards"] == [] and log_n() == n1,
      f"failed_steps={f['checks']['failed_steps']}")
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("next clean run sends the held alert (withheld is not dropped)", ev == [("forming", "ETH-3D-2026-11-15")], str(ev))

set_cards([("ETH 5D", "2026-11-20")])
open(f"{DS}/stack_status.txt", "a").write("2026-11-10 20:14 UTC FAILED card cross-check\n")
f = run()
check("stack status FAILED -> withheld, as before", f["alerts_withheld"] and f["alerts"] == [] and not f["checks"]["passed"])
lines = [l for l in open(f"{DS}/stack_status.txt") if "FAILED" not in l]
open(f"{DS}/stack_status.txt", "w").writelines(lines)
check("hand run with no step outcomes is not withheld", not run(outcomes=None)["alerts_withheld"])

ids = [r["alert_id"] for r in csv.DictReader(open(LOG))]
check("alert log holds no duplicate alert_id", len(ids) == len(set(ids)), f"{len(ids)} rows")

print(f"\n{sum(results)}/{len(results)} passed")
shutil.rmtree(W)
sys.exit(0 if all(results) else 1)
