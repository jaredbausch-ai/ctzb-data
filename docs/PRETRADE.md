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

### A signals only: does CT close at 50 before it turns down? (26 Oct 2026, partial)

*`analysis/aclusters.py`, `analysis/areads.py`.* For an A signal (CT at the
trough below 40), watch the chart's CT after entry. Either it closes at 50 or
above first ("broke 50"), or it turns down from the 40-50 band first
("rejected"). Known around day 2-4. Trades not yet at +20% at that point.

| | Broke 50 first | Rejected first |
|---|---|---|
| ETH | 67% (30) | 43% (125) |
| BTC | 59% (39) | 38% (99) |
| 2016-21 / 2022-26, both assets | 88% / 49% | 44% / 39% |

Not the same read as the five above: inside green/red on day 10, CT above or
below its Signal on day 10, undercut or not, and down 10% or not, the gap stays
+10 to +32 points (both assets pooled; ETH +14 to +43). **Weaker than the five
above, so partial:** it failed its first declared rule because almost every
break comes with price already above entry; BTC loses the gap when green on
day 10 (-2); it reverses in 2019 and 2025; and only ETH/BTC 1D and 2D have
enough A signals to check by chart. Rejected-first is the common path, 224 of
293. Report it on A signals as context, not as a filter.

---

## Positioning read — report with every signal's statistics

`python3 -I analysis/posread.py --asset ETH --date <entry date>`. Funding versus
its 90-day median, funding direction, long/short ratio, open-interest change.
Caution only: funding below its 90-day median at entry ran 7-17 points worse in
both test periods; nothing from positioning met the 70/80 standard.

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
| Joe's extra-edge ideas (`analysis/joeideas.py`, declared): (1) adaptive cycle length (Ehlers dominant cycle, half or full cycle) for the momentum line and its stochastic; (2) Ehlers super smoother on the stochastic, period 3 or 10; (3a) entry when the gap between momentum and its stochastic starts closing; (3b) entry on the stochastic crossing up through momentum; (5a) weekly momentum rising | All failed their declared pass rules. (1) changes almost nothing: 95-100% of signals land within 3 bars of today's, win rates within 1-3 pts, better in both periods on 3/10 and 1/10 charts. (2) better prime/diamond on 0-2 of 10 charts. (3a) 29-44% of entries on lows that never confirm, at least as good on 1/10 charts. (3b) skips 23-42% of troughs, pays +1% to +25% more than the confirmation close, passes on 5/10. (5a) +4 / +2 pooled. Near miss, not adopted: (5b) weekly momentum above its signal line -- ETH 70% vs 55% (81/63, 53/43 by period), touched -30% 18% vs 33%, holds inside the chart's own momentum state; BTC 59% vs 46% but none of it in 2022-26 (36/36); only 4/8 charts ahead in both periods. Forward-watch candidate for ETH | 25 Oct 2026 |
| Hurst cycles, all forms (`analysis/fldtest.py`, `proj.py`, `hurstlow.py`, `hurstcal.py`, `hurstnest.py`; indicator `pine/ctzb_hurst_lows.pine` deleted by Jared) | FLDs are momentum with a cycle lookback. proj.py's "160D due" timed troughs of a filter that sit mid-range, not price lows. On real price lows, 160D DUE is flat at signals and flips by period; lows scatter by a third of a cycle or more; cycles have lengthened since 2022 (145-206 days between big lows); no route to a two-week window. CTZB signals already confirm 0-4 days after every big low; the window cannot say which signal is the big one. **Closed by Jared 27 Oct 2026** | 27 Oct 2026 |
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
- **The bounce between two A signals (26 Oct 2026, too thin to test).** In a
  run of A signals on one chart, the next A signal reached +20% 58% of the time
  (n=150) when the bounce since the previous one peaked under CT 50, and 17%
  (n=24) when it closed above 50. Only 24 cases, so it could not be checked
  inside the Tier 1 features (`analysis/areads.py`). Watch it; do not use it.

---

## Conviction grade — report with every signal (27-28 Oct 2026)

*`analysis/grade.py`, `grade2.py` (addendum), `grade3.py` (audit of every
documented read), all declared, with placebo checks on the added lenses.*
Not a filter: every signal is still a signal; the grade says how much history
supports it, for sizing. Grade = count of independent lenses present, equal
weights: C = 0-1, B = 2, A = 3, A+ = 4+. Applied daily by `grade_live.py`;
shown on the dashboard.

