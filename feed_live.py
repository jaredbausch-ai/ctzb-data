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
from datetime import datetime, timezone

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
        "confirms_on": r["confirms"],
        "bars_to_confirm": num(r["barsNeeded"]),
        "must_close_above": num(r["killClose"]),
        "price_now": num(r["priceNow"]),
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
        "if_it_falls_first": [
            {"fell_pct": k, "past_trades": num(r[f"l{k}n"]),
             "still_rose10_pct": num(r[f"l{k}ok"]), "went_on_to_fall25_pct": num(r[f"l{k}liq"])}
            for k in (5, 10, 15, 20)
        ],
    }


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
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
        "prints": [
            {"label": LABEL, "signal_id": sid(r["chart"], r["confirms"]), "chart": r["chart"], "state": r["state"],
             "provisional": r["state"] != "confirmed",
             "low_date": r["trough"], "confirms_on": r["confirms"],
             "entry_close": num(r["entry"]), "tags": r["tags"], "note": r["note"]}
            for r in rows(d("prints.csv"))
        ],
        "open_signals": [
            {"label": LABEL, "signal_id": sid(r["chart"], r["entry"]), "chart": r["chart"], "entry_date": r["entry"],
             "entry_close": num(r["entryClose"]), "tags": r["tag"], "grade": r["grade"],
             "confirmations": r["lenses"], "days_elapsed": num(r["elapsed"]),
             "day10_pct": num(r["d10"]), "day30_pct": num(r["d30"]), "day60_pct": num(r["d60"]),
             "best_so_far_pct": num(r["best"]), "worst_so_far_pct": num(r["worst"])}
            for r in rows(d("forward.csv")) if r["status"] == "open"
        ],
        "confluence_windows": [
            {"opened_by": r["openedBy"], "confirmed": r["confirmed"],
             "closes": r["closes"], "applies_to": r["appliesTo"]}
            for r in rows(d("windows.csv"))
        ],
        "grade_odds": [
            {"label": LABEL, "asset": r["asset"], "grade": r["grade"], "past_trades": num(r["n"]),
             "rose10_never_fell25_within60d_pct": num(r["surv10"]),
             "rose20_within60d_pct": num(r["reach20"]),
             "median_deepest_dip_pct": num(r["medDip"]), "sample": r["sample"],
             "note": "Pooled across every chart and mix for this asset. Context only: the card is the number for a live setup."}
            for r in rows(d("grades.csv"))
        ],
    }
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
         "note": "Signals of this grade that did not reach +20% within 60 days. Show the median peak."}
        for r in rows(d("missstats.csv"))] if extras_ok else []
    fade = rows(d("oddsfade.csv")) if extras_ok else []
    feed["odds_fade"] = {
        "label": LABEL,
        "posting_bar_pct": num(fade[0]["posting_bar_pct"]) if fade else None,
        "sample": "Every kept signal, all grades. Below the posting bar the signal's edge is gone.",
        "early_dip": [{"band": r["band"], "past_trades": num(r["n"]), "rose20_within60d_pct": num(r["reached20_pct"]),
                       "edge": r["edge"]} for r in fade if r["kind"] == "early_dip"],
        "day10": [{"check": r["band"], "past_trades": num(r["n"]), "rose20_within60d_pct": num(r["reached20_pct"]),
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

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(feed, f, indent=1)
        f.write("\n")
    print(f"alerts: {len(alerts)} new" + (" (WITHHELD: " + ", ".join(failed_steps or ["stack"]) + " failed)" if not all_ok else "")
          + (" (log SEEDED with what is already live; nothing sent)" if seeded else ""))
    print(f"feed: {len(cards)} cards{' (WITHHELD: checks failed)' if not all_ok else ''}, "
          f"{len(feed['prints'])} prints, {len(feed['open_signals'])} open signals, "
          f"{len(feed['confluence_windows'])} windows -> {a.out}")


if __name__ == "__main__":
    main()
