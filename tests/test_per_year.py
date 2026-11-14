"""The quiet card's "about N times a year (2020 to Y average)" counts only full years whose every signal is in the
ledger (13 Nov 2026 audit #27). The ledger lists a signal once its 60th day has closed, so until about 1 March the
year just ended is incomplete; on 15 Jan 2026 the average must run 2020 to 2024, not 2020 to 2025.

Replays 15 Jan 2026 (tests/replay_at.sh), makes the feed quiet (no forming or live setup; filter on), renders the
page, and checks the years and the count against the replay's own ledger.

    python3 tests/test_per_year.py      # exit 1 on failure
"""
import csv, json, os, re, shutil, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    T = tempfile.mkdtemp(prefix="peryear_")
    try:
        d = f"{T}/r"
        p = subprocess.run(["bash", f"{R}/tests/replay_at.sh", "2026-01-15", d], capture_output=True, text=True)
        if p.returncode:
            print("*** FAIL *** replay did not run", p.stdout[-300:], p.stderr[-300:]); return 1
        feed = json.load(open(f"{d}/feed/ctzb_feed.json"))
        feed.update(cards=[], open_signals=[], market_regime="Bullish")
        ledger = open(f"{d}/datasets/ledger.csv").read()
        top = [r for r in csv.DictReader(open(f"{d}/datasets/ledger.csv")) if r["grade"] == "A+"]
        n = sum(1 for r in top if 2020 <= int(r["entry"][:4]) <= 2024)
        want = f"about {round(n / 5)} times a year (2020 to 2024 average"
        page = open(f"{R}/docs/artifacts/member-site/index.html", encoding="utf-8").read()
        doc = "<!doctype html><html><head><meta charset=utf-8></head><body>" + page + "</body></html>"
        with sync_playwright() as pw:
            b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            def h(route):
                u = route.request.url
                if u.endswith("/"): return route.fulfill(body=doc, content_type="text/html")
                if u.endswith("ctzb_feed.json"): return route.fulfill(body=json.dumps(feed), content_type="application/json")
                if u.endswith("ledger.csv"): return route.fulfill(body=ledger)
                return route.abort() if "fonts" in u else route.fulfill(status=404, body="x")
            pg.route("**/*", h); pg.clock.install(time=feed["generated_at"])
            pg.goto("http://site.test/#now"); pg.wait_for_timeout(1500)
            if pg.is_checked("#previewSwitch"):   # a quiet market switches the worked example on; the quiet card is under it
                pg.click("#previewSwitch"); pg.wait_for_timeout(500)
            txt = pg.inner_text("#card"); b.close()
        got = re.search(r"about \d+ times a year \(\d{4} to \d{4} average", txt)
        ok = got is not None and got.group(0) == want and not errs
        print(("PASS" if ok else "*** FAIL ***"), " quiet card on 15 Jan 2026:", got.group(0) if got else txt[:200], "| expected:", want, errs[:1])
        return 0 if ok else 1
    finally:
        shutil.rmtree(T, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
