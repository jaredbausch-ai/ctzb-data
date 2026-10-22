# CTZB — read this first

Start every session here, then `docs/PRETRADE.md` — the filter checklist to run
before a position goes on, with every validated filter's odds, the failed ideas
that must not be re-tested, and the methodology guards that killed four
findings. This file exists because conversations get compacted
and the assistant loses everything that is not written down. If you are an
assistant picking this up cold: read this file, then `README.md`, then the
docstrings in `engine.py`, `troughs.py` and `odds.py`. Do not re-derive
definitions from a chat summary, and do not invent a second definition for
something that already has one here.

This repository is the permanent record. The chat is not. Anything worth
keeping gets committed, because git history is the version archive — every
published version of every document is recoverable with `git log -- <path>`.

## Who and what

Jared Bausch trades the CTZB (CT Zone Bounce) setup on ETH and BTC, long only,
around 3.3x leverage, 35–40% of account per position. He hand-tests every
entry. **Exits are discretionary and deliberately so** — fibs, moving averages,
divergence, macro, and two long-followed traders whose agreement he weighs.
Four mechanical exits were tested and all lost to simply holding, as did his
own 50-line cross. Do not propose an exit rule as if it were an open question;
it has been answered. The consequence, which must be stated whenever results
are presented: this work measures **entry quality only**. It cannot produce a
strategy return or a track record, because there is no exit in the data.

Joe Mauro is a creditor doing due diligence. He has his own Coinbase API and
CoinStats read access and an AI reading a shared dashboard link. Anything
presented to Joe must be real-time knowable and must not be dressed up.

### Joe — state as of 22 Oct 2026

Access he holds: read-only Coinbase API key, created 2026-10-04, nickname
"Joe". CoinStats API key, sent 15 Oct, confirmed working by him the same day.
**The CoinStats key is not to be rotated** — settled, do not raise it again.
A live credential never goes into a thread his bot parses; if he needs one
resent it goes as its own message.

Figures that have been settled in writing, so do not re-derive them from
scratch or contradict them:

| | |
|---|---|
| The $1,036 gap in the 4.669 BTC reconciliation | CoinStats booked the 23 Mar transaction **gross, not net** — a $949.69 fee. Closed |
| The $532K vs $664K gap | 1,500 CRCL **shares** (not $1,500), cost basis $99,750, worth roughly $130K. Closed |
| Coinbase vs Aave | Coinbase is the larger side: roughly $662K against Aave's ~$507K net. Do not state it the other way round |
| The $444,142 trail | Replied in full and sent |

Sent this session: the old-ETH-wallet reply (offering MetaMask/Ledger recovery
if he has seed phrases), the $444,142 trail, a five-sentence stablecoin /
GENIUS Act summary, the BTC-and-ETH setup summary written for his AI, and the
CoinStats-key-plus-Aave follow-up. **Open on his side:** whether both API keys
actually reach his bot, and an IP allowlist address. He has not come back yet.

HARD LINE, stated to him and to be maintained: **no fabricated transaction
record, and no help constructing an account of where the 4.669 BTC went.**
Reconciling real exports he supplies is fine. Generating records is not.

He is funnelling every email into his own AI, so keep them short and
parseable, and label theory-craft as unsupported rather than risk being
fact-checked on it. He does not want daily tedious tasks; he is comfortable
with the AI monitoring spending and does not want to hand-assemble bank
statements.

## Confirmation lag

The symbol fires three bars after the RSI low, so the calendar lag is three
times the bar: 3 days on 1D, 6 on 2D, **9 on 3D**, 15 on 5D, 24 on 8D. Verified
across every chart; the only exceptions are single instances caused by
irregular bar gaps in the data.

## The setup

CT RSI = `rsi(close, 14)`. Stoch = `sma(stoch(ct, ct, ct, 14), 3)` — the
stochastic of the RSI series, not of price. A trough is a pivot low on `ct`
with 3 bars either side, strictly lower on both. **Entry is the close of the
confirmation bar, `ei = ti + 3`** — three bars after the trough, not the
trough bar. Every row's date field is that confirmation date, not the trough
date.

| tag | rule |
|---|---|
| bucket A/B/C/D | `ct[ti]` < 40 / < 55 / < 65 / else |
| diamond | `ct` and `K` moved opposite ways vs the **previous trough**, where the previous-trough chain runs over *all* troughs, gated or not |
| filled vs hollow | diamond with `ct[ti]` < 50 is filled; ≥ 50 is hollow |
| prime dot | `20 <= K[ti] < 50` |

