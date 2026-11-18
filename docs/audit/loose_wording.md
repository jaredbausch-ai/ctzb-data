# Loose wording waiting for the end of the segment

Kind 3 and outside-scope findings from round 41 on, recorded here and corrected together once damage and docs have
two clean rounds in a row (STATUS.md, "The plan from round 41"). Each row: round, file, line, quote, suggested sentence.

| Round | File | Line | Quote | Suggested |
|---|---|---|---|---|
| 40 (fix check) | docs/FEED_SPEC.md | 333 | was then put back to the run before's | ...was then put back to an earlier run's (most often the run before's, because that run died between the copy and the log). |
| 40 (fix check) | docs/FEED_SPEC.md | 334 | When the log on disk is the copy or a beginning of it, the log is restored from the copy | When the log on disk is missing, the copy, or a beginning of it, the log is restored from the copy... |
| 40 (fix check) | feed_live.py | 239 | this happens only when a later run wrote the copy and its feed (or its feed and log) was then put back to the run before's ... (when the log on disk is the copy or a beginning of it) | ...put back to an earlier run's ... (when the log is missing, is the copy, or is a beginning of it)... |
| 40 (fix check) | README.md | 76 | and when each forming low would confirm (`buy.csv`'s `buyDate`: a computed date, not a planned buy) | ...and, for each forming low that matches a tier setup, the date it would confirm (`buy.csv`'s `buyDate`: a computed date, not a planned buy). |
| 40 (fix check) | .github/workflows/daily.yml | 126 | the odds-fade marks and the chart candle files, from this run's ledger and candles. | ...the odds-fade marks and the chart candle files, from this run's ledger, early-dip and day-10 tables and candles. |
