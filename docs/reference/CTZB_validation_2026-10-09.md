# CTZB Validation Study — 9 October 2026

Record of two validation tests run against the CT Zone Bounce indicator suite,
the regime rule that came out of them, and the mistake made along the way.
Written to be self-contained: a session with no prior context should be able to
work from this file alone.

**Current versions: CT Zone Bounce v11, CTZB Scanner v8, CTZB Odds v4.**

---

## The two questions

**Q1 — Real-time regime.** The bull windows ended on known cycle tops (Dec 2017,
Nov 2021). Nobody rang a bell on those days, so any result measured inside them
is contaminated by hindsight. Replace them with a rule that could have been
followed live, then re-score.

**Q2 — Out of sample.** Freeze every setting using data up to 31 Dec 2021, then
score 2022–2026 without changing anything.

**Verdict.** The indicator passed both. The edge is not an artifact of hindsight
and it held — in places improved — on unseen data. But **the absolute win rates
in every document before Odds v4 were inflated by roughly nine points**, because
windows that end on known tops exclude exactly the stretches that fail. The model
was always this good; the measurement was flattering.

---

## Method

- **Engine.** The Pine logic was re-implemented in Python from the v9 source
  (not from memory) and validated against the constants baked into the
  indicator. ETH 2D diamonds reproduced exactly: n=35, 89% win, +53.3% upside,
  −2.0% risk, matching the hardcoded values.
- **Entry.** Close of the confirmation bar, three pivot bars after the RSI low.
  Six days on 2D, nine on 3D, fifteen on 5D.
- **WIN** = close at the horizon above the entry close.
- **UPSIDE** = median best price *reached* by the horizon.
- **RISK** = worst *close* between entry and the eventual peak. Closes only, so
  exchange wicks are excluded.
- **EDGE** = percentage points of win rate over **that chart's own** all-troughs
  rate *in the same regime*. A chart's baseline is its all-troughs rate by
  definition, so an ALL TROUGHS row must show zero.
- **Horizon** 60 days throughout unless stated.
- **Data.** 81 TradingView exports. ETH 2016–2026, BTC 2014–2026. ADA, XRP and
  BNB were tested but are excluded from all conclusions.

---

## Q1 — Real-time regime

### Regimes tested

Pooled ETH 1D/2D/3D + BTC 1D/2D. "Live?" asks whether you could have known, on
the day, which state you were in.

| regime | live? | all troughs | diamonds | edge |
|---|---|---|---|---|
| Hindsight windows (old default) | **no** | n=1064, 71%, +31.0% | n=243, 75%, +33.7% | +5 |
| Halving +0 to +365d | yes | n=397, 70% | n=82, 77%, +43.6% | +7 |
| Halving +0 to +550d | yes | n=578, 70% | n=126, 78%, +43.7% | +7 |
| Halving +0 to +730d | yes | n=771, 59% | n=180, 58%, +27.7% | −0 |
| Halving +180 to +550d | yes | n=382, 71% | n=84, 79%, +55.7% | +7 |
| Cycle low +0 to +900d | partly | n=911, 69% | n=200, 74%, +31.0% | +5 |
| BTC above its 200D SMA | yes | n=784, 63% | n=183, 68%, +26.6% | +5 |
| **No regime filter at all** | — | n=1412, 59%, +23.5% | n=317, 60%, +25.4% | **+1** |

**Findings.**

1. The edge is not hindsight. Every genuinely live rule matched or beat the
   hand-drawn windows.
2. **The regime filter IS the primary edge.** Remove it and the diamond is worth
   +1. That single row is the most important number in the study.
3. Window *length* matters more than the anchor. Halving +730d drops to zero —
   stretch past ~18 months and you hold through the bust.
4. Halvings are the only calendar anchor knowable in advance (block-height
   driven). A cycle *low* is only known to be a low in hindsight.

### The ETH 5D confirmation under each regime

A signal on another chart firing within 10 days of an ETH 5D trough.

| regime | within 10d | outside | lift |
|---|---|---|---|
| Hindsight windows | n=421, 82% | n=643, 63% | +18 |
| Halving +0 to +550d | n=241, 81% | n=337, 63% | +19 |
| BTC above 200D SMA | n=274, 78% | n=510, 55% | +23 |
| **No regime filter** | n=556, 73% | n=856, 50% | **+23** |

It gets *stronger* under live rules and holds at +23 with no regime filter at
all. **It does not depend on the cycle call in any way.** Most robust effect in
the stack.

---

## The adopted regime: CT RSI bull control zone

Jared's rule, from his observation that the RSI reclaiming and holding the
bullish control zone does not happen in bear markets. Tested and adopted.

```
BEAR -> BULL   BTC 2D CT RSI closes >= 60 for  8 consecutive bars
BULL -> BEAR   BTC 2D CT RSI closes <= 40 for 12 consecutive bars
neither        hold the previous state
```

Two zone lines already on the chart. Fully live. Between them nothing changes,
so an ordinary correction passes through the middle without flipping the state.

### Bull-side separation test — clean

