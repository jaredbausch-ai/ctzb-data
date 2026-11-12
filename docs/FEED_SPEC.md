# Live feed spec

`feed/ctzb_feed.json`, written by `feed_live.py` in every run of the candle
Action (every 4 hours, first run 7 minutes after the 00:00 UTC close). It is
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
- Card numbers follow `docs/CARD_SPEC.md`. A screen showing a card shows
  `past_trades` beside every percentage and labels forming lows provisional.
- `grade_odds` is pooled context only. Never show it as the number for a
  live setup (CONTEXT, "Never quote the pooled grade alone").

## Top level (schema 3; schema 2 added the four card timing fields, 1 Nov 2026; schema 3 added `active_confluences`, 4 Nov 2026)

| Field | Source | Meaning |
|---|---|---|
| `schema_version` | | 3 |
| `generated_at` | | UTC time the file was written |
| `scored_as_of` | status.csv | Date of the data scored |
| `label` | | The computed-signal label |
| `checks.passed`, `checks.lines` | stack_status.txt | Stack and card checks |
| `cards_withheld` | | True when checks failed |
| `market_regime`, `next_buy_date`, `trades_a_year` | status.csv | As on the dashboard |
| `cards[]` | cards.csv | One per live setup (below) |
| `prints[]` | prints.csv | Every confirmed and forming low; `provisional` true until it confirms |
| `open_signals[]` | forward.csv, status open | Signals inside their 60 days, with day 10/30/60 and best/worst so far (computed, not fills) |
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
| `rose10_never_fell25_within60d_pct` | surv10 | The big number |
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
| `if_it_misses[]` | top level | Per asset and grade (A+, A, B, C; all grades from 11 Nov 2026): `signals`, `misses` (did not reach +20% within 60 days), `up_first` (of those, how many were above entry first), `median_peak_pct` (**the card shows this**, Jared 11 Nov), `mean_peak_pct`, `peaked_5_or_more`, `peaked_10_or_more`, `median_worst_drop_pct`, `median_day60_pct`. |
| `odds_fade` | top level | `posting_bar_pct` (70; below it the edge is gone, Jared 11 Nov), `early_dip[]` (deepest dip in the first 10 days → `past_trades`, `rose20_within60d_pct`, `edge` intact/gone) and `day10[]` (green / red on day 10, same fields). Every kept signal, all grades. |
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
  `edge_measured_on: "rose 10% within 60 days"`.

The grading itself (which setups are A+, `WINMIN` in refresh.py) is unchanged.