## Regime gate — use the mechanical one

`R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)`.

There is also a set of hand-drawn bull windows in `engine.BULL`, and
`engine.signals()` still falls back to them when `regime=` is omitted. **Do not
use them for anything presented as a result.** They were drawn knowing where
the bull markets were, so every rate built on them is flattered. They disagree
with the mechanical gate on roughly 50 signals per chart. The first version of
the odds sheet used them; it was regenerated.

## Traps that have already bitten, do not re-introduce

**Exchange flash prints.** Coinbase's feed carries a $0.06 low on BTC
2017-04-15 against a $1,173 open, and $0.10 on ETH 2017-06-21 against $325 —
the GDAX cascade, largely reversed by the exchange. Genuine venue records, but
seconds long, and no position transacted there. Left raw they make five rows
read as a 100% drawdown. `engine.load()` clamps them (`_declamp`), as does
`refresh.py` (`_declean`); both use the same 0.5-of-body threshold and both
return the clamp list. Keep them in sync.

**A drop after the high is not a wipeout.** Counting any −30% at any point
flags 104 of 138 ETH 2D troughs, because held long enough nearly every entry
eventually prints one. That measures holding period, not entry quality. The
`dead` field only counts a −30% that lands *before* the trough gives back 5%.

**Unbounded upside measures the asset, not the setup.** With no time limit a
2016 trough reports +21,435%. `umx` is bounded to 365 days.

**The confluence window peeks forward.** `ds_confluence` in `refresh.py` scores
agreement on `abs(days) <= 10`, which credits a chart that prints up to ten
days *after* entry. 627 of 979 rows score higher under it than they could have
at entry. The reach-+20% gradient across agreement levels collapses from
44%–79% to **52%–64%** once only prior prints count. `troughs.py` carries both:
`cf` (backward only, trade from this) and `cfs` (symmetric, kept so the sheet
reconciles with the dashboard). The dashboard still uses the symmetric one and
is inflated accordingly.

**The green star / WGMI tag cannot be rebuilt.** It was diamond + WGMI liquidity
timing below zero. `docs/reference/CTZB_tag_reference.pdf` states in its own
limitations that the M2 data is revised after publication, so those figures were
never knowable on the day the signal fired. It was an upper bound, not an
estimate. Do not reconstruct it; do not promise to.

**A high before the wipeout is still a high.** The sheet strikes through a
60-day high only when `d60 > dead` — when the high landed *after* the position
was already closed. Striking every row that was ever wiped out marked 114 rows
instead of 22, and most of those had made their high first and were perfectly
reachable. Jared caught this one.

**Price transforms keep failing; different axes keep working.** Fibs, moving
averages, Elliott wave, opens/closes and now money flow have all come back
empty. The two things that have worked — the regime gate and cross-timeframe
agreement — are not transforms of the same closes. Weigh new ideas by that test
before spending a night on them.

**Scratch dies.** Two generators were lost that way. Anything that produces a
number someone will look at twice goes in this repo.

**The indicator was not in version control until 22 Oct 2026.** For two weeks
this repo held `engine.py` — the Python reimplementation — and the scanner, but
not `ct_zone_bounce_v15.pine`, the 751-line source that actually paints the
chart. It survived only in an uncommitted working directory that a container
reset would have taken. It is now in `pine/` with its whole lineage. The lesson
generalises: before trusting that the repo is complete, look for working
directories outside it. Three were found on 22 Oct — `/home/claude/w`,
`/tmp/*.csv`, and the session scratchpad — holding the indicator, three trade
logs and every generator from the CT/Signal work.

## Where things live

