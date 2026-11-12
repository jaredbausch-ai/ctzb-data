#!/usr/bin/env python3
"""Fire drills: break the live pipeline on purpose and check that it fails safe.

11 Nov 2026, launch list item 1. Every drill runs the REAL scripts on a throwaway copy
of the repo, with a fault injected. Nothing here touches the real data, the network or
Cloudflare. The question each drill answers: when this goes wrong, does the system stop,
retry and hold back, rather than publish something wrong as if it were fine?

  A  before the commit   stale candles, missing files, corrupt candles, a second
                         exchange disagreeing, Coinbase unreachable. These must fail
                         the run (so it retries) and must not change the committed data.
  B  scoring steps       each step crashing, plus four realistic faults. Cards AND
                         alerts must be withheld (extras: only the member-card figures).
  C  alerts              never sent twice; a held-back alert goes out on the next clean run.
  D  workflow wiring     every scoring step reaches both the gate and the red-run check.
  E  the member site     feed down, checks failed, feed out of date: the page must say
                         so, never read as a quiet market. Run in a real browser.
  F  Cloudflare          mirror down, Coinbase down, GitHub down for the backup: the
                         Worker test suites, which mock those outages.

Run: python tests/fire_drills.py           (about 3 minutes; exit 1 if any drill fails)
     python tests/fire_drills.py --skip-browser
"""
import csv, datetime as dt, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".github", "scripts"))
import check_candles as CC  # noqa: E402

PY = sys.executable
RESULTS = []
TMP = tempfile.mkdtemp(prefix="ctzb-drill-")
STEPS = [("refresh", "refresh.py", ["--data", "data", "--out", "datasets"]),
         ("grade", "grade_live.py", []), ("extras", "extras_live.py", []),
         ("stack", "stack_live.py", []), ("cards", "verify_cards.py", []),
         ("regress", "tests/regression.py", ["--quiet"])]
GATING = ("refresh", "grade", "stack", "cards", "regress")


def record(group, name, ok, detail=""):
    RESULTS.append((group, name, bool(ok), detail))
    print(f"  {'PASS' if ok else '*** FAIL ***'}  {group} {name}" + (f"  -- {detail}" if detail else ""), flush=True)


# Groups B and C replay a pinned past pipeline run (12 Nov 2026): today's code on the data
# committed by the 04:14 UTC run of 12 Nov, which had four forming setups, with the clock set
# to that moment. So the drills always have cards to break, whatever the market is doing.
FIXTURE_COMMIT = "4aa1208"
FIXTURE_NOW = "2026-11-12T04:14:00Z"
FIXDIRS = set()


def fresh_copy(tag, fixture=False):
    d = os.path.join(TMP, tag)
    shutil.copytree(BASE_FIX if fixture else BASE, d)
    if fixture:
        FIXDIRS.add(d)
    return d


def fed_this_run(d):
    """The feed file was rewritten by this drill (a crash used to leave the old one)."""
    return os.path.getmtime(os.path.join(d, "feed", "ctzb_feed.json")) >= START_TS


def run(d, script, args=(), env=None):
    e = dict(os.environ, **(env or {}))
    if any(d == x or d.startswith(x + os.sep) for x in FIXDIRS):
        e["CTZB_NOW"] = FIXTURE_NOW
    p = subprocess.run([PY, script, *args], cwd=d, env=e, capture_output=True, text=True, timeout=900)
    return p.returncode, p.stdout + p.stderr


def digest(d, sub):
    h = hashlib.sha256()
    for root, _, files in sorted(os.walk(os.path.join(d, sub))):
        for f in sorted(files):
            h.update(f.encode()); h.update(open(os.path.join(root, f), "rb").read())
    return h.hexdigest()


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.reader(f))


def write_rows(path, rows):
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)


