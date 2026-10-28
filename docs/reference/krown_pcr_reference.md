# Krown PCR — reference points for calibrating our put/call build

From screenshots of Krown's video ("What the Signal Is: My Put/Call Ratio",
Krown Wire, around 27 Oct 2026), sent by Jared 27 Oct 2026. Read off images,
so dates are as labelled on his x-axis and values are approximate. Use these
to check that `fetch_pcr.py` + `analysis/pcrtest.py` land near his readings.
Do not treat any of this as a tested result.

## What his indicator is (as far as the images show)

- Panel "Krown PCR — BTC options: Deribit + ETFs". Rows: Data through, PCR
  (day), PCR (7d avg), Percentile (100d), Zone.
- The plotted line runs 0-100, so the line is the **100-day percentile**, not
  the raw ratio.
- Drawn on a **1W BTCUSD (Coinbase) chart**, one point per week.
- Shaded bands at roughly **95-100 (top, teal)** and **0-5 (bottom, red)**.
  83 reads "neutral", so the zones are the extremes, not quintiles.
- Red vertical lines mark his signal weeks. They line up with the line hitting
  the top band (put-heavy extreme) and with teal up-triangles under price at
  several weekly lows. Line segments are coloured teal / yellow / red, and
  there are teal triangles at peaks and red triangles at troughs of the line.
- His history reaches back to at least 2021, before US ETF options existed
  (IBIT options launched Nov 2024), so pre-2024 his ratio must be Deribit
  (or Deribit plus other crypto venues).

## Panel reading

| Data through | PCR (day) | PCR (7d avg) | Percentile (100d) | Zone |
|---|---|---|---|---|
| 2026-10-25 | 0.60 | 0.76 | 83 | neutral |

## Red-line (signal) weeks with a readable label

Partial list: more red lines are drawn than are labelled.

| Week (Mon) | Seen on |
|---|---|
| 2021-04-19 | price chart, 2021 |
| 2021-12-06 | price chart, 2021 |
| 2023-09-11 | PCR panel + price chart |
| 2023-12-18 | PCR panel + price chart |
| 2024-07-08 | PCR panel + price chart |
| 2025-03-03 | PCR panel + price chart |
| 2025-12-08 (one image labels 2025-12-15) | PCR panel + price chart |
| 2026-03-02 | PCR panel + price chart |
| 2026-04-06 | PCR panel |
| 2026-06-08 | PCR panel |
| 2026-08-03 or 2026-08-17 (one may be the cursor) | PCR panel |
| 2026-10-19 | PCR panel + price chart |

## How to use this once data/options/ is filled

1. Compute our BTC 7-day average and its 100-day percentile on 2026-10-25 and
   compare to 0.76 / 83. Our BTC number excludes ETF options, so a gap in 2025-26
   is expected; a gap in 2021-23 would mean a different formula.
2. Sample our percentile at each weekly close and list the weeks it reached 95+.
   Compare with the table above, 2021-2023 first (no ETF effect there).
3. If they line up, test whether he uses volume or open interest, and where his
   band edges sit, from the weeks that do not match.