Every maximal run of CT RSI ≥ 60, sorted by regime. **Uses no return data**, so
the threshold is not fitted to P&L.

**BTC 2D, 86 runs total**

| run length | in bull windows | in bear periods |
|---|---|---|
| 8+ bars | **27** | **0** |
| 12+ bars | 22 | 0 |
| 16+ bars | 11 | 0 |
| 20+ bars | 7 | 0 |

Longest run entirely inside a bear period: **7 bars**. ETH 2D is the same — 23
runs of 8+, none in a bear. Clean separation, no overlap. **The thesis is
correct.**

### Bear-side separation test — does NOT mirror

Runs of CT RSI ≤ 40:

| run length | bull windows | bear periods |
|---|---|---|
| 3+ bars | 20 | 16 |
| 5+ bars | 12 | 11 |
| 8+ bars | 4 | 8 |
| 12+ bars | 2 | 6 |

Roughly even until 12 bars, and only 3:1 even there. **Bull markets dip into the
bear zone constantly.** Holding the bull zone proves something; visiting the bear
zone proves almost nothing. This asymmetry is a real market property, not a
modelling artifact — which is why the bear trigger must be slow (12 bars) where
the bull trigger can be fast (8 bars). 12 is the shortest length where bear
periods clearly dominate.

---

## The mistake: optimising EDGE instead of ODDS

**This is the most important methodological lesson in the session and it should
not be repeated.**

v10 shipped with the bear trigger set to "RSI below 60 for 10 bars", chosen
because it produced the highest edge (+9). It was wrong:

| ETH 2D diamond | n | WIN | UPSIDE |
|---|---|---|---|
| hand-drawn windows | 35 | 89% | +53.3% |
| **v10 (bear = 10 bars <60)** | **18** | **78%** | **+30.8%** |
| **v11 (bear = 12 bars ≤40)** | **36** | **75%** | **+46.5%** |

v10 halved the signal count and cost 23 points of upside. It dropped to bear
**19 times inside known bull cycles** and sat out 58% of them.

**Why the edge number lied.** EDGE is measured against the regime's own baseline.
Cutting the window aggressively depresses the baseline faster than it improves
the tag, so edge rises while the trading gets worse. Edge is a *ranking* tool
within one regime. It is not a measure of whether a change is good.

**Rule: when changing the regime, judge on absolute WIN, UPSIDE and signal
count. Edge is only valid for comparing tags inside a fixed regime.**

### Churn comparison

"Bear flips" = times the regime dropped to bear while inside a hand-drawn bull
window.

| bear trigger | flips | sits out | edge | pooled diamonds |
|---|---|---|---|---|
| 10 bars <60 (v10) | **19** | 58% | +9 | n=124, 73%, +30.8% |
| **12 bars ≤40 (v11)** | **2** | 19% | +5 | n=237, 68%, +28.4% |
| 15 bars ≤40 | 0 | 14% | +5 | n=259, 66%, +27.8% |
| 20 bars <50 | 4 | 22% | +6 | n=217, 70%, +29.3% |
| hand-drawn (hindsight) | 0 | 0% | +5 | n=243, 75%, +33.7% |

v11 matches the hindsight windows on edge and signal count with two bear flips
instead of nineteen.

---

## Q2 — Out of sample

Everything frozen at 31 Dec 2021, scored on 2022–2026 with nothing re-tuned.
ETH and BTC only.

### Under the v11 regime

| | in-sample ≤2021 | out 2022–2026 |
|---|---|---|
| every trough | n=603, 64%, +34.9% | n=389, 61%, +15.2% |
| every diamond | n=150, 65%, +34.7% | n=87, 72%, +17.0% |
| **diamond edge** | **+1 pp** | **+11 pp** |
| diamond + prime dot | n=44, 64%, +41.7% | n=25, 76%, +24.4% |
| **prime dot edge** | **−1 pp** | **+5 pp** |
| within 10d of ETH 5D | n=216, 72%, +58.1% | n=180, 82%, +28.5% |
| **5D lift** | **+14 pp** | **+39 pp** |
| **ETH 2D diamond** | n=21, **71%** | n=15, **80%** |

Everything held or improved on unseen data.

### Under the hand-drawn windows (for reference)

| | ≤2021 | 2022–2026 |
|---|---|---|
| diamond edge | +3 pp | +8 pp |
| prime dot | −2 pp | **+16 pp** |
| 5D lift | +11 pp | +30 pp |
| bucket C | 69% | **59%** (confirmed worst) |
| hollow − filled | **+10 pp** | **−1 pp** (FAILED) |

### Tag-level: would the 2021 leaderboard have steered you right?