| | |
|---|---|
| `engine.py` | indicator, signal detection, candle loading and clamping |
| `regimes.py` | the mechanical regime gate |
| `refresh.py` | builds `datasets/*.csv` for the dashboard; run by the Action |
| `troughs.py` → `troughs.json` | one row per trough, 996 rows, 6 charts |
| `odds.py` → `odds.json` | aggregate odds by chart and tag |
| `waves.py` | swing segmentation and Elliott counts |
| `fetch.py` | candle fetch, including 4H/12H |
| `pine/` | **every Pine source**, indicator and scanner. `ct_zone_bounce_v15.pine` is the live indicator; `ctzb_scanner_v9.pine` the live scanner. See its README |
| `analysis/` | generators for every figure quoted, plus `RESULTS_*.txt` captures. See its README |
| `analysis/legacy/` | the 9-16 Oct generation behind the published v3/v4 odds pages. Figures there predate the current gate and the backward-only confluence window |
| `docs/PRETRADE.md` | the pre-trade filter checklist — validated, failed, theory-craft, guards |
| `docs/PROJECT_INSTRUCTIONS.md` | the block pasted into the Claude project's custom instructions |
| `docs/artifacts/` | published pages, committed so git keeps every version |
| `docs/reference/` | source documents |

The refresh Action runs six times a day at 01:20, 05:20, 09:20, 13:20, 17:20
and 21:20 UTC. Coinbase is unreachable from the Claude container but works from
a GitHub Actions runner, which is why the pipeline is built this way.
`GH_TOKEN` in the container is invalid; mint working credentials with
`add_repo` using `access: "push"`.

## Live artifacts

