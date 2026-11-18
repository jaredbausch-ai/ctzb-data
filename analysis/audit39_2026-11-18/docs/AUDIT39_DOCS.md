# Audit 39, docs part: every doc sentence against the code at 465e385

**Top line.** 18 documents read in full (plus the docstrings, comments and test headers in item 5). About 900 statements checked (about 560 in scope and 340 outside it). **Counted findings (in scope): 2. By kind: kind 1 = 0, kind 2 = 0, kind 3 = 2, kind 4 = 0. Kinds 1, 2 and 4 together: 0.** Outside scope (not counted): 4, all kind 3.

Entry quality only: everything checked describes computed signals and their 60-day records. There are no fills, no exits and no strategy return. No in-scope sentence reads as a trade, a return or a track record (kind 4 = 0).

Method: I worked on a copy of the repo at commit 465e385 (`audit39d/repo`). I rebuilt the feed there exactly as the brief says: refresh, grade_live, extras_live, stack_live and verify_cards, then `tests/regression.py` (PASS, 919 baselined, 4 new), then `feed_live.py` with every step reported as success. The result was 4 cards, 34 prints, 21 open signals and 10 windows. I listed every key in the rebuilt feed and found each one described in FEED_SPEC (the `*_exact_pct` twins through the "(`_exact_pct`)" shorthand). I then read each sentence against the code that produces the behaviour.

Figures recomputed and found to match:

| Figure | Where it is quoted | Recomputed value |
|---|---|---|
| Datasets refresh.py writes | README | 13 |
| Setups in keep.json | README | 12 |
| Candidate tags | README | 11 |
| Daily-history requests per run | README | about 14 per asset, 28 in all |
| Tests that assert schema 6 | FEED_SPEC | 2 |
| Example file | member-site README | 51 bars, 12 Aug 2024 to 20 Nov 2024, entry bar 21-22 Sep |
| Smallest rule-3 pool | CARD_SPEC | 33 (BTC top grade) |
| First graded ETH signal | CARD_SPEC | ETH 3D, 21 Mar 2020, grade C |
| First ETH top-grade signal | CARD_SPEC | 18 Apr 2020 |
| troughs.json | CONTEXT | 996 rows, 6 charts |
| Confluence cells | CONTEXT and stack_live | 176 (83 + 49 + 44) |
| numbers_check replay dates | CONTEXT | 13 |
| Damage families | CONTEXT | 6 |
| Fire-drill result | CONTEXT | 58/58 |
| Regime turned on | CONTEXT | 2026-09-02 (still the current episode) |
| Shared 4H gaps | FEED_SPEC | 28 Feb 2017 and 25 Oct 2025 |
| Each asset's own 4H/12H gaps | FEED_SPEC | as listed in `fetch.OWN_GAPS` |
| ETH/BTC close ratio | fetch.py | 0.77% to 14.96% |
| Funding range | fetch.py | -0.49 to 0.30 |
| Perp markets per asset | CONTEXT | 13 |
| Scheduler dispatches per day | cloudflare README | 26 (12 + 6 + 8) |
| Worker test counts | cloudflare README | 21 / 26 / 21 / 45 / 26 / 36 (node suites re-run, all pass) |
| Forming lows in `test_gate_off.sh` | test header | 10 (re-run: PASS) |

## Every finding

Full rows, with what the code does and the sentence ready to paste, are in `findings.csv`.

### Counted (in scope)

| # | File, line | Kind | Quoted sentence (short) | What the code does | Suggested sentence (ready to paste) |
|---|---|---|---|---|---|
| 1 | README.md 86-88 | 3 | "The dashboard page ... reads `status`, `live`, `grades`, `forward`, `dipdist`, `cards`, `liveread`, `prints` and `windows`." | `docs/artifacts/eth-setup-standard.html` line 400 also reads `dash.data("maxsafe")` and fills the grade table's maxSafe column from it. No pipeline step writes `datasets/maxsafe.csv` (only the page and its generated worker mention it), so that column is always empty. | "The dashboard page (`docs/artifacts/eth-setup-standard.html`, served by the ctzb-dashboard Worker) reads `status`, `live`, `grades`, `forward`, `dipdist`, `cards`, `liveread`, `prints` and `windows`; it also asks for `maxsafe`, which no pipeline step writes, so its max-safe column stays empty." |
| 2 | docs/artifacts/member-site/README.md 17 | 3 | "...and two phrases of plain description ("sometimes for a year" ..., "usually within the hour" ...)." | The page types at least two more plain-description phrases. One is "within about a minute of each fill" (the lead-trader panel, `index.html` lines 838 and 842, added in round 38). The other is "(on a 2D, 3D or 5D chart that can be a few days before the low itself)" (How to read, line 288). The README presents its list as complete. | "...and four phrases of plain description ("sometimes for a year" for how long the filter can stay off, "usually within the hour" for when a held run retries, "within about a minute of each fill" for when a lead-trader trade is posted, and "a few days before the low itself" for how far a 2D-5D bar's open can precede its low)." |

