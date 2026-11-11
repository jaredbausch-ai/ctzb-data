"""Member card figures for the live feed (item 18, schema 5). Runs every pipeline run,
after grade_live.py has written datasets/ledger.csv.

Writes three datasets that feed_live.py repackages, so no number a member sees is typed
by hand (item 17b):

  missstats.csv  Signals that did not reach +20% within 60 days, per asset and grade (all
                 grades since 11 Nov 2026, so a below-bar forming card has them too): how many,
                 how many were above entry first, median / mean peak before failing,
                 median worst drop and day-60 return. Jared 11 Nov 2026: the card shows
                 the MEDIAN peak.
  pastpaths.csv  Every A+ signal's 60-day path on daily closes, lined up at entry: the
                 25th / 50th / 75th percentile for each day, per asset (the chart view's
                 "where the past signals went").
  oddsfade.csv   datasets/earlydip.csv and datasets/holdcheck.csv marked against the
                 70% posting bar (WINMIN in refresh.py). Jared 11 Nov 2026: below 70%
                 the signal's edge is gone. Every kept signal, all grades.

The arithmetic is analysis/carddesign.py's, imported, so the analysis write-up and the
feed can never disagree. Descriptive only: entry quality, no exit in the data, computed
signals and never fills.

Fails (exit 1) rather than write a half result: no A+ signals, an asset with no
usable path, or a non-finite figure.

Usage: python extras_live.py [--datasets datasets]
"""
import argparse
import csv
import importlib.util
import math
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("carddesign", os.path.join(ROOT, "analysis", "carddesign.py"))
cd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cd)

ASSETS = ("ETH", "BTC")
MISS_FIELDS = ["asset", "grade", "aplus_signals", "misses", "up_first", "median_peak_pct", "mean_peak_pct",
               "peaked_5_or_more", "peaked_10_or_more", "median_worst_drop_pct", "median_day60_pct"]
PATH_FIELDS = ["asset", "day", "n", "q25_pct", "median_pct", "q75_pct"]
FADE_FIELDS = ["kind", "band", "n", "reached20_pct", "posting_bar_pct", "edge"]


def write(path, fields, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def finite(*vals):
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default=os.path.join(ROOT, "datasets"))
    a = ap.parse_args()
    full = cd.rows("datasets/ledger.csv")
    led = [r for r in full if r["grade"] == "A+"]
    if not led:
        sys.exit("extras_live: no A+ signals in datasets/ledger.csv; refusing to write")

    miss_rows, path_rows = [], []
    for asset in ASSETS:
        if not any(r["asset"] == asset for r in led):
            continue
        for grade in ("A+", "A", "B", "C"):
            g = [r for r in full if r["grade"] == grade and r["asset"] == asset]
            if not g:
                continue
            m = cd.misses(g, asset)
            if m["misses"] and not finite(m["median_peak_pct"], m["mean_peak_pct"], m["median_worst_drop_pct"], m["median_day60_pct"]):
                sys.exit(f"extras_live: non-finite miss figure for {asset} {grade}")
            miss_rows.append({"grade": grade, **{k: m[k] for k in MISS_FIELDS if k in m}})
        p = cd.paths(led, asset)
        if not p["n"]:
            sys.exit(f"extras_live: no usable 60-day path for {asset}")
        for day in range(61):
            if not finite(p["q25"][day], p["median"][day], p["q75"][day]):
                sys.exit(f"extras_live: non-finite path figure for {asset} day {day}")
            path_rows.append({"asset": asset, "day": day, "n": p["n"],
                              "q25_pct": p["q25"][day], "median_pct": p["median"][day], "q75_pct": p["q75"][day]})
        for s in p["skipped"]:
            print(f"extras_live: {asset} path skipped: {' '.join(s)}")

    f = cd.fade()
    fade_rows = [{"kind": "early_dip", "band": r["band"], "n": r["n"], "reached20_pct": r["reached20_pct"],
                  "posting_bar_pct": f["posting_bar_pct"], "edge": r["edge"]} for r in f["early_dip"]] + \
                [{"kind": "day10", "band": r["check"], "n": r["n"], "reached20_pct": r["reached20_pct"],
                  "posting_bar_pct": f["posting_bar_pct"], "edge": r["edge"]} for r in f["day10"]]
    if not fade_rows:
        sys.exit("extras_live: earlydip.csv / holdcheck.csv empty; refusing to write")

    write(os.path.join(a.datasets, "missstats.csv"), MISS_FIELDS, miss_rows)
    write(os.path.join(a.datasets, "pastpaths.csv"), PATH_FIELDS, path_rows)
    write(os.path.join(a.datasets, "oddsfade.csv"), FADE_FIELDS, fade_rows)
    for m in (x for x in miss_rows if x["grade"] == "A+"):
        print(f"extras_live: {m['asset']} A+ {m['aplus_signals']}, missed +20% {m['misses']}, "
              f"up first {m['up_first']}, median peak {m['median_peak_pct']:+.1f}%")
    print(f"extras_live: paths {', '.join(f'{r} n {n}' for r, n in sorted({(x['asset'], x['n']) for x in path_rows}))}; "
          f"odds-fade rows {len(fade_rows)}")


if __name__ == "__main__":
    main()
