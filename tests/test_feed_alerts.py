"""Tests for the alert guard in feed_live.py (item 17d). Runs feed_live.py as the
pipeline does, on a copy of datasets/, across a sequence of simulated runs.

Since 14 Nov 2026 (audit #28) an emitted alert stays in `alerts` for its delivery window, so "sent" below is what
a sender that remembers every alert_id it sent (as the dashboard Worker does) would send from each feed.

Run: python tests/test_feed_alerts.py   -- exits 1 if any case fails.
"""
import csv, datetime as dt, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from reseal import reseal  # noqa: E402 -- fixtures stand in for the scoring steps, so they re-record the run seal
import dataclock; dataclock.pin()  # noqa: E402 -- the repo data's own day, not the wall clock
W = tempfile.mkdtemp()
DS, FEED, LOG = f"{W}/datasets", f"{W}/feed/ctzb_feed.json", f"{W}/feed/alert_log.csv"
shutil.copytree(f"{ROOT}/datasets", DS)
CARD_COLS = open(f"{DS}/cards.csv").readline().strip().split(",")
TODAY = dt.datetime.now(dt.timezone.utc).date()
DAY = lambda k: (TODAY + dt.timedelta(days=k)).isoformat()   # a forming card confirms today or later
D1, D2, D3, D4 = DAY(1), DAY(2), DAY(3), DAY(4)
REAL_CARD = {"chart": "ETH 1D", "asset": "ETH", "tf": "1D", "trough": "2026-11-10", "lowDay": "2026-11-10", "confirms": "2026-11-13", "barsNeeded": "1", "killClose": "2047.2", "priceNow": "2052.66", "entryClose": "", "grade": "C", "lenses": "funding at or above its 90-day median", "basis": "all 17 past ETH 1D signals with exactly the same confirmations", "n": "17", "surv10": "53", "scaled20": "47", "reach20": "29", "reach10": "65", "bestMove": "13.3", "dipBeforeHigh": "-8.2", "maxDip60": "-17.7", "touched30": "29", "bestMoveExact": "13.296089", "dipBeforeHighExact": "-8.223853", "maxDip60Exact": "-17.748592", "nOld": "6", "surv10Old": "67", "nNew": "11", "surv10New": "45", "l0ok": "65", "l0liq": "24", "l5n": "14", "l5ok": "57", "l5liq": "29", "l10n": "8", "l10ok": "25", "l10liq": "50", "l15n": "8", "l15ok": "25", "l15liq": "50", "l20n": "5", "l20ok": "0", "l20liq": "80", "l0okExact": "64.705882", "l5okExact": "57.142857", "l10okExact": "25.0", "l15okExact": "25.0", "l20okExact": "0.0", "daysTo10": "9", "daysTo20": "29", "daysToHigh": "21", "daysToLow": "32", "confluences": "[]"}
results = []
SENT = set()   # every alert_id the simulated sender has sent


def deliver(f):
    """What the sender sends from this feed: nothing while alerts are withheld, else each alert_id once ever."""
    if f.get("alerts_withheld"):
        return []
    out = [a for a in f["alerts"] if a["alert_id"] not in SENT]
    SENT.update(a["alert_id"] for a in out)
    return out


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


def run(outcomes="refresh=success,grade=success,stack=success,cards=success,regress=success", seed=False, seen=True):
    env = dict(os.environ)
    env.pop("CTZB_STEP_OUTCOMES", None)
    env.pop("CTZB_SEED_ALERT_LOG", None)
    if seed:
        env["CTZB_SEED_ALERT_LOG"] = "1"   # a new log only on purpose (13 Nov 2026 audit #22)
    if outcomes is not None:
        env["CTZB_STEP_OUTCOMES"] = outcomes
    p = subprocess.run([sys.executable, "-I", f"{ROOT}/feed_live.py", "--datasets", DS, "--out", FEED,
                        "--alert-log", LOG], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    f = json.load(open(FEED)); f["_sent"] = deliver(f) if seen else []   # seen=False: the mirror never pulled it
    return f


def log_n():
    return sum(1 for _ in open(LOG)) - 1 if os.path.exists(LOG) else 0


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else '*** FAIL ***'}  {name}{('  -- ' + detail) if detail else ''}")


set_cards([])
p0 = subprocess.run([sys.executable, "-I", f"{ROOT}/feed_live.py", "--datasets", DS, "--out", FEED, "--alert-log", LOG],
                    env=dict(os.environ, CTZB_STEP_OUTCOMES="refresh=success,grade=success,stack=success,cards=success,regress=success"), capture_output=True, text=True)
check("no log and no published feed: the run fails closed instead of starting a new log", p0.returncode == 1 and "CTZB_SEED_ALERT_LOG" in p0.stderr and not os.path.exists(LOG), p0.stderr[-160:])
f = run(seed=True)
check("first run (seeding on purpose) seeds the log and sends nothing", f["alerts_seeded"] and f["alerts"] == [] and log_n() > 0,
      f"seeded {log_n()} existing signals")
