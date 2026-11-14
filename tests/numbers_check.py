"""Quick numbers check: replays a fixed set of past dates and compares every figure the pipeline and the member
page produce with a stored baseline. Any change stops the line until it is explained and re-approved.

Why (Jared, 13 Nov 2026): the full numbers audit (two hours, an independent agent) had been at or near zero for
many rounds, so it no longer runs every round. Damage fixes still change pipeline code and could move a figure
(round 22: a round-21 check held back a good Sep 2020 feed), so this check runs after every change instead.
The full numbers audit still runs in the two final clean runs.

Compared per date:
  - every file in datasets/ and feed/ (exact text);
  - the numbers a member reads on the page (every price, percentage, count and date token in the Now, Chart,
    Past signals and How to read tabs, in order). Wording changes that move no number pass.

    python3 tests/numbers_check.py              # compare with tests/numbers_baseline/
    python3 tests/numbers_check.py --approve    # write a new baseline (only after checking every change)
    python3 tests/numbers_check.py --dates 2021-06-25,2024-12-31
Exit 0: every figure unchanged. Exit 1: something changed (listed). Needs playwright + chromium.
"""
import concurrent.futures as cf, difflib, glob, gzip, json, os, re, shutil, subprocess, sys, tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = f"{R}/tests/numbers_baseline"
# Fixed set: states every past audit had to reach. Chosen 13 Nov 2026; add, never silently drop.
DATES = [
    "2020-09-05",  # live card with no past signals yet (round 22)
    "2020-09-15",  # early quiet day
    "2021-03-15",  # asset/grade with signals but no miss (round 16)
    "2021-06-25",  # BTC volatility median era (round 26 numbers finding)
    "2022-01-26",  # last day of a market-filter episode
    "2023-12-31",  # year-end: 2D+ bars restart on 1 Jan (round 15)
    "2024-02-29",  # leap day
    "2024-12-31",  # year-end with a forming BTC 5D low (round 15)
    "2025-04-18",  # mid-2025, filter on
    "2026-03-15",  # quiet market, filter off (round 17)
    "2026-06-11",  # filter off with lows forming (round 14)
    "2026-09-07",  # filter on, nothing live or forming: the quiet card (round 15)
    "2026-11-12",  # the audits' REPLAY state: four forming setups, live BTC 2D
]
VIEWS = ("now", "chart", "record", "read")
NUM = re.compile(r"[−\-+]?\$?\d[\d,]*(?:\.\d+)?%?|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b")


def replay(date, root):
    d = f"{root}/{date}"
    p = subprocess.run(["bash", f"{R}/tests/replay_at.sh", date, d], capture_output=True, text=True)
    return date, d, p.returncode, (p.stdout + p.stderr)[-600:]


def files(d):
    out = {}
    for p in sorted(glob.glob(f"{d}/datasets/*") + glob.glob(f"{d}/feed/*")):
        if os.path.isfile(p): out[os.path.relpath(p, d)] = open(p, encoding="utf-8").read()
    return out


