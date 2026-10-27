"""Hurst Future Lines of Demarcation, with measured cycle drift.

J.M. Hurst's FLD is the candle MIDPOINT (high+low)/2 displaced forward in time
by HALF the cycle's wavelength. Not the close, and not a moving average -- it is
the price series itself, shifted. Price crossing above its FLD confirms the
trough of that cycle frequency; crossing below confirms the peak. The whole
construct is only as good as the wavelength you feed it, which is why the second
half of this file exists.

NOMINAL MODEL. Hurst's cycles sit at roughly 2:1 ratios. Wavelengths in days,
as the nominal model states them (not the round names):

    5D 4.3 | 10D 8.5 | 20D 17 | 40D 34.1 | 80D 68.2 | 160D 136.4
    320D 272.8 | 18mo 545.6 | 54mo 1636.8

CYCLE SHIFT OVER TIME -- the part that matters. Hurst's principle of variation
says cycles vary in length around their nominal average; they are not a metronome.
A fixed-wavelength FLD therefore drifts out of phase with the market and starts
producing signals at the wrong time. Two measurements here, both empirical:

  measure_period()  Bandpass the log-price series around a target wavelength,
                    then take the dominant period by FFT inside a rolling window.
                    Returns a period PER BAR, so the drift is visible as a series
                    rather than assumed away.

  trough_spacing()  The blunter cross-check: distance between consecutive price
                    troughs, rolling median. If the FFT and the trough spacing
                    disagree badly, neither is trustworthy for that chart.

  adaptive_fld()    The FLD built with the measured half-period at each bar
                    instead of a constant. This is what "accounting for cycle
                    shift" actually means in code: the displacement itself moves.

HONEST WARNING, recorded here so it travels with the file. An FLD is a
transform of price and nothing else. CONTEXT.md: "Price transforms keep failing;
different axes keep working. Fibs, moving averages, Elliott wave, opens/closes
and now money flow have all come back empty." Elliott wave in particular is a
cycle-counting method and it failed here. This belongs to that family and the
prior should be set accordingly. It is cheap to test, which is the only reason
to test it.
"""
import math
import numpy as np

NOMINAL = {'5D': 4.3, '10D': 8.5, '20D': 17.0, '40D': 34.1, '80D': 68.2,
           '160D': 136.4, '320D': 272.8, '18mo': 545.6, '54mo': 1636.8}

TF_DAYS = {'1D': 1, '2D': 2, '3D': 3, '5D': 5, '8D': 8, '12H': 0.5, '4H': 1/6}


def midpoint(b):
    return [(h + l) / 2.0 for h, l in zip(b['high'], b['low'])]


def fld(b, wavelength_days, tf_days):
    """Midpoint displaced forward by half the wavelength. None until it fills."""
    shift = int(round(wavelength_days / 2.0 / tf_days))
    if shift < 1:
        return None, 0
    mp = midpoint(b)
    return [None] * shift + mp[:-shift], shift


def _bandpass(x, lo_bars, hi_bars):
    """Difference of two TRAILING moving averages.

    This was centred (np.convolve mode='same') in the first version, which made
    bp[i] a function of bars after i. measure_period() then fed that into a
    rolling window and the adaptive FLD inherited the lookahead, inflating every
    adaptive feature from about +9 to about +17 in the first test run. Trailing
    only. If a filter needs a centred smoother to work, it does not work.
    """
    x = np.asarray(x, float)
    def tma(n):
        n = max(2, int(round(n)))
        cs = np.concatenate(([0.0], np.cumsum(x)))
        out = np.full(len(x), np.nan)
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
        return out
    return tma(lo_bars) - tma(hi_bars)


