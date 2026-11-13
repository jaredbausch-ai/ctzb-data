# Live feed spec

`feed/ctzb_feed.json`, written by `feed_live.py` in every run of the candle
Action (every 4 hours: the `ctzb-scheduler` Worker triggers it 13 minutes after each 4-hour close, 00, 04,
08, 12, 16 and 20 UTC, with a backup at :43). It is
the "one feed" in the live-feed plan agreed with Joe on 31 Oct 2026
(`docs/joe/2026-10-28_live_feed_proposal_SENT.md`, `docs/joe/2026-10-31_feed_open_items_SENT.md`).

It repackages the datasets written earlier in the same run. It computes no figure of its own (so it cannot
disagree with the dashboard or the cards): it decides which alerts are new against `feed/alert_log.csv`, and it
refuses to publish a feed that fails the strict check.

## Rules

- Fields are only ever **added**, never renamed or removed. `schema_version`
  goes up by one whenever a field is added. (The 11-12 Nov 2026 additions were made at schema 5 and are
  batched into **schema 6**, 12 Nov 2026; from 6 on, one step per addition again.)
- Every card, print, open signal and grade row carries `label`: computed
  signal, not a fill, entry quality only, not a track record.
- `cards`, `open_signals`, `example_card`, `prints`, `confluence_windows`, `grade_odds` and the extras are
  empty, the status fields are null, and `cards_withheld` is true whenever `stack_status.txt` has a FAILED
  line or any gating step (refresh, grade, stack, cards, regress) did not report success. A broken run seal,
  a missing dataset, a damaged alert log or a feed that fails the strict check publishes the fail-closed
  feed instead (feed_live exits 1).