### Outside scope (not counted)

| # | File, line | Kind | Quoted sentence (short) | What the code does | Suggested sentence (ready to paste) |
|---|---|---|---|---|---|
| 3 | refresh.py 270-272 (comment in `select_tier`) | 3 | "...so the entry is the close of that bar, tf - 1 days later..." | 2D+ bars restart on 1 January, so a year's last bar can be short and closes fewer than tf - 1 days after it opens. Line 274 still adds tf - 1, which then works as a conservative bound (no lookahead). | "...so the entry is the close of that bar, at most tf - 1 days later (fewer for a year's short last bar, where tf - 1 is a conservative bound), and the outcome's last day is 60 days after" |
| 4 | tests/test_feed_damage.py 11-12 (header) | 3 | "...no raw placeholder (NaN, undefined, null, [object, Infinity, ${, $-)" | The test's BAD pattern (line 28) also rejects `n/a%` and `n/ax`. | "...no raw placeholder (NaN, undefined, null, n/a%, n/ax, [object, Infinity, ${, $-);" |
| 5 | tests/test_seal.py 3-7 (header) | 3 | Part 2 list: "a clean run; ... a dataset cut between two steps ...; and a dataset changed after the last step ..." | Part 2 also runs `feed_live.py` on its own a day later and checks that the earlier run's seal is refused (line 164, audit #25). The header does not list that case. | "...; a dataset cut between two steps (the next step refuses to run); feed_live.py run again on its own a day later (refused as an earlier run's seal); and a dataset changed after the last step (the fail-closed feed is published)." |
| 6 | docs/artifacts/member-site/index.html 1304-1305 (code comment, not member-facing) | 3 | "The two notes are the only texts that depend on the viewer's clock." | `tradesProblems` (line 548) also uses the viewer's clock: an event more than 5 minutes ahead of it makes the lead-trader file read "unavailable". The page's comment at line 622 and FEED_SPEC line 501 already say so. | "The two notes, and the lead-trader file's "in the future" check, are the only things that depend on the viewer's clock." |

## Documents with zero findings

- docs/FEED_SPEC.md. I checked every row of every table, the aliases, and the sections on held and fail-closed feeds, alerts and the alert log, the seal, the inputs, the strict check and what the page does with each file.
- docs/CARD_SPEC.md. This includes the member-card table, the dashboard console's card (checked against `eth-setup-standard.html`) and "What keeps it airtight".
- The member page's own words (`docs/artifacts/member-site/index.html`). I checked How to read, every label, heading, badge, banner, footer and stale or daily-close note, and the comment that describes FEED_SCHEMA. Each label means what its number measures.
- cloudflare/README.md.
- CONTEXT.md, current-rule sections:
  - Confirmation lag (including the 3/7/11/19/31-day note and the ETH 3D example of 13 to 24 Sep 2026)
  - The setup
  - Regime gate
  - Traps
  - Where things live
  - Live artifacts note
  - Where the current regime sits
  - Open items
  - Standing instructions
  - The 4 Nov notes, which carry supersede markers
- Outside scope:
  - cloudflare/BRIEF_dashboard.md, BRIEF_monitor.md, BRIEF_site.md and BRIEF_trades.md. Their verify steps describe the commit-pinned builds they deploy.
  - docs/PRETRADE.md (statements about pipeline behaviour only).
  - docs/SITE_CHANGES.md. Every Pending row (1 to 7b) is on the page or in the worker on disk, or is marked superseded. R1, R2 and R3 are not built.
  - Docstrings and comments in grade_live, stack_live, verify_cards, extras_live, feed_live, feedcheck, seal, engine, measures, rounding, clock, fetch, regimes, analysis/tagstats, analysis/carddesign, .github/scripts/* and daily.yml.
  - The headers of every other `tests/*.py`, `*.sh` and `*.mjs` file.

## What I could not check, and why

- **Cloudflare dashboard configuration.** Cron triggers (`*/15`, `5,20,35,50`, `* * * * *`), bindings, Access policies, the R2 lifecycle rule and the deployed version ids (656d67c3, 8704c084 and others) exist only in Cloudflare, not in the repo. I checked the worker code they run.
- **Live URLs and claude.ai artifacts named in CONTEXT.** These were not opened; checking them would mean reaching outside the repo.
- **Browser-run tests.** test_feed_damage, test_page_states, test_page_timing, test_per_year, numbers_check and fire_drills group E need playwright and chromium. I checked the page's behaviour by reading its code. I did not re-run fire_drills in full, so "58/58" is checked against `tests/fire_drills_result.json` only.
- **Dated research records and figures** in CONTEXT, PRETRADE and the README's "Figures as of 16 October 2026". These were excluded by the brief.
- **Numbers and broken-file behaviour.** These are checked separately, as the brief says. I checked only the wording of the sentences that describe them.
- **The rebuilt feed's alerts.** It differs from the committed feed only by time: one alert aged out of its 24-hour window, plus the timestamps.
