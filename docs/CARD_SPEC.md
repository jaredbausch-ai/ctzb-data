# Trade card specification

Approved by Jared 28 Oct 2026. This is the single definition of every number and
every word on a trade card: the console's card now, and the client screens later
(Joe's side builds those from the same feed). A card may not show a number that is
not defined here, and a definition may not change without changing this file in the
same commit.

## Where a card's numbers come from

One card per forming low, on every chart (ETH and BTC, 1D to 8D), rebuilt every
pipeline run by `stack_live.py` into `datasets/cards.csv`.

**The sample: like for like only.** The card's past trades are chosen by the first
rule that gives 15 or more:

1. Same chart, exactly the same confirmations (lenses) on.
2. Same chart, same grade (any mix of confirmations that adds up to that grade).
3. Same grade across all of that asset's charts.

The card always says which rule it used, in plain words, in the "Where these numbers
come from" line, and states the sample size there and in the corner. Never use a
group of stronger setups ("at least these confirmations") as a trade's odds: on
28 Oct that showed 82% for a trade whose like-for-like record was 60%.

ETH samples start in 2020 (funding data begins then); BTC samples start in 2016.
Only signals whose 60 days are complete are counted.

## Every number on the card

All are measured from the buy price (the close of the confirmation bar) and within
60 days of buying.

| On the card | Definition | Field |
|---|---|---|
| Corner: N past trades | Size of the sample above | `n` |
| Big number: Rose 10% and never fell 25%, within 60 days of buying | Share of the sample whose highest price in the 60 days was at least 10% above the buy price AND whose lowest price in the 60 days never reached 25.3% below it (where 3.3x with 5% maintenance margin liquidates). Exact prices, not rounded figures | `surv10` |
| Rose 20% or more | Share whose highest price in 60 days was at least 20% above the buy price | `reach20` |
| Typical biggest rise | Median of each trade's highest price in 60 days vs the buy price | `bestMove` |
| Typical dip before it rose | Median of each trade's lowest price before its 60-day high | `dipBeforeHigh` |
| Typical deepest dip | Median of each trade's lowest price in 60 days | `maxDip60` |
| Fell 30% or more at some point | Share whose lowest price in 60 days was 30% or more below the buy price | `touched30` |
| Beat a normal move for the market at the time | Share whose highest rise reached 20% x (365-day daily volatility at entry / the asset's 2016-21 median volatility) | `scaled20` |
| Before 2022 / since 2022 (N trades) | The big-number measure split by entry date, with each half's count. The two counts must add up to the corner number | `surv10Old`, `nOld`, `surv10New`, `nNew` |
| If it falls before it rises 10%: rows 5, 10, 15, 20% | Of the trades that fell that far below the buy price before ever rising 10%: how many there were, the share that still rose 10% without falling 25.3%, and the share that went on to fall 25.3%. Information for a discretionary exit, never a stop rule (five mechanical exits lost to holding) | `l{5,10,15,20}{n,ok,liq}` |
| Confirms at the [day] close, if [asset] closes above X | The close on the confirmation bar below which CT would not stay above the trough, so the low would not confirm. Shown when the confirmation bar is the bar now open or the next one (fixed 29 Oct: it was blank on the confirmation day itself) | `killClose` |
| Confirmations | The confirmations (grade lenses) on now, in plain words | `lenses` |

## Wording rules

- Plain words only. No internal names (lens codes, "headline", "surv10", "basis",
  "bucket") on a card.
- Every percentage that depends on a time window says "within 60 days".
- The sample size is always visible, small, in the card's corner.
- The card always ends with: these are past signals, not real trades, and past
  results don't promise future ones. Entry quality only.
- Forming lows are labelled provisional until they confirm.

## What keeps it airtight

1. `stack_live.py` refuses to write the cards (and fails the run) if a card's two
   period counts don't add up to its sample, its source line doesn't state the
   sample size, any share is outside 0-100, the big number exceeds "rose 10%", or the
   dip-table counts don't shrink row by row.
2. `verify_cards.py` re-derives every card's sample from `datasets/ledger.csv`, which
   `grade_live.py` builds separately, and recomputes the figures; any mismatch fails
   the run (red Action, `stack_status.txt` FAILED). The dashboard refresh reports it.
   On 28 Oct this check caught a dip of -25.26% that a rounded figure turned into
   -25.3%; the cards use exact prices.
3. The quoted-versus-actual record (ledger, "odds on the day") shows how past quotes
   held up. Quotes ran 10-20 points high on +20% and on this measure (28 Oct); the
   per-trade fitted models that tried to fix it lost to the grade out of sample
   (`analysis/model.py`). Watch this gap; it is the honest limit of the numbers.