check("schema version is 6", f["schema_version"] == 6)
check("every print and open signal carries a signal_id",
      all(x.get("signal_id") for x in f["prints"] + f["open_signals"]))
n0 = log_n()

f = run()
check("second identical run: nothing sent, log unchanged", f["_sent"] == [] and log_n() == n0)

set_cards([("ETH 2D", D1)])
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["_sent"]]
check("new forming card -> one 'forming' alert", ev == [("forming", f"ETH-2D-{D1}")], str(ev))
check("card and alert share the signal_id", f["cards"][0]["signal_id"] == f"ETH-2D-{D1}")

n_ = log_n(); dups = sum(len(run()["_sent"]) for _ in range(36))
check("36 back-to-back runs on the same state (10 Nov) -> zero duplicates", dups == 0 and log_n() == n_, f"{dups} alerts")

set_cards([]); add_print("ETH 2D", D1)
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["_sent"]]
check("card confirms -> 'confirmed', not 'vanished'", ev == [("confirmed", f"ETH-2D-{D1}")], str(ev))

set_cards([("BTC 1D", D2)]); run()
set_cards([])
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["_sent"]]
check("forming card disappears unconfirmed -> 'vanished' once", ev == [("vanished", f"BTC-1D-{D2}")], str(ev))
check("...and not again next run", run()["_sent"] == [])

set_cards([("ETH 3D", D3)]); n1 = log_n()
f = run("refresh=success,grade=success,stack=success,cards=success,regress=failure")
check("regression guard failed -> alerts AND cards withheld, log untouched",
      f["alerts_withheld"] and f["cards_withheld"] and f["alerts"] == [] and f["cards"] == [] and log_n() == n1,
      f"failed_steps={f['checks']['failed_steps']}")
f = run()
ev = [(a["event"], a["signal_id"]) for a in f["_sent"]]
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
    f = json.load(open(FEED)); f["_sent"] = deliver(f)
    return p.returncode, f, p.stderr


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
f = run(); ev = [(a["event"], a["signal_id"]) for a in f["_sent"]]
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

# ---- 13 Nov 2026 (audit #22): the alert log must be the one the last published feed recorded ----
good_log = open(LOG, "rb").read()
lines_ = good_log.splitlines(keepends=True)
open(LOG, "wb").write(b"".join(lines_[:1] + lines_[2:]))   # its first row (a seeded one, no longer in any feed) cut
rc, f, err = run_fail()
check("alert log with a row cut -> withheld, nothing re-sent", rc == 1 and f["cards_withheld"] and f["_sent"] == [] and "alert log" in err, err[-160:])
open(LOG, "wb").write(good_log); run()
good_log = open(LOG, "rb").read()
open(LOG, "wb").write(good_log[:good_log.rindex(b"\n", 0, len(good_log) - 1) + 1])   # last row cut
rc, f, err = run_fail()
check("alert log with its last row cut while the feed still carries that alert -> restored exactly, nothing re-sent",
      rc == 0 and open(LOG, "rb").read() == good_log and f["_sent"] == [] and not f["cards_withheld"], err[-160:])
open(LOG, "wb").write(good_log.split(b"\n", 1)[0] + b"\n")   # emptied to its header
rc, f, err = run_fail()
check("alert log emptied -> withheld, nothing re-sent", rc == 1 and f["_sent"] == [], err[-160:])
os.remove(LOG); rc, f, err = run_fail()
check("alert log deleted -> withheld, no new log started", rc == 1 and not os.path.exists(LOG), err[-160:])
open(LOG, "wb").write(good_log)
f = run()
check("...the right log back -> runs clean again, nothing re-sent", f["_sent"] == [] and not f["cards_withheld"])
set_cards([("ETH 3D", D4)])
f = run(); sent = [a_["alert_id"] for a_ in f["_sent"]]
open(LOG, "wb").write(good_log)   # the run published its feed, then died before writing the log
f = run(); rows_ = [r["alert_id"] for r in csv.DictReader(open(LOG))]
check("feed published but the log not written: the next run rebuilds the log from the feed, nothing re-sent",
      sent == [f"ETH-3D-{D4}:forming"] and f["_sent"] == [] and sent[0] in rows_, str((sent, f["_sent"])))
# the same, with a crashed run in between (audit #24: the crash used to lock every later run)
set_cards([]); run(); good_log = open(LOG, "rb").read()
set_cards([("BTC 3D", D4)]); f = run(); sent = [a_["alert_id"] for a_ in f["_sent"]]
open(LOG, "wb").write(good_log)   # died before writing the log
shutil.move(f"{DS}/open.csv", f"{DS}/open.csv.gone"); rc, f, err = run_fail(); shutil.move(f"{DS}/open.csv.gone", f"{DS}/open.csv")
f = run(); rows_ = [r["alert_id"] for r in csv.DictReader(open(LOG))]
check("...and with a crashed run in between: the log is still rebuilt, nothing re-sent, no lock-up",
      rc == 1 and sent == [f"BTC-3D-{D4}:forming"] and f["_sent"] == [] and sent[0] in rows_ and not f["cards_withheld"], str((rc, sent, f["_sent"])))