- Card numbers follow `docs/CARD_SPEC.md`. A screen showing a card shows the card's sample size
  (`past_trades`) under the big number, which covers every figure from that sample; anything on a
  different sample shows its own n (each ladder row, each era, and the misses: their count and pool).
  A forming low is shown as "Setup forming ... can still vanish before it confirms" until it
  confirms (`prints[].provisional`; the card's own state is the `cards[]` list itself, forming only).
- `grade_odds` is pooled context only. Never show it as the number for a
  live setup (CONTEXT, "Never quote the pooled grade alone").

## Top level (schema 6 now; schema 2 added the four card timing fields, 1 Nov 2026; schema 3 added `active_confluences`, 4 Nov 2026; 4 and 5 below)

| Field | Source | Meaning |
|---|---|---|
| `schema_version` | | 6 |
| `posting_bar_pct` | feed_live `POSTING_BAR` | 70: the bar below which a card's "still rose 10%" share means the edge is gone. Top level so a card's ladder can be read against it even when `odds_fade` is withheld. It is the same number as refresh.py's `WINMIN`, which chooses the ETH walk-forward tier on a different measure (chart/tag pairs whose past signals, 8 or more, closed above entry on the chart's last bar within 60 days at least 70% of the time); `trades_a_year` and `next_buy_date` come from that ETH tier |
| `generated_at` | | UTC time the file was written |
| `scored_as_of` | status.csv | Date of the data scored |
| `label` | | The computed-signal label |
| `checks.passed`, `checks.lines` | stack_status.txt | Stack and card checks |
| `cards_withheld` | | True when checks failed |
| `market_regime`, `next_buy_date`, `trades_a_year` | status.csv | `market_regime`: the market filter on today's date, Bullish or Bearish. `next_buy_date`: the close date of the bar on which the next forming ETH tier low would confirm (2D+ bars restart on 1 January; since 13 Nov 2026 audit #23, it was the bar's open date), whatever the market filter reads (a filter-off low is included though it cannot become a signal); a computed date, not a planned buy. `trades_a_year`: computed ETH tier signals per year (twin `signals_a_year`). All three are null in a held feed |
| `cards[]` | cards.csv | One per FORMING setup (below). A live (open) setup's card is `open_signals[].card`; the worked example's is `example_card` |
| `prints[]` | prints.csv | The last 3 signals per chart (lows that confirmed with the market filter on at the trough date; a low that confirms with the filter off is not a signal and is not listed) plus any forming low (listed with a "regime off" note while the filter is off); `provisional` true until it confirms. The regime note is read on the trough date (since 12 Nov 2026 audit #13; it was the confirmation date) |
| `open_signals[]` | open.csv (stack_live.py; forward.csv until 12 Nov 2026) | Signals inside their 60 days, ETH and BTC, with day 10/30/60 and best/worst so far and their own `card` (computed, not fills) |
| `confluence_windows[]` | windows.csv | Every confluence window open now and when it closes |
| `grade_odds[]` | grades.csv | Pooled record per asset and grade (A+, A, B, C), plus four ETH flag rows whose `grade` is "HTF divergence" / "no HTF divergence" / "diamond or prime dot" / "no diamond or prime dot". Each: `past_trades`, `rose10_within60d_pct`, `rose10_never_fell25_within60d_pct`, `rose20_within60d_pct`, `median_deepest_dip_pct`, `sample`, `note`. Empty in a held feed |

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
| `typical_day_first_rose10`, `typical_day_first_rose20` (schema 2) | daysTo10, daysTo20 | Median days from entry to the first +10% / +20%, past signals that got there |
| `typical_day_of_60d_high`, `typical_day_of_deepest_dip` (schema 2) | daysToHigh, daysToLow | Median day of the 60-day high / of the deepest dip |
| `active_confluences[]` (schema 3) | confluences (JSON) | Every confluence cell active for this setup today, weak ones included: `after` (the confirming signal), `after_confirmed`, `window_closes`, `applies_to` (which of this chart's signals the record covers), `past_trades`, `rose20_within60d_pct`, `rose10_within60d_pct`, `fell30_within60d_pct`. Each is its own sample, never blended into the card number; rows overlap. Show `past_trades` beside each; under 15 is too few to lean on. Filled for forming cards only: on `open_signals[].card` and `example_card` it is always empty. Each item also carries `note` |

## Not built yet

- Keyed views per tier (admin, Prime, Signal, delayed Free). The Cloudflare backend itself was built
  10-11 Nov 2026 (mirror `ctzb-feed`, `ctzb-site` behind a login, scheduler, dashboard, trades relay in dry
  run; see CONTEXT); the per-tier views are what is not built.
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
| `alerts_seeded` | top level | True only on a run made with `CTZB_SEED_ALERT_LOG=1`, which starts a new alert log on purpose and records what is already live without alerting on it. |
| `checks.all_passed`, `checks.steps`, `checks.failed_steps` | `checks` | `steps`: every step outcome the workflow passed (refresh, grade, extras, stack, cards, regress; extras does not gate). `failed_steps`: the gating steps that did not report success. `all_passed`: no FAILED line and no failed gating step. `checks.passed` keeps its old meaning: no FAILED line in stack_status.txt, i.e. the stack check and the card cross-check (verify_cards.py appends to that file). |
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
| `extras_withheld` | top level | True when the extras step was reported as anything but success (an extras outcome that is absent counts as success), the run was held back, or one of its files (missstats, pastpaths, oddsfade) is missing. The lists in `if_it_misses`, `past_paths` and `odds_fade` are then empty and `example_if_it_misses` / `example_past_paths` are null, so a stale copy is never served. |
| `if_it_misses[]` | top level | Per asset and grade (A+, A, B, C; all grades from 11 Nov 2026): `signals`, `misses` (did not rise 10% within 60 days; +20% until 11 Nov 2026), `up_first` (of those, how many went above entry at some point in the 60 days, i.e. best price above entry; the name is kept, fields are never renamed), `median_peak_pct` (**the card shows this**, Jared 11 Nov), `mean_peak_pct`, `peaked_5_or_more`, `peaked_10_or_more`, `median_worst_drop_pct`, `median_day60_pct`, `note` (the sample in plain words). |
| `odds_fade` | top level | `posting_bar_pct` (70; below it the edge is gone, Jared 11 Nov), `early_dip[]` (deepest dip in the first 10 days → `past_trades`, `rose10_after_day10_pct`, `rose20_after_day10_pct`, `edge` intact/gone on the +10% share) and `day10[]` (green / red on the day-10 close, same fields). ETH walk-forward tier signals only, every chart (see the 12 Nov sections). The `*_within60d_pct` fields carry the same values under their original names, kept because fields are never renamed; their window is also days 11 to 60. |
| `past_paths[]` | top level | Per asset, grade A+: `signals` and `days[]` (day 0-60: `q25_pct`, `median_pct`, `q75_pct`, percent from entry on daily closes, every past signal lined up at entry). `note` (the sample in plain words). The chart view's "where the past signals went". |

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
`feed_error` naming the exception type, then exits 1. It is a withheld feed; the one thing a reader
must handle is that `market_regime` and `scored_as_of` are empty in it, which means unknown, not "off" (the
member page shows "Market filter: unavailable"; audit #17).

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
- Every rounded figure is rounded half away from zero (62.5 -> 63), once, from the unrounded value. Precisely (13 Nov 2026 audit #20): `rounding.rnd` rounds the stored number's binary float, as Python's `Decimal(float)` and JavaScript's `toFixed` both do, so a value that reads as an exact tie at the display digit in decimal (2.675) is decided by the float (2.67). No such tie exists in the data; the pipeline and the page use the same rule, so they cannot disagree.
- A signal appears in the ledger, and in every figure built from it, only once its 60th day has closed.

### Second audit corrections (12 Nov 2026, independent audit #3)

- `cards[]` gain `typical_biggest_rise_exact_pct`, `typical_dip_before_rise_exact_pct`, `typical_deepest_dip_exact_pct`:
  the same medians unrounded. The member page shows the exact field rounded once (the same figure as the rounded field) and builds prices (entry x (1 + pct/100)) from the exact ones.
- `cards[].sample` says "all N past ... signals", not "the last N ... trades": every past signal in the sample's rule is used (ETH from 2020, when funding data begins; BTC from 2016), and none was traded.
- `example_card` (new, top level): the member site's worked example (ETH 2D, confirmed 2024-09-22) as a full card, same
  fields as `cards[]` plus `example: true` and `entry_close`, built by the forming-card rules from only the signals whose
  60th day had closed by 2024-09-22. `null` when withheld.
- `open_signals[]` now cover ETH and BTC on 1D/2D/3D/5D (they were ETH only), come from `datasets/open.csv`
  (stack_live.py), are dated by the confirmation CLOSE date (same id as the print and the card), count `days_elapsed` in
  calendar days since that close (today is the clock's UTC date, not the last candle's; audit #16), and take day-10/30/60 and best/worst from closed daily candles. Each carries `card`:
  its own full card (sample, ladder, edge). Withheld (empty) when checks fail.
- `odds_fade`: measured on daily candles from the entry close; every row's +10%/+20% share counts highs after day 10
  (days 11 to 60); the day-10 rows group by the day-10 daily close. Labelled as a general explainer.
- `past_paths`: quantiles taken on exact path values, rounded once.
- `cards[].low_day` (12 Nov 2026, audit #4): the calendar day the low printed. `low_date` stays the trough BAR's open
  date, which on a 2D+ chart can be up to one bar length minus a day earlier (1 day on 2D, 2 on 3D, 4 on 5D).
- The walk-forward tier (refresh.py `select_tier(upto=...)`, used by `odds_fade` and forward.csv's `tier`) counts only
  signals whose 60-day outcome had closed before 1 January of the year in question (it used to count signals dated
  before 1 January whose outcomes ended after it).

### Audit #5 corrections (12 Nov 2026)

- `cards[].from_entry` (also on `example_card` and `open_signals[].card`): `past_trades`, `still_rose10_pct` (the
  share of the sample that rose 10% before ever falling 25.3%) and `went_on_to_fall25_pct` (the share that fell
  25.3% BEFORE rising 10%; one that rose 10% first and fell 25.3% later is not counted. The same holds on every
  `if_it_falls_first` row; 13 Nov 2026 audit #21 wording). It is the ladder's first
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
  60th day had closed by 2024-09-22 (the same sample as `example_card`). Same shape as one `past_paths[]` entry, `note` included.
- Every 60-day window (ladder, from-entry row, paths) counts 60 CALENDAR days after the entry date, not 60 bars.

### Audit #7 corrections (12 Nov 2026)

- Every `past_trades` now has a `past_signals` twin, and `trades_a_year` a `signals_a_year` twin, with the
  same values. They count computed signals; none was traded. The old names stay because fields are never renamed.
- `if_it_misses[].up_first` counts misses whose best price within the 60 days was above entry (they went above
  entry at some point), not "above entry before ever being below it". The page says "went above entry".

### Audit #8 corrections (12 Nov 2026)

- `odds_fade.sample` now says what the sample is: ETH signals on the chart/tag pairs of the walk-forward tier
  as fixed on 1 January of the current year (`odds_fade.tier_fixed_on`), applied to every signal from 2016. That is **in-sample** (the tier was chosen on the
  outcomes of almost all of them). It is a general explainer and is not on any card.
- The 70% edge bar is tested once, on the exact share, never on the whole-percent one shown: `earlydip.csv` /
  `holdcheck.csv` gain `reached10Exact`; card ladder rows and `from_entry` gain `still_rose10_exact_pct`
  (cards.csv `l0okExact`, `l5okExact` ... `l20okExact`). The page tests the bar on those.
- **Rounding, stated precisely.** Each signal's measures are stored to 6 decimal places (the ledger); that is
  the "exact" value. Card medians and shares are computed on full-precision measures and stored to 6 places
  (`*_exact_pct`); every displayed figure is rounded once, from that value, half away from zero (on the float's binary value; see "Audit corrections").
- `verify_cards.py` now re-derives every figure computed from the card's sample (n, the shares, the medians, the eras, the timing and the ladder rows; see CARD_SPEC "What keeps it airtight" #2). The card's dates and prices (low day, confirms, must close above, latest price, entry close) and its active confluences come from stack_live.py and are not re-derived there.

### Audit #9 corrections (12 Nov 2026)

- `open_signals[]` gain `edge_level_pct` (the setup's own edge level from its card's ladder, exact shares, as a
  negative percent from the entry close: 0 if even the from-entry share is below 70%, else minus the first fall
  whose share is below 70% (e.g. -5), else empty) and
  `edge_status`: on closed daily bars after entry, whichever came first, a low at or below
  the edge level (low checked first within a day) gives "lost", a high at +10% gives "rose10" (since 12 Nov 2026
  audit #16; it was reported as "intact"), neither yet gives "intact"; "lost" from the start when the edge level
  is 0. The page's Previous signals badges read it.
- `example_if_it_misses` (new, top level): the worked example's "if it misses" figures, ETH top-grade signals
  whose 60th day had closed by 2024-09-22 (same sample as `example_card`), with a `note`. The page used to compute these itself.
- One "known by then" rule: a past signal counts once its 60th day (entry + 60) has closed by the moment in
  question. The ledger's odds-on-the-day columns used entry + 61 (one day stricter); they now use entry + 60,
  like the example. 73 ledger rows' odds-on-the-day columns moved; nothing else (baseline re-approved).
- The page types no figures: the 70% bar in How to read comes from the feed (top-level `posting_bar_pct` since audit #14; `odds_fade.posting_bar_pct` before), "about N times a year" is counted from the ledger (2020 to last year, so it rolls forward each January), and without the
  feed's `example_card` the example says "unavailable" rather than falling back to built-in numbers.
- Every forming card says it can still vanish (top grade too), and How to read says a confirmed alert is final
  while a forming heads-up can vanish.

### Audit #11 corrections (12 Nov 2026)

- No grade letters in member-facing text (CONTEXT: "the grade stays internal"). A card's `sample` now reads
  "signals of the top grade" / "signals of the same grade" instead of "graded C" / "grade A+"; the `grade` field
  itself is unchanged (it drives logic, it isn't shown).
- The chart's lead-trader note says his feed is unavailable when it can't be read, instead of "None on this one".

### Audit #14 corrections (12 Nov 2026, schema 6)

- **Schema 6.** No field changed meaning; 6 marks everything added on 11-12 Nov. New in 6: top-level `posting_bar_pct`.
- **Forming cards (`cards[]`, and so forming alerts) exist only on graded charts (1D, 2D, 3D, 5D) and only when
  the regime gate is on at the low's trough date.** A gate-off low can never confirm as a signal, and 8D is not
  graded. Before this, a forming low with the filter off (or on 8D) still produced a card and a forming alert.
  While still forming, such lows appear in `prints[]` with their "regime off" note; once confirmed with the filter
  off they are not signals and drop out of `prints[]` (13 Nov 2026 audit #21 wording).
- A forming low's tags (`prints[].tags`, the card's confirmations) use exact CT and K with the engine's EPS guard,
  the same test applied once it confirms; they used the 1-decimal display values.
- `trades_a_year` / `signals_a_year` is rounded once from the unrounded rate (was the 1-decimal rate rounded again).
- liveread.csv's "Regime gate" row reads ON / OFF on the trough date, like everything else (its "on for N days" age stays as of the entry date).
- Member page: a live setup's card says on the card itself whether its edge is lost or on track, and that its
  odds are "as of the entry close, not from today"; an edge-lost live card is no longer drawn in the live colour.
  The chart's ladder bands show n and are captioned; the chart side box restates the sample for every card.

### Audit #16 corrections (12 Nov 2026)

- `must_close_above` is rounded DOWN to the cent: every close above the shown price confirms, a close at it does
  not (rounding to nearest could show a price a cent above the real threshold).
- `open_signals[].edge_status` has a third value, "rose10": the setup rose 10% before reaching its edge level.
  "intact" now means neither has happened yet.
- `odds_fade.tier_fixed_on` and the sample sentence quote refresh.py's own tier anchor (status.csv "Tier fixed
  on"); feed_live derives nothing from its clock.
- `if_it_misses[]` rows with no misses carry empty medians (an asset/grade with signals but no miss used to crash
  extras_live.py).
- stack_live.py takes "today" from the clock's UTC date, like refresh.py: day counts were one short on a run just
  after midnight UTC, before the new day's candle existed.
- Member page: prices built from a percentage use exact decimal arithmetic; the "If it misses" row names its pool
  on every card; a feed that is down or held back, a missing ledger and a missing chart file each read as
  unavailable, not as "none" / "0 signals" / the previous setup's figures.

### Audit #17 corrections (12 Nov 2026)

- **A quiet market is not a failure.** With no low forming on any chart and no signal in its 60 days,
  stack_live.py raised COVERAGE FAILURE (no subject, so no read was evaluated) and the feed was withheld: the
  page said "held back" instead of the quiet card. By the auditor's scan that was 38 of the 271 filter-off days
  from 5 Dec 2025 to 1 Sep 2026. The coverage check now needs a subject before it requires every read.
- **The last daily bar is always today's open bar.** fetch.py builds today's bar from the hourly candles when
  the daily endpoint has not opened it yet; check_fresh.py no longer accepts yesterday's bar in the first 20
  minutes after midnight; stack_live.py fails closed if the last daily bar isn't today's. Before, such a run
  showed a setup whose confirmation bar had already closed as "forming ... can still vanish".
- A fail-closed feed has no `market_regime` or `scored_as_of`: the page shows "unavailable", never "off".
- No `-0.0` in the feed.
- Member page: a chart that can't be drawn clears everything from the setup charted before; the chart note no
  longer claims lead-trader markers (none are drawn; his trades are listed on the Now tab).

### Audit #18 corrections (12 Nov 2026)

- A forming low gets a card (and a forming alert) only when its sample has at least one past signal; a card with
  n 0 carried no figure. Early history only (a replay of Aug 2020); samples only grow.
- Member page: a share with no value prints "n/a", never "n/a%"; a setup whose card has no past signals shows
  "No odds yet" instead of a card of blanks.

### Audit #19 corrections (12 Nov 2026)

- The pipeline's card check (verify_cards.py) fails the run if any live signal in open.csv has no card in
  cards_open.csv, so `open_signals[].card` is never empty in a published feed.
- Member page: a live setup with no `card` shows "Card unavailable" and no figures (it used to build a pooled
  stand-in), and with no `edge_status` its badge reads "Status unavailable" (no page-side guess). The lead-trader
  line reads "not in" when he has trades but none on that asset. A chart file whose last bar is older than the
  feed labels that bar "Latest bar · date", not "Today".
- Replays of dates before 22 Nov 2024 carry no worked example (`example_card` empty): the example signal's 60
  days had not closed yet. The page then says "Example unavailable".

### Audit #20 corrections (13 Nov 2026)

- Candle files are checked whole before anything is scored (`fetch.history_problems`, called by
  `.github/scripts/check_candles.py` and again by `stack_live.py`, which fails closed): each daily file must
  start on the exchange's first day (ETH 2016-05-18, BTC 2016-01-01) and have no missing day after it
  (ETH 21 and 22 May 2016 excepted: the exchange has no candle for them), and every 2D-8D file must be exactly its
  daily candles bucketed. A file cut short used to pass every step.
- The member page checks the feed before using it: it must be a JSON object with a readable `generated_at`,
  or the page says "Data unavailable". With `cards_withheld` true, `cards` and `open_signals` are ignored even
  if present. `odds_fade` is used only when both of its lists are non-empty. A price that is not a number
  prints "n/a". An `edge_status` other than lost / rose10 / intact reads "Status unavailable", and a
  `market_regime` other than Bullish / Bearish reads "Market filter: unavailable".
- The worked example's chart file (`data/example_ETH-2D-2024-09-22.json`) ends with the bar that holds day 60
  (51 bars); it carried one later bar.
- Definitions that were only in code:
  - Ledger odds-on-the-day columns (`dayReach10`, `dayReach20`, `dayReach30`, `dayTouched30`, `daySurv10`,
    `dayScaled20`, `dayN`): from signals of the same asset whose 60th day (entry + 60) had closed by this
    entry's date. `dayN` is how many of those had the same grade; the columns are blank until `dayN` is 10.
    Each rate is (hits among the same grade + 5 x the rate among all those prior signals) / (same-grade count
    + 5), rounded once: the grade's rate pulled toward the asset's base rate with a weight of 5 signals.
    `dayScaled20` leaves out signals with no full year of volatility before entry, in both the grade and the base.
  - `trades_a_year` / `signals_a_year`: signals in the 70%+ tier (one per chart per date) divided by the years
    from the tier's first signal to the last date a signal could have completed its 60 days (data end minus 60
    days), rounded once.
  - `past_paths` / `example_past_paths` quartiles and medians: linear interpolation between the two nearest
    ranked values (position (n - 1) x q), on the exact path values, rounded once.

### Audit #21 corrections (13 Nov 2026): the strict check

- **One definition of a well-formed feed.** The member page holds a schema (`FEED_SCHEMA` in
  `docs/artifacts/member-site/index.html`, between the `/*FEED_SCHEMA*/` markers) covering every feed field the
  page reads: its type (percentage 0-100, whole count, day 0-60, price above zero, date, UTC time, one of a fixed
  set of words), whether it may be empty, and list lengths. Rules across fields follow: a card's two eras add up
  to its sample; a count of zero goes with an empty share and nothing else does; ladder rows are 5, 10, 15, 20;
  a signal's id matches its chart and date; a live signal's card is its own; dates are in order; no signal,
  asset or grade appears twice; quartiles are in order and days run 0 to 60; `cards_withheld` is the opposite of
  `checks.all_passed`; a withheld feed carries no cards, live signals or example; a feed that is not withheld
  states the market filter, the scored date and the posting bar.
- **The page uses a feed only if it passes, whole.** Any failure and the page reads "Data unavailable": no
  field is patched, skipped or guessed. The lead-trader file is checked against the schema's `trades` part (a
  failure reads "unavailable"), the ledger row by row (right number of cells, known chart, real date, numbers
  where numbers are read, no signal twice; a failure reads "Past signals unavailable"), and each chart file bar
  by bar (numbers, prices above zero, high and low bracketing open and close, times ascending, at least 10 bars).
- **The pipeline never publishes a feed the page would reject.** `feedcheck.py` reads the same schema block;
  `feed_live.py` runs it on the feed it has built and, on any failure, publishes the withheld (fail-closed) feed
  and exits 1. The alert log is written only after the feed has passed.
- **The run seal (`seal.py`, `datasets/manifest.json`).** refresh.py starts a new seal; each scoring step
  (refresh, grade, extras, stack, cards) checks as it starts that the steps before it finished in order and
  that no file in `datasets/` has changed since, and records its name and a SHA-256 of every file as it
  finishes. feed_live.py checks the same before publishing. A file deleted, emptied, cut, edited or replaced by
  an older copy between steps, a step that never finished, or steps out of order fail the run closed. The
  extras step is not gating: if it fails part-way its files are left out of the later checks and only the
  extras fields are withheld.
- **Step outcomes are read strictly.** When `CTZB_STEP_OUTCOMES` is set, a gating step reported as anything
  but "success" (failure, skipped, cancelled, missing) withholds the cards and alerts. Only a hand run with no
  `CTZB_STEP_OUTCOMES` at all is judged on the checks alone.
- `feed_live.py` also crashes into the fail-closed feed if `cards.csv`, `open.csv`, `cards_open.csv`,
  `cards_example.csv` or `prints.csv` is missing after every check passed (a missing `open.csv` used to read as
  "no live signals", a quiet market).
- When the refresh step failed this run, `market_regime`, `scored_as_of`, `next_buy_date`, `trades_a_year` and
  `odds_fade.tier_fixed_on` are empty: `status.csv` is then the last good run's, and a held feed used to repeat
  its market filter reading. The page shows "Market filter: unavailable".
- The page footer's "Daily candles closed through" date is the day before `scored_as_of` (the data's own date),
  not worked out from the feed's timestamp, and is left off when `scored_as_of` is empty. Its "checks passed /
  FAILED" reads `cards_withheld`, the same flag the card area uses.
- Candle files: `fetch.history_problems` also requires every candle file's rows (1D to 8D, 4H, 12H) and the
  funding series to run in strictly ascending time. A file with a row twice, or rows out of order, used to pass
  because the other checks key rows by date while the engine reads them as a list.
- Member wording: Previous signals' first group is headed "On track or rose 10%" (was "Edge intact": a setup
  that rose 10% and later fell past its edge level sat under it). How to read says the market filter is read on
  the day the bar that made the low opened, which on a 2D, 3D or 5D chart can be a few days before the low.
  With no market filter reading and nothing live or forming, the quiet card no longer says the filter is off.
- `tests/test_feed_damage.py`: damages every field the page reads in about 35 ways each (missing, empty, wrong
  type, out of range, unknown word, impossible date, lists emptied, cut, doubled or reversed) and checks that
  the page and the pipeline give the same verdict on every one, that every accepted one renders with no script
  error or raw placeholder, that rejected ones read "Data unavailable", and that every field the page reads is
  in the schema.

### Audit #22 corrections (13 Nov 2026)

- **Fields not described above:**
  - `prints[]`: `state` (confirmed / forming), `provisional` (true while forming), `low_date` (the trough bar's open
    date), `confirms_on`, `entry_close` (the confirmation close; for a forming low, the latest price, not an entry),
    `tags`, `note` ("regime on" or "regime off", plus "N bar(s) to confirm" while forming).
  - `open_signals[]`: `entry_date` (the confirmation close date), `entry_close`, `grade`, `tags`, `confirmations`
    (the grade lens codes joined by " + ", e.g. "GAP + FASTCT"; `card.confirmations` gives the same lenses in plain words), `days_elapsed` (days since the entry date; the day in progress),
    `day10_pct` / `day30_pct` / `day60_pct` (the close of that day vs the entry close, once that daily bar has
    closed; null before), `best_so_far_pct` / `worst_so_far_pct` (highest daily high / lowest daily low of the
    closed daily bars since entry, vs the entry close), `edge_level_pct`, `edge_status`, `card`.
  - `alerts[]`: `alert_id` (signal id plus event), `event` (forming / confirmed / vanished), `signal_id`, `chart`,
    `emitted_at`. Every grade. Confirmed alerts cover every chart, 8D included; forming (and so vanished) alerts
    exist only where a forming card exists: graded charts 1D-5D with the market filter on at the trough. Alerts go
    to the operator's private Telegram through the dashboard Worker; no member alert channel exists yet.
  - `alert_log`: `sha256` and `rows` of `feed/alert_log.csv` as this run left it. The next run checks the log
    against it (below).
  - `candle_check`: the candle check's time, mode, `structural_ok` and each asset's second-exchange status.
  - `confluence_windows[]`: `opened_by`, `confirmed`, `closes`, `applies_to`.
- **The strict check covers more** (page and feedcheck.py alike): every number has a range (shares 0 to 100 and
  whole where rounded; dips -100 to 0; rises 0 and up; changes above -100; prices above 0 and under 10^9; any
  other number under a million either way); a card's shares nest (never-fell-25.3% and +20% within rose-10%),
  its dip before the high is no deeper than its deepest dip, its rounded and exact shares agree, its ladder
  counts never rise; a card with no past signals (early history) has no figures and any other card has all of
  them; a live signal's day count and closed-day figures follow from its entry date, its figures sit between its
  best and worst, its status agrees with its best, worst and edge level, and its card is its own (chart, date,
  grade, entry close); the miss counts and past paths describe the same samples as `grade_odds`; the example
  card is the worked example; `odds_fade` rows are the fixed bands and checks in order (a band or check with fewer than 5 past
  signals is left out), each edge mark agrees with its share, and the tier date is stated.
- **The page checks its other files against the feed:** the ledger's top-grade rows must match `grade_odds`
  per asset (count and rose-10% share), each row must agree with itself (yes/no columns with the best move,
  deepest dip, dip before the high and day-60 change in order), every signal's 60 days must have closed by the
  feed's `scored_as_of`, and with no usable feed (down or held back) the ledger is not shown; each chart file
  must name the chart asked for, run on the chart's own steps, end no later than the feed, and its entry bar
  must close at the live signal's entry close; the example file must run on 2-day steps, its entry bar must be
  the one closing 22 Sep 2024 and its entry close the example card's; the lead-trader file must be newest first
  with nothing in the future.
- **The page draws the card as soon as the feed arrives**; the ledger, lead-trader and example files fill in as
  they come ("Loading…" meanwhile). The stale warning shows on every tab. With the feed down or held back, the
  example switch and the Chart tab say so instead of "the example's data couldn't be loaded". The example
  stands in for a quiet market only if the feed carries it.
- **Alerts on the page:** member alerts are not switched on, and the page now says so (banner and How to read); the alert promises are gone.
- **Pipeline:**
  - Every candle file is checked row by row for its whole history (prices above zero and finite, high and low
    bracketing open and close, volume not negative, on the 4H / 12H grid); ETH's daily close must be between 0.1%
    and 50% of BTC's every day (a file of one asset under the other's name fails); the funding series must be
    whole (no missing day, values between -1 and 1, ending no more than 3 days before today).
  - The run seal also covers the candle files and the funding series.
  - feed_live publishes only if `candle_check.json` says the candles passed (when step outcomes are set), treats
    any gating outcome but "success" as a failure (status fields cleared too), and a held feed carries no
    figures from the run's datasets.
  - The alert log must be exactly what the last published feed recorded (`alert_log`); a deleted, cut, emptied
    or older log fails the run instead of losing or re-sending alerts. A new log is started only on purpose
    (`CTZB_SEED_ALERT_LOG=1`). The feed is written whole or not at all, then the log; if a run dies between the
    two, the next run rebuilds the log from that feed's alerts.
  - tests/regression.py fails when its baseline is missing (it used to re-baseline and pass).
  - feedcheck.py trims text and matches digits as JavaScript does, so the page and the pipeline give the same
    verdict on unusual characters.
  - An ETH grade-A live card with no past signals yet (1-11 Sep 2020) is published with no figures ("No odds
    yet") instead of failing the strict check and holding the whole feed back.
- **Known limit:** the seal and the alert-log record guard against accidents and partial runs, not against
  someone with write access to the repo, who could rewrite a file and its record together, or the code.

### Audit #23 corrections (13 Nov 2026)

- **More inputs checked whole** (`fetch.history_problems`, so the candle check and stack_live.py both stop on them):
  the 4H and 12H files must exist, be on their own timeframe (99% of bars exactly one step apart) and be their
  asset (last close within 25% of that day's daily close); the long/short ratio and open-interest series (per
  asset) and the BTC put/call series must start on their first day, have no missing day, hold numbers in range
  and be current; every derivatives file's market columns must be its own asset's (an ETH/BTC swap fails); the
  funding series must start on 21 Jan 2020. All of them are in the run seal.
- **`next_buy_date`** is now the confirmation bar's close date (it was the bar's open date, a few days early on
  2D+ charts and across 1 January).
- **Page timing:** the card area says "Loading the latest data…" until the feed arrives; the Chart tab says
  "Loading <chart>…" while a chart file loads (the previous setup's chart is cleared), and a file that arrives
  after the member picked another setup is not drawn; the example chart says "Loading" while its file loads; a
  page left open re-checks the data's age every minute, so the stale warning appears without a reload. A chart
  file for a forming setup must close at the card's latest price. A card's `sample` must state its size.
  `tests/test_page_timing.py` covers these.
