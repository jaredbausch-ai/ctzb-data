"""Render the member page in states today's data doesn't show, and fail on any raw placeholder
("${", "undefined", "NaN", "null%", "n/a%") in what a member reads (12 Nov 2026 audit #15: the quiet
card printed "${perYear()}"). Needs playwright + chromium. Reads datasets/ and feed/ of this repo
(run the pipeline first so feed/ctzb_feed.json has cards).

    python3 tests/test_page_states.py
"""
import copy, csv, json, os, re, sys
from playwright.sync_api import sync_playwright

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = open(f"{R}/docs/artifacts/member-site/index.html", encoding="utf-8").read()
DOC = "<!doctype html><html><head><meta charset=utf-8></head><body>" + PAGE + "</body></html>"
FEED = json.load(open(f"{R}/feed/ctzb_feed.json"))
LEDGER = open(f"{R}/datasets/ledger.csv").read()
EX = open(f"{R}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json").read()
BAD = re.compile(r"\$\{|undefined|NaN|null%|n/a%|\[object")


def candles(a, tf):
    p = f"{R}/datasets/candles_{a.lower()}_{tf.lower()}.csv"
    if not os.path.exists(p): return None
    return json.dumps({"chart": f"{a} {tf}", "bars": [{"t": float(r["time"]), "o": float(r["open"]), "h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"])} for r in csv.DictReader(open(p))]})


def render(pw, feed, views=("now", "chart", "record", "read"), ledger=LEDGER):
    out = {}
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    def h(route):
        u = route.request.url
        if u.endswith("/"): return route.fulfill(body=DOC, content_type="text/html")
        if u.endswith("ctzb_feed.json"): return route.fulfill(body=json.dumps(feed), content_type="application/json") if feed is not None else route.fulfill(status=503, body="x")
        if u.endswith("ledger.csv"): return route.fulfill(body=ledger) if ledger is not None else route.fulfill(status=503, body="x")
        if "example_" in u: return route.fulfill(body=EX, content_type="application/json")
        if "/candles/" in u:
            a, tf = u.rsplit("/", 1)[1][:-5].split("_"); c = candles(a, tf)
            return route.fulfill(body=c, content_type="application/json") if c else route.fulfill(status=404, body="x")
        if "fonts" in u: return route.abort()
        return route.fulfill(status=404, body="x")
    pg.route("**/*", h)
    if feed is not None: pg.clock.install(time=feed["generated_at"])
    for v in views:
        pg.goto("http://site.test/#" + v); pg.wait_for_timeout(1500)
        out[v] = pg.inner_text("body")
    b.close()
    return out, errs


def main():
    quiet = copy.deepcopy(FEED); quiet["cards"] = []; quiet["open_signals"] = []; quiet["market_regime"] = "Bullish"
    off = copy.deepcopy(quiet); off["market_regime"] = "Bearish"
    noextras = copy.deepcopy(FEED); noextras.update(extras_withheld=True, if_it_misses=[], past_paths=[], example_past_paths=None, example_if_it_misses=None)
    noextras["odds_fade"] = {"label": FEED["label"], "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}
    noexample = copy.deepcopy(quiet); noexample["example_card"] = None
    oneera = copy.deepcopy(FEED)
    for o in oneera["open_signals"]:
        if o.get("card"): o["card"]["before_2022"] = {"past_trades": 0, "past_signals": 0, "rose10_never_fell25_within60d_pct": None}
    states = {"as built": FEED, "quiet, filter on": quiet, "quiet, filter off": off, "extras withheld": noextras,
              "no example card": noexample, "an era with no signals": oneera, "feed down": None}
    ok = n = 0
    with sync_playwright() as pw:
        for name, feed in states.items():
            texts, errs = render(pw, feed)
            if name.startswith("quiet") or name == "no example card":   # the page opens on the example; switch it off too
                pass
            bad = [(v, m.group(0), t[max(0, m.start() - 40):m.end() + 20].replace("\n", " ")) for v, t in texts.items() for m in BAD.finditer(t)]
            for label, cond, detail in [(f"{name}: no raw placeholder in any view", not bad, str(bad[:2])), (f"{name}: no page error", not errs, str(errs[:1]))]:
                n += 1; ok += bool(cond); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f"  -- {detail}" if not cond else ""))
        # the quiet card itself, with the example switched off
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.route("**/*", lambda route: (route.fulfill(body=DOC, content_type="text/html") if route.request.url.endswith("/") else
                                        route.fulfill(body=json.dumps(quiet), content_type="application/json") if route.request.url.endswith("ctzb_feed.json") else
                                        route.fulfill(body=LEDGER) if route.request.url.endswith("ledger.csv") else
                                        route.fulfill(body=EX, content_type="application/json") if "example_" in route.request.url else route.fulfill(status=404, body="x")))
        pg.clock.install(time=quiet["generated_at"]); pg.goto("http://site.test/#now"); pg.wait_for_timeout(1500)
        if pg.is_checked("#previewSwitch"): pg.click("#previewSwitch"); pg.wait_for_timeout(500)
        t = pg.inner_text("#card"); b.close()
        led = [r for r in csv.DictReader(open(f"{R}/datasets/ledger.csv")) if r["grade"] == "A+"]
        y1 = int(quiet["generated_at"][:4]) - 1
        want = round(sum(1 for r in led if 2020 <= int(r["entry"][:4]) <= y1) / (y1 - 2020 + 1) + 1e-9)
        for label, cond, detail in [("quiet card: prints the per-year count from the ledger", f"about {want} times a year (2020 to {y1} average" in t, t[:300].replace("\n", " ")),
                                    ("quiet card: no raw placeholder", not BAD.search(t), t[:200])]:
            n += 1; ok += bool(cond); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f"  -- {detail}" if not cond else ""))
        # unknown must not read as "none" (12 Nov 2026 audit #16)
        held = copy.deepcopy(FEED); held.update(cards_withheld=True, cards=[], open_signals=[])
        t_down, _ = render(pw, None, views=("now",)); t_held, _ = render(pw, held, views=("now",)); t_led, _ = render(pw, FEED, views=("record", "now"), ledger=None)
        nomiss = copy.deepcopy(FEED)
        for r in nomiss["if_it_misses"]: r.update(misses=0, up_first=0, median_peak_pct=None, median_worst_drop_pct=None, median_day60_pct=None)
        t_nm, e_nm = render(pw, nomiss, views=("now",))
        for label, cond, detail in [
            ("feed down: never says there are no live setups", "No live top-grade setups" not in t_down["now"] and "No open top-grade setup" not in t_down["now"] and "Feed unavailable" in t_down["now"], ""),
            ("held back: never says there are no live setups", "No live top-grade setups" not in t_held["now"] and "No open top-grade setup" not in t_held["now"] and "Held back" in t_held["now"], ""),
            ("ledger missing: Past signals says unavailable, not 0 signals", "0 signals" not in t_led["record"] and "Past signals unavailable" in t_led["record"], t_led["record"][:200].replace("\n", " ")),
            ("no misses: the card says so, with no placeholder or error", "none missed" in t_nm["now"] and not BAD.search(t_nm["now"]) and not e_nm, str(e_nm[:1])),
        ]:
            n += 1; ok += bool(cond); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f"  -- {detail}" if detail and not cond else ""))
    print(f"\n{ok}/{n} passed"); sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()