def make_current(d):
    """Extend the copy's 1D and 4H files with flat bars up to the bar forming now, so the
    freshness check has a clean baseline whatever time the drill runs."""
    now = int(time.time())
    for a in ("ETH", "BTC"):
        for name, step in ((f"{a}_1D.csv", 86400), (f"{a}_4H.csv", 14400)):
            p = os.path.join(d, "data", name)
            rows = read_rows(p)
            last = rows[-1]
            t = int(float(last[0]))
            while t + step <= now:
                t += step
                c = last[4]
                rows.append([str(t), c, c, c, c, last[5] if float(last[5]) > 0 else "1"])
            write_rows(p, rows)


def scoring_chain(d, before=None, extra_env=None):
    """daily.yml from 'Rescore' to 'Write the live feed', with outcomes from real exit codes.
    before(step, d) runs just before each step, to inject a fault."""
    out = {}
    for sid, script, args in STEPS:
        if before:
            before(sid, d)
        rc, log = run(d, script, args)
        out[sid] = "success" if rc == 0 else "failure"
    env = {"CTZB_STEP_OUTCOMES": ",".join(f"{k}={v}" for k, v in out.items())}
    env.update(extra_env or {})
    rc, log = run(d, "feed_live.py", [], env)
    feed = json.load(open(os.path.join(d, "feed", "ctzb_feed.json")))
    return out, rc, feed


def crash(path):
    """Simulate a code bug: the script raises before doing anything."""
    def inject(d):
        p = os.path.join(d, path)
        src = open(p).read()
        open(p, "w").write("raise RuntimeError('fire drill: injected crash')\n" + src)
    return inject


