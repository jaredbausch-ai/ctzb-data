#!/usr/bin/env python3
"""Rescore every CTZB dashboard dataset from the daily candle repo.

Reads data/ETH_{1,2,3,5,8}D.csv and data/BTC_2D.csv as written by fetch.py,
runs the CTZB engine over each chart, and writes the ten dataset CSVs the
"ETH Setup Odds" dashboard reads.

The 70%+ tier is DERIVED, not stored, so nothing has to be committed back
and nothing drifts. --tier picks how:

  walkforward  (default) the tier as it stood on 1 January of the current
               year, using only data available by then. This is exactly the
               rule the walk-forward test validates, and it rolls over on
               its own every January.
  current      reselected from all data to date. The better estimate of
               today's odds, but it can change mid-year and it is not what
               the walk-forward measured.
  frozen       read keep.json verbatim. For reproducing an earlier run.

  python refresh.py --data data --out datasets
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E          # noqa: E402
import regimes as R         # noqa: E402

CHARTS = [("ETH 1D", "ETH_1D.csv"), ("ETH 2D", "ETH_2D.csv"),
          ("ETH 3D", "ETH_3D.csv"), ("ETH 5D", "ETH_5D.csv"),
          ("ETH 8D", "ETH_8D.csv")]
REGIME_SRC = "BTC_2D.csv"
INVAL_CHARTS = ["ETH 1D", "ETH 2D", "ETH 3D", "ETH 5D"]
CONFLUENCE_CHART = "ETH 2D"

HOR = 60            # forward horizon in days for win / run / dip
NMIN = 8            # minimum past instances for a tag to qualify
WINMIN = 70         # minimum win rate for the tier
AGREE_DAYS = 10     # a chart "agrees" if it printed within this many days
WF_FROM = 2019      # first walk-forward year
# The live forward record starts here: every tier signal from this date on,
# each scored against the tier as it stood in January of its own year, so
# nothing in it was chosen with hindsight. It accumulates, it is rebuilt from
# candles every run, and it needs no alerts.
FORWARD_FROM = dt.date(2026, 1, 1)
MARKS = (10, 30, 60)   # day marks reported for each forward trade

TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow",
        "prime dot", "diamond+dot", "zone-exit B"]

PLAIN = {
    "A": "a deep oversold low",
    "B": "a pullback low",
    "C": "a shallow dip",
    "D": "a high-level dip",
    "zone-exit B": "a pullback that held the midline after a strong run",
    "prime dot": "a low with momentum already winding up",
    "diamond": "a low where price and momentum disagreed",
    "hollow": "a disagreement low above the midline",
    "filled": "a disagreement low below the midline",
    "diamond+dot": "a disagreement low with momentum winding up",
    "any trough": "a confirmed low on this timeframe",
}

BANDS = [(0, -5, "0 to -5%"), (-5, -10, "-5 to -10%"),
         (-10, -15, "-10 to -15%"), (-15, -25, "-15 to -25%"),
         (-25, -100, "worse than -25%")]

EARLY = 10          # days counted as "early" in the first-dip test
EARLY_BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"),
               (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"),
               (-20, -100, "worse than -20%")]


# ---------------------------------------------------------------- helpers

def zser(ct):
    """Running minimum of CT RSI since it was last at or above 60."""
    out, z = [], None
    for v in ct:
        if v is None:
            out.append(None)
            continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        out.append(z)
    return out


def fw(C, Hi, Lo, D, i, days=HOR):
    """(close change, best high, worst low) as % of entry, over `days`.

    None unless the whole horizon has elapsed. A trade opened three weeks
    ago has no 60-day verdict yet, and scoring it on the days available
    would count it as a win or a loss according to whatever the market
    has just done.
    """
    e = C[i]
    end = D[i] + dt.timedelta(days=days)
    if D[-1] < end:
        return None
    j, last, best, mn = i + 1, None, -1e9, 1e9
    while j < len(D) and D[j] <= end:
        best = max(best, Hi[j])
        mn = min(mn, Lo[j])
        last = C[j]
        j += 1
    if last is None:
        return None
    return ((last / e - 1) * 100, (best / e - 1) * 100, (mn / e - 1) * 100)


def tags_of(bucket, dis, strong, prime, ct_at, zmin):
    """Every tag a trough carries. Mirrors the Pine tag builders."""
    t = [bucket, "any trough"]
    if dis:
        t += ["diamond", "filled" if strong else "hollow"]
    if prime:
        t.append("prime dot")
    if dis and prime:
        t.append("diamond+dot")
    if bucket == "B" and ct_at < 60 and zmin is not None and zmin >= 50:
        t.append("zone-exit B")
    return t


def bucket_of(v):
    return "A" if v < 40 else "B" if v < 55 else "C" if v < 65 else "D"


def provisional(ct, kL, zm, D, n):
    """The pivot low still waiting on right-hand bars, if there is one."""
    for back in (1, 2, 3):
        ti = n - 1 - back
        if ti - 3 < 0:
            continue
        v = ct[ti]
        if v is None:
            continue
        if any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)):
            continue
        if any(ct[j] < v for j in range(ti + 1, n)):
            continue
        bk = bucket_of(v)
        tg = [bk, "any trough"]
        if bk == "B" and v < 60 and zm[ti] is not None and zm[ti] >= 50:
            tg.append("zone-exit B")
        if kL[ti] is not None and 20 <= kL[ti] < 50:
            tg.append("prime dot")
        return dict(ti=ti, date=D[ti], ct=round(v, 1),
                    k=None if kL[ti] is None else round(kL[ti], 1),
                    bucket=bk, tags=tg, need=3 - ((n - 1) - ti))
    return None


def wr(rows):
    return sum(1 for r in rows if r["win"]) / len(rows) * 100 if rows else float("nan")


def write_csv(path, header, rows):
    # lineterminator="\n": csv.writer defaults to CRLF, which leaves a stray
    # carriage return on every row's last cell. A strict reader then sees
    # "Bullish\r", and any exact string comparison on a final column fails
    # silently.
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(r)


# ------------------------------------------------------------------- load

def load_charts(data_dir, reg):
    """Run the engine over every chart once. Returns {name: {...}}."""
    out = {}
    for name, fn in CHARTS:
        path = os.path.join(data_dir, fn)
        if not os.path.exists(path):
            raise SystemExit(f"missing {path}")
        sg, b = E.signals(path, regime=reg)
        C, Hi, Lo, D = b["close"], b["high"], b["low"], b["date"]
        n = len(C)
        ct = E.rsi(C, 14)
        zm = zser(ct)
        kL = E.sma(E.stoch_of(ct, 14), 3)
        for s in sg:
            s["tg"] = tags_of(s["bk"], s["dis"], s["strong"], s["prime"],
                              s["ct"], zm[s["ti"]])
        step = int(st.median([(D[i] - D[i - 1]).days
                              for i in range(max(1, n - 20), n)]))
        out[name] = dict(sg=sg, C=C, Hi=Hi, Lo=Lo, D=D, n=n, ct=ct, zm=zm,
                         kL=kL, step=step,
                         prov=provisional(ct, kL, zm, D, n))
    return out


def pool(ch):
    """Every scored trough across every chart, with its agreement count."""
    dates = {nm: [s["edate"] for s in c["sg"]] for nm, c in ch.items()}
    rows = []
    for nm, c in ch.items():
        for s in c["sg"]:
            f = fw(c["C"], c["Hi"], c["Lo"], c["D"], s["ei"])
            if not f:
                continue
            agree = len({o for o in dates if o != nm and
                         any(abs((d - s["edate"]).days) <= AGREE_DAYS
                             for d in dates[o])})
            rows.append(dict(chart=nm, tags=set(s["tg"]), d=s["edate"],
                             win=f[0] > 0, up=f[1], mae=f[2], agree=agree))
    return rows, dates


# --------------------------------------------------------------- datasets

def select_tier(rows, upto=None):
    """Chart-and-tag combinations clearing NMIN instances at WINMIN percent."""
    keep = []
    for name, _ in CHARTS:
        for t in TAGS:
            sub = [r for r in rows if r["chart"] == name and t in r["tags"]
                   and (upto is None or r["d"] < upto)]
            if len(sub) >= NMIN and wr(sub) >= WINMIN:
                keep.append((name, t))
    return keep


def dedupe(rows):
    """One trade per chart per date."""
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x["d"]):
        k = (r["chart"], r["d"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def ds_setups(ch, keep, outdir):
    """setups.csv - every kept setup rescored, plus the stats buy.csv reads."""
    stats = {}
    for name, c in ch.items():
        for cn, t in [k for k in keep if k[0] == name]:
            sub = []
            for s in c["sg"]:
                if t not in s["tg"]:
                    continue
                f = fw(c["C"], c["Hi"], c["Lo"], c["D"], s["ei"])
                if f:
                    sub.append(f)
            if len(sub) < 4:
                continue
            stats[(name, t)] = dict(
                n=len(sub),
                win=round(sum(1 for x in sub if x[0] > 0) / len(sub) * 100),
                p20=round(sum(1 for x in sub if x[1] >= 20) / len(sub) * 100),
                medRun=round(E.med([x[1] for x in sub]), 1),
                medDD=round(E.med([x[2] for x in sub]), 1))
    rows = [[f"{c} — {PLAIN.get(t, t)}", v["n"], v["win"], v["p20"],
             v["medRun"], v["medDD"]]
            for (c, t), v in sorted(stats.items(), key=lambda kv: -kv[1]["win"])]
    write_csv(os.path.join(outdir, "setups.csv"),
              ["setup", "n", "win", "p20", "medRun", "medDD"], rows)
    return stats


def ds_buy(ch, stats, dates, today, outdir):
    """buy.csv - what is forming now, its confirmation date and best odds."""
    rows = []
    for name, c in ch.items():
        p = c["prov"]
        if not p:
            continue
        conf = c["D"][-1] + dt.timedelta(days=c["step"] * p["need"])
        best, bt = None, None
        for t in p["tags"]:
            k = (name, t)
            if k in stats and (best is None or stats[k]["win"] > best["win"]):
                best, bt = stats[k], t
        if not best:
            continue
        # every other chart, scored against the full signal history
        agree = len({o for o in dates if o != name and
                     any(abs((d - conf).days) <= AGREE_DAYS for d in dates[o])})
        rows.append(dict(
            chart=name, buyDate=str(conf),
            status="Needs fresh data" if conf <= today else "Upcoming",
            setup=PLAIN.get(bt, bt), tagName=bt, win=best["win"],
            reach20=best["p20"], n=best["n"], medRun=best["medRun"],
            medDD=best["medDD"], level=round(c["Lo"][p["ti"]], 2), agree=agree))
    rows.sort(key=lambda r: (r["status"] != "Upcoming", r["buyDate"]))
    hdr = ["chart", "buyDate", "status", "setup", "tagName", "win", "reach20",
           "n", "medRun", "medDD", "level", "agree"]
    write_csv(os.path.join(outdir, "buy.csv"), hdr,
              [[r[h] for h in hdr] for r in rows])
    return rows


def ds_live(ch, outdir):
    """live.csv - the state of each chart as of its last bar."""
    rows = []
    for name, c in ch.items():
        last = c["sg"][-1]
        p = c["prov"]
        rows.append([
            name, str(c["D"][-1]), str(last["date"]), str(last["edate"]),
            " + ".join(last["tg"][:1] + [t for t in last["tg"][1:]
                                         if t != "any trough"]),
            (c["D"][-1] - last["edate"]).days, round(c["ct"][-1], 1),
            "yes" if p else "no",
            " + ".join([t for t in p["tags"] if t != "any trough"]) if p else "",
            p["need"] if p else ""])
    write_csv(os.path.join(outdir, "live.csv"),
              ["chart", "dataTo", "lastPrint", "lastEntry", "lastTag",
               "daysSince", "ctNow", "forming", "formingTag", "barsNeeded"],
              rows)


def ds_tier(ch, rows_all, keep, outdir, scoreable_to):
    """tier.csv - the kept tier pooled, then narrowed by agreement."""
    sel = [r for r in rows_all
           if any(r["chart"] == c and t in r["tags"] for c, t in keep)]
    T = dedupe(sel)
    if not T:
        raise SystemExit("tier is empty - no setups qualify")
    # Measure frequency against all the time a trade could have been scored
    # in, not just first trade to last. Ending the span at the last trade
    # would drop a quiet recent stretch out of the denominator and inflate
    # trades per year.
    span = max(0.25, (scoreable_to - min(r["d"] for r in T)).days / 365.25)
    out = []

    def rep(sub, lab):
        if len(sub) < 4:
            return
        out.append([lab, len(sub), round(len(sub) / span, 1), round(wr(sub)),
                    round(E.med([r["up"] for r in sub]), 1),
                    round(E.med([r["mae"] for r in sub]), 1)])

    rep(T, "all 70%+ trades")
    for k in (1, 2, 3, 4):
        rep([r for r in T if r["agree"] >= k], f"with {k}+ other charts agreeing")
    write_csv(os.path.join(outdir, "tier.csv"),
              ["filter", "trades", "perYear", "win", "medRun", "medDD"], out)
    per_year = out[0][2] if out else None
    return T, per_year


def ds_walkforward(ch, rows_all, today, outdir):
    """walkforward.csv and years.csv - tier refit each January, traded blind."""
    base = []
    for nm, c in ch.items():
        for i in range(60, c["n"]):
            if c["in_regime"][i]:
                f = fw(c["C"], c["Hi"], c["Lo"], c["D"], i)
                if f:
                    base.append((c["D"][i], f[0] > 0))
    agg = {0: [], 3: [], 4: []}
    years = []
    for y in range(WF_FROM, today.year):
        keep = select_tier(rows_all, upto=dt.date(y, 1, 1))
        if not keep:
            continue
        yr = dedupe([r for r in rows_all if r["d"].year == y and
                     any(r["chart"] == c and t in r["tags"] for c, t in keep)])
        if not yr:
            continue
        bs = [w for d, w in base if d.year == y]
        bw = round(sum(1 for w in bs if w) / len(bs) * 100) if bs else ""
        a3 = [r for r in yr if r["agree"] >= 3]
        a4 = [r for r in yr if r["agree"] >= 4]
        agg[0] += yr
        agg[3] += a3
        agg[4] += a4
        years.append([y, len(yr), round(wr(yr)), bw])
    write_csv(os.path.join(outdir, "years.csv"),
              ["year", "trades", "win", "baseline"], years)

    pooled = [(d, w) for d, w in base if d.year >= WF_FROM]
    allbase = round(sum(1 for _, w in pooled if w) / len(pooled) * 100)
    span = max(1, today.year - WF_FROM)
    rows = []
    for k, lab in ((0, "All 70%+ setups"), (3, "With 3+ charts agreeing"),
                   (4, "With 4+ charts agreeing")):
        v = agg[k]
        if not v:
            continue
        rows.append([lab, len(v), round(wr(v)), allbase,
                     round(E.med([r["up"] for r in v]), 1),
                     round(E.med([r["mae"] for r in v]), 1),
                     round(len(v) / span, 1)])
    write_csv(os.path.join(outdir, "walkforward.csv"),
              ["rule", "trades", "win", "baseline", "medRun", "medDD",
               "perYear"], rows)
    return allbase


def ds_confluence(ch, dates, outdir):
    """confluence.csv - ETH 2D lows grouped by how many charts agreed."""
    c = ch[CONFLUENCE_CHART]
    buck = {}
    for s in c["sg"]:
        f = fw(c["C"], c["Hi"], c["Lo"], c["D"], s["ei"])
        if not f:
            continue
        others = {o for o in dates if o != CONFLUENCE_CHART and
                  any(abs((d - s["edate"]).days) <= AGREE_DAYS
                      for d in dates[o])}
        buck.setdefault(len(others), []).append(f)
    rows = []
    for k in sorted(buck):
        if k == 0:
            continue
        v = buck[k]
        rows.append([k, f"{k} other chart" + ("s" if k > 1 else ""), len(v),
                     round(sum(1 for x in v if x[0] > 0) / len(v) * 100),
                     round(E.med([x[1] for x in v]), 1),
                     round(E.med([x[2] for x in v]), 1)])
    write_csv(os.path.join(outdir, "confluence.csv"),
              ["agreeing", "label", "n", "win", "medRun", "medDD"], rows)


def ds_invalidation(ch, outdir):
    """invalidation.csv and levels.csv - how depth of dip changes the odds."""
    pooled = []
    for name in INVAL_CHARTS:
        c = ch[name]
        C, H, L, D, n = c["C"], c["Hi"], c["Lo"], c["D"], c["n"]
        for s in c["sg"]:
            ei = s["ei"]
            # a trade still in flight has no final peak or dip to bin
            if D[-1] < D[ei] + dt.timedelta(days=HOR):
                continue
            e = C[ei]
            pk, pkj, j = e, ei, ei + 1
            while j < n:
                if H[j] > pk:
                    pk, pkj = H[j], j
                if C[j] < pk * 0.85:
                    break
                j += 1
            mfe = (pk / e - 1) * 100
            mn = min(L[k] for k in range(ei + 1, pkj + 1)) if pkj > ei else L[ei]
            pooled.append(dict(mfe=mfe, dd=(mn / e - 1) * 100,
                               r10=mfe >= 10, r20=mfe >= 20))
    rows = []
    for hi, lo, lab in BANDS:
        sub = [p for p in pooled if lo < p["dd"] <= hi]
        if len(sub) < 5:
            continue
        rows.append([lab, len(sub),
                     round(sum(1 for p in sub if p["r10"]) / len(sub) * 100),
                     round(sum(1 for p in sub if p["r20"]) / len(sub) * 100),
                     round(E.med([p["mfe"] for p in sub]), 1)])
    write_csv(os.path.join(outdir, "invalidation.csv"),
              ["band", "n", "reached10", "reached20", "medRun"], rows)

    lv = []
    for name in INVAL_CHARTS:
        c = ch[name]
        p = c["prov"]
        if not p:
            continue
        lv.append([name, round(c["Lo"][p["ti"]], 2), str(p["date"]),
                   round((c["Lo"][p["ti"]] / c["C"][-1] - 1) * 100, 1)])
    write_csv(os.path.join(outdir, "levels.csv"),
              ["chart", "level", "troughDate", "pctFromLast"], lv)
    return len(pooled)


def ds_earlydip(ch, keep, outdir):
    """earlydip.csv - does an early fall predict failure?

    Grouped by the worst dip in the first EARLY days only, then scored on
    what happened from day EARLY to the horizon. Splitting the window this
    way is what keeps it honest: grouping a trade by its eventual worst dip
    and then reporting its eventual outcome is partly circular, because a
    deep dip and a bad result are the same fact measured twice.
    """
    pool = []
    for nm, c in ch.items():
        C, Hi, Lo, D, n = c["C"], c["Hi"], c["Lo"], c["D"], c["n"]
        for s in c["sg"]:
            if not any(nm == k[0] and k[1] in s["tg"] for k in keep):
                continue
            ei = s["ei"]
            if D[-1] < D[ei] + dt.timedelta(days=HOR):
                continue
            e = C[ei]
            lo, hi_after = None, None
            for j in range(ei + 1, n):
                d = (D[j] - D[ei]).days
                if d > HOR:
                    break
                if d <= EARLY:
                    lo = Lo[j] if lo is None else min(lo, Lo[j])
                if d >= EARLY:
                    hi_after = Hi[j] if hi_after is None else max(hi_after, Hi[j])
            if lo is None or hi_after is None:
                continue
            pool.append(dict(dip=(lo / e - 1) * 100,
                             mfe=(hi_after / e - 1) * 100))
    rows = []
    for hi, lo, lab in EARLY_BANDS:
        g = [p for p in pool if lo < p["dip"] <= hi]
        if len(g) < 5:
            continue
        rows.append([lab, len(g),
                     round(sum(1 for p in g if p["mfe"] >= 10) / len(g) * 100),
                     round(sum(1 for p in g if p["mfe"] >= 20) / len(g) * 100),
                     round(E.med([p["mfe"] for p in g]), 1)])
    write_csv(os.path.join(outdir, "earlydip.csv"),
              ["band", "n", "reached10", "reached20", "medRun"], rows)
    return rows


def ds_holdcheck(ch, keep, outdir):
    """holdcheck.csv - is the position green at the day-10 check?

    The cheapest question with the most in it. Trades that are green on
    day 10 and trades that are not behave like two different populations:
    a good trade dips early and peaks around day 40, a bad one peaks in
    the first week and bleeds for two months. The liquidation-grade
    drawdowns live almost entirely in the red group, and their low does
    not arrive until about day 50, so the check leaves well before the
    damage.
    """
    rows = []
    groups = {"green on day 10": [], "red on day 10": []}
    for nm, c in ch.items():
        C, Hi, Lo, D, n = c["C"], c["Hi"], c["Lo"], c["D"], c["n"]
        for s in c["sg"]:
            if not any(nm == k[0] and k[1] in s["tg"] for k in keep):
                continue
            ei = s["ei"]
            if D[-1] < D[ei] + dt.timedelta(days=HOR):
                continue
            e = C[ei]
            cl10 = None
            hi = lo = None
            for j in range(ei + 1, n):
                age = (D[j] - D[ei]).days
                if age > HOR:
                    break
                hi = Hi[j] if hi is None else max(hi, Hi[j])
                lo = Lo[j] if lo is None else min(lo, Lo[j])
                if age <= 10:
                    cl10 = (C[j] / e - 1) * 100
            if cl10 is None or hi is None:
                continue
            g = "green on day 10" if cl10 >= 0 else "red on day 10"
            groups[g].append(dict(run=(hi / e - 1) * 100, dip=(lo / e - 1) * 100))
    for lab in ("green on day 10", "red on day 10"):
        g = groups[lab]
        if len(g) < 5:
            continue
        rows.append([lab, len(g),
                     round(sum(1 for x in g if x["run"] >= 20) / len(g) * 100),
                     round(E.med([x["run"] for x in g]), 1),
                     round(E.med([x["dip"] for x in g]), 1),
                     sum(1 for x in g if x["dip"] <= -33.3)])
    write_csv(os.path.join(outdir, "holdcheck.csv"),
              ["check", "n", "reached20", "medRun", "medDip", "deepDips"], rows)
    return rows


def ds_forward(ch, rows_all, outdir):
    """forward.csv - the live out-of-sample record, rebuilt from candles.

    Every tier signal entered on or after FORWARD_FROM, scored against the
    tier as it stood in January of that signal's own year. A trade stays
    "open" until its horizon elapses; no alert, no email, no manual entry,
    and a missing row cannot be mistaken for a quiet market because the
    whole file is derived each run.
    """
    tiers = {}   # year -> the tier fixed at that year's January

    def tier_for(year):
        if year not in tiers:
            tiers[year] = set(select_tier(rows_all, upto=dt.date(year, 1, 1)))
        return tiers[year]

    out = []
    for nm, c in ch.items():
        C, Hi, Lo, D, n = c["C"], c["Hi"], c["Lo"], c["D"], c["n"]
        last = D[-1]
        for s in c["sg"]:
            if s["edate"] < FORWARD_FROM:
                continue
            if not any(nm == k[0] and k[1] in s["tg"] for k in tier_for(s["edate"].year)):
                continue
            ei = s["ei"]
            e = C[ei]
            elapsed = (last - D[ei]).days
            best, worst = None, None
            for j in range(ei + 1, n):
                if (D[j] - D[ei]).days > HOR:
                    break
                best = Hi[j] if best is None else max(best, Hi[j])
                worst = Lo[j] if worst is None else min(worst, Lo[j])
            marks = {}
            for m in MARKS:
                marks[m] = ""
                if elapsed < m:
                    continue
                # the last close at or before the mark
                v = None
                for j in range(ei + 1, n):
                    if (D[j] - D[ei]).days <= m:
                        v = C[j]
                    else:
                        break
                if v is not None:
                    marks[m] = round((v / e - 1) * 100, 1)
            out.append([
                nm, str(s["edate"]),
                " + ".join(t for t in s["tg"] if t != "any trough"),
                round(e, 2), elapsed,
                "closed" if elapsed >= HOR else "open",
                marks[10], marks[30], marks[60],
                "" if best is None else round((best / e - 1) * 100, 1),
                "" if worst is None else round((worst / e - 1) * 100, 1)])
    out.sort(key=lambda r: (r[1], r[0]))
    write_csv(os.path.join(outdir, "forward.csv"),
              ["chart", "entry", "tag", "entryClose", "elapsed", "status",
               "d10", "d30", "d60", "best", "worst"], out)
    closed = [r for r in out if r[5] == "closed"]
    won = [r for r in closed if isinstance(r[8], float) and r[8] > 0]
    return out, len(closed), len(won)


def ds_status(reg, today, buy, per_year, outdir):
    """status.csv - regime, next buy, frequency, when this was scored."""
    up = [r for r in buy if r["status"] == "Upcoming"]
    rows = [["Market regime", "Bullish" if reg(today) else "Bearish"],
            ["Next buy date", up[0]["buyDate"] if up else "none ahead"],
            ["Trades a year", f"{per_year:.0f} on average" if per_year else "—"],
            ["Scored as of", str(today)]]
    write_csv(os.path.join(outdir, "status.csv"), ["item", "value"], rows)
    return rows


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="folder of candle CSVs")
    ap.add_argument("--out", default="datasets", help="where to write datasets")
    ap.add_argument("--keep", default=None, help="keep.json, for --tier frozen")
    ap.add_argument("--today", default=None, help="override today, YYYY-MM-DD")
    ap.add_argument("--tier", default="walkforward",
                    choices=["walkforward", "current", "frozen"],
                    help="how the traded tier is chosen (default walkforward)")
    a = ap.parse_args()

    today = (dt.date.fromisoformat(a.today) if a.today else dt.date.today())
    os.makedirs(a.out, exist_ok=True)
    keep_path = a.keep or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "keep.json")

    regime_path = os.path.join(a.data, REGIME_SRC)
    if not os.path.exists(regime_path):
        raise SystemExit(f"missing {regime_path}")
    reg = R.rsi_regime(regime_path, 8, 13, 60, 41)

    ch = load_charts(a.data, reg)
    for c in ch.values():
        c["reg"] = reg
        c["in_regime"] = [reg(d) for d in c["D"]]

    rows_all, dates = pool(ch)

    if a.tier == "walkforward":
        anchor = dt.date(today.year, 1, 1)
        keep = select_tier(rows_all, upto=anchor)
        tier_note = f"as it stood on {anchor}"
    elif a.tier == "current":
        keep = select_tier(rows_all)
        tier_note = "reselected from all data to date"
    else:
        keep = [(k["chart"], k["tag"]) for k in json.load(open(keep_path))]
        tier_note = f"frozen, from {os.path.basename(keep_path)}"
    if not keep:
        raise SystemExit(f"no setups qualify ({a.tier})")

    # the last date a trade could already have been scored over the horizon
    data_end = max(c["D"][-1] for c in ch.values())
    scoreable_to = data_end - dt.timedelta(days=HOR)

    stats = ds_setups(ch, keep, a.out)
    buy = ds_buy(ch, stats, dates, today, a.out)
    ds_live(ch, a.out)
    T, per_year = ds_tier(ch, rows_all, keep, a.out, scoreable_to)
    allbase = ds_walkforward(ch, rows_all, today, a.out)
    ds_confluence(ch, dates, a.out)
    n_inval = ds_invalidation(ch, a.out)
    early = ds_earlydip(ch, keep, a.out)
    hold = ds_holdcheck(ch, keep, a.out)
    fwd, fwd_closed, fwd_won = ds_forward(ch, rows_all, a.out)
    status = ds_status(reg, today, buy, per_year, a.out)

    # ------------------------------------------------------------ summary
    print(f"\nscored {today}   regime {status[0][1]}   "
          f"{len(rows_all)} troughs across {len(ch)} charts")
    for nm, c in ch.items():
        p = c["prov"]
        print(f"  {nm:7s} data->{c['D'][-1]}  CT {c['ct'][-1]:5.1f}  "
              f"forming: {'+'.join(t for t in p['tags'] if t != 'any trough') if p else '-'}")
    print(f"\n  tier ({a.tier}, {tier_note}): {len(keep)} setups, "
          f"{len(T)} trades, {per_year}/yr   walk-forward baseline {allbase}%")
    for c, t in sorted(keep):
        print(f"      {c:7s} {t}")
    print(f"  invalidation pool {n_inval} setups")
    print("\n  the day-10 check:")
    for r in hold:
        print(f"      {r[0]:17s}  n={r[1]:3d}  reached +20% {r[2]:3d}%  "
              f"median run {r[3]:+6.1f}%  median dip {r[4]:+6.1f}%  "
              f"{r[5]} deep enough to wipe 3x")
    print(f"\n  first {EARLY} days, then day {EARLY} to {HOR}:")
    for r in early:
        print(f"      {r[0]:>19s}  n={r[1]:3d}  +10% {r[2]:3d}%  +20% {r[3]:3d}%  "
              f"median run {r[4]:+6.1f}%")
    print(f"\n  live forward record since {FORWARD_FROM}: {len(fwd)} signals, "
          f"{fwd_closed} closed"
          + (f", {fwd_won} of those won" if fwd_closed else " (none have run 60 days yet)"))
    for r in fwd:
        print(f"      {r[0]:7s} {r[1]}  {r[5]:6s} {r[4]:3d}d  "
              f"best {r[9]}%  worst {r[10]}%  {r[2]}")
    if buy:
        print("\n  next buys:")
        for r in buy:
            print(f"    {r['chart']:7s} {r['buyDate']}  {r['status']:17s} "
                  f"{r['tagName']:12s} win {r['win']}%  n={r['n']}  "
                  f"agree {r['agree']}")
    else:
        print("\n  nothing forming")
    written = sorted(f for f in os.listdir(a.out) if f.endswith(".csv"))
    print(f"\n  {len(written)} datasets written to {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
