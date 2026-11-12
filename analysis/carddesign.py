"""Figures added to the member card in the 10-11 Nov 2026 redesign (item 18).

Descriptive only. Nothing here is a filter test, nothing selects or grades a
signal, and nothing is tuned: every figure re-reads the pipeline's own
datasets for A+ signals (the only grade members are sent) and reports it.

1. If it misses. A+ signals that did NOT rise 10% within 60 days of entry (+20% until 11 Nov 2026):
   how many were above entry first, and how far (median and mean of the best
   move above entry inside the 60 days). Also their median worst drop and
   median day-60 return. Source: datasets/ledger.csv (bestMove, maxDrawdown,
   return60d). Jared 11 Nov: the card shows the MEDIAN peak.

2. Where the past signals went. Every A+ signal's 60-day path from entry on
   daily closes, lined up at entry: median and quartiles per day, and the
   count clipped by the +100% / -40% chart range. Entry = the ledger's
   entryPrice (the confirmation close, ei = ti + 3). The daily path starts the
   day after the chart's confirmation bar closes. Sources: datasets/ledger.csv,
   data/<ASSET>_<TF>.csv to place the entry bar, data/<ASSET>_1D.csv for the
   path. Signals with fewer than 60 daily closes after entry are skipped and
   counted.

3. Where the odds fade. Re-reads datasets/earlydip.csv (deepest dip in the
   first 10 days -> rose 10%, +20% alongside) and datasets/holdcheck.csv (green / red on
   day 10) and marks each row against the 70% posting bar (WINMIN in
   refresh.py). Jared 11 Nov: below 70% the signal's edge is gone. These two
   datasets pool every kept signal, not A+ only, and are labelled so.

Entry quality only: there is no exit in the data, so none of this is a
strategy return or a track record. Computed signals, never fills.

Usage: python3 -I analysis/carddesign.py [--json analysis/carddesign.json]
"""
import argparse
import csv
import datetime as dt
import json
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POST_BAR = 70  # WINMIN in refresh.py; Jared 11 Nov 2026: below this the edge is gone
CLIP_HI, CLIP_LO = 100.0, -40.0


def rows(path):
    with open(os.path.join(ROOT, path), newline="") as f:
        return list(csv.DictReader(f))


