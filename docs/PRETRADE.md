# Pre-trade checklist

Run this before putting a position on. It does not replace the signal — the
signal is still a confirmed trough with the regime gate on. This is the layer
that sorts good signals from mediocre ones.

Every number here is **reaching +20% within 60 days of entry**, measured from
the close of the confirmation bar (`ei = ti + 3`), on regime-gated signals
only. Pooled baseline across 9 charts and 993 signals, 2016–2025: **54%**.
Per-chart baselines differ and are given where they matter — compare against
the chart's own, not the pooled one.

Tested dates are kept so a figure can be traced back to the run that produced
it. Nothing goes in Tier 1 until it has survived both a per-chart and a
per-year split.

---

## Tier 1 — validated. Stack these.

### 1. CT RSI more than 5 points above the Signal line
*Tested 22 Oct 2026. The strongest single filter found.*

The Signal line is the orange line on the indicator: `ta.ema(ct_rsi, 14)`.
Fitted with zero error over 1,879 ETH 2D bars.

| | n | +20% | Edge | Med upside | Med 60d ret | Med DD |
|---|---|---|---|---|---|---|
| gap > +5 | 204 | **68%** | +15 | +33.7% | +14.6% | −4.7% |
| baseline | 993 | 54% | — | +24.1% | +9.2% | −5.4% |

Positive in **9 of 9** testable years. Per chart against each chart's own
baseline: ETH 1D 64/45, ETH 2D 87/62, ETH 3D 59/55, ETH 5D 69/70, ETH 1W 86/68,
BTC 1D 71/52, BTC 2D 66/52, BTC 3D 50/51, BTC 5D 55/47. Seven of nine positive,
none of them carrying it.

**The distance is the signal, not the cross.** See the failed list.

### 2. CT above the Signal line **and** a prime dot
*Tested 22 Oct 2026.* n=109, **72%**, edge +19, med upside +32.8%, med DD −4.0%.
Positive in 8 of 9 years. ETH 2D 87%, ETH 3D 92%, BTC 1D 70%, BTC 2D 75%.
Only miss: ETH 1D at 40% against a 45% baseline.

### 3. CT above the Signal line **and** a diamond
*Tested 22 Oct 2026.* n=110, **67%**, edge +14, med upside +31.7%.
Positive in 8 of 8 testable years.

> **These three overlap.** gap>5 and prime share 48 signals of 204/109;
> gap>5 and diamond share 38. All three require CT above the line. This is one
> condition read three ways, not three independent confirmations. All three
> together is n=13 at 92% — too thin to use.

### 4. Higher low versus the previous signal's entry
*Tested 19 Oct 2026.* Compare this signal's entry close to the **previous
signal's entry close** on the same chart.

| | ETH | BTC |
|---|---|---|
| stepping up | 69% (n=292) | 57% (n=236) |
| stepping down | 52% (n=263) | 45% (n=182) |

Monotonic from −20% to +15%. Stacked: diamond + dot with a higher entry is 78%
(n=46) against 55% for the same tag with a lower entry. Below −30% it inverts
to 81% on ETH (n=21) — capitulation rather than a staircase, but thin.

**This is a late-regime filter.** Spread by how long the regime has been on:
+3 (0–60 days), +6 (60–150), +15 (150–300), +19 (300+). Near useless on a
fresh regime, worth 19 points deep into one. Check the regime age before
leaning on it.

### 5. Cross-timeframe agreement — ETH only
*Tested 19 Oct 2026.* Backward-only count: how many other timeframes have
**already** printed, never ones that print after.

ETH 1D 58→67 (n=205/83), ETH 2D 59→71 (n=102/35). BTC 1D 52→52, BTC 2D 52→51 —
**no edge on BTC**. ETH 3D and 5D give no reading; they almost never fire alone.

A pooled figure across both assets reads as +12 everywhere and is wrong.

### 6. Regime gate on
`R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)`. Not optional and not a
tiebreaker — every number on this page is measured inside regime-on periods.
Known blind spot: episode 2021-08-19 → 2022-01-25 stayed ON through the November
2021 top, and troughs 60–150 days into it went 3-for-35.

---

## Promising — passed some guards, not Tier 1 yet

### BTC 3D signal already confirmed within 10 days before an ETH 1D / 2D signal
*Tested 22 Oct 2026, declared in `analysis/xconf.py`.* Reach +20% in 60 days:

| | with BTC 3D | without | n with / without | years positive |
|---|---|---|---|---|
| ETH 1D | **73%** | 55% | 95 / 193 | 9 of 10 (2017 −17) |
| ETH 2D | **77%** | 56% | 39 / 98 | 6 of 9 testable, small n |

Not collinear with ETH's own agreement: inside ETH-agreement 0–1 it is
66% vs 56% (1D) and 74% vs 53% (2D); inside 2+ it is 79% vs 48% (1D) and 80%
vs 64% (2D). ETH 1D also holds at a 5-day window (74% vs 58%). **ETH 2D does
not** (65% vs 62% at 5 days), and both fade at 20 days (+9, +8). That window
sensitivity on 2D is why this is not Tier 1. Date-anchored by construction, so
the per-year split is the real test; it passes on 1D.

