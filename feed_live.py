"""Write the CTZB live feed: one versioned JSON file per pipeline run.

This is the "one feed" in the live-feed plan sent to Joe (docs/joe/
2026-10-28_live_feed_proposal_SENT.md, settled 31 Oct). Every screen on Joe's
side (admin portal, member site, alerts, his Grok AI) is meant to read this
file instead of emailed copies. The Cloudflare backend that serves views per
audience will read it too, once the ETHKROS Cloudflare account exists.

Rules (docs/FEED_SPEC.md):
  - fields are only ever added, never renamed or removed; schema_version goes
    up by one whenever a field is added
  - every record carries the computed-signal label
  - cards are withheld (empty list, cards_withheld true) whenever the stack
    check or the card cross-check failed, the same gate the dashboard uses
  - it only repackages datasets/*.csv written earlier in the same run; it
    computes nothing of its own
  - (schema 4, 10 Nov 2026, item 17d) every card, print and open signal carries
    a signal_id = chart + confirmation date, which is the same at every stage of
    a signal's life. "alerts" lists the events NEW in this generation --
    forming, confirmed, vanished -- each with a fixed alert_id. feed/alert_log.csv
    is an append-only record of every alert_id ever emitted, committed with the
    feed, so an alert appears in exactly one generation however many runs happen.
    Senders must still never send an alert_id twice: the same generation is read
    many times.
  - (schema 5, 11 Nov 2026, item 18) the member card figures written by
    extras_live.py: if_it_misses, odds_fade, past_paths. Withheld (empty, with
    extras_withheld true) when that step failed this run, so a stale copy from an
    earlier run is never served. They never gate cards or alerts.
  - cards AND alerts are withheld when ANY scoring check in the run failed
    (refresh, grade, stack, cards, regression guard), not only the stack check.
    Withheld alerts are not logged, so they go out on the next clean run.

Usage: python feed_live.py [--datasets datasets] [--out feed/ctzb_feed.json]
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone


def now_utc():
    """Real time, or CTZB_NOW (ISO 8601) when a test replays a past run; same rule as clock.py,
    inlined because the tests run this file from a copy of its own."""
    v = os.environ.get("CTZB_NOW")
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc) if v else datetime.now(timezone.utc)

SCHEMA_VERSION = 5
ALERT_LOG_FIELDS = ["alert_id", "event", "signal_id", "chart", "emitted_at"]
# Steps whose failure withholds cards and alerts. Passed in by daily.yml as
# CTZB_STEP_OUTCOMES="refresh=success,grade=success,...". Absent = run by hand.
GATING_STEPS = ("refresh", "grade", "stack", "cards", "regress")
LABEL = ("Computed signal, not a fill. No trade was taken. Entry quality only: "
         "the data has no exits, so this is not a strategy return or a track record.")


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
        return int(x) if x.is_integer() and "." not in str(v) else x
    except ValueError:
        return v


def sid(chart, date):
    """Stable signal id: chart + confirmation date. 'ETH 1D', '2026-11-12' -> 'ETH-1D-2026-11-12'."""
    return f"{chart.replace(' ', '-')}-{date}" if chart and date else None


def step_outcomes():
    out = {}
    for part in os.environ.get("CTZB_STEP_OUTCOMES", "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def read_log(path):
    return rows(path)


def write_log(path, all_rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALERT_LOG_FIELDS)
        w.writeheader()
        w.writerows(all_rows)


def pending_alerts(forming, confirmed, log_rows):
    """Events not yet in the log. forming/confirmed: {signal_id: chart}."""
    logged = {(r["signal_id"], r["event"]) for r in log_rows}
    out = []
    for s_, ch in sorted(forming.items()):
        if (s_, "forming") not in logged and (s_, "confirmed") not in logged:
            out.append(("forming", s_, ch))
    for s_, ch in sorted(confirmed.items()):
        if (s_, "confirmed") not in logged:
            out.append(("confirmed", s_, ch))
    alerted_forming = {r["signal_id"]: r["chart"] for r in log_rows if r["event"] == "forming"}
    finished = {r["signal_id"] for r in log_rows if r["event"] in ("confirmed", "vanished")}
    for s_, ch in sorted(alerted_forming.items()):
        if s_ in finished or s_ in forming or s_ in confirmed:
            continue
        out.append(("vanished", s_, ch))
    return out


def stack_check(path):
    lines = open(path).read().strip().splitlines() if os.path.exists(path) else []
    failed = [l for l in lines if "FAILED" in l]
    ok = bool(lines) and not failed
    return ok, lines


def card(r):
    return {
        "label": LABEL,
        "signal_id": sid(r["chart"], r["confirms"]),
        "chart": r["chart"],
        "asset": r["asset"],
        "timeframe": r["tf"],
        "low_date": r["trough"],
        "low_day": r.get("lowDay") or r["trough"],  # the day the low printed (12 Nov 2026); low_date is its bar's open date
        "confirms_on": r["confirms"],
        "bars_to_confirm": num(r["barsNeeded"]),
        "must_close_above": num(r["killClose"]),
        "price_now": num(r["priceNow"]),     # forming: today's price (stand-in for the entry); live: today's price; example: none
        "entry_close": num(r.get("entryClose", "")),   # live and example: the actual entry close; forming: not yet known
        "grade": r["grade"],
        "confirmations": r["lenses"],
        "sample": r["basis"],
        "past_trades": num(r["n"]),
        "rose10_never_fell25_within60d_pct": num(r["surv10"]),
        "beat_normal_move_pct": num(r["scaled20"]),
        "rose20_within60d_pct": num(r["reach20"]),
        "rose10_within60d_pct": num(r["reach10"]),
        "typical_biggest_rise_pct": num(r["bestMove"]),
        "typical_dip_before_rise_pct": num(r["dipBeforeHigh"]),
        "typical_deepest_dip_pct": num(r["maxDip60"]),
        # unrounded, for prices built from them (12 Nov 2026 audit); display the rounded ones
        "typical_biggest_rise_exact_pct": num(r.get("bestMoveExact", "")),
        "typical_dip_before_rise_exact_pct": num(r.get("dipBeforeHighExact", "")),
        "typical_deepest_dip_exact_pct": num(r.get("maxDip60Exact", "")),
        "fell30_within60d_pct": num(r["touched30"]),
        "before_2022": {"past_trades": num(r["nOld"]), "rose10_never_fell25_within60d_pct": num(r["surv10Old"])},
        "since_2022": {"past_trades": num(r["nNew"]), "rose10_never_fell25_within60d_pct": num(r["surv10New"])},
        "typical_day_first_rose10": num(r.get("daysTo10", "")),
        "typical_day_first_rose20": num(r.get("daysTo20", "")),
        "typical_day_of_60d_high": num(r.get("daysToHigh", "")),
        "typical_day_of_deepest_dip": num(r.get("daysToLow", "")),
        "active_confluences": [
            {"after": f"{x['after']} {x['afterTag']}", "after_confirmed": x["confirmed"], "window_closes": x["closes"],
             "applies_to": x["tag"], "past_trades": x["n"], "rose20_within60d_pct": num(x["reach20"]),
             "rose10_within60d_pct": num(x["reach10"]), "fell30_within60d_pct": num(x["touched30"]),
             "note": "Its own sample, separate from the card number; rows overlap and are not added."}
            for x in json.loads(r.get("confluences") or "[]")
        ],
        # the ladder's first row (12 Nov 2026 audit #5): from entry, rose 10% before ever falling 25.3%
        "from_entry": {"past_trades": num(r["n"]), "still_rose10_pct": num(r.get("l0ok", "")), "went_on_to_fall25_pct": num(r.get("l0liq", "")),
                       "still_rose10_exact_pct": num(r.get("l0okExact", ""))},
        "if_it_falls_first": [
            {"fell_pct": k, "past_trades": num(r[f"l{k}n"]),
             "still_rose10_pct": num(r[f"l{k}ok"]), "went_on_to_fall25_pct": num(r[f"l{k}liq"]),
             "still_rose10_exact_pct": num(r.get(f"l{k}okExact", ""))}
            for k in (5, 10, 15, 20)
        ],
    }


def signal_aliases(o):
    """Audit #7 (12 Nov 2026): no signal was traded, so every `past_trades` gains a `past_signals` twin and
    `trades_a_year` a `signals_a_year` twin, same values, placed right after. The old names stay (fields are
    never renamed)."""
    if isinstance(o, list):
        return [signal_aliases(x) for x in o]
    if not isinstance(o, dict):
        return o
    out = {}
    for k, v in o.items():
        out[k] = signal_aliases(v)
        if k == "past_trades":
            out["past_signals"] = out[k]
        elif k == "trades_a_year":
            out["signals_a_year"] = out[k]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="datasets")
    ap.add_argument("--out", default="feed/ctzb_feed.json")
    ap.add_argument("--alert-log", default="feed/alert_log.csv")
    a = ap.parse_args()
    d = lambda name: os.path.join(a.datasets, name)

    status = {r["item"]: r["value"] for r in rows(d("status.csv"))}
    ok, check_lines = stack_check(d("stack_status.txt"))
    steps = step_outcomes()
    failed_steps = [k for k in GATING_STEPS if steps.get(k) == "failure"]
    all_ok = ok and not failed_steps
    cards = [card(r) for r in rows(d("cards.csv"))] if all_ok else []
    # the member site's worked example, as a real card from what was known at its alert (12 Nov 2026)
    ex_rows = rows(d("cards_example.csv")) if os.path.exists(d("cards_example.csv")) else []
    example_card = dict(card(ex_rows[0]), example=True) if all_ok and ex_rows else None
    open_cards = {(r["chart"], r["confirms"]): card(r) for r in (rows(d("cards_open.csv")) if os.path.exists(d("cards_open.csv")) else [])} if all_ok else {}
    now = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- alerts: once per event, ever (item 17d) ----
    forming = {sid(r["chart"], r["confirms"]): r["chart"] for r in rows(d("cards.csv")) if r.get("confirms")}
    confirmed = {sid(r["chart"], r["confirms"]): r["chart"] for r in rows(d("prints.csv")) if r["state"] == "confirmed"}
    confirmed.update({sid(r["chart"], r["entry"]): r["chart"] for r in rows(d("forward.csv"))})
    log_rows = read_log(a.alert_log)
    alerts, seeded = [], False
    if not all_ok:
        pass  # withheld: nothing emitted, nothing logged -- the next clean run sends it
    elif not os.path.exists(a.alert_log):
        # First run: record what is already live without alerting on it, or day one
        # would announce every signal currently on the books.
        seeded = True
        log_rows = [{"alert_id": f"{s_}:forming", "event": "forming", "signal_id": s_, "chart": ch, "emitted_at": "seeded"}
                    for s_, ch in sorted(forming.items())] + \
                   [{"alert_id": f"{s_}:confirmed", "event": "confirmed", "signal_id": s_, "chart": ch, "emitted_at": "seeded"}
                    for s_, ch in sorted(confirmed.items())]
        write_log(a.alert_log, log_rows)
    else:
        new_events = pending_alerts(forming, confirmed, log_rows)
        for ev, s_, ch in new_events:
            aid = f"{s_}:{ev}"
            alerts.append({"alert_id": aid, "event": ev, "signal_id": s_, "chart": ch,
                           "emitted_at": now, "label": LABEL})
            log_rows.append({"alert_id": aid, "event": ev, "signal_id": s_, "chart": ch, "emitted_at": now})
        if new_events:
            write_log(a.alert_log, log_rows)

    feed = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now,
        "scored_as_of": status.get("Scored as of"),
        "label": LABEL,
        "checks": {"passed": ok, "lines": check_lines,
                   "all_passed": all_ok, "steps": steps, "failed_steps": failed_steps},
        "cards_withheld": not all_ok,
        "alerts_withheld": not all_ok,
        "alerts_seeded": seeded,
        "alerts": alerts,
        "market_regime": status.get("Market regime"),
        "next_buy_date": status.get("Next buy date"),
        "trades_a_year": status.get("Trades a year"),
        "cards": cards,
        "example_card": example_card,
        "prints": [
            {"label": LABEL, "signal_id": sid(r["chart"], r["confirms"]), "chart": r["chart"], "state": r["state"],
             "provisional": r["state"] != "confirmed",
             "low_date": r["trough"], "confirms_on": r["confirms"],
             "entry_close": num(r["entry"]), "tags": r["tags"], "note": r["note"]}
            for r in rows(d("prints.csv"))
        ],
        # every signal inside its 60 days, ETH and BTC, from stack_live's open.csv (12 Nov 2026 audit);
        # each carries its own card (sample, ladder, edge). Dated by the confirmation close.
        "open_signals": [
            {"label": LABEL, "signal_id": sid(r["chart"], r["entry"]), "chart": r["chart"], "entry_date": r["entry"],
             "entry_close": num(r["entryClose"]), "tags": r["tag"], "grade": r["grade"],
             "confirmations": r["lenses"], "days_elapsed": num(r["elapsed"]),
             "day10_pct": num(r["d10"]), "day30_pct": num(r["d30"]), "day60_pct": num(r["d60"]),
             "best_so_far_pct": num(r["best"]), "worst_so_far_pct": num(r["worst"]),
             "card": open_cards.get((r["chart"], r["entry"]))}
            for r in (rows(d("open.csv")) if os.path.exists(d("open.csv")) else [])
        ] if all_ok else [],
        "confluence_windows": [
            {"opened_by": r["openedBy"], "confirmed": r["confirmed"],
             "closes": r["closes"], "applies_to": r["appliesTo"]}
            for r in rows(d("windows.csv"))
        ],
        "grade_odds": [
            {"label": LABEL, "asset": r["asset"], "grade": r["grade"], "past_trades": num(r["n"]),
             "rose10_within60d_pct": num(r["reach10"]),
             "rose10_never_fell25_within60d_pct": num(r["surv10"]),
             "rose20_within60d_pct": num(r["reach20"]),
             "median_deepest_dip_pct": num(r["medDip"]), "sample": r["sample"],
             "note": "Pooled across every chart and mix for this asset. Context only: the card is the number for a live setup."}
            for r in rows(d("grades.csv"))
        ],
    }
    # ---- the second-exchange check (11 Nov 2026): lets the health monitor see Kraken
    # being skipped run after run, which on its own never fails anything ----
    cc = {}
    try:
        with open(d("candle_check.json")) as f:
            cc = json.load(f)
    except (OSError, ValueError):
        pass
    feed["candle_check"] = {
        "checked_at": cc.get("checked_at"), "cross_mode": cc.get("cross_mode"),
        "structural_ok": cc.get("structural_ok"),
        "kraken": {a: (v or {}).get("status") for a, v in (cc.get("cross") or {}).items()},
    } if cc else None
    # ---- schema 5: member card figures (extras_live.py) ----
    extras_ok = steps.get("extras") != "failure" and all(
        os.path.exists(d(f)) for f in ("missstats.csv", "pastpaths.csv", "oddsfade.csv"))
    feed["extras_withheld"] = not extras_ok
    feed["if_it_misses"] = [
        {"label": LABEL, "asset": r["asset"], "grade": r["grade"], "signals": num(r["aplus_signals"]),
         "misses": num(r["misses"]), "up_first": num(r["up_first"]),
         "median_peak_pct": num(r["median_peak_pct"]), "mean_peak_pct": num(r["mean_peak_pct"]),
         "peaked_5_or_more": num(r["peaked_5_or_more"]), "peaked_10_or_more": num(r["peaked_10_or_more"]),
         "median_worst_drop_pct": num(r["median_worst_drop_pct"]), "median_day60_pct": num(r["median_day60_pct"]),
         "miss_rule": "did not rise 10% within 60 days",
         "note": "Signals of this asset and grade that did not rise 10% within 60 days (the card's headline). Show the median peak."}
        for r in rows(d("missstats.csv"))] if extras_ok else []
    fade = rows(d("oddsfade.csv")) if extras_ok else []
    feed["odds_fade"] = {
        "label": LABEL,
        "posting_bar_pct": num(fade[0]["posting_bar_pct"]) if fade else None,
        "sample": "ETH signals on the chart/tag pairs in the walk-forward tier as fixed on 1 Jan 2026, applied to every signal from 2016 (refresh.py earlydip/holdcheck). In-sample: the tier was chosen on the outcomes of almost all of these signals. Measured on daily candles from the entry close. Each row is grouped by what was known at the day-10 close (the deepest dip in days 1-10, or the day-10 close vs entry) and its +10%/+20% shares count highs AFTER day 10 (days 11 to 60). General explainer only: a card uses its own ladder. Below the posting bar the edge is gone.",
        "edge_measured_on": "rose 10% after day 10 (days 11 to 60)",
        # rose10/20_after_day10_pct name the real window (days 11-60). The *_within60d_pct names are
        # kept, same values, because feed fields are never renamed or removed (FEED_SPEC); don't use them.
        "early_dip": [{"band": r["band"], "past_trades": num(r["n"]),
                       "rose10_after_day10_pct": num(r["reached10_pct"]), "rose20_after_day10_pct": num(r["reached20_pct"]),
                       "rose10_within60d_pct": num(r["reached10_pct"]), "rose20_within60d_pct": num(r["reached20_pct"]),
                       "edge": r["edge"]} for r in fade if r["kind"] == "early_dip"],
        "day10": [{"check": r["band"], "past_trades": num(r["n"]),
                   "rose10_after_day10_pct": num(r["reached10_pct"]), "rose20_after_day10_pct": num(r["reached20_pct"]),
                   "rose10_within60d_pct": num(r["reached10_pct"]), "rose20_within60d_pct": num(r["reached20_pct"]),
                   "edge": r["edge"]} for r in fade if r["kind"] == "day10"],
    }
    paths = rows(d("pastpaths.csv")) if extras_ok else []
    feed["past_paths"] = [
        {"label": LABEL, "asset": asset, "grade": "A+",
         "signals": num(next(r["n"] for r in paths if r["asset"] == asset)),
         "note": "Every past signal of this grade, daily closes, lined up at entry: percent from entry by day.",
         "days": [{"day": num(r["day"]), "q25_pct": num(r["q25_pct"]), "median_pct": num(r["median_pct"]),
                   "q75_pct": num(r["q75_pct"])} for r in paths if r["asset"] == asset]}
        for asset in dict.fromkeys(r["asset"] for r in paths)]

    pe = rows(d("pastpaths_example.csv")) if extras_ok and os.path.exists(d("pastpaths_example.csv")) else []
    feed["example_past_paths"] = {
        "label": LABEL, "asset": "ETH", "grade": "A+", "signals": num(pe[0]["n"]),
        "note": "The worked example's cloud: only ETH top-grade signals whose 60th day had closed by 2024-09-22.",
        "days": [{"day": num(r["day"]), "q25_pct": num(r["q25_pct"]), "median_pct": num(r["median_pct"]),
                  "q75_pct": num(r["q75_pct"])} for r in pe]} if pe else None

    feed = signal_aliases(feed)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(feed, f, indent=1)
        f.write("\n")
    print(f"alerts: {len(alerts)} new" + (" (WITHHELD: " + ", ".join(failed_steps or ["stack"]) + " failed)" if not all_ok else "")
          + (" (log SEEDED with what is already live; nothing sent)" if seeded else ""))
    print(f"feed: {len(cards)} cards{' (WITHHELD: checks failed)' if not all_ok else ''}, "
          f"{len(feed['prints'])} prints, {len(feed['open_signals'])} open signals, "
          f"{len(feed['confluence_windows'])} windows -> {a.out}")


def fail_closed(out_path, err):
    """Fire drills, 11 Nov 2026: when this script itself crashes (a missing column after an
    upstream step failed, say), the PREVIOUS feed used to stay published, cards and all, as
    if the run were clean. Overwrite it with an empty, withheld feed instead, so every reader
    sees that this run's checks failed. Exit 1 still turns the run red and retries it."""
    now = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    feed = {"schema_version": SCHEMA_VERSION, "generated_at": now, "scored_as_of": None, "label": LABEL,
            "checks": {"passed": False, "all_passed": False, "lines": [], "steps": step_outcomes(),
                       "failed_steps": ["feed"]},
            "feed_error": type(err).__name__,
            "cards_withheld": True, "alerts_withheld": True, "extras_withheld": True,
            "alerts": [], "cards": [], "prints": [], "open_signals": [], "confluence_windows": [],
            "grade_odds": [], "if_it_misses": [], "past_paths": [], "candle_check": None, "example_card": None, "example_past_paths": None,
            "odds_fade": {"label": LABEL, "posting_bar_pct": None, "sample": None, "early_dip": [], "day10": []}}
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(feed, f, indent=1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 -- any crash must leave a withheld feed behind
        out = "feed/ctzb_feed.json"
        if "--out" in sys.argv[1:-1]:
            out = sys.argv[sys.argv.index("--out") + 1]
        fail_closed(out, e)
        print(f"FEED BUILD FAILED ({type(e).__name__}: {e}); wrote a withheld feed to {out}", file=sys.stderr)
        sys.exit(1)