def q(vals, f):
    s = sorted(vals)
    k = (len(s) - 1) * f
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def utc_date(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


MISS_RULE = "did not rise 10% within 60 days"  # Jared 11 Nov 2026: +10% is the headline, so a miss is a +10% miss


def misses(led, asset):
    a = [r for r in led if r["asset"] == asset]
    m = [r for r in a if r["reached10"] == "no"]
    best = [float(r["bestMove"]) for r in m]
    return {
        "asset": asset, "aplus_signals": len(a), "misses": len(m),
        "up_first": sum(b > 0 for b in best),
        "median_peak_pct": round(st.median(best), 1),
        "mean_peak_pct": round(st.mean(best), 1),
        "peaked_5_or_more": sum(b >= 5 for b in best),
        "peaked_10_or_more": sum(b >= 10 for b in best),
        "median_worst_drop_pct": round(st.median(float(r["maxDrawdown"]) for r in m), 1),
        "median_day60_pct": round(st.median(float(r["return60d"]) for r in m), 1),
    }


def paths(led, asset):
    daily = rows(f"data/{asset}_1D.csv")
    at = {int(r["time"]): i for i, r in enumerate(daily)}
    bars, out, skipped = {}, [], []
    for r in led:
        if r["asset"] != asset:
            continue
        tf = r["chart"].split()[1]
        if tf not in bars:
            bars[tf] = rows(f"data/{asset}_{tf}.csv")
        b, ep = bars[tf], float(r["entryPrice"])
        cand = [i for i, x in enumerate(b) if abs(float(x["close"]) - ep) < 0.005]
        if not cand:
            skipped.append((r["chart"], r["entry"], "entry bar not found"))
            continue
        ed = dt.date.fromisoformat(r["entry"])
        i = min(cand, key=lambda c: abs((utc_date(b[c]["time"]) - ed).days))
        nxt = int(b[i + 1]["time"]) if i + 1 < len(b) else None
        if nxt not in at:
            skipped.append((r["chart"], r["entry"], "no daily bar at the chart's next open"))
            continue
        j = at[nxt]
        p = [0.0] + [(float(daily[j + k]["close"]) / ep - 1) * 100 for k in range(60) if j + k < len(daily)]
        if len(p) < 61:
            skipped.append((r["chart"], r["entry"], "fewer than 60 daily closes"))
            continue
        out.append({"chart": r["chart"], "entry": r["entry"], "reached20": r["reached20"], "path": [round(v, 2) for v in p]})
    days = range(61)
    pct = {f: [round(q([x["path"][d] for x in out], f), 1) for d in days] for f in (0.25, 0.5, 0.75)}
    return {
        "asset": asset, "n": len(out), "skipped": skipped,
        "median": pct[0.5], "q25": pct[0.25], "q75": pct[0.75],
        "above_clip": sum(max(x["path"]) > CLIP_HI for x in out),
        "below_clip": sum(min(x["path"]) < CLIP_LO for x in out),
        "signals": out,
    }


def fade():
    # Edge is marked on +10% (Jared 11 Nov 2026: the headline moved to +10%); +20% kept alongside.
    early = [{"band": r["band"], "n": int(r["n"]), "reached10_pct": int(r["reached10"]), "reached20_pct": int(r["reached20"]),
              "edge": "intact" if int(r["reached10"]) >= POST_BAR else "gone"}
             for r in rows("datasets/earlydip.csv")]
    hold = [{"check": r["check"], "n": int(r["n"]), "reached10_pct": int(r["reached10"]), "reached20_pct": int(r["reached20"]),
             "edge": "intact" if int(r["reached10"]) >= POST_BAR else "gone"}
            for r in rows("datasets/holdcheck.csv")]
    return {"posting_bar_pct": POST_BAR, "sample": "every kept signal, all grades", "early_dip": early, "day10": hold}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(ROOT, "analysis", "carddesign.json"))
    a = ap.parse_args()
    led = [r for r in rows("datasets/ledger.csv") if r["grade"] == "A+"]
    res = {"label": "Computed signals, not fills. Entry quality only: no exit in the data.",
           "misses": [misses(led, x) for x in ("ETH", "BTC")],
           "paths": [paths(led, x) for x in ("ETH", "BTC")],
           "fade": fade()}

    print("Card redesign figures (analysis/carddesign.py). Computed signals; entry quality only.\n")
    print("1. If it misses: A+ signals that did not rise 10% within 60 days\n")
    print(f"{'':6}{'A+':>5}{'miss':>6}{'up 1st':>8}{'med peak':>10}{'mean peak':>11}{'>=+5%':>7}{'>=+10%':>8}{'med worst':>11}{'med d60':>9}")
    for m in res["misses"]:
        print(f"{m['asset']:6}{m['aplus_signals']:>5}{m['misses']:>6}{m['up_first']:>8}{m['median_peak_pct']:>+9.1f}%"
              f"{m['mean_peak_pct']:>+10.1f}%{m['peaked_5_or_more']:>7}{m['peaked_10_or_more']:>8}"
              f"{m['median_worst_drop_pct']:>+10.1f}%{m['median_day60_pct']:>+8.1f}%")
    print("\n2. Where the past signals went: 60-day paths on daily closes, lined up at entry\n")
    for p in res["paths"]:
        print(f"{p['asset']}  n {p['n']}  skipped {len(p['skipped'])}  "
              f"day 10 median {p['median'][10]:+.1f}%  day 41 median {p['median'][41]:+.1f}%  "
              f"day 60 median {p['median'][60]:+.1f}%, middle half {p['q25'][60]:+.1f}% to {p['q75'][60]:+.1f}%  "
              f"beyond +{CLIP_HI:.0f}%: {p['above_clip']}  beyond {CLIP_LO:.0f}%: {p['below_clip']}")
        for s in p["skipped"]:
            print("   skipped:", *s)
    f = res["fade"]
    print(f"\n3. Where the odds fade (posting bar {f['posting_bar_pct']}%; {f['sample']})\n")
    for r in f["early_dip"]:
        print(f"   deepest dip in first 10 days {r['band']:<20} n {r['n']:>3}  rose 10% {r['reached10_pct']:>3}%  (+20% {r['reached20_pct']:>3}%)  edge {r['edge']}")
    for r in f["day10"]:
        print(f"   {r['check']:<46} n {r['n']:>3}  rose 10% {r['reached10_pct']:>3}%  (+20% {r['reached20_pct']:>3}%)  edge {r['edge']}")

    with open(a.json, "w") as fh:
        json.dump(res, fh, separators=(",", ":"))
        fh.write("\n")
    print(f"\nwrote {os.path.relpath(a.json, ROOT)}")


if __name__ == "__main__":
    main()
