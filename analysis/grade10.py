#!/usr/bin/env python3
"""What the conviction grade looks like measured on +10% instead of +20% (11 Nov 2026).

Jared, 11 Nov 2026: "give me the statistics of grading by the 10% instead of 20%, the
statistics sheet first." DESCRIPTIVE ONLY. Nothing here is chosen, tuned or tested as a
filter: the grade is exactly the live one (grade_live.py: count of lenses, C 0-1, B 2,
A 3, A+ 4+; lenses picked in analysis/grade.py on +20%), applied to every graded signal
in datasets/ledger.csv (mechanical regime gate R.rsi_regime(BTC_2D, 8, 13, 60, 41); entry
at the confirmation close, ei = ti + 3; 1D/2D/3D/5D charts; every signal has its full 60
days). Only the yardstick changes. Declared before running, these tables and nothing else:

  1. per asset and grade: n, signals a year, rose 10% (with its 95% Wilson lower bound),
     rose 10% and never fell 25%, reached +20%, median best move
  2. the same split by chart (rose 10% and +20%)
  3. the same split by era (2016-19, 2020-21, 2022-23, 2024-26), assets kept apart
  4. ordering: does A+ beat A, B and C on +10% in each asset, chart and era?
  5. the 70% bar on +10%: which asset/grade/chart cells clear it

ETH and BTC are one sample for anything date-anchored (same market moves): read the era
table per asset, not as two confirmations. The ledger's grade odds are whole-sample, so
hindsight for past signals. ENTRY QUALITY ONLY: no exit, not a strategy return or a track
record. Writes analysis/RESULTS_grade10.txt and analysis/grade10.json.
"""
import csv, json, math, os, statistics as st, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADES = ("A+", "A", "B", "C")
ERAS = (("2016-19", 2016, 2019), ("2020-21", 2020, 2021), ("2022-23", 2022, 2023), ("2024-26", 2024, 2026))
BAR = 70


def wilson_lo(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n) * 100


def stats(rs):
    n = len(rs)
    if not n:
        return {"n": 0}
    k10 = sum(r["reached10"] == "yes" for r in rs)
    return {"n": n, "rose10": round(k10 / n * 100), "rose10_lo": round(wilson_lo(k10, n)),
            "surv10": round(sum(r["surv10"] == "yes" for r in rs) / n * 100),
            "rose20": round(sum(r["reached20"] == "yes" for r in rs) / n * 100),
            "med_best": round(st.median(float(r["bestMove"]) for r in rs), 1)}


