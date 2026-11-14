# Live feed spec

`feed/ctzb_feed.json` is one JSON file that carries every computed signal, card and card figure the member page and
the alert sender use. It is the feed agreed in the plan with Joe. `feed_live.py` writes it at the end of each pipeline run. It is entry quality only: the data has
no exit, so nothing in it is a strategy return, a result or a track record. Every signal in it is a computed signal,
never a fill.

Superseded change notes are in `docs/history/FEED_SPEC_history_to_2026-11-13.md`. Card arithmetic is in
`docs/CARD_SPEC.md`.

## Where it is published and who reads it

- The pipeline commits it to `feed/` in this repository, beside `data/` and `datasets/`. The repository is public.
- The `ctzb-feed` Worker mirrors it from GitHub every 15 minutes.
- The `ctzb-site` Worker serves the mirror's copy to the member page as `/data/ctzb_feed.json`.
- The `ctzb-dashboard` Worker reads `alerts` from the mirror on its cron and sends each `alert_id` once to the
  operator's private Telegram, remembering what it sent. It sends nothing while `alerts_withheld` is true.
- The `ctzb-scheduler` health monitor reads `generated_at`, `cards_withheld`, `checks.failed_steps`, `extras_withheld`
  and `candle_check.kraken` from the mirror.

## When it is written

- The `ctzb-scheduler` Worker dispatches `daily.yml` 13 minutes after each 4-hour close (00, 04, 08, 12, 16 and 20
  UTC), with a backup at 43 minutes that the workflow's gate skips when the first run landed the candle. The automatic
  re-run after a failure, the watchdog's re-dispatch and a manual run are not gated and also write a feed.
- In each run: fetch, the freshness check and the candle check must pass, or the job stops and no feed is written.
  Then refresh, grade, extras, stack, cards and regress run (each may fail without stopping the job), then
  `feed_live.py`, with every step's outcome passed in `CTZB_STEP_OUTCOMES`.
- The feed is written whole or not at all (a temporary file, then a rename). The commit step commits it.
- `CTZB_NOW` replaces the clock when a test replays a past run.

## Rules

- **Fields are only ever added, never renamed or removed.** A field whose name does not fit what it holds keeps its
  name and gains a correctly named twin with the same value (Aliases, below).
- **`schema_version` is 6.** It is the constant `SCHEMA_VERSION` in `feed_live.py`, set by hand and written into every
  feed, the fail-closed feed included. Nothing in the pipeline, the page or the Workers computes or reads it (the
  strict check does not); two tests assert it is 6. It changes
  only when the constant is edited; `alert_log` and `alert_log_carry` are schema 6 fields that came without a bump.
- **It computes no figure.** It repackages the datasets the same run wrote. Its own work is: the time stamp, the
  schema version, the posting bar constant, the aliases, the label and note texts, which alerts are new, and the alert
  log record.
- **Every card, print, live signal, grade row, alert and extras block carries `label`**: computed signal, not a fill,
  entry quality only, not a strategy return or a track record.
- **Dates** are YYYY-MM-DD (UTC calendar days); times are ISO 8601 UTC ending in `Z`, except `candle_check.checked_at`,
  which ends in `+00:00`. Every signal is dated by its
  confirmation bar's close date (the entry). The exceptions are named where they occur.
- **Units.** A share is a percent, 0 to 100 (a whole number in the rounded fields). A change is a percent from the
  entry close (negative below it). Prices are USD (Coinbase ETH-USD and BTC-USD candles), rounded to the cent. Day
  counts are calendar days.
- **The 60-day window** is the 60 calendar days after the entry date, on daily candles. A past signal is counted only
  once its 60th day (entry + 60) has closed by the date in question.
