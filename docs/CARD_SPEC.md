# Trade card specification

Approved by Jared 28 Oct 2026. This is the single definition of every number and
every word on a trade card: the console's card now, and the client screens later
(Joe's side builds those from the same feed). A card may not show a number that is
not defined here, and a definition may not change without changing this file in the
same commit.

## Where a card's numbers come from

One card per forming low on a graded chart (ETH and BTC, 1D, 2D, 3D, 5D) with the regime gate on at
its trough date, rebuilt every pipeline run by `stack_live.py` into `datasets/cards.csv`, provided its sample has at least one past signal (until 12 Nov 2026:
every chart, 1D to 8D, whatever the gate; see "The member site's card").

**The sample: like for like only.** The card's past trades are chosen by the first
rule that gives 15 or more:

1. Same chart, exactly the same confirmations (lenses) on.
2. Same chart, same grade (any mix of confirmations that adds up to that grade).
3. Same grade across all of that asset's charts.

Rule 3 is the last resort and is used whatever its size, including under 15 (the card shows the n). Since
12 Nov 2026 (audit #18) a forming low whose sample is empty gets no card at all; that only happened in early
history, and today the smallest rule-3 pool is 33.

The card always says which rule it used, in plain words, under the big number (and again on the
chart view), and states the sample size there. Never use a
group of stronger setups ("at least these confirmations") as a trade's odds: on
28 Oct that showed 82% for a trade whose like-for-like record was 60%.

ETH samples start once funding data and its 90-day median exist (the first graded ETH signal is ETH 3D, 21 Mar 2020, grade C; the first ETH top grade is 18 Apr 2020); BTC samples start in 2016.
Only signals whose 60 days are complete are counted.

## Every number on the card

All are measured from the buy price (the close of the confirmation bar) and within
60 days of buying.

| On the card | Definition | Field |
|---|---|---|
| Corner: N past signals | Size of the sample above | `n` |
| Big number (since 11 Nov 2026): Rose 10% within 60 days of the entry close | Share of the sample whose highest daily high in the 60 days was at least 10% above the entry close | `reach10` |
| Line under it: did it without ever falling 25.3% | Share of the sample that rose 10% AND whose lowest daily low in the 60 days never reached 25.3% below the entry close (where 3.3x with 5% maintenance margin liquidates). Exact prices, not rounded figures (until 11 Nov 2026 this was the big number) | `surv10` |
| Rose 20% or more | Share whose highest price in 60 days was at least 20% above the buy price | `reach20` |
| Typical biggest rise | Median of each trade's highest price in 60 days vs the buy price | `bestMove` |
| Typical lowest point vs the buy price, before it made its 60-day high (wording fixed 4 Nov 2026; was "Typical dip before the 60-day high", which read as a pullback from profit) | Median, across the past trades, of each trade's lowest low from the day after the buy up to the day of its 60-day high, as a percentage of the BUY PRICE. Negative = it was under the buy price at some point before topping. It is not a pullback from a profit | `dipBeforeHigh` |
| Typical deepest dip below the buy price | Median of each trade's lowest price in 60 days, as a percentage of the buy price | `maxDip60` |
| Fell 30% or more at some point | Share whose lowest price in 60 days was 30% or more below the buy price | `touched30` |
| Beat a normal move for the market at the time | Share whose highest rise reached 20% x (365-day daily volatility at entry / the asset's 2016-21 median volatility) | `scaled20` |
| Before 2022 / since 2022 (N signals) | "Rose 10% and never fell 25.3%" (surv10, the line under the big number) split by entry date, with each half's count. The two counts must add up to the card's n | `surv10Old`, `nOld`, `surv10New`, `nNew` |
| If it falls before it rises 10%: rows 5, 10, 15, 20% | Of the trades that fell that far below the buy price before ever rising 10%: how many there were, the share that then rose 10% BEFORE falling 25.3% (12 Nov 2026 wording: "before", which is what the code measures), and the share that went on to fall 25.3%. Information for a discretionary exit, never a stop rule (five mechanical exits lost to holding) | `l{5,10,15,20}{n,ok,liq}` |
| Confirms at the [day] close, if [asset] closes above X | The close on the confirmation bar below which CT would not stay above the trough, so the low would not confirm. Shown rounded DOWN to the cent (since 12 Nov 2026 audit #16), so every close above the shown price confirms and a close at it does not. Shown when the confirmation bar is the bar now open or the next one (fixed 29 Oct: it was blank on the confirmation day itself) | `killClose` |
| Confirmations | The confirmations (grade lenses) on now, in plain words | `lenses` |
| Typical day it first hit +10% / +20% (trades that got there) | Median calendar days from the buy to the first daily high at least 10% / 20% above the buy price, among the trades in the sample that got there within 60 days (added 1 Nov 2026, Jared: "how long do I stay in the tree?") | `daysTo10`, `daysTo20` |
| Typical day of the 60-day high / of the deepest dip | Median day, counted from the buy, on which each trade made its highest high / its lowest low within the 60 days | `daysToHigh`, `daysToLow` |
| Active confluences now (4 Nov 2026) | Every confluence cell active for this setup today, weak ones included, each with its own past trades, rose 20%, fell 30% and the date its window closes. Its own sample, never blended into the big number; rows overlap. Nothing else is listed in this section. Under 15 trades is flagged too few to lean on | `confluences` (JSON list) |

## The member site's card (12 Nov 2026)

Which lows get a card: a forming low only on a graded chart (1D, 2D, 3D, 5D) with the regime gate on at its
trough date and at least one past signal in its sample; a live (open) setup on a graded chart; the worked example. There are no 8D cards.

A live setup's card is the card as issued at its entry close. Because a from-entry figure beside an open signal
can read as today's chance (CONTEXT, 31 Oct 2026), the card itself says "Edge lost", "Rose 10%" (it rose 10% before reaching its edge level) or "On track", says the
odds are "as of the entry close, not from today", and an edge-lost card is dimmed and not drawn in the live
colour. No from-today odds are computed for members.

The member site (`docs/artifacts/member-site/index.html`) shows the same card in its own words. Each label
below is defined here; anything not listed is in the table above.

| On the member card | Definition | Feed field |
|---|---|---|
| Big number, "rose 10% within 60 days" | As above (`reach10`) | `rose10_within60d_pct` |
| "X% did it without ever falling 25.3%" | As above (`surv10`) | `rose10_never_fell25_within60d_pct` |
| "from [sample]" under it | The sample rule in plain words and n, no grade letters | `sample`, `past_trades` |
| Typical high / Typical drop from entry | Median best move / median deepest dip in the 60 days (the Chart tab also shows each as a price) | `typical_biggest_rise_pct` / `typical_deepest_dip_pct` (+ their `*_exact_pct`) |
| Dip before the high, from entry | Median lowest point before the 60-day high, from the entry close | `typical_dip_before_rise_pct` (+ `*_exact_pct`) |
| Edge gone below | The first fall whose exact "still rose 10%" share is below the 70% bar; "below the bar from entry" when even the from-entry row is | ladder `still_rose10_exact_pct`, `from_entry` |
| Where the odds fade: From entry | Share of the sample that rose 10% before ever falling 25.3% (low checked first within a day) | `from_entry.still_rose10_pct` |
| Where the odds fade: Falls X% first | Of the signals that fell X% before rising 10%, the share that then rose 10% before falling 25.3% | `if_it_falls_first[]` |
| If it misses: went above entry | Of the asset/grade's signals that did not rise 10% in 60 days, how many had a best price above entry, and the median best price of all those misses | `if_it_misses[]` (`up_first`, `median_peak_pct`) |
| Typical worst drop, misses / Typical change by day 60, misses | Median deepest dip / median day-60 change of those misses, with their count and pool | `if_it_misses[]` |
| Reached +20% / Touched −30% within 60 days | As above (`reach20`, `touched30`) | `rose20_within60d_pct`, `fell30_within60d_pct` |
| High lands around / Deepest dip lands around | Median day of the 60-day high / deepest dip | `typical_day_of_60d_high`, `typical_day_of_deepest_dip` |
| By era | surv10 before 2022 / since 2022 with each n | `before_2022`, `since_2022` |
| +10% level | Entry close x 1.10 (a measuring level, not an exit) | computed from the entry |

## Wording rules

- Plain words only. No internal names (lens codes, "headline", "surv10", "basis",
  "bucket") on a card, and no grade letters: the grade stays internal, so a card says "the top grade" or
  "the same grade" (12 Nov 2026 audit #11; the sample line, e.g. "all 37 past BTC 1D signals of the same
  grade", and the miss tiles, e.g. "95 misses of all 312 BTC same-grade signals").
- The card says once, under the big number, that every figure covers the 60 days after entry ("rose 10%
  within 60 days" ... "every figure covers the 60 days after entry"). A figure on a different window
  names its window (e.g. "after day 10", "by day 60").
- The sample size is always visible, small, under the big number. Anything on a different sample
  shows its own n: each ladder row, each era, and the misses (their count and the pool, named on the
  "If it misses" row itself and on the miss tiles, on every card).
- The card always ends with: these are past signals, not real trades, and past
  results don't promise future ones. Entry quality only.
- A forming low is labelled "Setup forming" with "It can still vanish before it confirms" until it
  confirms.

## What keeps it airtight

1. `stack_live.py` refuses to write the cards (and fails the run) if a card's two
   period counts don't add up to its sample, its source line doesn't state the
   sample size, any share is outside 0-100, the line under the big number (surv10) exceeds the big number ("rose 10%"), or the
   dip-table counts grow from one row to the next (each row is a subset of the one above, so a count can stay
   level but never rise), or the first exceeds n. These checks run on every card: forming, live and the example.
2. `verify_cards.py` re-derives every card's sample from `datasets/ledger.csv`, which
   `grade_live.py` builds separately, and recomputes every figure on the card: n, the big number,
   surv10, scaled20, +20%, -30%, the rounded and exact medians, the eras, the timing, and the
   from-entry and falls-first ladder rows (from the 1D candles, written out independently). Exact,
   except the three 6-place exact medians, confirmable from the 6-place ledger to one unit in the
   6th place (since 12 Nov 2026, audit #8). Any mismatch fails the run (red Action, `stack_status.txt` FAILED). The dashboard refresh reports it.
   On 28 Oct this check caught a dip of -25.26% that a rounded figure turned into
   -25.3%; the cards use exact prices.
3. The quoted-versus-actual record (ledger, "odds on the day") shows how past quotes
   held up. Quotes ran 10-20 points high on +20% and on this measure (28 Oct); the
   per-trade fitted models that tried to fix it lost to the grade out of sample
   (`analysis/model.py`). Watch this gap; it is the honest limit of the numbers.


**Wording, 12 Nov 2026 (audit #4):** the page says "signals", never "trades", for the sample: these are
computed signals and none was traded. Older rows above that still say "trades" mean the same past signals.