---

### ETH 2D signal already confirmed within 10 days before a BTC 1D signal
*Tested 23 Oct 2026, declared in `analysis/xmap.py` (32-cell map, 2 passed).*
BTC 1D reach +20% in 60d: **60%** with (n=136) vs 44% without. Ahead in 7 of
9 years; positive inside BTC's own agreement 0-1 (+12) and 2+ (+24); +7 at a
5-day window. The mirror of the BTC 3D -> ETH 1D cell above, which the same
map reproduced (73% vs 55%, 7 of 8 years). One of 32 cells, so treat as a
candidate. Near miss: ETH 3D -> BTC 1D (+7, 6 of 9 years, both strata
positive). Every other cell failed, including BTC 1D/2D/5D -> ETH 1D.

---

### Higher-timeframe CT rising — the asset's 8D CT RSI up on its last completed bar
*Tested 23 Oct 2026, `analysis/sweep.py`: cut on 2016-2021, checked on 2022-26.*
Reach +20% in 60d: 72% vs 59% (discovery), 49% vs 34% (holdout). 7 of 8
charts, 8 of 10 years; fewer -20% touches (-13 / -10). **Adds nothing on top of
Tier 1 #1** (gap>5 signals: 70% either way) but lifts the rest: gap ≤ 5
signals 60% with it vs 46% without.

### Shallow pullback — entry close near its 30-day high (top third per chart)
*Same sweep.* 81% vs 55% (discovery), 45% vs 37% (holdout), 8 of 8 charts,
but only 5 of 8 years. Mostly the same thing as Tier 1 #1 (almost every gap>5
signal is a shallow pullback); among gap ≤ 5 signals it is 64% vs 49%, with
-20% touches 27% vs 51%.

---

## In-trade reads — information for the discretionary exit, not exit rules

**Not an entry rule.** Measured from the price you would actually pay
(`analysis/delayed.py`, 23 Oct 2026), waiting for day 5 / day 10 and buying
only if green costs +3% to +10% on the entry and leaves only +1 to +7 points of
reach-+20%: 2022-26, confirmation entry 42%, buy green on day 5 45%, on day 10
44%. The day-10 gap is mostly where the trade already went. The entry
improvement that survives the same test is 8D CT rising: 49% vs 42%, -20%
touches 20% vs 25%, no extra price paid, half the signals.

*`analysis/sweep.py`, 23 Oct 2026.* Trades that had not already reached +20%
by the check day. Reach +20% within 60 days of entry, discovery / holdout.
Every one held on 8 of 8 charts and in 10 of 10 years, inside and outside
Tier 1 #1. Partly mechanical (a trade already down has further to climb), but
the size is the point.

| State at the check | +20% yes vs no (2016-21) | +20% yes vs no (2022-26) | -20% touch, yes vs no |
|---|---|---|---|
| Green on day 5 | 74% vs 50% | 52% vs 28% | 22 / 20 pts lower |
| Green on day 10 | 74% vs 40% | 55% vs 25% | 37 / 30 pts lower |
| Chart CT above its Signal line on day 10 | 75% vs 44% | 51% vs 28% | 33 / 22 pts lower |
| Price undercut the trough bar's low by day 10 | 39% vs 68% | 23% vs 50% | 36 / 23 pts higher |
| Down 10% or more by day 10 | 37% vs 71% | 14% vs 46% | 46 / 45 pts higher |

---

## Costs to price in before sizing

These are not filters. They are what the system charges regardless.

| | |
|---|---|
| **Confirmation lag** | 3 bars — 3 days on 1D, 6 on 2D, 9 on 3D, 15 on 5D, 24 on 8D. Costs **23.9%** of the available upside paid up front and **51%** of the move. |
| **Weekly diamond drawdown** | Median MAE **−18.5%** within 90 days of entry. 3 of 9 went past −30%. At 3.3x this is the liquidation question, not a cosmetic one. |
| **The flush is front-loaded** | Median 100% of the eventual drawdown lands in the **first two weeks** after entry. Expect it; it is not a sign the signal failed. |
| **Nothing marks the flush ending** | See failed list. There is no tested tell. |

---

## Failed — do not re-test