**ETH lenses (6):** CT > Signal by 5+; entry above the previous signal; 2+
other ETH charts confirmed 0-10 days before; BTC 3D confirmed 0-10 days before
(1D/2D); funding at or above its 90-day median; funding not cooling (7-day mean
at or above its level 14 days earlier). The two funding lenses passed the
overlap test as separate reads, but both are funding: an A that rests on
both is worth reading as one funding star plus the rest.

| ETH grade (2020 on) | per year | +20% in 60d | worst plausible | touched -30% | median dip (60d) | median dip before the high | 1 in 4 dipped past | 1 in 10 dipped past | worst on record | median max upside | top-quarter upside |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A+ | 17.3 | 75% (104) | 66% | 7% | -10.9% | -5.5% | -18.6% | -27.1% | -57.0% | +34.9% | +68.3% |
| A | 10.2 | 62% (61) | 50% | 21% | -15.0% | -7.9% | -23.8% | -35.3% | -50.5% | +28.5% | +56.3% |
| B | 13.5 | 53% (81) | 42% | 21% | -15.3% | -4.6% | -28.2% | -39.9% | -52.3% | +22.5% | +48.2% |
| C | 18.3 | 44% (110) | 35% | 30% | -16.4% | -6.1% | -33.4% | -41.6% | -52.2% | +15.1% | +53.1% |

**BTC lenses (3):** CT > Signal by 5+; 8D CT rising; an ETH 2D signal
confirmed 0-10 days before a BTC 1D/2D entry. BTC tops out at A.

| BTC grade (2016 on) | per year | +20% in 60d | worst plausible | touched -30% | median dip (60d) | median dip before the high | 1 in 4 dipped past | 1 in 10 dipped past | worst on record | median max upside | top-quarter upside |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 4.4 | 77% (44) | 63% | 7% | -7.9% | -3.9% | -15.9% | -27.3% | -39.9% | +42.0% | +58.0% |
| B | 14.3 | 56% (143) | 48% | 15% | -9.6% | -4.3% | -20.6% | -37.3% | -70.1% | +25.7% | +49.9% |
| C | 37.4 | 46% (374) | 41% | 14% | -11.9% | -4.8% | -26.5% | -32.8% | -62.3% | +17.5% | +47.0% |

**Flags beside the grade, not counted (ETH):** they passed the lens rules and
placebo but, counted as stars, broke the grade's ordering.
- Bullish Stoch divergence on a HIGHER chart, confirmed in the 10 days before
  entry: 74% (38), touched -30% 11%, against 56% and 21% without.
- A diamond or a prime dot: 66% (136), touched -30% 21%, against 53% and 19% without.

**Tried and not used (audit, 28 Oct):** CT above Signal + prime and + diamond
(-30% worse in one period); divergence on the signal's own chart (-30% worse
2022-26); shallow pullback and volume rising into confirmation (failed the
placebo); weekly momentum above its signal line (ETH: adds nothing once CT >
Signal by 5+ is known; BTC: failed the placebo); the other asset's CT above its
Signal (failed the per-period rule); 8D CT rising on ETH (adds nothing once the
higher-entry lens is known); same-asset agreement and higher entry on BTC (no
effect on BTC); an ETH 3D signal before a BTC 1D/2D entry (no effect in
2022-26; `analysis/grade4.py`).

Upside = the highest high within 60 days of entry (the best possible exit, not
a return; exits are discretionary). Worst on record is not worst possible.

---

## A second lens: volatility-scaled target (26 Oct 2026)

The headline win stays a fixed +20% in 60 days. Because the market moves less
each cycle, `analysis/voltarget.py` also measures a scaled target: +20% x the
365-day daily volatility at entry / the asset's 2016-21 median (about 12% in
2023-25). 2022-26 base rates rise from ETH 48% to 61% and BTC 36% to 59%;
2016-21 barely moves. Every ETH filter keeps a both-periods lift under it. On
BTC, higher entry and 2+ own charts lose their 2022-26 lift and CT > Signal by
5+ falls to +1. Use it to show the recent market fairly, not to re-select
filters.

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

**Grade of every signal, and of anything forming:** `python3 -I grade_live.py`
(runs in the daily Action). It writes `datasets/grades.csv` (each grade's
record) and adds `grade` / `lenses` to `datasets/forward.csv` and
`formingGrade` / `formingLenses` to `datasets/live.csv`. The dashboard's
"Conviction grade" section reads those three files. A forming grade is
provisional until the low confirms.

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