# ---------------------------------------------------------------- A: before the commit
def drills_a():
    g = "A"
    d = fresh_copy("a-control"); make_current(d)
    rc, _ = run(d, ".github/scripts/check_fresh.py", ["data"])
    record(g, "control: current candles pass the freshness check", rc == 0)
    rc = CC.main([os.path.join(d, "data"), "--out", os.path.join(d, "cc.json")], kraken=lambda a: None)
    record(g, "control: real candles pass the structural check", rc == 0)

    for label, fn in [
        ("4H candles one bar behind (exchange stopped updating)", lambda d: write_rows(p4 := os.path.join(d, "data", "ETH_4H.csv"), read_rows(p4)[:-1])),
        ("1D candles a day behind", lambda d: write_rows(p1 := os.path.join(d, "data", "BTC_1D.csv"), read_rows(p1)[:-1])),
        ("BTC_1D.csv missing", lambda d: os.remove(os.path.join(d, "data", "BTC_1D.csv"))),
        ("ETH_4H.csv empty", lambda d: open(os.path.join(d, "data", "ETH_4H.csv"), "w").write("time,open,high,low,close,volume\n")),
    ]:
        x = fresh_copy("a-" + re.sub(r"\W+", "-", label)[:30]); make_current(x); fn(x)
        if label.startswith("1D") and dt.datetime.now(dt.timezone.utc).hour == 0 and dt.datetime.now(dt.timezone.utc).minute < 20:
            record(g, label, True, "skipped: 00:00-00:20 UTC grace window"); continue
        rc, _ = run(x, ".github/scripts/check_fresh.py", ["data"])
        record(g, f"{label}: run fails before the commit", rc != 0, f"exit {rc}")

    def corrupt(fn):
        x = fresh_copy("a-corrupt"); p = os.path.join(x, "data", "ETH_1D.csv")
        with open(p) as fh:
            rows = list(csv.DictReader(fh))
        fn(rows)
        with open(p, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        rc = CC.main([os.path.join(x, "data"), "--out", os.path.join(x, "cc.json")], kraken=lambda a: None)
        shutil.rmtree(x)
        return rc
    record(g, "corrupt candle (low above high): run fails", corrupt(lambda r: r[-5].update(low=str(float(r[-5]["high"]) * 1.02))) == 1)
    record(g, "missing day in the 1D file: run fails", corrupt(lambda r: r.pop(-8)) == 1)
    record(g, "zero close: run fails", corrupt(lambda r: r[-3].update(close="0")) == 1)
    record(g, "zero volume on a closed day: run fails", corrupt(lambda r: r[-4].update(volume="0")) == 1)

    # Kraken cross-check at the live threshold (0.5%, set 11 Nov 2026)
    live = ["--cross", "enforce", "--max-close-gap", "0.5"]
    today = dt.datetime.now(dt.timezone.utc).date()

    def kraken(bad_pct=None, asset="ETH"):
        def k(a):
            cb = {dt.datetime.fromtimestamp(t, dt.timezone.utc).date(): v[3] for t, v in CC.load(os.path.join(d, "data", f"{a}_1D.csv")).items()}
            out = {x: v * 1.0002 for x, v in cb.items() if today - dt.timedelta(days=720) <= x < today}
            if bad_pct and a == asset:
                y = today - dt.timedelta(days=2); out[y] = out[y] * (1 + bad_pct / 100)
            return out
        return k
    o = os.path.join(d, "cc.json")
    record(g, "Kraken agrees (0.02% gap): passes at the live 0.5%", CC.main([os.path.join(d, "data"), "--out", o] + live, kraken=kraken()) == 0)
    record(g, "Coinbase close 0.8% off Kraken two days ago: run fails", CC.main([os.path.join(d, "data"), "--out", o] + live, kraken=kraken(0.8)) == 1)
    record(g, "Kraken unreachable: does NOT block the candles", CC.main([os.path.join(d, "data"), "--out", o] + live, kraken=lambda a: None) == 0)

    # Coinbase unreachable: point the real fetch.py at a closed port
    x = fresh_copy("a-coinbase-down"); before = digest(x, "data")
    dead = {k: "http://127.0.0.1:9" for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")}
    t0 = time.time(); rc, log = run(x, "fetch.py", [], dict(dead, NO_PROXY="", no_proxy=""))
    record(g, "Coinbase unreachable: fetch fails (run retries)", rc != 0, f"exit {rc} after {time.time() - t0:.0f}s")
    record(g, "Coinbase unreachable: candle files untouched", digest(x, "data") == before)
    shutil.rmtree(x)


# ---------------------------------------------------------------- B: scoring steps
def drills_b():
    g = "B"
    d = fresh_copy("b-control", fixture=True)
    log_before = open(os.path.join(d, "feed", "alert_log.csv")).read()
    out, rc, feed = scoring_chain(d)
    record(g, "control: every step passes, cards published", all(v == "success" for v in out.values()) and not feed["cards_withheld"]
           and not feed["extras_withheld"] and rc == 0, str(out))
    global CONTROL
    CONTROL = d

    def expect_withheld(label, out, feed, step, d):
        # the feed itself must be THIS run's (a crash used to leave the previous one published)
        lb = open(os.path.join(d, "feed", "alert_log.csv")).read()
        ok = (fed_this_run(d) and out.get(step) == "failure" and feed["cards_withheld"] and feed["alerts_withheld"]
              and feed["cards"] == [] and feed["alerts"] == [] and lb == log_before)
        record(g, label, ok, f"{step}={out.get(step)} cards_withheld={feed['cards_withheld']} alerts_withheld={feed['alerts_withheld']} log unchanged={lb == log_before}")

    for sid, script, _ in STEPS:
        x = fresh_copy(f"b-crash-{sid}", fixture=True)
        out, rc, feed = scoring_chain(x, before=lambda s, dd, sid=sid, script=script: crash(script)(dd) if s == sid else None)
        if sid == "extras":
            ok = fed_this_run(x) and out["extras"] == "failure" and feed["extras_withheld"] and not feed["cards_withheld"] and not feed["if_it_misses"] and not feed["odds_fade"]["early_dip"] and not feed["past_paths"]
            record(g, "extras step crashes: card figures withheld, cards still published", ok,
                   f"extras_withheld={feed['extras_withheld']} cards_withheld={feed['cards_withheld']}")
        else:
            expect_withheld(f"{sid} step crashes: cards and alerts withheld", out, feed, sid, x)
        shutil.rmtree(x)

    # Realistic faults
    x = fresh_copy("b-missing-chart", fixture=True); os.remove(os.path.join(x, "data", "ETH_3D.csv"))
    out, rc, feed = scoring_chain(x); expect_withheld("ETH_3D.csv missing: rescore fails, all withheld", out, feed, "refresh", x); shutil.rmtree(x)

    def past_grade(s, dd):
        if s != "regress":
            return
        p = os.path.join(dd, "datasets", "ledger.csv"); rows = list(csv.DictReader(open(p)))
        old = [r for r in rows if r["entry"] < "2024-01-01"][0]
        old["grade"] = "C" if old["grade"] != "C" else "A+"
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    x = fresh_copy("b-regress", fixture=True); out, rc, feed = scoring_chain(x, before=past_grade)
    expect_withheld("a 2023 signal's grade silently changes: regression guard trips", out, feed, "regress", x); shutil.rmtree(x)

    def bad_card(s, dd):
        if s != "cards":
            return
        p = os.path.join(dd, "datasets", "cards.csv"); rows = list(csv.DictReader(open(p)))
        rows[0]["surv10"] = str(int(rows[0]["surv10"]) + 7)
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    x = fresh_copy("b-card", fixture=True); out, rc, feed = scoring_chain(x, before=bad_card)
    expect_withheld("a card's odds off by 7 points: card cross-check trips", out, feed, "cards", x); shutil.rmtree(x)

    def unmapped(s, dd):
        if s != "stack":
            return
        p = os.path.join(dd, "docs", "PRETRADE.md"); t = open(p).read()
        t = t.replace("## In-trade reads", "### Fire drill lens, not in the registry\n\nInjected.\n\n## In-trade reads", 1)
        open(p, "w").write(t)
    x = fresh_copy("b-coverage", fixture=True); out, rc, feed = scoring_chain(x, before=unmapped)
    expect_withheld("a documented read missing from the live stack (the 11 Nov incident)", out, feed, "stack", x); shutil.rmtree(x)

    x = fresh_copy("b-hand", fixture=True); out, rc, feed = scoring_chain(x, extra_env={"CTZB_STEP_OUTCOMES": ""})
    open(os.path.join(x, "datasets", "stack_status.txt"), "w").write("")
    rc, _ = run(x, "feed_live.py", [], {"CTZB_STEP_OUTCOMES": ""})
    feed = json.load(open(os.path.join(x, "feed", "ctzb_feed.json")))
    record(g, "stack status file empty (stack never ran): withheld", feed["cards_withheld"] and feed["alerts_withheld"]); shutil.rmtree(x)


# ---------------------------------------------------------------- C: alerts
def drills_c():
    g = "C"
    d = fresh_copy("c-alerts", fixture=True)
    shutil.copytree(os.path.join(CONTROL, "datasets"), os.path.join(d, "datasets"), dirs_exist_ok=True)
    shutil.copy(os.path.join(CONTROL, "feed", "alert_log.csv"), os.path.join(d, "feed", "alert_log.csv"))
    ok_env = {"CTZB_STEP_OUTCOMES": ",".join(f"{k}=success" for k in GATING + ("extras",))}
    bad_env = {"CTZB_STEP_OUTCOMES": ok_env["CTZB_STEP_OUTCOMES"].replace("grade=success", "grade=failure")}
    feed = lambda: json.load(open(os.path.join(d, "feed", "ctzb_feed.json")))
    logn = lambda: len(read_rows(os.path.join(d, "feed", "alert_log.csv")))

    run(d, "feed_live.py", [], ok_env); n0 = logn()
    run(d, "feed_live.py", [], ok_env)
    record(g, "same data twice: second run sends nothing", feed()["alerts"] == [] and logn() == n0)

    p = os.path.join(d, "datasets", "cards.csv"); rows = list(csv.DictReader(open(p)))
    new = dict(rows[0], chart="BTC 5D", asset="BTC", tf="5D", trough="2099-01-01", confirms="2099-01-04")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows + [new])
    run(d, "feed_live.py", [], bad_env)
    record(g, "new setup while a check is failing: no alert, nothing logged", feed()["alerts"] == [] and logn() == n0)
    run(d, "feed_live.py", [], ok_env); a = feed()["alerts"]
    record(g, "next clean run: the held alert goes out once", [x["alert_id"] for x in a] == ["BTC-5D-2099-01-04:forming"], str([x["alert_id"] for x in a]))
    run(d, "feed_live.py", [], ok_env)
    record(g, "and not again on the run after", feed()["alerts"] == [])
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    run(d, "feed_live.py", [], ok_env); a = feed()["alerts"]
    record(g, "setup disappears: one 'vanished' alert", [x["alert_id"] for x in a] == ["BTC-5D-2099-01-04:vanished"], str([x["alert_id"] for x in a]))
    run(d, "feed_live.py", [], ok_env)
    record(g, "and not again", feed()["alerts"] == [])
    log = read_rows(os.path.join(d, "feed", "alert_log.csv"))[1:]
    ids = [r[0] for r in log]
    record(g, "alert log has no duplicate ids", len(ids) == len(set(ids)), f"{len(ids)} ids")


# ---------------------------------------------------------------- D: workflow wiring
def drills_d():
    g = "D"
    y = open(os.path.join(ROOT, ".github", "workflows", "daily.yml")).read()
    gate_env = re.search(r'CTZB_STEP_OUTCOMES: "([^"]+)"', y).group(1)
    fail_if = y.split("Fail the run if any step failed")[1].split("run:")[0]
    for sid, _, _ in STEPS:
        record(g, f"{sid}: outcome passed to the feed gate", f"{sid}=${{{{ steps.{sid}.outcome }}}}" in gate_env)
        record(g, f"{sid}: a failure turns the run red (so it retries)", f"steps.{sid}.outcome == 'failure'" in fail_if)
    record(g, "Kraken cross-check enforced at 0.5%", "--cross enforce --max-close-gap 0.5" in y)
    fl = open(os.path.join(ROOT, "feed_live.py")).read()
    record(g, "feed gate covers every gating step", all(f'"{s}"' in fl.split("GATING_STEPS =")[1].split("\n")[0] for s in GATING))


# ---------------------------------------------------------------- E: the member site
def drills_e():
    g = "E"
    from playwright.sync_api import sync_playwright
    page_src = open(os.path.join(ROOT, "docs", "artifacts", "member-site", "index.html"), encoding="utf-8").read()
    doc = "<!doctype html><html><head><meta charset=utf-8></head><body>" + page_src + "</body></html>"
    good = json.load(open(os.path.join(CONTROL, "feed", "ctzb_feed.json")))
    ledger = open(os.path.join(CONTROL, "datasets", "ledger.csv")).read()
    now = dt.datetime.now(dt.timezone.utc)

    def scenario(feed_status, feed_obj):
        def handler(route):
            u = route.request.url
            if u.endswith("/"):
                return route.fulfill(status=200, body=doc, content_type="text/html")
            if u.endswith("ctzb_feed.json"):
                return route.fulfill(status=feed_status, body=json.dumps(feed_obj) if feed_obj else "Data source unavailable",
                                     content_type="application/json")
            if u.endswith("ledger.csv"):
                return route.fulfill(status=feed_status, body=ledger if feed_status == 200 else "x", content_type="text/csv")
            if "fonts." in u:
                return route.abort()
            return route.fulfill(status=404, body="Not available")
        pg = br.new_page(viewport={"width": 1400, "height": 1000})
        pg.route("**/*", handler)
        pg.goto("http://site.test/"); pg.wait_for_timeout(800)
        card = pg.inner_text("#card"); picker = pg.inner_text("#picker")
        state = pg.eval_on_selector("#card .state", "e => e.dataset.state || ''")
        stale = pg.query_selector("#card .stale-note") is not None
        example = pg.eval_on_selector("#previewSwitch", "e => e.checked")
        pg.close()
        return card, picker, state, stale, example

    fresh_feed = dict(good, generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    with sync_playwright() as p:
        br = p.chromium.launch()
        card, picker, state, stale, ex = scenario(200, fresh_feed)
        record(g, "control: fresh feed, no outage or stale warning", state not in ("down", "held") and not stale)
        card, picker, state, stale, ex = scenario(502, None)
        record(g, "mirror down: page says 'Data unavailable', not a quiet market",
               state == "down" and "Waiting for the next one" not in card and "filter is off" not in card.lower() and not ex, card.split("\n")[1] if "\n" in card else card)
        held = dict(fresh_feed, cards=[], cards_withheld=True, alerts_withheld=True, open_signals=[])
        card, picker, state, stale, ex = scenario(200, held)
        record(g, "checks failed: page says setups are held back", state == "held" and "Held back" in picker and not ex, card.split("\n")[1] if "\n" in card else card)
        old = dict(fresh_feed, generated_at=(now - dt.timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        card, picker, state, stale, ex = scenario(200, old)
        record(g, "feed 11 hours old: page warns the data is out of date", stale and "11 hours old" in card)
        quiet = dict(old, cards=[], open_signals=[])
        card, picker, state, stale, ex = scenario(200, quiet)
        record(g, "old feed and nothing forming: warning still shown", stale)
        br.close()


# ---------------------------------------------------------------- F: Cloudflare
def drills_f():
    g = "F"
    for t, what in [("tests/test_site_worker.mjs", "member site Worker (mirror down, bad paths, gate)"),
                    ("tests/test_trades_relay.mjs", "trades relay (Coinbase down, missing key, recovery)"),
                    ("tests/test_mirror_backup.mjs", "mirror backup (GitHub down, tiny snapshot refused)"),
                    ("tests/test_health_monitor.mjs", "health monitor (every outage messages once, reminds, recovers)"),
                    ("tests/test_dashboard_alerts.mjs", "setup-alert sender (Telegram down, heartbeat)")]:
        p = subprocess.run(["node", t], cwd=ROOT, capture_output=True, text=True, timeout=300)
        m = re.search(r"(\d+)/(\d+) passed", p.stdout)
        record(g, what, p.returncode == 0, m.group(0) if m else p.stdout[-200:])


def main():
    global BASE, BASE_FIX, START_TS
    BASE = os.path.join(TMP, "base")
    shutil.copytree(ROOT, BASE, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
    BASE_FIX = os.path.join(TMP, "base-fixture")
    shutil.copytree(BASE, BASE_FIX)
    for sub in ("data", "datasets", "feed"):
        shutil.rmtree(os.path.join(BASE_FIX, sub))
    arc = subprocess.run(["git", "-C", ROOT, "archive", FIXTURE_COMMIT, "data", "datasets", "feed"], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", BASE_FIX], input=arc, check=True)
    START_TS = time.time() - 1
    t0 = time.time()
    global START
    START = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        print("--- A: before the commit ---"); drills_a()
        print("--- B: scoring steps ---"); drills_b()
        print("--- C: alerts ---"); drills_c()
        print("--- D: workflow wiring ---"); drills_d()
        if "--skip-browser" not in sys.argv:
            print("--- E: member site ---"); drills_e()
        print("--- F: Cloudflare ---"); drills_f()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    n = sum(ok for *_, ok, _ in [(g, nm, ok, dd) for g, nm, ok, dd in RESULTS])
    print(f"\n{n}/{len(RESULTS)} drills passed in {time.time() - t0:.0f}s")
    out = {"run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "passed": n, "total": len(RESULTS),
           "drills": [{"group": g, "drill": nm, "passed": ok, "detail": dd} for g, nm, ok, dd in RESULTS]}
    if "--record" in sys.argv:
        json.dump(out, open(os.path.join(ROOT, "tests", "fire_drills_result.json"), "w"), indent=1)
    sys.exit(0 if n == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
