#!/usr/bin/env python3
"""Elliott-style swing structure: segmentation, motive-wave test, live counts.

What this is for
----------------
Not to produce "the" wave count - there is no answer key, and two analysts
label the same chart differently. It enumerates every count the hard rules
still permit at the current price and names the level that kills each one.
The useful output is those levels, not the labels.

Measured on 218 valid structures across ETH and BTC, 4H through 3D
(see README):

    wave 4 retrace of wave 3   median 0.40, quartiles 0.34-0.50
                               stable at EVERY scale and on both assets
    wave 3 as a multiple of 1  median 2.14, quartiles 1.49-3.17
    wave 2 retrace of wave 1   median 0.65, quartiles 0.47-0.83
                               the textbook 0.5-0.618 catches 19% of them;
                               intraday retraces deeper than daily

So the zones below are calibrated to this data, not inherited from the books.
"""
import argparse, csv, datetime as dt, os, sys

# Calibrated from the 218 structures; see the module docstring.
ZONES = {"w2": (0.47, 0.83, 0.65),
         "w4": (0.34, 0.50, 0.40),
         "w3": (1.49, 3.17, 2.14)}


def load(path):
    bars = []
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                bars.append((int(r["time"]), float(r["open"]), float(r["high"]),
                             float(r["low"]), float(r["close"])))
            except (ValueError, KeyError):
                continue
    return bars


def pivots(bars, left, right=1):
    """ta.pivothigh / ta.pivotlow(src, left, right), in bar order."""
    ev, n = [], len(bars)
    for i in range(left, n - right):
        h, l = bars[i][2], bars[i][3]
        if all(bars[j][2] < h for j in range(i - left, i)) and \
           all(bars[i + k][2] <= h for k in range(1, right + 1)):
            ev.append((i, h, +1))
        if all(bars[j][3] > l for j in range(i - left, i)) and \
           all(bars[i + k][3] >= l for k in range(1, right + 1)):
            ev.append((i, l, -1))
    ev.sort(key=lambda e: (e[0], -e[2]))
    return ev


def zigzag(bars, left):
    """Alternating pivots: push on a direction change, extend on the same one."""
    pts = []
    for i, y, d in pivots(bars, left):
        if not pts or pts[-1][2] != d:
            pts.append([i, y, d])
        elif (d == 1 and y > pts[-1][1]) or (d == -1 and y < pts[-1][1]):
            pts[-1] = [i, y, d]
    return pts


def motive(pts, k):
    """The four hard rules, on the six points ending at index k.

    Matches LuxAlgo's isWave, which omits the textbook "wave 3 must exceed the
    end of wave 1". That omission turns out not to matter: across 218 valid
    structures it was never violated anyway, so the looser test finds the same
    set. `w3_beats_w1` reports it regardless.
    """
    if k < 5:
        return None
    p = pts[k - 5:k + 1]
    d = [x[2] for x in p]
    y = [x[1] for x in p]
    if d == [-1, 1, -1, 1, -1, 1]:
        up = True
        W1, W3, W5 = y[1] - y[0], y[3] - y[2], y[5] - y[4]
        W2, W4 = y[1] - y[2], y[3] - y[4]
        ok = y[5] > y[3] and y[2] > y[0] and y[4] > y[1]
    elif d == [1, -1, 1, -1, 1, -1]:
        up = False
        W1, W3, W5 = y[0] - y[1], y[2] - y[3], y[4] - y[5]
        W2, W4 = y[2] - y[1], y[4] - y[3]
        ok = y[5] < y[3] and y[2] < y[0] and y[4] < y[1]
    else:
        return None
    if min(W1, W3, W5) <= 0:
        return None
    ok = ok and W3 != min(W1, W3, W5)
    return dict(ok=ok, up=up, pts=p, W1=W1, W2=W2, W3=W3, W4=W4, W5=W5,
                ret2=W2 / W1, ret4=W4 / W3, ext3=W3 / W1, ext5=W5 / W1,
                w3_beats_w1=(y[3] > y[1]) if up else (y[3] < y[1]))


def counts(bars, left, lookback=9):
    """Every count the hard rules still allow at the last bar."""
    pts = zigzag(bars, left)
    out = []
    for s in range(len(pts[-lookback:]) - 1):
        seq = pts[-lookback:][s:]
        up = seq[0][2] == -1
        y = [p[1] for p in seq]
        nw = len(y) - 1
        if not 1 <= nw <= 4:            # 5 complete means the count is finished
            continue
        gt = (lambda a, b: a > b) if up else (lambda a, b: a < b)
        if nw >= 2 and not gt(y[2], y[0]):
            continue
        if nw >= 3 and not gt(y[3], y[1]):
            continue
        if nw >= 4 and not gt(y[4], y[1]):
            continue
        building = nw + 1
        # the level that kills this count - indexed lazily, since a count with
        # one leg complete has no y[4] to look at
        invalid = (y[0] if building == 2 else
                   y[2] if building == 3 else
                   y[1] if building == 4 else
                   y[4] if building == 5 else None)
        W1 = abs(y[1] - y[0])
        base, tgt = y[nw], {}
        if building == 3:
            lo, hi, mid = ZONES["w3"]
            tgt = {f"{m:.2f}x wave 1": base + (W1 * m if up else -W1 * m)
                   for m in (lo, mid, hi)}
        elif building == 5:
            net = abs(y[3] - y[0])
            tgt = {"= wave 1": base + (W1 if up else -W1),
                   "0.618 x waves 1-3": base + (net * .618 if up else -net * .618)}
        out.append(dict(up=up, complete=nw, building=building, pivots=y,
                        invalid=invalid, targets=tgt))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "data"))
    ap.add_argument("--file", help="a single CSV, instead of --data/--symbol")
    ap.add_argument("--symbol", default="ETH")
    ap.add_argument("--tf", default="2D")
    ap.add_argument("--degrees", default="4,8,16")
    a = ap.parse_args()
    path = a.file or os.path.join(a.data, f"{a.symbol}_{a.tf}.csv")
    if not os.path.exists(path):
        sys.exit(f"no such file: {path}")
    bars = load(path)
    px = bars[-1][4]
    when = dt.datetime.fromtimestamp(bars[-1][0], dt.timezone.utc)
    print(f"{os.path.basename(path)}  last close {px:,.2f}  {when:%Y-%m-%d %H:%M} UTC\n")
    for L in [int(x) for x in a.degrees.split(",")]:
        C = counts(bars, L)
        print(f"  degree {L} - {len(C)} count(s) still allowed")
        for c in C:
            side = "bullish" if c["up"] else "bearish"
            inv = f"{c['invalid']:,.2f}" if c["invalid"] else "-"
            word = "below" if c["up"] else "above"
            print(f"    {side} impulse, {c['complete']} leg(s) done, "
                  f"building wave ({c['building']})")
            print(f"      dies {word} {inv}")
            for k, v in c["targets"].items():
                print(f"      target {k:20s} {v:,.2f}")
        if not C:
            print("    (none - price has broken every structure at this degree)")
        print()


if __name__ == "__main__":
    main()