set_cards([]); f = run()
cc = json.load(open(f"{DS}/candle_check.json")); json.dump(dict(cc, structural_ok=False), open(f"{DS}/candle_check.json", "w")); reseal(DS)
rc, f, err = run_fail()
check("candle check says the candles failed -> withheld", rc == 1 and f["cards_withheld"] and "candle_check" in err, err[-160:])
json.dump(cc, open(f"{DS}/candle_check.json", "w")); reseal(DS); run()

# ---- 14 Nov 2026 (audit #28): the delivery window. A red run's retry 1 minute later replaced the feed before the
# mirror (every 15 minutes) pulled it, so its alerts were logged as sent but never delivered ----
B = dt.datetime.fromisoformat(os.environ["CTZB_NOW"].replace("Z", "+00:00"))
def at(minutes):
    os.environ["CTZB_NOW"] = (B + dt.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ"); reseal(DS)
ids_ = lambda f: [a_["alert_id"] for a_ in f["alerts"]]
X, Y = f"BTC-5D-{D4}:forming", f"ETH-1D-{D4}:forming"
at(10); set_cards([("BTC 5D", D4)]); f1 = run(seen=False)
at(11); f2 = run()
check("an alert in a feed the mirror never pulled is still in the 1-minute retry's feed, and is sent from it",
      X in ids_(f1) and [a_["alert_id"] for a_ in f2["_sent"]] == [X] and log_n() == sum(1 for _ in open(LOG)) - 1, str(ids_(f2)))
at(12); f = run(); check("...and not sent twice", f["_sent"] == [] and X in ids_(f))
at(15); set_cards([("BTC 5D", D4), ("ETH 1D", D4)]); f = run(seen=False)
check("a second alert emitted (the mirror misses this feed too)", Y in ids_(f))
at(16); f = run("refresh=success,grade=success,stack=success,cards=success,regress=failure", seen=False)
check("a held run sends nothing and keeps it in alerts_held", f["alerts"] == [] and Y in [a_["alert_id"] for a_ in f["alerts_held"]])
at(17); shutil.move(f"{DS}/open.csv", f"{DS}/open.csv.gone"); reseal(DS); rc, f, err = run_fail(); shutil.move(f"{DS}/open.csv.gone", f"{DS}/open.csv"); reseal(DS)
check("a fail-closed run keeps it in alerts_held too", rc == 1 and f["alerts"] == [] and Y in [a_["alert_id"] for a_ in f["alerts_held"]], err[-120:])
at(18); f = run()
check("the next clean run carries it and it is sent", [a_["alert_id"] for a_ in f["_sent"]] == [Y], str(ids_(f)))
at(20); f = run()
fk = json.load(open(FEED)); n_ = log_n()
fk["alerts"].append(dict(fk["alerts"][0], alert_id="ETH-9D-2030-01-01:forming", signal_id="ETH-9D-2030-01-01"))
json.dump(fk, open(FEED, "w"))
at(21); f = run()
check("an alert the log does not record is never carried or logged", "ETH-9D-2030-01-01:forming" not in ids_(f) and log_n() == n_)
# the window itself, on feed_live.carried_alerts (the scored datasets tie the feed to its day, so hours are not replayed)
sys.path.insert(0, ROOT); import feed_live as FL  # noqa: E402
E = dt.datetime(2026, 11, 14, 4, 14, tzinfo=dt.timezone.utc)
ts = lambda h: (E + dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
LOGR = [{"alert_id": "A:forming", "event": "forming", "signal_id": "A", "chart": "ETH 1D", "emitted_at": ts(0)}]
carry = lambda prev, h, **k: [x["alert_id"] for x in FL.carried_alerts(prev, LOGR, E + dt.timedelta(hours=h), **k)]
clean = lambda g: {"alerts_withheld": False, "generated_at": ts(g), "alerts": [dict(LOGR[0])]}
heldf = {"alerts_withheld": True, "generated_at": ts(0.1), "alerts": [], "alerts_held": [dict(LOGR[0])]}
check("window: kept 23 hours after emission, though the last feed stood 19 hours", carry(clean(4), 23) == ["A:forming"])
check("window: dropped past 24 hours once the last clean feed carrying it stood an hour", carry(clean(23), 25) == [])
check("window: kept past 24 hours while the last feed carrying it has stood under an hour", carry(clean(25), 25.5) == ["A:forming"])
check("window: kept however old while the last feed was held (nothing was being sent)", carry(heldf, 72) == ["A:forming"])
check("window: a held run keeps everything", carry(clean(23), 25, keep_all=True) == ["A:forming"])
check("window: a seeded log row is never carried", FL.carried_alerts(clean(0), [dict(LOGR[0], emitted_at="seeded")], E) == [])

ids = [r["alert_id"] for r in csv.DictReader(open(LOG))]
check("alert log holds no duplicate alert_id", len(ids) == len(set(ids)), f"{len(ids)} rows")

print(f"\n{sum(results)}/{len(results)} passed")
shutil.rmtree(W)
sys.exit(0 if all(results) else 1)
