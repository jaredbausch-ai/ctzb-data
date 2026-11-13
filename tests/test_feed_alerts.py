"""Tests for the alert guard in feed_live.py (item 17d). Runs feed_live.py as the
pipeline does, on a copy of datasets/, across a sequence of simulated runs.

Run: python tests/test_feed_alerts.py   -- exits 1 if any case fails.
"""
import csv, datetime as dt, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from reseal import reseal  # noqa: E402 -- fixtures stand in for the scoring steps, so they re-record the run seal
W = tempfile.mkdtemp()
DS, FEED, LOG = f"{W}/datasets", f"{W}/feed/ctzb_feed.json", f"{W}/feed/alert_log.csv"
shutil.copytree(f"{ROOT}/datasets", DS)
CARD_COLS = open(f"{DS}/cards.csv").readline().strip().split(",")
TODAY = dt.datetime.now(dt.timezone.utc).date()
DAY = lambda k: (TODAY + dt.timedelta(days=k)).isoformat()   # a forming card confirms today or later
D1, D2, D3, D4 = DAY(1), DAY(2), DAY(3), DAY(4)
REAL_CARD = {"chart": "ETH 1D", "asset": "ETH", "tf": "1D", "trough": "2026-11-10", "lowDay": "2026-11-10", "confirms": "2026-11-13", "barsNeeded": "1", "killClose": "2047.2", "priceNow": "2052.66", "entryClose": "", "grade": "C", "lenses": "funding at or above its 90-day median", "basis": "all 17 past ETH 1D signals with exactly the same confirmations", "n": "17", "surv10": "53", "scaled20": "47", "reach20": "29", "reach10": "65", "bestMove": "13.3", "dipBeforeHigh": "-8.2", "maxDip60": "-17.7", "touched30": "29", "bestMoveExact": "13.296089", "dipBeforeHighExact": "-8.223853", "maxDip60Exact": "-17.748592", "nOld": "6", "surv10Old": "67", "nNew": "11", "surv10New": "45", "l0ok": "65", "l0liq": "24", "l5n": "14", "l5ok": "57", "l5liq": "29", "l10n": "8", "l10ok": "25", "l10liq": "50", "l15n": "8", "l15ok": "25", "l15liq": "50", "l20n": "5", "l20ok": "0", "l20liq": "80", "l0okExact": "64.705882", "l5okExact": "57.142857", "l10okExact": "25.0", "l15okExact": "25.0", "l20okExact": "0.0", "daysTo10": "9", "daysTo20": "29", "daysToHigh": "21", "daysToLow": "32", "confluences": "[]"}
results = []


