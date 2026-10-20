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
| ETH Setup Odds (dashboard) | `claude.ai/artifact/6tH6hXMh3EYLvUUEM9XgSJ` | **Joe has this link.** Dashboard type; page content lives in the artifact DB at collection `files`, doc `index.html`, field `text`. Update via `ArtifactData` with `if_version` pinned |

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
(n=21) -- capitulation, not a staircase, but thin. NOT YET TESTED: how
independent this is of the regime gate, which may already capture some of it.

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

Four mechanical exits: a −5% stop, pivot-break, a probability ladder, and
cut-and-re-enter. The 50-line cross exit beat holding 32% of the time. Fib
levels are not special. Completed wave counts do not predict. A higher-low
filter shrank the sample to +7. Of 92 filters tested, only the WGMI one cleared
agreement across four datasets — and it is the one that cannot be rebuilt.

## Open items

- CT RSI day-ten read for the dashboard: three-state, both-agree-up /
  both-agree-down / disagree, 78% vs 30%. **He asked explicitly not to let this
  be forgotten.**
- A direction arrow on Joe's gauge — it shows a level, not whether probability
  is rising or falling. Offered, not yet greenlit.
- The scanner needs changes and updates. Next up.
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
