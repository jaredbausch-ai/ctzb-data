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

Usage: python feed_live.py [--datasets datasets] [--out feed/ctzb_feed.json]
"""
import argparse
import csv
import json
import os
from datetime import datetime, timezone

SCHEMA_VERSION = 1
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


def stack_check(path):
    lines = open(path).read().strip().splitlines() if os.path.exists(path) else []
    failed = [l for l in lines if "FAILED" in l]
    ok = bool(lines) and not failed
    return ok, lines


def card(r):
    return {
        "label": LABEL,
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
    a = ap.parse_args()
    d = lambda name: os.path.join(a.datasets, name)

    status = {r["item"]: r["value"] for r in rows(d("status.csv"))}
    ok, check_lines = stack_check(d("stack_status.txt"))
    cards = [card(r) for r in rows(d("cards.csv"))] if ok else []

    feed = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scored_as_of": status.get("Scored as of"),
        "label": LABEL,
        "checks": {"passed": ok, "lines": check_lines},
        "cards_withheld": not ok,
        "market_regime": status.get("Market regime"),
        "next_buy_date": status.get("Next buy date"),
        "trades_a_year": status.get("Trades a year"),
        "cards": cards,
        "prints": [
            {"label": LABEL, "chart": r["chart"], "state": r["state"],
             "provisional": r["state"] != "confirmed",
             "low_date": r["trough"], "confirms_on": r["confirms"],
             "entry_close": num(r["entry"]), "tags": r["tags"], "note": r["note"]}
            for r in rows(d("prints.csv"))
        ],
        "open_signals": [
            {"label": LABEL, "chart": r["chart"], "entry_date": r["entry"],
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
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(feed, f, indent=1)
        f.write("\n")
    print(f"feed: {len(cards)} cards{' (WITHHELD: checks failed)' if not ok else ''}, "
          f"{len(feed['prints'])} prints, {len(feed['open_signals'])} open signals, "
          f"{len(feed['confluence_windows'])} windows -> {a.out}")


if __name__ == "__main__":
    main()
