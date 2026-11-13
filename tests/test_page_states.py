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


def render(pw, feed, views=("now", "chart", "record", "read"), ledger=LEDGER, ex=EX, cut_candles=None, example_on=False, trades=None, pick=None):
    out = {}
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    def h(route):
        u = route.request.url
        if u.endswith("/"): return route.fulfill(body=DOC, content_type="text/html")
        if u.endswith("ctzb_feed.json"): return route.fulfill(body=json.dumps(feed), content_type="application/json") if feed is not None else route.fulfill(status=503, body="x")
        if u.endswith("trades.json") and trades is not None: return route.fulfill(body=json.dumps(trades), content_type="application/json")
        if u.endswith("ledger.csv"): return route.fulfill(body=ledger) if ledger is not None else route.fulfill(status=503, body="x")
        if "example_" in u: return route.fulfill(body=ex, content_type="application/json")
        if "/candles/" in u:
            a, tf = u.rsplit("/", 1)[1][:-5].split("_"); c = candles(a, tf)
            if c and cut_candles is not None:
                j = json.loads(c); j["bars"] = j["bars"][:cut_candles]; c = json.dumps(j)
            return route.fulfill(body=c, content_type="application/json") if c else route.fulfill(status=404, body="x")
        if "fonts" in u: return route.abort()
        return route.fulfill(status=404, body="x")
    pg.route("**/*", h)
    if isinstance(feed, dict) and isinstance(feed.get("generated_at"), str) and feed["generated_at"][:2] == "20": pg.clock.install(time=feed["generated_at"])
    for v in views:
        pg.goto("http://site.test/#" + v); pg.wait_for_timeout(1500)
        if pick and pg.is_visible(f'[data-sel="{pick}"]'):
            pg.click(f'[data-sel="{pick}"]'); pg.wait_for_timeout(600)
        if example_on and not pg.is_checked("#previewSwitch"):
            pg.click("#previewSwitch"); pg.wait_for_timeout(600)
        if example_on and v == "chart" and pg.is_visible("#bHap"):
            pg.click("#bHap"); pg.wait_for_timeout(600)
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
        held = copy.deepcopy(FEED); held.update(cards_withheld=True, cards=[], open_signals=[], example_card=None); held["checks"]["all_passed"] = False   # as feed_live writes it
        t_down, _ = render(pw, None, views=("now",)); t_held, _ = render(pw, held, views=("now",)); t_led, _ = render(pw, FEED, views=("record", "now"), ledger=None)
        fc = copy.deepcopy(held); fc.update(market_regime=None, scored_as_of=None)   # what feed_live writes when it fails closed, or when refresh failed
        t_fc, e_fc = render(pw, fc, views=("now",))
        # a card with no past signals at all (early history only): "n/a", never "n/a%" or "null%"
        empty = copy.deepcopy(FEED)
        for o in empty["open_signals"]:
            if o.get("card"):   # as the pipeline publishes one (1-11 Sep 2020): no past signals, so no figures at all
                c = o["card"]
                c.update(sample="all 0 past signals of the same grade across all ETH charts", past_trades=0, past_signals=0, rose10_within60d_pct=None, rose10_never_fell25_within60d_pct=None, rose20_within60d_pct=None, fell30_within60d_pct=None,
                         typical_biggest_rise_exact_pct=None, typical_dip_before_rise_exact_pct=None, typical_deepest_dip_exact_pct=None,
                         typical_day_of_60d_high=None, typical_day_of_deepest_dip=None)
                c["from_entry"].update(still_rose10_pct=None, still_rose10_exact_pct=None)
                for e in ("before_2022", "since_2022"): c[e].update(past_trades=0, past_signals=0, rose10_never_fell25_within60d_pct=None)
                for r in c["if_it_falls_first"]: r.update(past_trades=0, past_signals=0, still_rose10_pct=None, still_rose10_exact_pct=None, went_on_to_fall25_pct=None)
        t_em, e_em = render(pw, empty, views=("now", "chart"))
        # files cut short in transit (12 Nov 2026 audit #18)
        led_cut = "\n".join(LEDGER.split("\n")[:400]); led_head = LEDGER.split("\n")[0] + "\n"
        t_lc, e_lc = render(pw, FEED, views=("record", "now"), ledger=led_cut); t_lh, e_lh = render(pw, FEED, views=("record",), ledger=led_head)
        t_c0, e_c0 = render(pw, FEED, views=("chart",), cut_candles=0); t_c3, e_c3 = render(pw, FEED, views=("chart",), cut_candles=3)
        exj = json.loads(EX); ex21 = json.dumps(dict(exj, bars=exj["bars"][:21])); ex30 = json.dumps(dict(exj, bars=exj["bars"][:30]))
        t_e21, e_e21 = render(pw, FEED, views=("chart",), ex=ex21, example_on=True); t_e30, e_e30 = render(pw, FEED, views=("chart",), ex=ex30, example_on=True)
        # a live setup whose own card (and status) is missing from the feed: no pooled stand-in (audit #19)
        nocard = copy.deepcopy(FEED)
        for o in nocard["open_signals"]: o["card"] = None; o["edge_level_pct"] = None
        t_nc, e_nc = render(pw, nocard, views=("now", "chart"))
        # hand-broken feeds (13 Nov 2026 audit #20): each must read as unavailable, never as a figure or a blank page
        def mut(fn):
            f = copy.deepcopy(FEED); fn(f); return f
        def first_card(f): return next(o["card"] for o in f["open_signals"] if o.get("card") and o["grade"] == "A+")
        broken = {
            # 13 Nov 2026 (audit #21): a feed that contradicts itself or carries an unknown word is not used at all
            "withheld flag set but cards left in": (mut(lambda f: f.update(cards_withheld=True)), lambda x: "Feed unavailable" in x["now"] and "rose 10% within 60 days" not in x["now"]),
            "no posting bar anywhere and odds_fade empty": (mut(lambda f: (f.pop("posting_bar_pct", None), f.update(odds_fade={}))), lambda x: True),
            "odds_fade missing": (mut(lambda f: (f.pop("posting_bar_pct", None), f.pop("odds_fade", None))), lambda x: True),
            "price_now not a number": (mut(lambda f: first_card(f).update(price_now="abc")), lambda x: "$NaN" not in x["now"] + x["chart"]),
            "typical day of the high missing": (mut(lambda f: first_card(f).update(typical_day_of_60d_high=None)), lambda x: "day null" not in x["chart"] and "Day null" not in x["now"]),
            "unknown edge_status": (mut(lambda f: [o.update(edge_status="weird") for o in f["open_signals"]]), lambda x: "Feed unavailable" in x["now"] and "On track" not in x["now"]),
            "unknown market_regime": (mut(lambda f: f.update(market_regime="Sideways")), lambda x: "Feed unavailable" in x["now"] and "Market filter: o" not in x["now"]),
            "a null entry in cards": (mut(lambda f: f["cards"].append(None)), lambda x: "Feed unavailable" in x["now"]),
            "a null entry in grade_odds": (mut(lambda f: f["grade_odds"].append(None)), lambda x: "Feed unavailable" in x["now"]),
            "a card ladder that is not a list": (mut(lambda f: first_card(f).update(if_it_falls_first="x")), lambda x: "Feed unavailable" in x["now"]),
            "a past_paths entry without days": (mut(lambda f: f["past_paths"][0].pop("days")), lambda x: "Feed unavailable" in x["now"]),
            "a live signal without days_elapsed": (mut(lambda f: f["open_signals"][0].pop("days_elapsed")), lambda x: "Feed unavailable" in x["now"] and "day null" not in x["now"]),
            "withheld but checks say passed": (mut(lambda f: f.update(cards_withheld=True, cards=[], open_signals=[], example_card=None)), lambda x: "Feed unavailable" in x["now"] and "checks passed" not in x["now"]),
            "generated_at missing": (mut(lambda f: f.pop("generated_at")), lambda x: "Feed unavailable" in x["now"]),
            "generated_at not a date": (mut(lambda f: f.update(generated_at="soon")), lambda x: "Feed unavailable" in x["now"]),
            "feed is a list": ([1, 2, 3], lambda x: "Feed unavailable" in x["now"]),
        }
        for name, (feed, cond) in broken.items():
            tx, ex_ = render(pw, feed, views=("now", "chart", "record", "read"))
            good = cond(tx) and not ex_ and not any(BAD.search(v) for v in tx.values())
            n += 1; ok += bool(good)
            print(f"  {'PASS' if good else '*** FAIL ***'}  broken feed, {name}: reads as unavailable, no error, no placeholder" + ("" if good else f"  -- {str(ex_[:1])} {[m.group(0) for v in tx.values() for m in BAD.finditer(v)][:3]}"))
        for label_, tr in (("empty fields", {"trades": [{"asset": "BTC", "direction": None, "action": None, "price": None, "time": None}]}),
                           ("leverage and size not numbers (audit #21)", {"trades": [{"asset": "BTC", "direction": "long", "action": "open", "price": 100000, "time": "2026-11-10T12:00:00Z", "leverage": "x", "size_pct": "y"}]})):
            t_tr, e_tr = render(pw, FEED, views=("now", "chart"), trades=tr)
            good = "in · null" not in t_tr["now"] and "n/ax" not in t_tr["now"] and "n/a% of acct" not in t_tr["now"] and "feed is unavailable" in t_tr["now"] and not e_tr and not BAD.search(t_tr["now"])
            n += 1; ok += bool(good); print(f"  {'PASS' if good else '*** FAIL ***'}  lead-trader file with {label_}: reads unavailable, no placeholder, no error" + ("" if good else f"  -- {e_tr[:1]}"))
        nomiss = copy.deepcopy(FEED)
        for r in nomiss["if_it_misses"]: r.update(misses=0, up_first=0, median_peak_pct=None, median_worst_drop_pct=None, median_day60_pct=None)
        for g in nomiss["grade_odds"]: g.update(rose10_within60d_pct=100)   # no misses means every one rose 10% (the strict check holds them together)
        t_nm, e_nm = render(pw, nomiss, views=("now",))
        # audit #25: a must-close-above price one bar ahead is an estimate and says so; on the open bar it is exact
        fm = copy.deepcopy(FEED); fc_ = copy.deepcopy(FEED["example_card"] or FEED["open_signals"][0]["card"]); fc_.pop("entry_close", None)
        nxt = (__import__('datetime').date.fromisoformat(FEED["scored_as_of"]) + __import__('datetime').timedelta(days=1)).isoformat()
        fc_.update(confirms_on=nxt, signal_id=f"{fc_['asset']}-{fc_['timeframe']}-{nxt}", must_close_above=3000.12, bars_to_confirm=1, price_now=3100.0)
        fm["cards"] = [fc_]; fm0 = copy.deepcopy(fm); fm0["cards"][0]["bars_to_confirm"] = 0
        t_k1, e_k1 = render(pw, fm, views=("now",), pick=fc_["signal_id"]); t_k0, e_k0 = render(pw, fm0, views=("now",), pick=fc_["signal_id"])
        for label, cond, detail in [
            ("feed down: never says there are no live setups", "No live top-grade setups" not in t_down["now"] and "No open top-grade setup" not in t_down["now"] and "Feed unavailable" in t_down["now"], ""),
            ("held back: never says there are no live setups", "No live top-grade setups" not in t_held["now"] and "No open top-grade setup" not in t_held["now"] and "Held back" in t_held["now"], ""),
            ("fail-closed feed: the filter and the scored date read unavailable, not off, and no candle date is claimed", "Market filter: unavailable" in t_fc["now"] and "Market filter: off" not in t_fc["now"] and "closed through" not in t_fc["now"] and not BAD.search(t_fc["now"]) and not e_fc, t_fc["now"][:160].replace("\n", " ")),
            ("ledger missing: Past signals says unavailable, not 0 signals", "0 signals" not in t_led["record"] and "Past signals unavailable" in t_led["record"], t_led["record"][:200].replace("\n", " ")),
            ("a live card with no past signals yet (early history): 'No odds yet', no placeholder, no error", "No odds yet" in t_em["now"] and not BAD.search(t_em["now"]) and not BAD.search(t_em["chart"]) and not e_em, str(e_em[:1]) + str([m.group(0) for m in BAD.finditer(t_em["now"] + t_em["chart"])][:3])),
            ("ledger cut short or header only: Past signals says unavailable, never a partial record", all("Past signals unavailable" in x["record"] for x in (t_lc, t_lh)) and not e_lc and not e_lh, t_lc["record"][:160].replace("\n", " ")),
            ("candle file with 0 or 3 bars: chart says unavailable, no error, no broken geometry", all("candles couldn't be loaded" in x["chart"] and not BAD.search(x["chart"]) for x in (t_c0, t_c3)) and not e_c0 and not e_c3, str((e_c0 + e_c3)[:1])),
            ("example chart file cut short: example chart says unavailable, no error", all("couldn't be loaded" in x["chart"] for x in (t_e21, t_e30)) and not e_e21 and not e_e30, str((e_e21 + e_e30)[:1])),
            ("live setup with no card in the feed: 'Card unavailable', no pooled figures, no error",
             "Card unavailable" in t_nc["now"] and "ETH TIER SIGNALS" not in t_nc["now"].upper()
             and not BAD.search(t_nc["now"]) and not BAD.search(t_nc["chart"]) and not e_nc, str(e_nc[:1])),
            ("must close above, one bar ahead: shown as an estimate", "closes above about $3,000.12 (an estimate until the current bar closes)" in t_k1["now"] and not e_k1, t_k1["now"][:300].replace("\n", " ")),
            ("must close above, on the open bar: shown exact", "closes above $3,000.12" in t_k0["now"] and "about $3,000.12" not in t_k0["now"] and not e_k0, t_k0["now"][:300].replace("\n", " ")),
            ("no misses: the card says so, with no placeholder or error", "none missed" in t_nm["now"] and not BAD.search(t_nm["now"]) and not e_nm, str(e_nm[:1])),
        ]:
            n += 1; ok += bool(cond); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f"  -- {detail}" if detail and not cond else ""))
    print(f"\n{ok}/{n} passed"); sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()