| page | url | notes |
|---|---|---|
| CTZB odds | `claude.ai/artifact/L89GjbqYZcyPxAkzC4jRha` | his. Trough record grouped by marker |
| ETH at Day 48 | `claude.ai/artifact/U9DcJovkbFGQyrxULme8Cf` | his. The 20 Oct odds/scenario page, v2. Source `docs/artifacts/eth-day-48.html`. Figures are hardcoded and dated; it does not refresh |
| Setup Standard draft | `claude.ai/artifact/8ViZjND99xmo8rbcUmmr5r` | Standalone copy, for editing and review. Source `docs/artifacts/joe-console.html` |
| ETH Setup Standard (Joe's) | `claude.ai/artifact/6tH6hXMh3EYLvUUEM9XgSJ` | **Joe has this link.** Dashboard type; page content lives in the artifact DB at collection `files`, doc `index.html`, field `text`. Update via `ArtifactData` with `if_version` pinned |

The dashboard's live signals are **computed signals, never fills**. Jared has
taken none of them. Presenting them to a creditor as trades would be
misrepresentation.

## What has been tested and failed

**Confluence lift is ETH-only — measured 19 Oct 2026.** Backward-only agreement,
2+ other timeframes already printed vs 0-1, reaching +20% in 60 days:
ETH 1D 58->67 (+9, n=205/83), ETH 2D 59->71 (+13, n=102/35), BTC 1D 52->52 (+0,
n=194/85), BTC 2D 52->51 (-1, n=92/49). ETH 3D and 5D give no reading because
they almost never fire alone (77 of 87, 47 of 47 already have 2+ agreeing), so
there is no lone-signal group to compare against. **A pooled figure across both
assets reads like a +12 edge everywhere and is wrong** — an earlier framing in
this session made that mistake before the split was run. Carried on the scanner
as its own CONF column, deliberately not folded into the ODDS number.

**CT RSI distance above the Signal line — tested 22 Oct 2026, WORKS. Best
single filter found.** The Signal line is the orange line on the indicator and
it is `ta.ema(ct_rsi, 14)` — fitted with zero error over 1,879 ETH 2D bars.
Reaching +20% in 60 days, 993 regime-gated signals across 9 charts, pooled
baseline 54%:

| | n | +20% | edge |
|---|---|---|---|
| gap > +5 points | 204 | 68% | +15 |
| above the line AND prime dot | 109 | 72% | +19 |
| above the line AND diamond | 110 | 67% | +14 |
| above the line, nothing else | 517 | 60% | +6 |

gap>5 is positive in 9 of 9 testable years and 7 of 9 charts (ETH 2D 87/62,
BTC 1D 71/52, the two misses are BTC 3D 50/51 and ETH 5D 69/70). prime is 8 of
9 years, diamond 8 of 8.

**The distance is the edge, not the cross.** Merely being above the line is
+6 and lost 35 points in 2022 — that one is noise. Do not treat a cross as a
trigger; it was separately tested as a bottom-marker and fires 19% above the
low, 14 days late, with −14.8% still to come.

CAVEATS that belong with the figures. The three cuts overlap heavily — gap>5
and prime share 48 of 204/109, gap>5 and diamond 38 — all require CT above the
line, so this is one condition read three ways. The walk-forward gate never
bound: all three qualified in every year, zero skipped, so it is a year-by-year
stability test and not a true out-of-sample result. And of the 21 declared
features, G/O were mathematically identical to A and H/R to B, because an EMA
rises exactly when its input is above it — ~17 independent tests, not 21.

**Higher low vs the previous signal — tested 19 Oct 2026, WORKS.** The one
cluster feature that survives. Compare this signal's entry close to the
*previous signal's* entry close on the same chart. Higher: ETH 69% reach +20%
(n=292), BTC 57% (n=236). Lower: ETH 52% (n=263), BTC 45% (n=182). Monotonic
across bands from -20% to +15%, and it passes on both assets, which the grind
zone (ETH +19, BTC +2) and money flow did not. Stacked: diamond+dot with a
higher entry is 78% (n=46) against 55% for the same tag with a lower entry.
Reading: a cluster stepping up is a base; a cluster stepping down is a
descending staircase and the indicator fires on every step because it only
sees RSI shape. Below -30% vs the previous entry it inverts to 81% on ETH
(n=21) -- capitulation, not a staircase, but thin.

INDEPENDENCE CONFIRMED 19 Oct 2026. Every trough in the record already passed
the regime gate, so this is measured inside regime-on periods and cannot be
restating the gate. Stratified by how long the regime had been continuously on
at entry, the step-up/step-down spread runs +3 (0-60 days), +6 (60-150),
+15 (150-300), +19 (300+). It is a LATE-regime filter: useless when a regime
is fresh and everything bounces, worth 19 points deep into one. Near
independent of the agreement count too -- both features co-occur 26% of the
time against 21% expected by chance -- so the two stack.

**Regime age -- tested 19 Oct 2026, ARTIFACT. Do not use.** The apparent dead
zone at 60-150 days into a regime (36% against a 57% baseline, n=169) does not
survive being broken out by regime episode: 56% / 40% / 87% / 3% / 11% across
the 2016, 2019, 2020, 2021 and 2023 episodes. The same band ran 87% in the 2020
episode. Two windows drag the pooled figure down, Aug 2021 - Jan 2022 at 3% and
Apr - Jun 2023 at 11%.

METHOD NOTE worth keeping: ETH and BTC agreed closely here (38% and 36%), which
looked like cross-asset confirmation and was not. Both assets live through the
same calendar, so for any effect anchored to dates they are one sample, not two.
That check is only meaningful for features that are not time-anchored -- it was
real for the higher-low filter and worthless for this.

**The regime gate has a cycle-top blind spot -- found 19 Oct 2026, untested.**
Regime episode 2021-08-19 to 2022-01-25 stayed ON straight through the November
2021 cycle top, and the 35 troughs that fired 60-150 days into it went 3-for-35
(3%). This is a weakness in a filter already relied on everywhere, not a new
filter. Worth a session of its own.

**Analog market-state rating, 14/30/60/90 days — tested 22 Oct 2026, no
skill.** `analysis/twoweek.py` matches today's live CT/gap/K on 1D/2D/3D/5D
against every regime-on day and reports the next H days. Declared before
running (14 days first, then a second declared block for 30/60/90), with a
walk-forward test as the guard. P(up) beats the regime-on base rate in no more than
four testable years at any horizon on either asset (best: 4 of 7). "+10% first" loses to the base
rate at every horizon on both. Forecast terciles invert at 60/90 on ETH and at
30 on BTC. The answer also flips with the feature subset. The base rate is the
honest number at every horizon; analog figures are theory-craft.

Independently replicated the same day by a blind re-implementation that never
saw the script. Live state, every base rate at every horizon, the analogs and
the BTC walk-forward match exactly. The ETH walk-forward Brier differs in the
fourth decimal because twoweek.py waits 30 bars before using a chart's features,
which drops five ETH days in October 2016 (pool 2,530 vs 2,535). No conclusion
changes. The live-state reconstruction (forming bars stepped exactly as
TradingView paints them) equals the completed bar on every bar's last day and
matched the board to the decimal, so the script is kept for that.

**The rating replayed over the last year — 22 Oct 2026.** `analysis/lastyear.py`.
The gate was on for only 94 of the 365 days (to 5 Dec 2025, then from 3 Sep
2026). On the 22 Oct - 5 Dec 2025 stretch every forecast leaned up (base rate
54-67% up) and the market fell: realised up 29% at 14 days, 16% at 30, 27% at
60, 0% at 90 on ETH, with all 90-day outcomes below the forecast's 25th
percentile. On the Sep-Oct 2026 stretch the 14/30-day base rate was close to
calibrated (ETH realised up 49% / 58% against 54% / 55% forecast). The 60/90-day
gate-on figures are that one 2025 stretch only. Forecasts reproduce the
walk-forward exactly on the 11 shared days.

**The rating replayed over 2023 — 22 Oct 2026.** `lastyear.py --start
2023-01-01 --end 2023-12-31`, output `analysis/RESULTS_2023.txt`. Gate on all
year from 26 Jan, 340 scorable days per horizon. The base rate's P(up) was
close to calibrated (ETH forecast 57-62% vs realised 54-70%; BTC 58-65% vs
60-80%), Brier at or below a coin flip at every horizon. The forecast range was
too wide: realised returns landed inside the forecast middle half 90-98% of the
time on ETH and 75-87% on BTC (target 50%), and the -20% touch it priced at
16-49% happened 0-4% of the time. The closest-match version did not beat the
base rate except BTC 30 days by 0.004.

**Money flow (MFI) — tested 19 Oct 2026, failed.** On 478 ETH troughs with
TradingView's own MFI column, against a 60% baseline for reaching +20% in 60
days: MFI level gives no gradient (67% / 54% / 59% / 66% across <20 / 20-40 /
40-60 / 60+, non-monotonic, and the 67% cell is 18 troughs). A "money diamond"
— CT RSI and MFI disagreeing vs the previous trough, the same construct as the
real diamond with volume as the second opinion — came in at 61% vs 60%, i.e.
nothing, and it *degrades* the existing tags when stacked: diamond alone 70%
falls to 64% with it, diamond+dot 76% falls to 69%. Do not re-test this.
The only survivor was MFI above its own signal line, 67% vs 58% on n=121, which
is probably just restating that the bounce has started and is likely collinear
with the prime dot. Untested whether it is independent.

**Inverted diamond as an exit — tested 19 Oct 2026, failed.** Mirror the whole
construct: pivot HIGHS on CT RSI, confirmation three bars later, disagreement
against the previous peak. Over 979 trades, median return +2.2% against +10.0%
for simply holding 60 days, beating hold only 45% of the time, capturing 7% of
the available high. Fails on both assets (ETH 50%, BTC 39%). Worth recording
that the disagreement filter is doing something: a naive any-peak exit fires on
day 6 and captures 0% of the max, the inverted-diamond version waits to day 33
and at least finishes positive. Also note its MEAN is +32.7% against hold's
+26.2% while its median is far worse -- a few real tops carry it and the rest
clip early. That is not tradable mechanically, which is the fifth time an exit
rule has reached that conclusion.

Four mechanical exits: a −5% stop, pivot-break, a probability ladder, and
cut-and-re-enter. The 50-line cross exit beat holding 32% of the time. Fib
levels are not special. Completed wave counts do not predict. A higher-low
filter shrank the sample to +7. Of 92 filters tested before 22 Oct, only the WGMI
one cleared agreement across four datasets — and it is the one that cannot be
rebuilt. The CT/Signal distance filter is the first clean survivor since.

## Where the current regime sits

The regime turned on 2026-09-02. As of 19 Oct 2026 that is 47 days, which is
the 0-60 day band -- the one where the higher-low column carries almost no
information (+3 spread, against +19 at 300+ days). Do not lean on it yet.

## Open items

- **`cycday` mislabels the 2026-07-13 ETH weekly signal** — reports cycle day
  1309 when it should be about 19. Its trough predates the recorded cycle low
  by two days, so the lookup falls through to the previous cycle. Related and
  unresolved: `CYCLE_LOWS` lists the ETH cycle low as 2026-06-24, but the
  actual low was $1,505 on 2026-06-01. Fix the anchor and the fall-through
  together.
- **No current Coinbase BTC export in the full CTZB layout.** Partly closed on
  22 Oct: two Binance BTCUSDC exports were recovered from uploads and
  **confirmed that the Signal line is `ta.ema(ct_rsi, 14)` on BTC too** — zero
  error over 1,113 BTC 2D bars and 2,228 BTC 1D bars, with EMA(13) and EMA(15)
  both off by ~0.9. The formula is now verified on both assets rather than
  fitted on ETH 2D alone. What is still missing: those files are Binance not
  Coinbase, end 20-21 Sept, use a different column order (CT RSI at 8, Signal
  at 9) and carry **no diamond or prime columns**, so flag alignment has never
  been checked on BTC at all. A current Coinbase BTC 2D, 3D, 5D and 1W in the
  23-column layout would close it. `data/tradingview/INDEX.md` has the settings.
- **The fractal checkpoints were never written down.** The last-cycle BTC and
  ETH overlay produced specific price and date checkpoints in conversation on
  21 Oct. They are not in this repo and cannot be reproduced without redoing
  the overlay, because the alignment was done by hand on his charts (shrunk to
  match the highs, anchored on the double bottom). `docs/PRETRADE.md` records
  that the fractal exists and that it is unsupported theory-craft; the numbers
  themselves are gone. Re-derive from his charts if they are wanted.
- CT RSI day-ten read for the dashboard: three-state, both-agree-up /
  both-agree-down / disagree, 78% vs 30%. **He asked explicitly not to let this
  be forgotten.**
- A direction arrow on Joe's gauge — it shows a level, not whether probability
  is rising or falling. Offered, not yet greenlit.
- **Joe's console is LIVE as of 20 Oct 2026 but its numbers are frozen.** The
  console was written into `files/index.html` (version 20) at `6tH6…`, replacing
  the thirteen-panel dashboard; `dash/meta` title is now "ETH Setup Standard".
  Every figure on it is hardcoded and dated 19 Oct 2026. **It does not refresh.**
  To make it live: turn the hardcoded values into `datasets/<id>` documents,
  mark the page's figures with `data-source`, and extend `refresh.py` to emit
  them so the six-a-day schedule drives it. Until that is done, the verdict
  ("ALMOST", ETH 3D) is a snapshot and must be rewritten by hand whenever the
  board changes — a stale verdict on a page someone sizes from is the main risk
  carried right now. The thirteen old `datasets/*` documents are still in the
  store, unreferenced; leave or reuse them during the port.
- The store copy is `docs/artifacts/joe-console-store.html`: fonts swapped to
  system stacks because the Dashboard type strips external font links, and every
  selector scoped under `.jc` so the page cannot restyle the frame around it.
  Edit `joe-console.html` (the standalone), then regenerate the store copy.
- Confirm the Coinbase perp contract size. The console defaults to 0.1 ETH per
  contract with a selector, because the search only turned up the Coinbase
  *Derivatives* nano spec via Interactive Brokers, not the perps Jared trades.
  Lock it and drop the selector once known.
- The console assumes **cross margin** — idle USDC counted as collateral, which
  is how Coinbase treats it. If Joe might run isolated margin instead, that
  needs to be a toggle, because under isolated the reserve does nothing.
- Scanner v9 is written (`docs/reference/ctzb_scanner_v9.pine`, diffed against
  the v8 Jared supplied, also kept). It adds the STEP column and an optional
  alert gate, renames EDGE to ODDS (it showed an increment over a baseline the
  panel hid once a signal fired), and adds a CONF column carrying the per-chart
  confluence lift. Seven columns now. First paste into TradingView failed with "Undeclared
  identifier o1" — Pine requires declaration before use, and the confluence
  block that computes o1..o6 sat below the alert-message block that reads them.
  Moved above it. **Still not confirmed compiling** — paste it in and check before
  relying on it. No agreement column was added: the LAST cell already turns
  green inside the confluence window, so the green count is the agreement count.
- Run the "Fetch candles" Action once. It now backfills 4H/12H history **and**
  brings down volume, which the pipeline previously discarded. Until that runs,
  `data/*.csv` has no volume column and money-flow style filters (MFI, CMF, OBV)
  cannot be tested at all. Expectation when it is testable: low. MFI is RSI with
  volume weighting and the RSI is already the signal; everything that has failed
  here failed for being another transform of the same closes. Agreement worked
  because it is a different axis.

## Standing instructions

Answer what was asked. Do not volunteer conclusions from patterns in the
numbers; if something looks wrong, ask one question rather than assume. No
extra sections, no follow-up requests unless asked. When he asks for an
opinion, give the opinion — do not turn it into a brainstorm. He does **not**
want the CoinStats API key rotated; that was settled and must not be raised
again.
