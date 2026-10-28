# Hurst cycles: everything tested, 26–27 Oct 2026

A cold-start handoff. Read this and you can continue without the chat it came
from. Code is in `analysis/`, results in the matching `RESULTS_*.txt`, and the
condensed version is already in `CONTEXT.md`.

---

## 1. What a Hurst FLD is, and why it failed

An FLD (Future Line of Demarcation) is the candle **midpoint** `(high+low)/2`
displaced forward in time by **half the cycle wavelength**. Not the close, not
a moving average — the price series itself, shifted. In Hurst's method, price
crossing above its FLD confirms the trough of that cycle frequency.

Built faithfully in `analysis/fld.py`, tested in `analysis/fldtest.py` on 1,120
regime-gated signals across 8 charts, baseline 56% win / 20% touched −30%.

Eight declared features. The best, "price above the 20D, 40D and 80D FLDs at
once", scored **+16** on win rate. That looked strong until benchmarked:

| | n | win | −30% | edge |
|---|---|---|---|---|
| above 20D, 40D, 80D FLDs | 461 | 65% | 16% | +16 |
| plain `close > close[N]`, same lookbacks | 434 | 65% | 16% | +15 |

**They agree on 93% of signals.** Where they disagree, both sides sit at
baseline (60% on n=53, 58% on n=26). Added to the existing stack: `gap>5` alone
is 70% win / 14% touched −30%; `gap>5` plus the FLD is 69% / 16% — slightly
worse.

**Why.** "Price above its FLD" unpacks to "close above the midpoint from N bars
ago", which is nearly "close above the close from N bars ago". The cycle
calculation only chooses *how far back N is*; it does not change the question
being asked. It is a trend check with a cycle-derived lookback.

**Do not re-test the FLD as a selector.**

## 2. Two bugs caught during the build — both shapes recur

**(a) An FFT that measured its own window.** The first cycle-period measurement
used an FFT. At these window lengths the search band around a target wavelength
spans only two or three frequency bins, so the peak landed on the same bin every
time and the function returned `window/3` for every chart and every year. The
"drift" it reported was the window size. Replaced with autocorrelation, which
resolves to one bar, plus parabolic interpolation for sub-bar precision.

*Tell:* the output was suspiciously identical across assets and years —
22.7, 45.3, 91.0, 182.0, 363.7, all exact doublings.

**(b) A centred bandpass that leaked the future.** `_bandpass` used
`np.convolve(..., mode='same')`, a centred moving average, so `bp[i]` depended
on bars after `i`. Every adaptive feature inherited the lookahead. Worth about
**+6** before it was fixed. Now trailing-only.

*Tell:* the one feature touching no measurement scored +9 while everything
measured scored +16. **If a filter needs a centred smoother to work, it does
not work.**

## 3. Two cycle measurements worth keeping regardless

These came out of the failed FLD work and stand on their own.

**Crypto cycles run 1.15–1.34× Hurst's nominal wavelengths.** Consistent on
both assets at all four degrees:

| cycle | Hurst nominal | measured (BTC / ETH) |
|---|---|---|
| 20D | 17.0 bars | 20.8 / 21.3 |
| 40D | 34.1 | 41.4 / 40.1 |
| 80D | 68.2 | 84.3 / 88.0 |
| 160D | 136.4 | 182.3 / 157.5 |

Anyone applying the nominal model straight to crypto is running about 25% short.

**A clean in-band period exists only 36–60% of the time.** The cycle is not
always present.

## 4. Phase failed, and the reason is structural

`analysis/phase.py`. Phase = fraction of the measured period elapsed since the
last **confirmed** trough. Edges ran −7 to +2 across three degrees — but the
real finding is *why it cannot work*:

A trough is only confirmed a quarter-period after it happens. So the phase<0.2
bin — "just past a cycle low", exactly the region of interest — is
**mathematically unreachable** and comes back empty, while 60% of rows pile into
the top bin.

**If a cycle measure needs to know where the last trough was, it is already too
late. Forward projection is the only causal form.**

## 5. Forward projection — this is the one that works

`analysis/proj.py`. `projected_next = last confirmed trough + measured period`;
`dist = (projected_next − i) / period`. Everything known at the entry bar.
DUE means `dist < 0.2`.

**The edge strengthens with cycle degree, and only the largest is consistent:**

| degree | edge | charts positive |
|---|---|---|
| 40D | +4 | 5 of 8 |
| 80D | +3 | 5 of 8 |
| **160D** | **+12** | **8 of 8** |

160D: DUE n=465 win 59%, not-due n=500 win 48%. Per chart: ETH 1D +9, 2D +5,
3D +7, 5D +23; BTC 1D +13, 2D +12, 3D +23, 5D +8.

**It passes the momentum benchmark that killed the FLD.** Plain momentum scores
+3 on the same rows against this feature's +12; they agree on only 53% of
signals; DUE-but-not-momentum wins 57% while momentum-but-not-DUE wins 48%.

## 6. Confidence battery — three of four pass

`analysis/projrobust.py`. Real pooled edge **+11.5** on n=965.

**PLACEBO — passes hard.** Every projected trough date jittered by a random
offset, re-scored 40 times. Shuffled edges: median +1.5, p95 +7.0, max +7.9.
The real +11.5 was beaten by **0 of 40**. (Note the shuffled median is +1.5, not
0, so the construct carries a small positive bias of its own; the real edge
clears it anyway.)

