#!/usr/bin/env python3
"""Are the fetched candles CORRECT, not just current? (item 17a, 10 Nov 2026)

check_fresh.py confirms the candles advanced. Nothing confirmed they were right. Every
CTZB chart (1D, 2D, 3D, 5D, 8D) is built from Coinbase 1D, so a bad daily candle
corrupts every signal built on it. Two kinds of check:

STRUCTURAL -- enforced. No grey area, so they fail the run (before the commit, like
check_fresh.py: a bad fetch is retried, never committed as if it were good).
  - 1D, last 90 closed days: no missing day
  - 1D and 4H, last 90 days / 540 bars: low <= open,close <= high; every price > 0
  - 1D, last 90 closed days: volume > 0
  - whole history (fetch.history_problems): every row of every candle file well formed (prices finite and
    above zero, high and low bracketing open and close, volume not negative, 4H/12H on their grid, rows
    strictly ascending); each daily file starts on the exchange's first day with no missing day; every 2D-8D
    file is its daily candles bucketed; ETH is ETH and BTC is BTC; the funding series is whole and current.

CROSS-SOURCE -- compares Coinbase daily closes with Kraken's for the same UTC day.
  --cross report    (default) measures and records the gap, never fails the run.
  --cross enforce --max-close-gap PCT   fails when any day in the last 30 closed days
                    differs by more than PCT percent.
  Report mode exists because the normal Coinbase-Kraken gap had not been measured
  when this was written, and a threshold picked without that would be made up. One
  report run compares ~700 days per asset, enough to set the threshold from data.
  If Kraken is unreachable the check records "unavailable" and does NOT fail: the
  second source being down must never stop the first.

Writes datasets/candle_check.json either way.
"""
import argparse, csv, datetime as dt, json, os, statistics as st, sys, time, urllib.request

KRAKEN = "https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440"
PAIRS = {"ETH": "XETHZUSD", "BTC": "XXBTZUSD"}
STRUCT_DAYS = 90
STRUCT_4H_BARS = 540
ENFORCE_WINDOW = 30


def load(path):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            t = int(float(r["time"]))
            out[t] = tuple(float(r[k]) for k in ("open", "high", "low", "close", "volume"))
    return out


def structural(asset, d1, h4, today):
    bad = []
    days = sorted(dt.datetime.fromtimestamp(t, dt.timezone.utc).date() for t in d1)
    closed = [d for d in days if d < today][-STRUCT_DAYS:]
    want = {closed[0] + dt.timedelta(days=i) for i in range((closed[-1] - closed[0]).days + 1)}
    missing = sorted(want - set(closed))
    if missing:
        bad.append(f"{asset}_1D missing {len(missing)} day(s): {', '.join(map(str, missing[:5]))}")
    by_date = {dt.datetime.fromtimestamp(t, dt.timezone.utc).date(): v for t, v in d1.items()}
    for d in closed:
        o, h, l, c, v = by_date[d]
        if min(o, h, l, c) <= 0:
            bad.append(f"{asset}_1D {d}: non-positive price")
        elif not (l <= min(o, c) and max(o, c) <= h):
            bad.append(f"{asset}_1D {d}: OHLC inconsistent o={o} h={h} l={l} c={c}")
        if v <= 0:
            bad.append(f"{asset}_1D {d}: zero volume on a closed day")
    for t in sorted(h4)[-STRUCT_4H_BARS:]:
        o, h, l, c, v = h4[t]
        if min(o, h, l, c) <= 0 or not (l <= min(o, c) and max(o, c) <= h):
            when = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
            bad.append(f"{asset}_4H {when}: OHLC inconsistent or non-positive")
    return bad


