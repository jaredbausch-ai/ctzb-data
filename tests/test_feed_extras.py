"""Tests for the schema 5 member card figures (extras_live.py -> feed_live.py, item 18).
Runs both as the pipeline does, on a copy of datasets/.

Run: python tests/test_feed_extras.py   -- exits 1 if any case fails.
"""
import csv, json, os, shutil, statistics as st, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = tempfile.mkdtemp()
DS, FEED, LOG = f"{W}/datasets", f"{W}/feed/ctzb_feed.json", f"{W}/feed/alert_log.csv"
shutil.copytree(f"{ROOT}/datasets", DS)
# Independent of today's live stack status: these cases test the extras, not the stack check.
open(f"{DS}/stack_status.txt", "w").write("2026-11-11 00:00 UTC OK stack\n")
results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else '*** FAIL ***'}  {name}" + (f"  -- {detail}" if detail else ""))


def run(script, *args, env_extra=None):
    env = dict(os.environ); env.pop("CTZB_STEP_OUTCOMES", None); env.update(env_extra or {})
    return subprocess.run([sys.executable, "-I", f"{ROOT}/{script}", *args], env=env, capture_output=True, text=True, cwd=ROOT)


OK = "refresh=success,grade=success,stack=success,cards=success,regress=success"
p = run("extras_live.py", "--datasets", DS)
check("extras_live runs clean", p.returncode == 0, p.stderr[-300:])

# Independent re-derivation from the ledger, not via carddesign.py
led = [r for r in csv.DictReader(open(f"{DS}/ledger.csv")) if r["grade"] == "A+"]
miss = {r["asset"]: r for r in csv.DictReader(open(f"{DS}/missstats.csv")) if r["grade"] == "A+"}
allmiss = list(csv.DictReader(open(f"{DS}/missstats.csv")))
for grade in ("A", "B", "C"):
    for asset in ("ETH", "BTC"):
        g = [r for r in csv.DictReader(open(f"{DS}/ledger.csv")) if r["grade"] == grade and r["asset"] == asset]
        row = next((r for r in allmiss if r["grade"] == grade and r["asset"] == asset), None)
        m = [float(r["bestMove"]) for r in g if r["reached20"] == "no"]
        if g:
            check(f"{asset} {grade}: miss count and median peak match the ledger",
                  row and int(row["misses"]) == len(m) and (not m or float(row["median_peak_pct"]) == round(st.median(m), 1)))
for asset in ("ETH", "BTC"):
    a = [r for r in led if r["asset"] == asset]
    m = [float(r["bestMove"]) for r in a if r["reached20"] == "no"]
    if not a:
        continue
    row = miss.get(asset)
    check(f"{asset}: signal and miss counts match the ledger", row and int(row["aplus_signals"]) == len(a) and int(row["misses"]) == len(m))
    check(f"{asset}: median peak on misses matches the ledger", row and float(row["median_peak_pct"]) == round(st.median(m), 1),
          f"{row and row['median_peak_pct']} vs {round(st.median(m), 1)}")
    check(f"{asset}: up-first count matches the ledger", row and int(row["up_first"]) == sum(x > 0 for x in m))

paths = list(csv.DictReader(open(f"{DS}/pastpaths.csv")))
for asset in ("ETH", "BTC"):
    days = [r for r in paths if r["asset"] == asset]
    check(f"{asset}: 61 path days, day 0 is entry", len(days) == 61 and float(days[0]["median_pct"]) == 0.0)
    ok_order = all(float(d["q25_pct"]) <= float(d["median_pct"]) <= float(d["q75_pct"]) for d in days)
    check(f"{asset}: quartiles ordered every day", ok_order)
    led60 = [float(r["return60d"]) for r in led if r["asset"] == asset]
    check(f"{asset}: day-60 median agrees with the ledger's 60-day return (within 0.5 pt)",
          abs(float(days[60]["median_pct"]) - st.median(led60)) <= 0.5, f"{days[60]['median_pct']} vs {st.median(led60):.1f}")

fade = list(csv.DictReader(open(f"{DS}/oddsfade.csv")))
check("odds-fade marks each row against 70%",
      fade and all((int(r["reached20_pct"]) >= 70) == (r["edge"] == "intact") and r["posting_bar_pct"] == "70" for r in fade))

p = run("feed_live.py", "--datasets", DS, "--out", FEED, "--alert-log", LOG, env_extra={"CTZB_STEP_OUTCOMES": OK + ",extras=success"})
f = json.load(open(FEED))
check("feed is schema 5", f["schema_version"] == 5)
check("feed carries if_it_misses, odds_fade and past_paths", not f["extras_withheld"] and f["if_it_misses"] and f["odds_fade"]["early_dip"] and f["past_paths"])
eth = next(x for x in f["if_it_misses"] if x["asset"] == "ETH" and x["grade"] == "A+")
check("feed miss figures equal the dataset", eth["median_peak_pct"] == float(miss["ETH"]["median_peak_pct"]) and eth["misses"] == int(miss["ETH"]["misses"]))
check("every new record carries the computed-signal label",
      all("Computed signal" in x["label"] for x in f["if_it_misses"] + f["past_paths"]) and "Computed signal" in f["odds_fade"]["label"])
check("schema 4 fields are all still there", all(k in f for k in ("cards", "alerts", "prints", "open_signals", "grade_odds", "checks")))

p = run("feed_live.py", "--datasets", DS, "--out", FEED, "--alert-log", LOG, env_extra={"CTZB_STEP_OUTCOMES": OK + ",extras=failure"})
f = json.load(open(FEED))
check("extras step failed: the three fields are withheld, not stale",
      f["extras_withheld"] and f["if_it_misses"] == [] and f["past_paths"] == [] and f["odds_fade"]["early_dip"] == [])
check("an extras failure does not withhold cards or alerts", not f["cards_withheld"] and not f["alerts_withheld"])

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