def main():
    led = list(csv.DictReader(open(os.path.join(ROOT, "datasets/ledger.csv"))))
    for r in led:
        r["yr"] = int(r["year"])
    out = {"note": "Descriptive. Live grade, +10% yardstick. Entry quality only.", "by_asset": {}, "by_chart": {}, "by_era": {}, "ordering": {}, "bar70": []}
    L = []
    p = L.append
    p("Conviction grade measured on +10% instead of +20% (analysis/grade10.py, 11 Nov 2026)")
    p("Descriptive only: the live grade, unchanged; only the yardstick moves. Entry quality only:")
    p("no exit, not a strategy return or a track record. Grade odds are whole-sample (hindsight).\n")

    p("1. By asset and grade (every graded signal, full 60 days)\n")
    p(f"   {'':9}{'n':>5}{'/yr':>6}{'rose 10%':>10}{'(95% low)':>11}{'+10%, never -25%':>18}{'+20%':>7}{'med best':>10}")
    for a in ("ETH", "BTC"):
        ra = [r for r in led if r["asset"] == a]
        yrs = max(r["yr"] for r in ra) - min(r["yr"] for r in ra) + 1
        for g in GRADES:
            s = stats([r for r in ra if r["grade"] == g])
            if not s["n"]:
                continue
            s["per_year"] = round(s["n"] / yrs, 1)
            out["by_asset"][f"{a} {g}"] = s
            p(f"   {a} {g:<5}{s['n']:>5}{s['per_year']:>6}{s['rose10']:>9}%{s['rose10_lo']:>10}%{s['surv10']:>17}%{s['rose20']:>6}%{s['med_best']:>+9}%")
        p("")

    p("2. By chart: rose 10% (+20% in brackets), n\n")
    charts = sorted({r["chart"] for r in led}, key=lambda c: (c[:3], ["1D", "2D", "3D", "5D"].index(c[4:])))
    p(f"   {'':8}" + "".join(f"{g:>17}" for g in GRADES))
    for c in charts:
        cells = []
        for g in GRADES:
            s = stats([r for r in led if r["chart"] == c and r["grade"] == g])
            out["by_chart"][f"{c} {g}"] = s
            cells.append(f"{s['rose10']}% ({s['rose20']}%) n{s['n']}" if s["n"] else "none on record")
        p(f"   {c:<8}" + "".join(f"{x:>17}" for x in cells))
    p("")

    p("3. By era, assets apart: rose 10% (+20%), n. ETH and BTC share dates: one sample, not two.\n")
    p(f"   {'':12}" + "".join(f"{g:>17}" for g in GRADES))
    for a in ("ETH", "BTC"):
        for name, y0, y1 in ERAS:
            cells = []
            for g in GRADES:
                s = stats([r for r in led if r["asset"] == a and r["grade"] == g and y0 <= r["yr"] <= y1])
                out["by_era"][f"{a} {name} {g}"] = s
                cells.append(f"{s['rose10']}% ({s['rose20']}%) n{s['n']}" if s["n"] else "none on record")
            p(f"   {a} {name:<8}" + "".join(f"{x:>17}" for x in cells))
        p("")

    p("4. Ordering on +10%: is A+ above every lower grade? (cells with fewer than 5 signals skipped)\n")
    def order(groups, label):
        held = tot = 0
        fails = []
        for key, rs in groups:
            top = stats([r for r in rs if r["grade"] == "A+"])
            if top["n"] < 5:
                continue
            lows = [(g, stats([r for r in rs if r["grade"] == g])) for g in GRADES[1:]]
            lows = [(g, s) for g, s in lows if s["n"] >= 5]
            if not lows:
                continue
            tot += 1
            bad = [f"{g} {s['rose10']}%" for g, s in lows if s["rose10"] >= top["rose10"]]
            if bad:
                fails.append(f"{key}: A+ {top['rose10']}% vs " + ", ".join(bad))
            else:
                held += 1
        out["ordering"][label] = {"held": held, "of": tot, "exceptions": fails}
        p(f"   {label:<8} A+ on top in {held} of {tot}" + ("" if not fails else ";  not on top: " + " | ".join(fails)))
    order([(a, [r for r in led if r["asset"] == a]) for a in ("ETH", "BTC")], "asset")
    order([(c, [r for r in led if r["chart"] == c]) for c in charts], "chart")
    order([(f"{a} {n}", [r for r in led if r["asset"] == a and y0 <= r["yr"] <= y1]) for a in ("ETH", "BTC") for n, y0, y1 in ERAS], "era")
    p("")

    p(f"5. The {BAR}% bar on +10%: cells that clear it (and on +20%, for comparison)\n")
    p(f"   {'':12}{'rose 10%':>10}{'clears':>8}{'+20%':>7}{'clears':>8}")
    for key, s in out["by_asset"].items():
        row = {"cell": key, "n": s["n"], "rose10": s["rose10"], "clears10": s["rose10"] >= BAR, "rose20": s["rose20"], "clears20": s["rose20"] >= BAR}
        out["bar70"].append(row)
        p(f"   {key:<12}{s['rose10']:>9}%{'yes' if row['clears10'] else 'no':>8}{s['rose20']:>6}%{'yes' if row['clears20'] else 'no':>8}")

    text = "\n".join(L) + "\n"
    open(os.path.join(ROOT, "analysis/RESULTS_grade10.txt"), "w").write(text)
    json.dump(out, open(os.path.join(ROOT, "analysis/grade10.json"), "w"), indent=1)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