**HOLDOUT — passes, both assets, both periods.** Rule fixed:

| | ETH | BTC | pooled |
|---|---|---|---|
| discovery 2016–21 | +9 | +12 | +11 |
| holdout 2022–25 | +11 | +21 | +16 |

**PARAMETERS — passes.** Confirmation lag 0.15 → +13.8, 0.35 → +8.8; bandpass
1.3/0.7 → +11.0, 2.0/0.4 → +10.8; threshold 0.15 → +9.7, 0.30 → +5.5. Every
setting positive.

**GRADIENT — fails to be clean, and this is the open problem.** Win rate by
distance to the projected low:

| distance | n | win |
|---|---|---|
| −0.50 to 0.00 (overdue) | 287 | 61% |
| 0.00 to 0.10 | 82 | 50% |
| 0.10 to 0.20 | 96 | 61% |
| 0.20 to 0.30 | 94 | **37%** |
| 0.30 to 0.45 | 174 | 52% |
| 0.45 to 0.60 | 117 | 50% |
| 0.60 to 1.10 | 115 | 46% |

Jagged: 61, 50, 61, 37, 52, 50, 46. The bin **closest** to the projected low is
only 50%. A good share of the +11.5 comes from the 0.20–0.30 cell being
unusually bad rather than the near cells being unusually good.

**"Closer to the cycle low is better" is NOT what the data says.** Anyone
describing it that way is over-reading it.

## 7. The confluence interaction — Jared's idea, holds on ETH

`analysis/projconf.py`. A print inside a projected low window *with* other
timeframes already confirming. Confluence is backward-only.

ETH, 160D, baseline 57%:

| | n | win | touched −30% |
|---|---|---|---|
| due AND 2+ agree | 103 | **69%** | 17% |
| due, 0–1 agree | 134 | 56% | 30% |
| not due, 2+ agree | 116 | 58% | 22% |
| not due, 0–1 agree | 122 | 48% | 33% |

**Neither half works alone** — 56% and 58% separately, 69% together. On BTC the
confluence half adds nothing (56% vs 57%), consistent with the existing record
that confluence lift is ETH-only.

Caution: 24 cells were examined across degrees and scopes; the ETH +12 is about
2.5 standard errors. The stacked `gap>5` cell is n=31 and is not actionable.

## 8. THE MOST IMPORTANT CAVEAT — found 27 Oct, after all the above

Everything in sections 5–7 is ranked on **win rate**, which is the wrong
variable for how this account is traded. At ~3.3x, a "win" that first draws
down 28% is not a win — the position is liquidated or shaken out long before
+20% arrives.

Re-ranked against failure (`analysis/failtest.py`), the 160D projection is near
the **bottom** of the feature set for risk:

| feature | n | touches −30% | cut vs 20% baseline |
|---|---|---|---|
| 2D/3D stoch divergence | 125 | 13% | −8 |
| funding not cooling | 359 | 13% | −7 |
| gap>5 | 223 | 14% | −6 |
| **160D trough DUE** | 465 | **18%** | **−2** |

**The projection is a win-rate filter, not a risk filter.** It does not keep you
alive. Describe it that way.

The stack that does cut risk is `funding not cooling AND gap>5`: n=102,
liquidation 6% against a 20% baseline, median drawdown −8.8% against −14.0%,
win 71% — keeping 9% of signals.

## 8b. CORRECTION — 27 Oct, late

Sections 5–7 project from troughs of the bandpass, and those are not price
lows: at each one price sits a median 43–47% of the way up its cycle range.
Rebuilt on real price swing lows in `analysis/hurstlow.py` and
`pine/ctzb_hurst_lows.pine`: 160D projections land a median 0.33 period early
and DUE does nothing at signals once it means a real low (flat pooled, flips by
period). 80D is tighter. See CONTEXT.md, "CORRECTION, 27 Oct 2026 late".

## 9. Where to pick up

1. **Explain the gradient or drop it.** A filter whose mechanism cannot be
   stated will be abandoned the first time it costs a trade. Why is 0.20–0.30
   so much worse than its neighbours?
2. **Walk-forward the projection** the way the CT/Signal distance was done —
   fix the rule each January on prior data only, apply blind to the next year.
3. **Re-score the projection and the confluence interaction against LIQ30 and
   median drawdown**, not win rate. Section 8 is the standing change.
4. **2025 inverts** at −21 on the projection. Unexplained.
5. 160D is the only degree that works. 40D and 80D are 5-of-8. No idea why the
   slow cycle carries information the faster ones do not.

## Files

| path | what |
|---|---|
| `analysis/fld.py` | FLD construction, period measurement, drift report, adaptive FLD |
| `analysis/fldtest.py` | the declared FLD test (failed) |
| `analysis/phase.py` | backward phase (failed, structurally) |
| `analysis/proj.py` | forward projection (works) |
| `analysis/proj2.py` | momentum / year / regime-age / stack validation |
| `analysis/projrobust.py` | placebo, gradient, holdout, parameter battery |
| `analysis/projconf.py` | projection × confluence interaction |
| `analysis/failtest.py` | every feature re-ranked against failure |

Run any of them from the repo root with `python3 -I analysis/<name>.py`.