def measure_period(b, target_days, tf_days, window_mult=4.0):
    """Dominant period in bars, per bar, by AUTOCORRELATION of a bandpassed
    log-price series inside a rolling window.

    Autocorrelation, not FFT. The first version of this used an FFT and was
    wrong in a way worth recording: the search band around a target wavelength
    spans only two or three FFT bins at these window lengths, so the peak landed
    on the same bin every time and the function returned window/3 for every
    chart and every year. The drift it reported was the window size, not the
    market. Autocorrelation resolves to one bar, and parabolic interpolation
    around the peak gives sub-bar precision.
    """
    close = np.asarray(b['close'], float)
    n = len(close)
    tgt = target_days / tf_days
    lo, hi = max(3, int(math.floor(tgt * 0.6))), int(math.ceil(tgt * 1.6))
    win = int(round(tgt * window_mult))
    if n < win + 2 or win < 10 or hi >= win - 2:
        return [None] * n
    lx = np.log(np.clip(close, 1e-9, None))
    bp = _bandpass(lx, tgt * 1.5, tgt * 0.5)
    out = [None] * n
    for i in range(win, n):
        seg = bp[i - win:i].astype(float)
        if not np.all(np.isfinite(seg)):
            continue
        seg = seg - seg.mean()
        d0 = float(seg @ seg)
        if d0 <= 0:
            continue
        best, bestv = None, -2.0
        vals = {}
        for L in range(lo, min(hi, win - 2) + 1):
            a, c = seg[:-L], seg[L:]
            den = math.sqrt(float(a @ a) * float(c @ c))
            if den <= 0:
                continue
            r = float(a @ c) / den
            vals[L] = r
            if r > bestv:
                best, bestv = L, r
        if best is None or bestv <= 0:
            continue
        ym1, y0, yp1 = vals.get(best - 1), bestv, vals.get(best + 1)
        adj = 0.0
        if ym1 is not None and yp1 is not None:
            den = (ym1 - 2 * y0 + yp1)
            if den != 0:
                adj = 0.5 * (ym1 - yp1) / den
                adj = max(-0.5, min(0.5, adj))
        # A peak pinned to either edge of the search band means the real cycle
        # is probably OUTSIDE the band, not at its boundary. Reporting the edge
        # as a measurement is how a band floor gets mistaken for a 20-bar cycle.
        if best <= lo or best >= min(hi, win - 2):
            continue
        out[i] = float(best + adj)
    return out


def trough_spacing(b, min_sep_bars):
    """Consecutive price-trough distances in bars, and the rolling median.
    The cross-check on measure_period()."""
    lo = np.asarray(b['low'], float)
    n = len(lo)
    k = max(2, int(min_sep_bars // 2))
    idx = [i for i in range(k, n - k)
           if lo[i] == lo[i - k:i + k + 1].min() and lo[i] < lo[i - 1] and lo[i] <= lo[i + 1]]
    pruned = []
    for i in idx:
        if pruned and i - pruned[-1] < min_sep_bars:
            if lo[i] < lo[pruned[-1]]:
                pruned[-1] = i
            continue
        pruned.append(i)
    gaps = [(pruned[j], pruned[j] - pruned[j - 1]) for j in range(1, len(pruned))]
    return pruned, gaps


def adaptive_fld(b, target_days, tf_days, fallback_days=None):
    """FLD whose displacement moves with the measured period. The displacement
    at bar i uses the period measured AT i, so it is causal in the sense that
    matters: it never reaches forward for the price it plots."""
    per = measure_period(b, target_days, tf_days)
    mp = midpoint(b)
    n = len(mp)
    fb = int(round((fallback_days or target_days) / 2.0 / tf_days))
    out = [None] * n
    used = [None] * n
    for i in range(n):
        p = per[i]
        sh = int(round(p / 2.0)) if p else fb
        sh = max(1, sh)
        used[i] = sh
        if i - sh >= 0:
            out[i] = mp[i - sh]
    return out, per, used


def drift_report(b, dates, target_days, tf_days, label=''):
    """How much has the cycle actually moved? The answer to 'account for cycle
    shift over time'."""
    per = measure_period(b, target_days, tf_days)
    have = [(dates[i], per[i]) for i in range(len(per)) if per[i]]
    if not have:
        return None
    vals = [p for _, p in have]
    nom_bars = target_days / tf_days
    yearly = {}
    for d, p in have:
        yearly.setdefault(d.year, []).append(p)
    return dict(label=label, n=len(have), nominal_bars=nom_bars,
                median=float(np.median(vals)),
                p10=float(np.percentile(vals, 10)), p90=float(np.percentile(vals, 90)),
                first=have[0][0], last=have[-1][0], latest=have[-1][1],
                yearly={y: float(np.median(v)) for y, v in sorted(yearly.items())})
