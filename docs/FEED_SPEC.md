# Live feed spec

`feed/ctzb_feed.json`, written by `feed_live.py` in every run of the candle
Action (every 4 hours: the `ctzb-scheduler` Worker triggers it 13 minutes after each 4-hour close, 00, 04,
08, 12, 16 and 20 UTC, with a backup at :43). It is
the "one feed" in the live-feed plan agreed with Joe on 31 Oct 2026
(`docs/joe/2026-10-28_live_feed_proposal_SENT.md`, `docs/joe/2026-10-31_feed_open_items_SENT.md`).

It repackages the datasets written earlier in the same run. It computes
nothing of its own, so it cannot disagree with the dashboard or the cards.

## Rules

- Fields are only ever **added**, never renamed or removed. `schema_version`
  goes up by one whenever a field is added.
- Every card, print, open signal and grade row carries `label`: computed
  signal, not a fill, entry quality only, not a track record.
- `cards` is empty and `cards_withheld` is true whenever `stack_status.txt`
  has a FAILED line (stack coverage or the card cross-check). Same gate as
  the dashboard refresh task.
- Card numbers follow `docs/CARD_SPEC.md`. A screen showing a card shows the card's sample size
  (`past_trades`) under the big number, which covers every figure from that sample; anything on a
  different sample shows its own n (each ladder row, each era, and the misses: their count and pool).
  A forming low is shown as "Setup forming ... can still vanish before it confirms" until it
  confirms (`prints[].provisional`; the card's own state is the `cards[]` list itself, forming only).
- `grade_odds` is pooled context only. Never show it as the number for a
  live setup (CONTEXT, "Never quote the pooled grade alone").

## Top level (schema 5 now; schema 2 added the four card timing fields, 1 Nov 2026; schema 3 added `active_confluences`, 4 Nov 2026; 4 and 5 below)

| Field | Source | Meaning |
|---|---|---|
| `schema_version` | | 5 |
| `generated_at` | | UTC time the file was written |
| `scored_as_of` | status.csv | Date of the data scored |
| `label` | | The computed-signal label |
| `checks.passed`, `checks.lines` | stack_status.txt | Stack and card checks |
| `cards_withheld` | | True when checks failed |
| `market_regime`, `next_buy_date`, `trades_a_year` | status.csv | As on the dashboard |
| `cards[]` | cards.csv | One per FORMING setup (below). A live (open) setup's card is `open_signals[].card`; the worked example's is `example_card` |
| `prints[]` | prints.csv | Every confirmed and forming low; `provisional` true until it confirms |
| `open_signals[]` | open.csv (stack_live.py; forward.csv until 12 Nov 2026) | Signals inside their 60 days, ETH and BTC, with day 10/30/60 and best/worst so far and their own `card` (computed, not fills) |
| `confluence_windows[]` | windows.csv | Every confluence window open now and when it closes |
| `grade_odds[]` | grades.csv | Pooled grade record per asset |

## Card fields

| Field | cards.csv | Card wording |
|---|---|---|
| `chart`, `asset`, `timeframe` | chart, asset, tf | |
| `low_date`, `confirms_on`, `bars_to_confirm` | trough, confirms, barsNeeded | |
| `must_close_above` | killClose | Confirms at the close if price closes above this |
| `price_now` | priceNow | |
| `grade`, `confirmations` | grade, lenses | |
| `sample`, `past_trades` | basis, n | The like-for-like sample and its size |
| `rose10_never_fell25_within60d_pct` | surv10 | The line under the big number (the big number until 11 Nov 2026; now `rose10_within60d_pct`) |
| `beat_normal_move_pct` | scaled20 | |
| `rose20_within60d_pct`, `rose10_within60d_pct` | reach20, reach10 | |
| `typical_biggest_rise_pct` | bestMove | |
| `typical_dip_before_rise_pct` | dipBeforeHigh | Lowest point vs the BUY PRICE before the 60-day high (median). Not a pullback from profit |
| `typical_deepest_dip_pct` | maxDip60 | |
| `fell30_within60d_pct` | touched30 | |
| `before_2022`, `since_2022` | nOld/surv10Old, nNew/surv10New | |
| `if_it_falls_first[]` | l{5,10,15,20}{n,ok,liq} | Information for a discretionary exit, never a stop rule |
| `typical_day_first_rose10`, `typical_day_first_rose20` (schema 2) | daysTo10, daysTo20 | Median days from entry to the first +10% / +20%, trades that got there |
| `typical_day_of_60d_high`, `typical_day_of_deepest_dip` (schema 2) | daysToHigh, daysToLow | Median day of the 60-day high / of the deepest dip |
| `active_confluences[]` (schema 3) | confluences (JSON) | Every confluence cell active for this setup today, weak ones included: `after` (the confirming signal), `after_confirmed`, `window_closes`, `applies_to` (which of this chart's signals the record covers), `past_trades`, `rose20_within60d_pct`, `rose10_within60d_pct`, `fell30_within60d_pct`. Each is its own sample, never blended into the card number; rows overlap. Show `past_trades` beside each; under 15 is too few to lean on |

## Not built yet

- The Cloudflare backend serving keyed views (admin, Prime, Signal, delayed
  Free). Waits on the ETHKROS Cloudflare account.
- The ping to Grok when a new signal lands as pending.
- The repo going private (after the Cloudflare account, before any paid
  member sees a signal). Until then this file is public, like the datasets.

## Schema 4 — signal ids and alerts (10 Nov 2026, item 17d)

Fields added; nothing renamed or removed.

| Field | Where | Meaning |
|---|---|---|
| `signal_id` | every card, print and open signal | Chart + confirmation date, e.g. `ETH-1D-2026-11-12`. The same at every stage of a signal's life: the forming card, the confirmed print, and the open signal share it. A trough that slides is a new signal with a new id. |
| `alerts` | top level | Events NEW in this generation. Each: `alert_id`, `event`, `signal_id`, `chart`, `emitted_at`, `label`. |
| `alerts[].event` | | `forming` (a card appeared), `confirmed` (it became a signal), `vanished` (an alerted forming card is gone and never confirmed — the trough slid, or the setup no longer qualifies). |
| `alerts[].alert_id` | | `{signal_id}:{event}`. Fixed for that event, forever. |
| `alerts_withheld` | top level | True when any scoring check failed this run. `alerts` is then empty. |
| `alerts_seeded` | top level | True only on the very first run, which records what was already live without alerting on it. |
| `checks.all_passed`, `checks.steps`, `checks.failed_steps` | `checks` | The outcome of each gating step (refresh, grade, stack, cards, regress). `checks.passed` keeps its old meaning: the stack check alone. |
| `cards_withheld` | top level | Unchanged meaning, wider trigger: now true when ANY gating step failed, not only the stack check. |

**The one rule for anything that sends alerts:** record every `alert_id` you send and
never send the same one twice. The pipeline guarantees an alert appears in exactly one
feed generation (`feed/alert_log.csv`, append-only, committed with the feed), but that
generation is read many times — every 15 minutes by the mirror, and by every poller.

**Withheld is not dropped.** A withheld alert is not logged, so it is emitted by the
next run in which every check passes.

## Schema 5 — member card figures (11 Nov 2026, item 18)

Fields added; nothing renamed or removed. Written by `extras_live.py` from the same
run's `datasets/ledger.csv`, `earlydip.csv` and `holdcheck.csv` (arithmetic in
`analysis/carddesign.py`). They never gate cards or alerts.

| Field | Where | Meaning |
|---|---|---|
| `extras_withheld` | top level | True when the `extras` step failed this run. The three fields below are then empty, so a stale copy is never served. |
| `if_it_misses[]` | top level | Per asset and grade (A+, A, B, C; all grades from 11 Nov 2026): `signals`, `misses` (did not rise 10% within 60 days; +20% until 11 Nov 2026), `up_first` (of those, how many went above entry at some point in the 60 days, i.e. best price above entry; the name is kept, fields are never renamed), `median_peak_pct` (**the card shows this**, Jared 11 Nov), `mean_peak_pct`, `peaked_5_or_more`, `peaked_10_or_more`, `median_worst_drop_pct`, `median_day60_pct`. |
| `odds_fade` | top level | `posting_bar_pct` (70; below it the edge is gone, Jared 11 Nov), `early_dip[]` (deepest dip in the first 10 days → `past_trades`, `rose10_after_day10_pct`, `rose20_after_day10_pct`, `edge` intact/gone on the +10% share) and `day10[]` (green / red on the day-10 close, same fields). ETH walk-forward tier signals only, every chart (see the 12 Nov sections). The `*_within60d_pct` fields carry the same values under their original names, kept because fields are never renamed; their window is also days 11 to 60. |
| `past_paths[]` | top level | Per asset, grade A+: `signals` and `days[]` (day 0-60: `q25_pct`, `median_pct`, `q75_pct`, percent from entry on daily closes, every past signal lined up at entry). The chart view's "where the past signals went". |

### `candle_check` (added 11 Nov 2026, additive, schema stays 5)

The candle sanity check from this run, so the health monitor can see the second-exchange
check being skipped run after run (an unreachable Kraken never fails a run on its own).
`null` when the check file is missing, and in a fail-closed feed.

```json
"candle_check": {"checked_at": "2026-11-11T20:13:52+00:00", "cross_mode": "enforce",
                 "structural_ok": true, "kraken": {"ETH": "ok", "BTC": "ok"}}
```

`kraken` values: `ok`, `over_threshold`, `unavailable`.

### Fail-closed feed (11 Nov 2026)

If `feed_live.py` itself crashes, it writes a feed with every list empty, `cards_withheld`,
`alerts_withheld` and `extras_withheld` all true, `checks.failed_steps: ["feed"]` and a
`feed_error` naming the exception type, then exits 1. Readers need no special case: it is a
withheld feed.

### +10% switch (11 Nov 2026, additive, schema stays 5)

The card's headline is "rose 10% within 60 days", so the figures built around it follow:

- `if_it_misses`: a miss is now a signal that **did not rise 10% within 60 days** (was +20%).
  Each entry carries `miss_rule` saying so. Field names unchanged.
- `odds_fade`: each `early_dip` and `day10` row gains `rose10_within60d_pct`; `edge` is now
  marked on it against the 70% bar (was on +20%). `rose20_within60d_pct` stays, for detail.
  `edge_measured_on` was "rose 10% within 60 days"; since 12 Nov (audit #6) it is "rose 10% after day 10
  (days 11 to 60)", which is the window those shares count, and the `rose10/20_after_day10_pct` fields name it.

The grading itself (which setups are A+, `WINMIN` in refresh.py) is unchanged.
- `grade_odds`: each entry gains `rose10_within60d_pct` (from grades.csv `reach10`).

### Audit corrections (12 Nov 2026)

- `grade_odds[].sample` is that grade's own first and last signal ("2020-04-18 to 2025-12-04"),
  not the asset's whole range.
- Every rounded figure is rounded half away from zero (62.5 -> 63), once, from the unrounded value.
- A signal appears in the ledger, and in every figure built from it, only once its 60th day has closed.

### Second audit corrections (12 Nov 2026, independent audit #3)

- `cards[]` gain `typical_biggest_rise_exact_pct`, `typical_dip_before_rise_exact_pct`, `typical_deepest_dip_exact_pct`:
  the same medians unrounded. Show the rounded fields; build prices (entry x (1 + pct/100)) from the exact ones.
- `cards[].sample` says "all N past ... signals", not "the last N ... trades": every past signal is used, and none was traded.
- `example_card` (new, top level): the member site's worked example (ETH 2D, confirmed 2024-09-22) as a full card, same
  fields as `cards[]` plus `example: true` and `entry_close`, built by the forming-card rules from only the signals whose
  60th day had closed by 2024-09-22. `null` when withheld.
- `open_signals[]` now cover ETH and BTC on 1D/2D/3D/5D (they were ETH only), come from `datasets/open.csv`
  (stack_live.py), are dated by the confirmation CLOSE date (same id as the print and the card), count `days_elapsed` in
  calendar days since that close, and take day-10/30/60 and best/worst from closed daily candles. Each carries `card`:
  its own full card (sample, ladder, edge). Withheld (empty) when checks fail.
- `odds_fade`: measured on daily candles from the entry close; every row's +10%/+20% share counts highs after day 10
  (days 11 to 60); the day-10 rows group by the day-10 daily close. Labelled as a general explainer.
- `past_paths`: quantiles taken on exact path values, rounded once.
- `cards[].low_day` (12 Nov 2026, audit #4): the calendar day the low printed. `low_date` stays the trough BAR's open
  date, which on a 2D+ chart can be a day earlier.
- The walk-forward tier (refresh.py `select_tier(upto=...)`, used by `odds_fade` and forward.csv's `tier`) counts only
  signals whose 60-day outcome had closed before 1 January of the year in question (it used to count signals dated
  before 1 January whose outcomes ended after it).

### Audit #5 corrections (12 Nov 2026)

- `cards[].from_entry` (also on `example_card` and `open_signals[].card`): `past_trades`, `still_rose10_pct` (the
  share of the sample that rose 10% before ever falling 25.3%) and `went_on_to_fall25_pct`. It is the ladder's first
  row, measured exactly like the `if_it_falls_first` rows under it. The big number stays `rose10_within60d_pct`.
- The ladder checks a day's low before its high in every step (the cautious reading; a daily bar doesn't say which
  came first).
- `price_now`: forming cards, the latest price (today's bar is still open), a stand-in for the entry; live cards,
  the latest price; the example, none. `entry_close`: live and example cards, the actual entry close; forming, empty.
- `open_signals[]` cover the graded charts only: 1D, 2D, 3D, 5D.
- `odds_fade`: the walk-forward tier itself is chosen by refresh.py's original rule (`select_tier`: each chart's own
  bars, `NMIN`/`WINMIN`, only outcomes closed before 1 January); only the fade's groupings and outcomes are measured on
  daily candles from the entry close.
- `low_day` is found within the trough bar's real span (2D+ bars restart on 1 January, so a year's last bar can be
  shorter).

### Audit #6 corrections (12 Nov 2026)

- `open_signals[].day60_pct` is always empty: a signal leaves the list the day its 60th daily bar closes. Kept
  because fields are never removed.
- `example_past_paths` (new, top level): the worked example's cloud, built only from ETH top-grade signals whose
  60th day had closed by 2024-09-22 (the same sample as `example_card`). Same shape as one `past_paths[]` entry.
- Every 60-day window (ladder, from-entry row, paths) counts 60 CALENDAR days after the entry date, not 60 bars.

### Audit #7 corrections (12 Nov 2026)

- Every `past_trades` now has a `past_signals` twin, and `trades_a_year` a `signals_a_year` twin, with the
  same values. They count computed signals; none was traded. The old names stay because fields are never renamed.
- `if_it_misses[].up_first` counts misses whose best price within the 60 days was above entry (they went above
  entry at some point), not "above entry before ever being below it". The page says "went above entry".

### Audit #8 corrections (12 Nov 2026)

- `odds_fade.sample` now says what the sample is: ETH signals on the chart/tag pairs of the walk-forward tier
  as fixed on 1 Jan 2026, applied to every signal from 2016. That is **in-sample** (the tier was chosen on the
  outcomes of almost all of them). It is a general explainer and is not on any card.
- The 70% edge bar is tested once, on the exact share, never on the whole-percent one shown: `earlydip.csv` /
  `holdcheck.csv` gain `reached10Exact`; card ladder rows and `from_entry` gain `still_rose10_exact_pct`
  (cards.csv `l0okExact`, `l5okExact` ... `l20okExact`). The page tests the bar on those.
- **Rounding, stated precisely.** Each signal's measures are stored to 6 decimal places (the ledger); that is
  the "exact" value. Card medians and shares are computed on full-precision measures and stored to 6 places
  (`*_exact_pct`); every displayed figure is rounded once, from that value, half away from zero.
- `verify_cards.py` now re-derives every figure on a card (see CARD_SPEC "What keeps it airtight" #2).

### Audit #9 corrections (12 Nov 2026)

- `open_signals[]` gain `edge_level_pct` (the setup's own edge level from its card's ladder, exact shares: 0 if
  even the from-entry share is below 70%, else the first fall whose share is below 70%, else empty) and
  `edge_status` ("intact" / "lost"): on closed daily bars after entry, whichever came first, a low at or below
  the edge level (low checked first within a day) or a high at +10%; "lost" from the start when the edge level
  is 0. The page's Previous signals badges read it.
- `example_if_it_misses` (new, top level): the worked example's "if it misses" figures, ETH top-grade signals
  whose 60th day had closed by 2024-09-22 (same sample as `example_card`). The page used to compute these itself.
- One "known by then" rule: a past signal counts once its 60th day (entry + 60) has closed by the moment in
  question. The ledger's odds-on-the-day columns used entry + 61 (one day stricter); they now use entry + 60,
  like the example. 73 ledger rows' odds-on-the-day columns moved; nothing else (baseline re-approved).
- The page types no figures: the 70% bar in How to read comes from the feed (`odds_fade.posting_bar_pct`), "about N times a year" is counted from the ledger (2020-2025), and without the
  feed's `example_card` the example says "unavailable" rather than falling back to built-in numbers.
- Every forming card says it can still vanish (top grade too), and How to read says a confirmed alert is final
  while a forming heads-up can vanish.

### Audit #11 corrections (12 Nov 2026)

- No grade letters in member-facing text (CONTEXT: "the grade stays internal"). A card's `sample` now reads
  "signals of the top grade" / "signals of the same grade" instead of "graded C" / "grade A+"; the `grade` field
  itself is unchanged (it drives logic, it isn't shown).
- The chart's lead-trader note says his feed is unavailable when it can't be read, instead of "None on this one".
