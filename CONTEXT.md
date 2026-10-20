# CTZB — read this first

Start every session here. This file exists because conversations get compacted
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
| Setup Standard draft | `claude.ai/artifact/8ViZjND99xmo8rbcUmmr5r` | Standalone copy, for editing and review. Source `docs/artifacts/joe-console.html` |
| ETH Setup Standard (Joe's) | `claude.ai/artifact/6tH6hXMh3EYLvUUEM9XgSJ` | **Joe has this link.** Dashboard type; page content lives in the artifact DB at collection `files`, doc `index.html`, field `text`. Update via `ArtifactData` with `if_version` pinned |

The dashboard's live signals are **computed signals, never fills**. Jared has
taken none of them. Presenting them to a creditor as trades would be
misrepresentation.

## What has been tested and failed

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
filter shrank the sample to +7. Of 92 filters tested, only the WGMI one cleared
agreement across four datasets — and it is the one that cannot be rebuilt.

## Where the current regime sits

The regime turned on 2026-09-02. As of 19 Oct 2026 that is 47 days, which is
the 0-60 day band -- the one where the higher-low column carries almost no
information (+3 spread, against +19 at 300+ days). Do not lean on it yet.

## Open items

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
  alert gate. **Not yet compiled in TradingView** — paste it in and check before
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