- **Rounding: one rule.** `rounding.rnd` rounds half away from zero, once, from the unrounded value, on the float's
  exact binary value (as JavaScript's `toFixed` does, so the page and the pipeline agree). Shares are whole numbers;
  median moves and changes 1 decimal; median days (`typical_day_*`) whole days; prices 2 decimals; `*_exact_pct` fields 6 decimals. `must_close_above` alone is
  rounded down to the cent. The feed never holds `-0.0`.
- **Exact vs shown.** The ledger stores each signal's measures to 6 decimals. Card medians and shares are computed at
  full precision. The `*_exact_pct` fields carry them to 6 decimals; the rounded fields are for display. The 70%
  posting bar is tested once, on the exact share. Prices built from a percentage (entry x (1 + pct/100)) use the exact
  field.
- **Grades** (A+, A, B, C) are in the feed. The member page never shows a grade letter; it says "top grade" or "not
  top grade".
- **`grade_odds` is pooled context.** It is never the number for a live setup (CONTEXT, "Never quote the pooled grade
  alone"); the card is.
- **`if_it_falls_first` is information for a discretionary exit**, never a stop rule.

### Aliases

| Preferred | Legacy alias, same value | Where |
|---|---|---|
| `past_signals` | `past_trades` | every object that has `past_trades`; the twin sits right after it |
| `signals_a_year` | `trades_a_year` | top level |
| `rose10_after_day10_pct`, `rose20_after_day10_pct` | `rose10_within60d_pct`, `rose20_within60d_pct` | `odds_fade.early_dip[]`, `odds_fade.day10[]`; both count days 11 to 60 |

`past_trades` and `trades_a_year` count computed signals; none of them is a fill. The strict check and the member page
read `past_trades`. `if_it_misses[].up_first` keeps its name; it counts misses that went above entry at some point in
the 60 days.

## Top level

"Strict" is the field's type in the strict check (below); `?` means it may be null or missing; a blank cell means the
strict check does not read the field.

| Field | Strict | Meaning and source |
|---|---|---|
| `schema_version` | | 6 |
| `generated_at` | ts | UTC time `feed_live.py` wrote the file |
| `posting_bar_pct` | pcti? | 70, the constant `POSTING_BAR`: a card ladder share below it means the edge is gone. The same number as refresh.py `WINMIN`, stack_live.py `EDGE_BAR` and carddesign.py `POST_BAR` |
| `scored_as_of` | date? | status.csv "Scored as of": the clock's UTC date when refresh.py ran, the day of the open daily bar |
| `label` | | The computed-signal label |
| `checks` | `all_passed` bool | Below |
| `cards_withheld` | bool | True when `checks.all_passed` is false |
| `alerts_withheld` | | Same value as `cards_withheld` |
| `alerts_seeded` | | True only on a run made with `CTZB_SEED_ALERT_LOG=1` that passed every check |
| `alerts[]` | | Alerts new in this generation (Alerts, below) |
| `market_regime` | Bullish or Bearish? | status.csv: the regime gate `rsi_regime(BTC_2D, 8, 13, 60, 41)` on the scored date |
| `next_buy_date` | | status.csv: a YYYY-MM-DD date or the text "none ahead". The earliest confirmation close date, today included, of a forming low on an ETH chart that carries a walk-forward tier tag, whatever the regime gate reads. A computed date, not a planned buy |
| `trades_a_year` (`signals_a_year`) | | status.csv: text "N on average", N = ETH tier signals per year rounded once, or "—" when the tier has fewer than 4 scored signals |
| `cards[]` | list of card | One card per forming low that qualifies (Cards, below) |
| `example_card` | card? | The worked example (Cards, below) |
| `prints[]` | | Below |
| `open_signals[]` | list | Below |
| `confluence_windows[]` | | Below |
| `grade_odds[]` | list | Below |
| `candle_check` | | Below |
| `extras_withheld`, `if_it_misses[]`, `odds_fade`, `past_paths[]`, `example_if_it_misses`, `example_past_paths` | (not read), list, object?, list, miss?, path? | Member-card extras, below |
| `alert_log` | | `sha256` and `rows` of `feed/alert_log.csv` as this run leaves it; null when there is no log |
| `feed_error`, `alert_log_carry` | | Fail-closed feed only (below) |

`next_buy_date` and `trades_a_year` come from refresh.py's ETH walk-forward tier: the ETH chart/tag pairs with at
least 8 past signals (`NMIN`) of which at least 70% (`WINMIN`) closed above entry on the chart's last bar within 60
days of the confirmation bar's open date, counting only signals whose 60 days had closed before 1 January of the
current year. The rate divides the tier's signals (one per chart per date) by the years (at least a quarter) from the
first one's confirmation bar open date to the data's end minus 60 days. If the tier has no signal at all, refresh.py
stops and the feed is held. 2D+ bars restart on 1 January, so a year's last bar can be short; the confirmation close
date follows that rule.

## Cards

A card is one setup's odds, from its own like-for-like sample. stack_live.py builds three kinds with one function.
verify_cards.py re-derives every figure computed from the sample (counts, shares, medians, eras, timing, ladder) from
the ledger and the 1D candles and fails the run on any difference; the dates, prices, `grade`, `confirmations`, the
`sample` wording and `active_confluences` come from stack_live.py alone (verify_cards.py uses the card's grade, lenses
and sample rule to rebuild the sample).

- **`cards[]`: forming lows.** Only on a graded chart (1D, 2D, 3D, 5D), only when the regime gate is on at the low's
  trough date, and only when the sample has at least one past signal.
- **`open_signals[].card`: live signals.** Every signal on a graded chart within its 60 days has one; verify_cards.py
  fails the run if one is missing. Its sample can be empty in early history: then it has `past_trades` 0 and no
  figures.
- **`example_card`: the worked example**, the ETH 2D signal confirmed 22 Sep 2024 (`ETH-2D-2024-09-22`), built by the
  forming-card rules from only the signals whose 60th day had closed by that date, plus `example: true`. Null when
  held back, and in a replay dated before 22 Nov 2024 (its 60 days had not closed).

**The sample** (`sample`, `past_trades`): the past signals on this chart with exactly the same confirmations, if there
are 15 or more; else this chart's signals of the same grade, if 15 or more; else the same grade across the asset's
graded charts. ETH samples use only signals with funding data (from 2020); BTC samples use its full history. `sample`
states the rule and the count in words, with no grade letter ("of the top grade" / "of the same grade").

| Field | Strict | Meaning |
|---|---|---|
| `signal_id` | str | Chart and confirmation date, e.g. `ETH-1D-2026-11-12`. A forming card, its print once confirmed and its live signal share it. A trough that slides is a new signal with a new id |
| `chart`, `asset`, `timeframe` | chart, asset, tf | e.g. "ETH 2D", "ETH", "2D" |
| `low_date` | date | The trough bar's open date |
| `low_day` | date | The day of the lowest daily low within the trough bar's span (up to one bar length minus a day after `low_date`) |
| `confirms_on` | date | The confirmation bar's close date (ei = ti + 3) |
| `bars_to_confirm` | n? | Forming: how many bars after the open bar the confirmation bar is: 0 (the open bar confirms at its close), 1 or 2. Live and example: null |
| `must_close_above` | px? | Forming only: the confirmation-bar close above which the low confirms (a close at it does not), rounded down to the cent. Exact when the confirmation bar is the open bar (`bars_to_confirm` 0); an estimate when it is the next bar (1), assuming the open bar closes at the latest price; null when further off |
| `price_now` | px? | Forming: the latest price of the chart's open bar, a stand-in for the entry. Live: the latest price of the open daily bar. Example: null |
| `entry_close` | px? | Live and example: the entry close. Forming: null |
| `grade` | grade | A+, A, B or C: how many of the asset's lenses are present (0-1 C, 2 B, 3 A, 4+ A+) |
| `confirmations` | | The lenses present, in plain words joined by "; ", or "none" |
| `sample`, `past_trades` | str, n | The sample and its size |
| `rose10_within60d_pct` | pcti? | Share whose high reached +10% within 60 days. The big number |
| `rose10_never_fell25_within60d_pct` | pcti? | Share that reached +10% and never fell 25.3% within 60 days. The line under the big number |
| `rose20_within60d_pct` | pcti? | Share that reached +20% |
| `beat_normal_move_pct` | | Share whose best move reached 20% x (365-day volatility at entry / the asset's 2016-21 median of it); signals with no 365 days of volatility before entry are left out |
| `fell30_within60d_pct` | pcti? | Share whose deepest dip reached -30% |
| `typical_biggest_rise_pct` (`_exact_pct`) | `_exact_pct` rise? | Median best move within 60 days |
| `typical_dip_before_rise_pct` (`_exact_pct`) | `_exact_pct` dip? | Median lowest point vs the entry close before the 60-day high. Not a pullback from profit |
| `typical_deepest_dip_pct` (`_exact_pct`) | `_exact_pct` dip? | Median deepest dip within 60 days |
| `typical_day_first_rose10`, `typical_day_first_rose20` | | Median day of the first +10% / +20% high, among signals that got there |
| `typical_day_of_60d_high`, `typical_day_of_deepest_dip` | day? | Median day of the 60-day high / of the deepest dip |
| `before_2022`, `since_2022` | era | `past_trades` and `rose10_never_fell25_within60d_pct` for the signals before / from 1 Jan 2022 |
| `from_entry` | `still_rose10_pct` pcti?, `still_rose10_exact_pct` pct? | The ladder's first row: `past_trades`, `still_rose10_pct` and `still_rose10_exact_pct` (share that rose 10% before ever falling 25.3%), `went_on_to_fall25_pct` (share that fell 25.3% before rising 10%) |
| `if_it_falls_first[]` | 4 rungs | Rows for `fell_pct` 5, 10, 15, 20: `past_trades` (signals that fell that far before rising 10%), and of those `still_rose10_pct` / `still_rose10_exact_pct` (then rose 10% before falling 25.3%) and `went_on_to_fall25_pct` (fell 25.3% first). One that rose 10% first and fell 25.3% later counts as having risen |
| `active_confluences[]` | | Forming cards only (empty on live and example cards). Below |
| `example` | | `example_card` only: true |

Every share, median and timing figure over a count of 0 is null. Each era, ladder row and confluence row has its own
count; a screen shows that count beside the figure. The ladder walks the daily bars of the 60 days after entry and
checks a day's low before its high (the cautious reading: a daily bar does not say which came first). Rose 10% is a
high at or above entry x 1.10; fell 25.3% is a low at or below entry x 0.747.

**`active_confluences[]`**: every documented confluence cell (analysis/grokpack.json) that will be active when this
setup confirms: this setup carries the cell's tag, and the cell's confirming chart printed a signal with the cell's
confirming tag 0-10 days before `confirms_on`. Weak ones are included. Each row is its own sample, this chart's whole
history, never blended into the card number; rows overlap and are not added. Fields: `after` (confirming chart and
tag), `after_confirmed`, `window_closes` (confirmed + 10 days), `applies_to` (which of this chart's signals the row
covers), `past_trades`, `rose20_within60d_pct`, `rose10_within60d_pct`, `fell30_within60d_pct`, `note`. Sorted by
`past_trades`, largest first. Under 15 is too few to lean on.

## prints[]

stack_live.py, for all ten charts (ETH and BTC, 1D to 8D): each chart's last 3 signals, plus its forming low if it has
one. A signal is a low that confirmed with the regime gate on at its trough date; a low that confirms with the gate
off is not a signal and is not listed. A forming low is listed whatever the gate reads. stack_live.py's `liveread.csv`
reads the gate on the trough date too (its "on for N days" age is as of the entry date, or today for a forming low).

| Field | Meaning |
|---|---|
| `signal_id`, `chart`, `label` | As on a card |
| `state`, `provisional` | "confirmed" or "forming"; `provisional` is true while forming |
| `low_date`, `confirms_on` | The trough bar's open date; the confirmation close date |
| `entry_close` | The confirmation close; for a forming low, the latest close (not an entry) |
| `tags` | Bucket, diamond type and prime dot, joined by " + ". A forming low's tags use the exact CT and K with the engine's EPS guard, the test applied once it confirms |
| `note` | "regime on" or "regime off" (the gate on the trough date), plus "; N bar(s) to confirm" while forming |

## open_signals[]

stack_live.py `open.csv`: every signal on a graded chart (1D, 2D, 3D, 5D), ETH and BTC, every grade, whose
confirmation close is 0 to 60 days before today (the clock's UTC date). The member page shows the top-grade ones.

| Field | Strict | Meaning |
|---|---|---|
| `signal_id`, `chart`, `label` | str, chart, str | As on a card |
| `entry_date`, `entry_close` | date, px | The confirmation close date and price |
| `grade`, `tags` | grade, text | As on a card / print |
| `confirmations` | text | The lens codes joined by " + " (e.g. "GAP + FASTCT"), or "-"; `card.confirmations` gives them in words |
| `days_elapsed` | day | Days since the entry date; the day in progress |
| `day10_pct`, `day30_pct`, `day60_pct` | chg? | That day's daily close vs the entry close, once its bar has closed; null before. `day60_pct` is always null: a signal leaves the list on the day its 60th daily bar closes |
| `best_so_far_pct`, `worst_so_far_pct` | chg? | Highest daily high / lowest daily low of the closed daily bars since entry, vs the entry close |
| `edge_level_pct` | dip? | From the card's ladder, exact shares: 0 if the from-entry share is below 70%; else minus the first `fell_pct` whose share is below 70%; else null |
| `edge_status` | lost, rose10 or intact | Walking the closed daily bars after entry: a low at or below the edge level (checked first within a day) gives "lost"; a high at +10% gives "rose10"; neither yet gives "intact". "lost" from the start when the edge level is 0 |
| `card` | card? | This signal's own card |

## confluence_windows[]

stack_live.py `windows.csv`: every window open today, from each signal (all ten charts) confirmed 0-10 days ago, and
each bullish Stoch divergence of the last 10 days on a chart that has lower charts, sorted by closing date.
`opened_by` (chart), `confirmed` (date), `closes` (confirmed + 10 days), `applies_to` (what it counts toward: the
agreement count, the BTC3 or BTCX lens, a near miss, a confluence cell, or the DIVH flag).

## grade_odds[]

grade_live.py `grades.csv`: per asset and grade (A+, A, B, C), the graded charts pooled (ETH from 2020, where funding
data exists; BTC full history; 60-day windows that have closed), plus four ETH flag rows whose `grade` is "HTF
divergence", "no HTF divergence", "diamond or prime dot" or "no diamond or prime dot" (a flag row with no signals is
left out). Each: `past_trades`, `rose10_within60d_pct`, `rose10_never_fell25_within60d_pct`, `rose20_within60d_pct`,
`median_deepest_dip_pct`, `sample` (that row's own first and last signal date, "YYYY-MM-DD to YYYY-MM-DD"), `note`. A
grade with no signals has `past_trades` 0 and null figures.

## Member-card extras

extras_live.py writes these from the same run's ledger, `earlydip.csv` and `holdcheck.csv` (arithmetic in
`analysis/carddesign.py`). It deletes its own previous outputs first, so a failed step never leaves an older copy.
They never gate cards or alerts.

**`extras_withheld`** is true when the run is held back, when the extras step is reported as anything but "success"
(an absent extras outcome counts as success), or when `missstats.csv`, `pastpaths.csv` or `oddsfade.csv` is missing.
Then `if_it_misses`, `past_paths`, `odds_fade.early_dip` and `odds_fade.day10` are empty and `example_if_it_misses`
and `example_past_paths` are null.

**`if_it_misses[]`**: per asset that has top-grade signals, per grade (A+, A, B, C) with at least one signal. A miss
is a signal that did not rise 10% within 60 days (`miss_rule` says so). `signals`, `misses`, `up_first` (misses whose
best price within the 60 days is above entry), `median_peak_pct` (the median best move of the misses; the figure the
card shows), `mean_peak_pct`, `peaked_5_or_more`, `peaked_10_or_more`, `median_worst_drop_pct`, `median_day60_pct`
(day-60 close vs entry close), `miss_rule`, `note`. With no misses the medians are null.

**`odds_fade`**: a general explainer, never on a card (a card uses its own ladder). ETH signals on the chart/tag pairs
of the walk-forward tier as fixed on 1 January of the current year (`tier_fixed_on`, status.csv's own anchor), applied
to every signal on those pairs from 2016. That is in-sample: the tier is chosen on the outcomes of almost all of them.
Measured on daily candles from the entry close.
- `early_dip[]`: grouped by the deepest dip in days 1-10 (`band`: "shallower than -2%", "-2% to -5%", "-5% to -10%",
  "-10% to -20%", "worse than -20%").
- `day10[]`: grouped by the day-10 daily close vs entry (`check`: "green on day 10" / "red on day 10").
- Each row: `past_trades`, `rose10_after_day10_pct` and `rose20_after_day10_pct` (share whose high reached +10% / +20%
  in days 11 to 60), `edge` ("intact" when the exact +10% share is at least 70, else "gone"). A band or check with
  fewer than 5 signals is left out.
- Also `label`, `posting_bar_pct` (70), `tier_fixed_on`, `sample` (the sentence above), `edge_measured_on` ("rose 10%
  after day 10 (days 11 to 60)").

**`past_paths[]`**: the past-signal cloud on the Chart tab (`example_past_paths` draws the example's). Per asset with
top-grade signals: `grade` "A+", `signals`, `note`, and `days[]` for day 0 to 60:
`q25_pct`, `median_pct`, `q75_pct`, percent from the entry close on the daily close of the k-th calendar day after the
entry date, every top-grade signal lined up at entry. A signal without 60 consecutive daily closes after entry is
skipped. Quartiles and medians interpolate linearly between the two nearest ranked values (position (n - 1) x q), on
the exact path values, rounded once.

**`example_if_it_misses`, `example_past_paths`**: the same figures for the worked example, from only the ETH top-grade
signals whose 60th day had closed by 22 Sep 2024 (the example card's sample). `example_if_it_misses` has `signals`,
`misses`, `up_first`, `median_peak_pct`, `median_worst_drop_pct`, `median_day60_pct`, `miss_rule`, `note`.

## checks and candle_check

| Field | Meaning |
|---|---|
| `checks.passed` | `datasets/stack_status.txt` exists, is not empty and has no line containing FAILED. stack_live.py writes it; verify_cards.py appends its cross-check line |
| `checks.lines` | That file's lines |
| `checks.steps` | Every step outcome passed in `CTZB_STEP_OUTCOMES` (refresh, grade, extras, stack, cards, regress) |
| `checks.failed_steps` | The gating steps (refresh, grade, stack, cards, regress) not reported as "success"; `["feed"]` in the fail-closed feed |
| `checks.all_passed` | `checks.passed` and no failed gating step |
| `candle_check` | From `datasets/candle_check.json` (`.github/scripts/check_candles.py`): `checked_at`, `cross_mode`, `structural_ok`, and `kraken`, each asset's second-exchange status: "ok", "over_threshold" or "unavailable". An unreachable Kraken never fails a run, so this is where a monitor sees it skipped. Null when the file is missing or unreadable |

## Alerts and the alert log

`alerts[]` lists the events new in this generation. Each: `alert_id` (`{signal_id}:{event}`, fixed for that event
forever), `event`, `signal_id`, `chart`, `emitted_at` (this feed's `generated_at`), `label`.

- `forming`: a forming card appeared (graded charts, regime gate on at the trough), unless that signal already has a
  forming or confirmed alert.
- `confirmed`: a signal confirmed: a confirmed print (any of the ten charts, 8D included) or a row of refresh.py's
  `forward.csv` (ETH, every signal from 1 Jan 2026).
- `vanished`: a signal that had a forming alert and no confirmed or vanished alert is neither forming nor confirmed
  (the trough slid, or the setup stopped qualifying).

Every grade alerts. `feed/alert_log.csv` (`alert_id`, `event`, `signal_id`, `chart`, `emitted_at`) records every alert
ever emitted and is committed with the feed, so an alert appears in exactly one generation. That generation is read
many times, so **a sender records every `alert_id` it sends and never sends one twice.**

- **Withheld is not dropped.** When the run is held back, `alerts` is empty and nothing is logged; the next run that
  passes every check emits what is pending.
- **Seeding.** A new log starts only on a run with `CTZB_SEED_ALERT_LOG=1`: it records every forming and confirmed
  signal with `emitted_at` "seeded", alerts on none of them and sets `alerts_seeded`.
- **The log must be the one the last feed left.** On every run that is not seeding, `feed_live.py` compares the log's
  SHA-256 with the previous feed's `alert_log`. A match passes. Otherwise it appends the previous feed's
  `alert_log_carry` and `alerts`; if that matches, the last run died between the feed and the log, and the log is
  rebuilt. Anything else (deleted, cut, emptied or older) fails closed. With no previous record, a missing log fails
  closed and an existing one is accepted.
- **Order.** The feed is written only after it passes the strict check, then the log. If the log cannot be written,
  the feed stays published and the run exits non-zero; the next run rebuilds the log from it.

## When the feed is held back

### Held feed

`checks.all_passed` is false when `stack_status.txt` is missing, empty or has a FAILED line, or when
`CTZB_STEP_OUTCOMES` is set and any gating step (refresh, grade, stack, cards, regress) is reported as anything but
"success" (failure, skipped, cancelled, missing). A hand run with no `CTZB_STEP_OUTCOMES` is judged on
`stack_status.txt` alone. A quiet market (no forming low on any chart and no signal in its 60 days) is not a failure:
the stack's coverage check requires every documented read only when there is a subject. A held feed is still
published, with:

- `cards_withheld`, `alerts_withheld` and `extras_withheld` true; `alerts` empty and nothing logged;
- `cards`, `prints`, `open_signals`, `confluence_windows`, `grade_odds`, `if_it_misses`, `past_paths`,
  `odds_fade.early_dip` and `odds_fade.day10` empty; `example_card`, `example_if_it_misses` and `example_past_paths`
  null;
- `scored_as_of`, `market_regime`, `next_buy_date`, `trades_a_year`, `signals_a_year` and `odds_fade.tier_fixed_on`
  null (status.csv may be the last good run's);
- `checks`, `candle_check`, `posting_bar_pct` and `alert_log` filled as usual.

### Fail-closed feed

When the checks pass, `feed_live.py` also requires, and raises an error on any failure:

- with `CTZB_STEP_OUTCOMES` set, `candle_check.json` saying `structural_ok` true;
- `cards.csv`, `open.csv`, `cards_open.csv`, `cards_example.csv` and `prints.csv` all present;
- an intact run seal: refresh, grade, stack and cards finished in order, and extras too unless it is reported as
  "failure" (its files are then left out of the check), and no sealed file changed, appeared or went missing since the
  step that wrote it;
- a seal started no more than 2 hours before this run, and not after it.

On every run it also checks the alert log (above, not on a seeding run) and the built feed against the strict check.
Any exception in `feed_live.py` (these, or a crash) overwrites the feed with the fail-closed feed and exits 1. It has
`posting_bar_pct` 70, `cards_withheld`, `alerts_withheld` and `extras_withheld` true, `checks.passed` and
`checks.all_passed` false, `checks.lines` empty, `checks.steps` as passed, `checks.failed_steps` `["feed"]`,
`feed_error` (the exception's type name), every list except `alert_log_carry` empty, `candle_check`, `example_card`, `example_if_it_misses`,
`example_past_paths`, `scored_as_of`, `market_regime`, `next_buy_date` and `trades_a_year` null, and `odds_fade` with
only `label`, `posting_bar_pct`, a null `sample` and empty lists. It has no `alerts_seeded`, `signals_a_year`,
`odds_fade.tier_fixed_on` or `odds_fade.edge_measured_on`. It carries `alert_log` (the last published feed's record,
or the log's own state if there is none) and `alert_log_carry` (alerts the last published feed sent that the log does
not hold). A null `market_regime` or `scored_as_of` means unknown, never "off".

## The run seal

`seal.py`, file `datasets/manifest.json`: `steps`, `files` (name to SHA-256) and `started_at`.

- refresh.py starts a new seal (`started_at` is its UTC start time) before it writes anything.
- Each later scoring step (grade, extras, stack, cards) checks as it starts that the steps before it finished in order
  and that no sealed file has changed, appeared or gone since; on finishing it records its name and a SHA-256 of every
  file. A step that already ran in this run fails.
- Sealed files: everything in `datasets/`, the candle files in `data/`, the funding, long/short and open-interest
  series in `data/derivs/` and `data/options/BTC_pcr_daily.csv`.
- extras is not gating: a later step runs without it, and when it did not finish its files are left out of the check.
- `feed_live.py` refuses a seal started more than 2 hours (`MAX_RUN_HOURS`) before it runs, or after it, so running it
  again on its own later cannot publish the last run's scoring as fresh.
- The seal and the alert-log record guard against accidents and partial runs, not against someone with write access to
  the repository.

## Inputs checked before scoring

`.github/scripts/check_candles.py` stops the job when `fetch.history_problems` reports anything; when any of the last
90 closed daily bars is missing, has bad prices or zero volume, or any of the last 540 4H bars has bad prices; or, in
enforce mode, when any of the last 30 closed days differs from Kraken's close by more than 0.5%. stack_live.py runs
`fetch.history_problems` again and fails the stack step on any problem. It requires:

- every candle file (1D to 8D, 4H, 12H) present, ending with a whole line, with a volume column and every row exactly
  the header's cells; every cell readable; prices finite and above zero; high and low bracketing open and close;
  volume not negative; times on the bar grid (daily and multi-day bars at midnight UTC) and strictly ascending;
- each daily file starting on the exchange's first day (ETH 2016-05-18, BTC 2016-01-01) with no missing day after it
  (ETH 2016-05-21 and 2016-05-22 excepted), and every 2D-8D file exactly its daily candles bucketed, volume included;
- 4H and 12H files on their own timeframe (99% of bars one step apart) and their own asset (last close within 25% of
  that day's daily close); ETH's daily close between 0.1% and 50% of BTC's every day;
- the funding series from 2020-01-21, the long/short ratio from 2020-05-31 and open interest from 2022-09-13 (per
  asset), and BTC put/call from 2016-11-01: no missing or repeated day; the columns the scorer reads in range (funding:
  `funding_mean` on every row and `funding_oi_weighted` where filled, both between -1 and 1; the FUND read takes
  `funding_oi_weighted` first, the FCOOL read `funding_mean`); every other cell blank or a finite number; whole rows;
  derivatives columns of their own asset. stack_live.py alone also requires each series' read column to be filled up
  to no more than 1 day before today (put/call: 2 days, it writes completed days only): the funding reads take the
  last known day as today's and the long/short and put/call reads go blank when their day is missing, so a series
  further behind can change the forming cards. A series behind that lag holds the run's cards back but does not stop
  the job, so the candles are still committed and the derivatives fetch that runs after the feed can catch up. In a
  normal run the derivatives end 0 or 1 day behind.

The freshness check requires the last daily bar to be today's open bar and the last 4H bar to be the current 4-hour
bar; fetch.py builds it from the hourly candles
when the daily endpoint has not opened it. stack_live.py fails if the last daily bar is not today's. fetch.py, fetch_derivs.py and fetch_pcr.py,
which write every file the scoring steps read, write each file whole or not at all.

## The strict check

One definition of a well-formed feed: `FEED_SCHEMA` in `docs/artifacts/member-site/index.html`, between the
`/*FEED_SCHEMA*/` and `/*END_FEED_SCHEMA*/` markers. The page applies it; `feedcheck.py` reads the same block and
applies the same rules, trimming text and matching digits as JavaScript does.

- **Types:** `pct` 0-100; `pcti` a whole number 0-100; `num` finite, under a million either way; `n` a whole number from 0
  to under a million; `day` a whole number 0-60; `px` above 0 and under 10^9; `dip` -100 to 0; `rise` 0 to 100,000; `chg` above
  -100 up to 100,000; `share` and `lev` above 0 up to 100; `date`; `ts`; `str` non-empty text; `text`; `bool`; one of
  a fixed set of words. A key marked `?` may be null or missing. A list has a minimum length and, where the
  schema gives one, a maximum.
- **Cards:** chart is asset + timeframe; `signal_id` matches chart and `confirms_on`; the two eras add up to the
  sample; an era's or ladder row's count is 0 exactly when its shares are null; ladder rows are 5, 10, 15, 20 with
  counts that never rise and never exceed the sample; a card with `past_trades` 0 has no checked figures and any other
  card has all of them; the never-fell-25.3% and +20% shares sit within the +10% share; the from-entry share sits between the never-fell-25.3%
  share and the +10% share; a ladder row's two shares add to at most 101; the dip before the high is no
  deeper than the deepest dip; rounded and exact shares agree; `sample` states the sample size; `low_date` <=
  `low_day` <= `confirms_on`; a forming card does not confirm before the feed's date.
- **Feed:** `cards_withheld` is the opposite of `checks.all_passed`; a withheld feed has no cards, live signals or
  example card; a feed that is not withheld states `market_regime`, `scored_as_of` and `posting_bar_pct`;
  `scored_as_of` is not after `generated_at`; no signal id, asset/grade pair or past-paths asset appears twice.
- **Live signals:** id matches chart and entry date; entry not after the feed's date; `days_elapsed` equals the days
  from entry to `generated_at`'s date; each day-10/30/60 figure present exactly when that day has passed; figures
  within best and worst; `edge_status` agrees with best, worst and edge level; the card is its own (chart, date,
  grade, entry close).
- **Grade rows:** figures present exactly when the count is above 0; the never-fell-25.3% and +20% shares sit within
  the +10% share.
- **Extras:** miss counts nest and medians are null exactly when there are no misses; past paths run day 0 to 60 with
  quartiles in order; `if_it_misses` and `past_paths` describe the same samples as `grade_odds`; the example card is
  `ETH-2D-2024-09-22` and the example extras describe its sample; `odds_fade` rows are the fixed bands and checks in
  order, each edge mark agrees with its share against the bar, and filled rows come with `tier_fixed_on`.

`feed_live.py` runs it on every feed it builds and never publishes one that fails.

## What the member page does with the feed and its other files

The page fetches the feed, `ledger.csv`, the lead-trader file, the example chart file and chart files from the site
Worker, uncached.

- **Feed.** Used only if it passes the strict check whole; otherwise there is no feed and the page reads "Data
  unavailable" / "Feed unavailable". Nothing is patched, skipped or guessed. With `cards_withheld` true it shows no
  card and no live signal ("Setups held back"). `odds_fade` is used only when both of its lists are non-empty. A
  missing `market_regime` reads "Market filter: unavailable". The footer's "Daily candles closed through" date is the
  day before `scored_as_of`, left off when it is null; its "checks passed / FAILED" reads `cards_withheld`. A feed
  older than 5 hours shows a stale warning on every tab, with its hour count kept current; a feed written before the
  latest daily close (00:00 UTC) shows a note that the close has passed and what it says about that bar is out of
  date. Both are re-checked every minute on the viewer's clock; when both apply, the 5-hour note shows. The only other
  check that uses the viewer's clock is the lead-trader file's "trade in the future" test. The example
  the page switched on by itself for a quiet market goes off when either appears; one the member switched on stays.
- **What it reads.** Live signals of the top grade, and forming cards of every grade (top grade first, the rest ranked
  by `rose10_within60d_pct`). The exact `typical_*_exact_pct` fields, never the rounded ones; prices built from them
  in exact decimal arithmetic. The 70% bar from `posting_bar_pct`. A card with no past signals shows "No odds yet"; a
  live signal with no card shows "Card unavailable". A share with no value, or a price that is not a number, prints
  "n/a". The worked example comes only from `example_card` ("Example unavailable" without it) and stands in for a
  quiet market only when the feed is clean, fresh and carries it. The quiet card's "about N times a year" is counted
  from the ledger's top-grade rows, 2020 to the last full year whose signals have all had their 60 days close by
  `scored_as_of` (the year before the year of `scored_as_of` minus 60 days).
- **How a card is worded.** Under the big number, the card's sample, which covers every figure from it; each ladder
  row and era shows its own n, and the "If it misses" row names its pool. Every forming card says it can still vanish
  before it confirms; when the confirmation bar is the next bar, its price reads "about $X (an estimate until the
  current bar closes)". A live card says on the card whether its edge is lost, it rose 10%, or it is on track, and
  that its odds are as of the entry close, not from today; an edge-lost card is not drawn in the live colour. The
  chart's ladder bands show their n, and its side box restates the sample. The market filter pill reads Bullish as on
  and Bearish as off; with no reading the quiet card does not call the filter off. Previous signals reads "as of the
  latest data · reload for each 4-hour update", with a first group headed "On track or rose 10%". How to read says a
  confirmed setup is final while a forming one can vanish, and that the filter is read on the day the bar that made
  the low opened.
- **Ledger.** Unavailable ("Past signals unavailable"), never partly shown, when it is missing, a row has the wrong
  number of cells, a top-grade row is malformed or inconsistent with itself (known chart, real date, numbers, yes/no
  columns agreeing with the best move, dips and day-60 change in order), a signal appears twice, its top-grade rows do
  not match `grade_odds` per asset (count and +10% share), a signal's 60 days had not closed by `scored_as_of`, or
  there is no usable feed.
- **Chart files.** Not drawn ("Chart data unavailable") unless the file names the chart asked for, has at least 10
  bars of numbers, prices above zero, high and low bracketing open and close, times ascending, runs on the chart's own
  steps (2D+ bars restart on 1 January), ends no later than `generated_at`, and closes at the card's `price_now`; for
  a live signal its entry bar must close at `entry_close`. The site Worker refuses a candle file with a row that is
  not numbers. A file that arrives after the member picked another setup is not drawn. A chart that cannot be drawn
  clears everything from the setup charted before. A forming setup's file whose last bar is older than the feed labels
  that bar "Latest bar · date", not "Today". With the feed down or held back, the example switch and the Chart tab say
  so.
- **Example file** (`data/example_ETH-2D-2024-09-22.json`, 51 bars, ending with the bar that holds day 60): used only
  if its bars are well formed on 2-day steps, its entry bar closes on 22 Sep 2024 at `entry_close`, it reaches 60 days
  past the entry bar, and its entry close equals the example card's.
- **Lead-trader file.** Served from the `ctzb-trades` relay, which the review banner says is in dry run. Checked
  against the schema's lead-trader part (key `trades`), newest first and none in the future; a failure reads
  "unavailable". It never changes the odds. The card's lead-trader line reads "not in" when he has posted entries but
  none on that asset. The chart's note says his feed is unavailable when it cannot be read, and that his entries and
  exits are not drawn on the chart.
- **Loading.** The card is drawn as soon as the feed arrives ("Loading the latest data…" until then); the ledger,
  lead-trader and example files are added as they arrive. A chart whose file is loading says "Loading", and the
  previous setup's chart is cleared.
- **Alerts.** Member alerts are not switched on, and the page's review banner says so and says which setups they will
  cover is undecided.

### The ledger beside the feed

`datasets/ledger.csv` (grade_live.py) has one row per graded signal (1D-5D; ETH only with funding data), dated by its
confirmation close, each measure stored to 6 decimals, listed only once its 60th day has closed. Its odds-on-the-day
columns (`dayReach10`, `dayReach20`, `dayReach30`, `dayTouched30`, `daySurv10`, `dayScaled20`, `dayN`) use only
signals of the same asset whose 60th day (entry + 60) had closed by this entry's date. `dayN` is how many of those had
the same grade; the rates are blank until `dayN` is 10. Each rate is (hits in the same grade + 5 x the rate among all
those prior signals) / (same-grade count + 5), rounded once. `dayScaled20` leaves out signals with no full year of
volatility before entry, in both parts.

`tests/test_feed_damage.py` damages every field the page reads and checks that the page and `feedcheck.py` give the
same verdict, that accepted feeds render cleanly and that rejected ones read "Data unavailable".
`tests/test_page_timing.py` covers the loading states. `tests/regression.py` fails when its baseline is missing.

## Not built yet

- Keyed views per audience: the site Worker serves one view behind one gate.
- A member alert channel; alerts go only to the operator's Telegram.
- A ping to Grok when a new signal lands.
- The repository going private. Until then this file and the datasets are public.