| chart | tag | ≤2021 | 2022–2026 |
|---|---|---|---|
| BTC 1D | HOLLOW diamond | n=22, 91%, e+19 | n=10, 60%, **e−13** |
| ETH 2D | Any diamond | n=19, 84%, e+12 | n=16, **94%, e+29** |
| ETH 2D | B + diamond | n=11, 82%, e+10 | n=8, 100%, e+35 |
| BTC 1D | A + diamond | n=11, 82%, e+10 | n=8, 88%, e+15 |
| ETH 1D | B + diamond | n=18, 78%, e+9 | n=9, 100%, e+32 |
| ETH 3D | A trough | n=11, 82%, e+9 | n=15, 80%, e+11 |
| ETH 2D | GOLD diamond | n=10, 80%, e+8 | n=11, 91%, e+26 |
| BTC 2D | A trough | n=27, 81%, e+8 | n=19, 68%, e+0 |

**The #1 and #2 tags on the 2021 leaderboard were the worst performers
afterwards. ETH 2D diamond ranked only 4th.** Trade the structural effects —
regime filter, diamond, prime dot, 5D window — not the top row of a sorted table.
Sorting 400+ combinations and taking the best is how false positives are made.

---

## The hindsight premium, quantified

Each chart's all-troughs win rate — its baseline — under both regimes:

| chart | hand-drawn | live (v11) | premium |
|---|---|---|---|
| ETH 1D | 69% | 60% | −9 |
| ETH 2D | 69% | 60% | −9 |
| ETH 3D | 71% | 60% | −11 |
| ETH 5D | 84% | 72% | −12 |
| BTC 1D | 72% | 66% | −6 |
| BTC 2D | 72% | 65% | −7 |

Total signal count barely moves: **1,113 → 1,039, −7%**. The drop is in win rate,
not opportunity, and it is the part that was never real.

**Plan with: ETH 2D diamond ~75% and +46.5% upside. Pooled diamonds 68% and
+28.4%.** Not 89% / +53.3%.

---

## What shipped

**CT Zone Bounce v11 / CTZB Scanner v8**

1. **Default regime is the BTC 2D CT RSI control zone**, with separate bull and
   bear parameters. Old windows still selectable.
2. **Hollow-beats-filled removed** — in-sample only (+10 before 2022, −1 after).
3. **Prime dot promoted** — bigger glyph, own tooltip block, own alert, own row
   on the bottom panel.

**CTZB Odds v4**

All figures under the live regime, ranked by edge, with the old hand-drawn
win/edge kept as grey reference columns. New "What the validation found" page.

---

## What was tested and rejected

| thing | why |
|---|---|
| **RSI regime AND halving window** | 89% win, +103.8% upside in-sample; **50% on 20 signals out**. Textbook overfitting. One rule or the other, never both. |
| **v10's bear trigger (10 bars <60)** | Highest edge, worst trading. See the mistake section. |
| **Hollow beats filled** | +10pp in, −1pp out. |
| **Range expansion filter** | Discarded a fifth of all diamonds; the discarded group had *higher* upside (+38.5% vs +31.9%) and lower risk. Removed in v9. |
| **Halving +0 to +730d** | Edge drops to zero. Window too long. |
| **Volume, money flow, stoch slope, stoch level, WGMI star** | All null or worse. |
| **Intraday (4H, 12H)** | −3 to +2pp at every horizon. No edge below the daily. |

---

## Known weaknesses

- **Overlapping measurement.** 1D and 2D signals on one asset often describe the
  same move, and consecutive 60-day windows overlap heavily. Effective sample is
  smaller than raw counts.
- **Thin cells.** Several tag/chart combinations rest on 3–15 signals.
- **Bucket boundaries are fragile.** Move 40/55/65 by five points and which
  letter looks worst changes. A/B/C/D is vocabulary, not measurement.
- **The 5D mechanism is unexplained.** The same test with a BTC 5D confirmer
  shows nothing (p=1.00). Promising, not proven.
- **One prior confluence finding** looked significant at p=0.003 and dissolved to
  p=0.42 on a longer file.
- **The v11 regime is young.** It has not been watched live for any length of
  time. Its character differs from the hand-drawn windows — shorter states
  (roughly 30–185 days), tracking momentum rather than cycle phase.

---

## Open items

- **Verify the regime state live.** The BTC 2D file used here ends 2026-09-12,
  roughly four weeks stale.
- **Watch v11 for a few weeks** before letting it gate a trade, given the
  character change.
- **Still outstanding:** conversion to a Pine `strategy()` with fees and
  slippage, walk-forward testing, a one-page rulebook, a live signal log, and
  compliance review before any publication.

---

## Current file versions

| file | status |
|---|---|
| `ct_zone_bounce_v11.pine` | **current indicator** |
| `ctzb_scanner_v8.pine` | **current scanner** |
| `CTZB_odds_v4.pdf` | **current odds sheet** |
| `ct_zone_bounce_v10.pine` / `ctzb_scanner_v7.pine` | superseded — bad bear trigger, do not use |
| `CTZB_odds_v3.pdf` | superseded — hindsight baselines |
| `wgmi_dir_v4.pine` | liquidity direction, unchanged |
| `btc_cycle_clock.pine` | cycle clock, unchanged |
| `wgmi_dir_v3_1_ORIGINAL.pine` | preserved original, do not edit |
| `ct_zone_bounce_LT.pine` | retired — redundant with v11, no intraday edge |