| Idea | Result | Tested |
|---|---|---|
| CT merely **crossing** above the Signal line | 60% vs 54%, and **−35 in 2022**. The cross is not the edge, the distance is | 22 Oct 2026 |
| Bullish divergence marking the end of the flush | **1 hit in 36 tests**, on both stochastic and CT RSI | 21 Oct 2026 |
| CT/Signal cross as a bottom-marker | Fires 19% above the low, 14 days late, with −14.8% still to come | 21 Oct 2026 |
| Money flow — MFI level, "money diamond" | No gradient; degrades existing tags when stacked | 19 Oct 2026 |
| Regime-age dead zone at 60–150 days | Artifact. 56/40/87/3/11% across episodes | 19 Oct 2026 |
| Inverted diamond as an exit | Median +2.2% vs +10.0% for holding | 19 Oct 2026 |
| Four other mechanical exits + the 50-line cross | All lose to holding. **Five rules, five failures** | — |
| Fibs, moving averages, Elliott counts, opens/closes | All empty | — |
| Compression agreement across BTC/ETH | Retracted — one measurement counted twice | 21 Oct 2026 |
| Green star / WGMI | Cannot be rebuilt; M2 data is revised after publication | — |
| Analog rating on CT/gap/K across 1D–5D, 14/30/60/90 days (`analysis/twoweek.py`) | Walk-forward: P(up) beats the base rate in no more than four testable years at any horizon (best 4 of 7); "+10% first" loses at every horizon on both assets; terciles invert at 60/90 (ETH) and 30 (BTC); answers flip with the feature subset. Blind replication agreed. Use the regime-on base rate | 22 Oct 2026 |
| Perp positioning as a filter: funding negative / low / cooling, long/short ratio low or falling, open-interest washout or build-up (`analysis/derivtest.py`) | Nothing reaches 70% while keeping 80% of winners. OI washout flips sign between 2022-24 and 2024-26. Only stable read is a caution: funding cooling or below its 90d median at entry runs 7-17 pts worse | 23 Oct 2026 |
| Sweep 23 Oct 2026 (`analysis/sweep.py`), killed by the 2022-26 holdout or by chart/size rules: volume spike at the trough, long lower wick, third+ signal in 30 days, long gap since last signal, rebound already paid, high realised volatility, extended above the 200d average, above own 200d average (+7 then -30), 8D CT >= 50 (+7 then -21), asset oversold vs the other (-11 then +13), asset leading the other. Near misses, not passed: volume rising into confirmation (+7 / +15), other asset CT above its Signal (+7 / +10) | 23 Oct 2026 |
| Gate blind-spot overlays: BTC > 200d SMA, bull zone revisited in 60d, BTC within 25% of 1y high, faster 8-bar exit (`analysis/gatefix.py`) | All failed a declared accept rule. Closest: 25%-off-high, removed 50% vs kept 58% (needed 10 pts). They cut normal bull-correction signals along with the top ones | 23 Oct 2026 |
| CTZB signals on the ETH/BTC ratio (`analysis/ethbtc.py`) | No tag beats "ratio CT below 40" on its own; all signals at baseline on 1D/2D/3D. The oversold lean is the RSI level, not the setup | 23 Oct 2026 |
| Forecast cone / vol-scaled range as a trading tool (`pine/ctzb_forecast_cone.pine`) | Bands calibrated (~50% / ~90% over all ETH history) but no direction; median is price shifted forward. Not useful to trade from — set aside | 22 Oct 2026 |

---

## Theory-craft — explicitly not supported by data

Kept because it is worth watching, flagged because it has no statistics behind
it. Do not present any of this as a tested result, and do not let it override
Tier 1.

- **The last-cycle BTC fractal overlay.** Aligned on the cycle high and the
  double bottom. Points lower before it points up. Fractals are not tested TA;
  there is confluence, and that is all there is.
- **Three moving averages and a fib extension still underneath price.** The
  observation stands on its own; fibs and MAs have both failed as filters here.
- **2D stochastic bullish divergence helping CT break the 50 line.** Tested as a
  flush-end marker and failed (1 of 36). Untested in this specific framing.

---

## Methodology guards

Four of these came from a result that did not survive contact with them.

1. **Split by chart before believing anything.** An ETH 2D finding of 90%
   against a 43% baseline collapsed to a pooled 67%/50% with 3 of 10 charts
   inverted. One chart can carry a pooled figure on its own.
2. **Split by year.** The year baseline swings from 28% (2025) to 92% (2017).
   Cycle position dominates every feature in Tier 1. A filter that is not
   positive in most years is a year in disguise.
3. **BTC and ETH are one sample for anything date-anchored.** Their anchors sit
   0–4 days apart and their returns correlate 0.804. Cross-asset agreement is
   only evidence for features that are not tied to the calendar.
4. **Check for collinearity before counting two hits.** An EMA rises precisely
   when its input is above it, so "EMA slope positive" and "CT above EMA" are
   the same feature. A 21-feature grid contained ~17 independent tests.
5. **Declare the candidate list before running it.** Report the failures next to
   the hits. A filter found by poking at data already stared at for hours is
   manufactured.
6. **Baseline on regime-gated signals, not all troughs.** Otherwise the gate's
   own edge is counted twice.

---

## Running it

```
python3 -I -c "
import sys; sys.path.insert(0,'/home/claude/ctzb-data')
import engine as E, regimes as R
gate = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
sg, b = E.signals('data/ETH_2D.csv', regime=gate)
ct = E.rsi(b['close'], 14); em = E.ema(list(ct), 14)
i = len(b['close']) - 1
print('CT', ct[i], 'Signal', em[i], 'gap', ct[i] - em[i])
"
```

Weekly and anything above 8D is not in `data/` — those charts exist only as
TradingView exports in `data/tradingview/`, where column 9 is CT RSI and
column 10 is the Signal line directly.