def page_text(pw, d):
    page = open(f"{R}/docs/artifacts/member-site/index.html", encoding="utf-8").read()
    doc = "<!doctype html><html><head><meta charset=utf-8></head><body>" + page + "</body></html>"
    feed = open(f"{d}/feed/ctzb_feed.json", encoding="utf-8").read()
    ledger = open(f"{d}/datasets/ledger.csv", encoding="utf-8").read()
    ex = open(f"{R}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json", encoding="utf-8").read()
    def candles(a, tf):
        p = f"{d}/datasets/candles_{a.lower()}_{tf.lower()}.csv"
        if not os.path.exists(p): return None
        import csv
        return json.dumps({"chart": f"{a} {tf}", "bars": [{"t": float(r["time"]), "o": float(r["open"]), "h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"])} for r in csv.DictReader(open(p))]})
    def h(route):
        u = route.request.url
        if u.endswith("/"): return route.fulfill(body=doc, content_type="text/html")
        if u.endswith("ctzb_feed.json"): return route.fulfill(body=feed, content_type="application/json")
        if u.endswith("ledger.csv"): return route.fulfill(body=ledger)
        if "example_" in u: return route.fulfill(body=ex, content_type="application/json")
        if "/candles/" in u:
            a, tf = u.rsplit("/", 1)[1][:-5].split("_"); c = candles(a, tf)
            return route.fulfill(body=c, content_type="application/json") if c else route.fulfill(status=404, body="x")
        return route.abort() if "fonts" in u else route.fulfill(status=404, body="x")
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/*", h); pg.clock.install(time=json.loads(feed)["generated_at"])
    out = {}
    for v in VIEWS:
        pg.goto("http://site.test/#" + v); pg.wait_for_timeout(1500)
        out[v] = pg.inner_text("body")
    b.close()
    if errs: out["page errors"] = "\n".join(errs)
    return out


def snapshot(date, d, pw):
    s = {"files": files(d), "page": page_text(pw, d)}
    s["page_numbers"] = {v: NUM.findall(t) for v, t in s["page"].items()}
    return s


def compare(date, new, old):
    problems = []
    for f in sorted(set(old["files"]) | set(new["files"])):
        a, b = old["files"].get(f), new["files"].get(f)
        if a == b: continue
        if a is None or b is None:
            problems.append(f"{date} {f}: {'new file' if a is None else 'file gone'}"); continue
        diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0))
        changed = sum(1 for l in diff if l[:1] in "+-" and l[:3] not in ("+++", "---"))
        problems.append(f"{date} {f}: {changed} lines changed\n    " + "\n    ".join(diff[2:12]))
    for v in sorted(set(old["page_numbers"]) | set(new["page_numbers"])):
        a, b = old["page_numbers"].get(v), new["page_numbers"].get(v)
        if a == b: continue
        diff = list(difflib.unified_diff(old["page"].get(v, "").splitlines(), new["page"].get(v, "").splitlines(), lineterm="", n=0))
        problems.append(f"{date} page '{v}': numbers changed\n    " + "\n    ".join(diff[2:14]))
    return problems


def main():
    args = sys.argv[1:]
    approve = "--approve" in args
    dates = DATES
    if "--dates" in args: dates = args[args.index("--dates") + 1].split(",")
    root = tempfile.mkdtemp(prefix="numbers_check_")
    try:
        with cf.ThreadPoolExecutor(3) as ex:   # 6 ran the container out of memory beside two audit agents
            runs = list(ex.map(lambda x: replay(x, root), dates))
        failed = [(dt_, log) for dt_, _, rc, log in runs if rc]
        if failed:
            for dt_, log in failed: print(f"REPLAY FAILED {dt_}:\n{log}")
            return 1
        from playwright.sync_api import sync_playwright
        problems = []; os.makedirs(BASE, exist_ok=True)
        with sync_playwright() as pw:
            for date, d, _, _ in runs:
                new = snapshot(date, d, pw)
                p = f"{BASE}/{date}.json.gz"
                if approve:
                    with gzip.open(p, "wt", encoding="utf-8") as fh: json.dump(new, fh, sort_keys=True)
                    print(f"approved {date}: {len(new['files'])} files, {sum(map(len, new['page_numbers'].values()))} page numbers")
                    continue
                if not os.path.exists(p): problems.append(f"{date}: no baseline"); continue
                with gzip.open(p, "rt", encoding="utf-8") as fh: old = json.load(fh)
                problems += compare(date, new, old)
                if "page errors" in new["page"]: problems.append(f"{date}: page errors: {new['page']['page errors'][:300]}")
        if approve: return 0
        if problems:
            print("\n".join(problems)); print(f"\nNUMBERS CHANGED: {len(problems)} item(s) across {len(dates)} dates"); return 1
        print(f"numbers unchanged: {len(dates)} dates, every dataset, feed and page figure identical to the baseline")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