def set_cards(cards):
    with open(f"{DS}/cards.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CARD_COLS); w.writeheader()
        for chart, confirms in cards:
            # a real card's figures (13 Nov 2026: the feed must pass the strict check, so a row of blanks no
            # longer makes a card), re-labelled to the chart and date under test
            r = dict(REAL_CARD)
            r.update(chart=chart, asset=chart.split()[0], tf=chart.split()[1], trough=DAY(-3), lowDay=DAY(-3),
                     confirms=confirms, grade="A", confluences="[]")
            w.writerow({k: r.get(k, "") for k in CARD_COLS})
    reseal(DS)


def add_print(chart, confirms):
    with open(f"{DS}/prints.csv", "a", newline="") as f:
        csv.writer(f).writerow([chart, "confirmed", "2026-11-07", confirms, "2100", "A", "regime on"])
    reseal(DS)


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
check("schema version is 6", f["schema_version"] == 6)
check("every print and open signal carries a signal_id",
      all(x.get("signal_id") for x in f["prints"] + f["open_signals"]))
n0 = log_n()

f = run()
check("second identical run: no alerts, log unchanged", f["alerts"] == [] and log_n() == n0)

set_cards([("ETH 2D", D1)])
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("new forming card -> one 'forming' alert", ev == [("forming", f"ETH-2D-{D1}")], str(ev))
check("card and alert share the signal_id", f["cards"][0]["signal_id"] == f"ETH-2D-{D1}")

dups = sum(len(run()["alerts"]) for _ in range(36))
check("36 back-to-back runs on the same state (10 Nov) -> zero duplicates", dups == 0, f"{dups} alerts")

set_cards([]); add_print("ETH 2D", D1)
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("card confirms -> 'confirmed', not 'vanished'", ev == [("confirmed", f"ETH-2D-{D1}")], str(ev))

set_cards([("BTC 1D", D2)]); run()
set_cards([])
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("forming card disappears unconfirmed -> 'vanished' once", ev == [("vanished", f"BTC-1D-{D2}")], str(ev))
check("...and not again next run", run()["alerts"] == [])

set_cards([("ETH 3D", D3)]); n1 = log_n()
f = run("refresh=success,grade=success,stack=success,cards=success,regress=failure")
check("regression guard failed -> alerts AND cards withheld, log untouched",
      f["alerts_withheld"] and f["cards_withheld"] and f["alerts"] == [] and f["cards"] == [] and log_n() == n1,
      f"failed_steps={f['checks']['failed_steps']}")
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("next clean run sends the held alert (withheld is not dropped)", ev == [("forming", f"ETH-3D-{D3}")], str(ev))

set_cards([("ETH 5D", D4)])
open(f"{DS}/stack_status.txt", "a").write("2026-11-10 20:14 UTC FAILED card cross-check\n"); reseal(DS)
f = run()
check("stack status FAILED -> withheld, as before", f["alerts_withheld"] and f["alerts"] == [] and not f["checks"]["passed"])
lines = [l for l in open(f"{DS}/stack_status.txt") if "FAILED" not in l]
open(f"{DS}/stack_status.txt", "w").writelines(lines); reseal(DS)
check("hand run with no step outcomes is not withheld", not run(outcomes=None)["alerts_withheld"])

# ---- 13 Nov 2026 (audit #21): the feed must pass the strict check, or the withheld feed is published ----
def run_fail(outcomes="refresh=success,grade=success,stack=success,cards=success,regress=success"):
    env = dict(os.environ); env["CTZB_STEP_OUTCOMES"] = outcomes
    p = subprocess.run([sys.executable, "-I", f"{ROOT}/feed_live.py", "--datasets", DS, "--out", FEED,
                        "--alert-log", LOG], env=env, capture_output=True, text=True)
    return p.returncode, json.load(open(FEED)), p.stderr


set_cards([]); run()
rows_ = list(csv.DictReader(open(f"{DS}/cards.csv")))
set_cards([("BTC 2D", D4)])
bad = list(csv.DictReader(open(f"{DS}/cards.csv"))); bad[0]["reach10"] = "140"   # a share above 100%
with open(f"{DS}/cards.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=CARD_COLS); w.writeheader(); w.writerows(bad)
reseal(DS)
n2 = log_n(); rc, f, err = run_fail()
check("a feed that fails the strict check is not published: withheld feed, exit 1, alert log untouched",
      rc == 1 and f["cards_withheld"] and f["cards"] == [] and f["open_signals"] == [] and "strict check" in err and log_n() == n2, err[-160:])
set_cards([("BTC 2D", D4)])
f = run(); ev = [(a["event"], a["signal_id"]) for a in f["alerts"]]
check("...and the alert it was holding goes out on the next clean run", ev == [("forming", f"BTC-2D-{D4}")], str(ev))
set_cards([])
run()
shutil.move(f"{DS}/open.csv", f"{DS}/open.csv.gone"); rc, f, err = run_fail()
check("open.csv missing after a clean run -> withheld feed, not a quiet market", rc == 1 and f["cards_withheld"] and "open.csv" in err, err[-160:])
shutil.move(f"{DS}/open.csv.gone", f"{DS}/open.csv")
f = run("refresh=failure,grade=success,stack=success,cards=success,regress=success")
cp = open(f"{DS}/grades.csv", "rb").read(); open(f"{DS}/grades.csv", "a").write("x\n"); rc, f, err = run_fail()
check("a dataset edited after its step finished (run seal broken) -> withheld feed", rc == 1 and f["cards_withheld"] and "seal" in err, err[-160:])
open(f"{DS}/grades.csv", "wb").write(cp)
rc, f, err = run_fail("refresh=success,grade=success,stack=success,cards=success")
check("a gating step missing from CTZB_STEP_OUTCOMES -> withheld, not published", rc == 0 and f["cards_withheld"] and "regress" in f["checks"]["failed_steps"])
rc, f, err = run_fail("refresh=success,grade=success,stack=skipped,cards=success,regress=success")
check("a gating step reported 'skipped' -> withheld", rc == 0 and f["cards_withheld"] and "stack" in f["checks"]["failed_steps"])
f = run("refresh=failure,grade=success,stack=success,cards=success,regress=success")
check("refresh failed -> the last good run's market filter reading and dates are not repeated",
      f["cards_withheld"] and f["market_regime"] is None and f["scored_as_of"] is None and f["trades_a_year"] is None)
f = run()
check("...and they return on the next clean run", f["market_regime"] in ("Bullish", "Bearish") and f["scored_as_of"])

ids = [r["alert_id"] for r in csv.DictReader(open(LOG))]
check("alert log holds no duplicate alert_id", len(ids) == len(set(ids)), f"{len(ids)} rows")

print(f"\n{sum(results)}/{len(results)} passed")
shutil.rmtree(W)
sys.exit(0 if all(results) else 1)