def kraken_closes(asset):
    """{date: close} for CLOSED Kraken days, or None if Kraken can't be reached."""
    req = urllib.request.Request(KRAKEN.format(pair=PAIRS[asset]), headers={"User-Agent": "ctzb-pipeline"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.load(r)
            if j.get("error"):
                raise RuntimeError(str(j["error"]))
            rows = j["result"][PAIRS[asset]]
            # the last row is the day still forming
            return {dt.datetime.fromtimestamp(int(x[0]), dt.timezone.utc).date(): float(x[4]) for x in rows[:-1]}
        except Exception:
            if attempt == 2:
                return None
            time.sleep(3 * (attempt + 1))


def compare(cb_by_date, kr, today):
    """Per-day percent gap between closes, on every closed day both sources have."""
    gaps = {}
    for d, kc in kr.items():
        if d >= today or d not in cb_by_date:
            continue
        cc = cb_by_date[d][3]
        if kc > 0:
            gaps[d] = 100.0 * abs(cc / kc - 1.0)
    return gaps


def summarise(gaps):
    if not gaps:
        return None
    v = sorted(gaps.values())
    pick = lambda q: v[min(len(v) - 1, int(q * len(v)))]
    worst = sorted(gaps.items(), key=lambda kv: -kv[1])[:5]
    return {
        "days_compared": len(v),
        "from": str(min(gaps)), "to": str(max(gaps)),
        "median_pct": round(st.median(v), 4), "p90_pct": round(pick(.90), 4),
        "p99_pct": round(pick(.99), 4), "max_pct": round(v[-1], 4),
        "worst_days": [{"date": str(d), "gap_pct": round(g, 4)} for d, g in worst],
    }


def main(argv=None, kraken=kraken_closes, today=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="?", default="data")
    ap.add_argument("--out", default="datasets/candle_check.json")
    ap.add_argument("--cross", choices=["report", "enforce"], default="report")
    ap.add_argument("--max-close-gap", type=float, default=None)
    a = ap.parse_args(argv)
    if a.cross == "enforce" and a.max_close_gap is None:
        sys.exit("--cross enforce needs --max-close-gap")
    today = today or dt.datetime.now(dt.timezone.utc).date()

    report = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "cross_mode": a.cross, "max_close_gap_pct": a.max_close_gap,
              "structural_ok": True, "structural_problems": [], "cross": {}}
    fail = []
    # whole-history checks (13 Nov 2026 audit #20): no lost history, and every 2D-8D file is its daily candles
    # bucketed. A daily file cut short, or a multi-day file that doesn't match it, fails the run here.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import fetch
    hist = fetch.history_problems(a.data)
    report["structural_problems"] += hist
    fail += hist
    for asset in ("ETH", "BTC"):
        try:
            d1 = load(os.path.join(a.data, f"{asset}_1D.csv"))
            h4 = load(os.path.join(a.data, f"{asset}_4H.csv"))
        except (OSError, KeyError, TypeError, ValueError) as e:
            # a file the whole-history check above has already reported: stop cleanly instead of crashing
            msg = f"{asset}: candle files unreadable ({type(e).__name__}); see the whole-history problems"
            report["structural_problems"].append(msg); fail.append(msg)
            continue
        probs = structural(asset, d1, h4, today)
        report["structural_problems"] += probs
        fail += probs

        kr = kraken(asset)
        if kr is None:
            report["cross"][asset] = {"status": "unavailable"}
            print(f"{asset}: Kraken unreachable -- cross-check skipped this run (not a failure)")
            continue
        cb = {dt.datetime.fromtimestamp(t, dt.timezone.utc).date(): v for t, v in d1.items()}
        gaps = compare(cb, kr, today)
        s = summarise(gaps)
        recent = {d: g for d, g in gaps.items() if d >= today - dt.timedelta(days=ENFORCE_WINDOW)}
        over = sorted([(d, g) for d, g in recent.items()
                       if a.max_close_gap is not None and g > a.max_close_gap], key=lambda x: -x[1])
        report["cross"][asset] = {"status": "ok" if not over else "over_threshold",
                                  "all": s, "recent_window_days": ENFORCE_WINDOW,
                                  "recent": summarise(recent),
                                  "over_threshold": [{"date": str(d), "gap_pct": round(g, 4)} for d, g in over]}
        if s:
            print(f"{asset}: {s['days_compared']} days vs Kraken  median {s['median_pct']}%  "
                  f"p99 {s['p99_pct']}%  max {s['max_pct']}% ({s['worst_days'][0]['date']})")
        if over and a.cross == "enforce":
            fail.append(f"{asset}: {len(over)} recent close(s) differ from Kraken by more than "
                        f"{a.max_close_gap}% -- worst {over[0][0]} {over[0][1]:.3f}%")

    report["structural_ok"] = not report["structural_problems"]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(report, f, indent=1, default=str)
    if fail:
        print("BAD CANDLES: " + "; ".join(fail))
        return 1
    print("candles pass: structure OK" + ("" if a.cross == "report" else f", closes within {a.max_close_gap}% of Kraken"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
