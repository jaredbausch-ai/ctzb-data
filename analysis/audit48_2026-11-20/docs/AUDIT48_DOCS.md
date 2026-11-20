# Round 48 docs audit: every doc sentence against the code at 4d4069d

Entry quality only. Everything checked here describes computed signals and their 60-day records; there are no fills, no exits and no strategy return.

## Top line

| | |
|---|---|
| Documents read | 21: 7 in scope (member page, FEED_SPEC, CARD_SPEC, README, member-site README, cloudflare README, CONTEXT current-rule sections) + 14 outside scope (4 BRIEF files, PRETRADE, SITE_CHANGES, docstrings/comments in the 17 listed code files and daily.yml, every tests/*.py, *.sh, *.mjs header) |
| Statements checked | about 900 (in scope about 630, outside scope about 270) |
| **Counted findings (in scope, kinds 1, 2, 4)** | **1**: kind 1 = 0, kind 2 = 1, kind 4 = 0 |
| In scope, kind 3 (reported, not counted) | 1 |
| Outside scope (not counted) | 3: kind 1 = 1, kind 2 = 1, kind 3 = 1 |
| Borderline findings | none |

Nothing on the member page, in FEED_SPEC or in the cloudflare README reads as a trade taken, a return or a track record.

## How it was checked

- A copy of the repo at `4d4069d` (`audit48d/repo`), never the live repo. The feed was rebuilt as the brief says (refresh, grade_live, extras_live, stack_live, verify_cards, regression, feed_live). The rebuilt feed differs from the committed one only in `generated_at`, the time on the two check lines and the key order of `checks.steps`.
- Every field in the feed was matched to a FEED_SPEC row and back (top level, cards, prints, open signals, windows, grade rows, extras, checks, candle_check, alerts). The Strict column was checked against the `FEED_SCHEMA` block; every cross rule against `feedcheck.py` and the page's `crossCheck`.
- Every count re-derived: 13 refresh datasets; 996 rows / 6 charts in troughs.json; 12 setups in keep.json; 11 candidate tags; 176 confluence cells (83 + 49 + 44); 36 registry ids; 12 PRETRADE headings; 13 replay dates; 6 damage families; 13 perp markets per asset; 51 example bars (12 Aug to 20 Nov 2024); smallest rule-3 pool 33 (BTC A+); first graded ETH signal ETH 3D 21 Mar 2020 grade C, first ETH top grade 18 Apr 2020; regime on since 2026-09-02; two tests asserting schema 6. Re-run: the six Worker suites (21, 26, 36, 21, 26, 45, all as the cloudflare README says), `tests/fire_drills.py` (58/58), `tests/test_gate_off.sh` (10 forming prints, as its header says). Both generated Workers rebuild byte-identical from their sources.
- Every Pending row of SITE_CHANGES was checked against the page on disk (rows 1 to 6v, 7, 7b against the page, the dashboard page and the dashboard Worker); every Requested row (R1-R3) confirmed not built.

## Every finding

| # | Scope | File, line | Kind | Quoted sentence (short) | What the code does | Suggested sentence |
|---|---|---|---|---|---|---|
| F1 | **in scope, counted** | docs/CARD_SPEC.md 148 | 2 stale | "Older rows above that still say "trades" mean the same past signals." | No row above calls the sample "trades" any more ("past trades" left in b6aac76, 13 Nov); the only "trades" above are "not real trades" (108-111). The code words the sample as signals (stack_live.py 557-559, 761-763). | "**Wording, 12 Nov 2026 (audit #4):** the page says "signals", never "trades", for the sample: these are computed signals and none was traded." |
| F2 | in scope, kind 3 | docs/CARD_SPEC.md 105-107 | 3 loose | "Anything on a different sample shows its own n: each ladder row, each era, and the misses ..." | The general odds-fade explainer has no n: "Red on day 10, rose 10% after" tile (index.html 801), "Where the odds fade · ETH tier signals" rows (823-825), chart "Day 10 · red here" line (1093). Shown only on a card with no ladder, which no current feed produces (every card has 4 rungs). | Add: "The general odds-fade explainer, shown only on a card with no ladder ("Red on day 10, rose 10% after", "Where the odds fade · ETH tier signals"), shows its shares without n." |
| O1 | outside | docs/PRETRADE.md 371-372 | 1 wrong window | "Bullish Stoch divergence on a HIGHER chart, confirmed in the 10 days before entry" | htfdiv.py 67 dates a divergence by the OPEN date of its confirming bar; stack_live.py 285/373 and grade_live.py 102 count it when that open date is 0-10 days before entry. On a 2D-8D chart the bar can close (confirm) up to tf-1 days after entry. On the committed data 9 of 69 DIVH signals counted only divergences confirmed after entry. (htfdiv.py's "Nothing reaches forward" is wrong for the same reason; not in the checked list.) | "Bullish Stoch divergence on a HIGHER chart whose confirming bar opened in the 10 days before entry (on a 2D-8D chart that bar can close, and so confirm, a few days after entry)", or change the code to require the close date and keep the sentence. |
| O2 | outside | CONTEXT.md 549-550 (dated record) | 2 stale note | "[Superseded 11-12 Nov 2026: ... the tile reads "median best (price within the 60 days)" ...]" | The row reads "If it misses: went above entry · X of Y · median best move Z%" (index.html 768, 789), since 19 Nov (SITE_CHANGES 6s). | "[Superseded 11-12 Nov 2026: a miss is now "did not rise 10%", and every figure comes from the feed (`missstats.csv`); since 19 Nov 2026 the row reads "If it misses: went above entry" with the "median best move"; the +20%-era numbers in this paragraph are history, not current.]" |
| O3 | outside | docs/SITE_CHANGES.md 43 (row 6v) | 3 loose | "when no top-grade setup is live and two or more forming setups tie ..." | bestNote (index.html 612-619) uses the tie wording when no top-grade setup is **forming** (`liveCards()` = top-grade forming cards, 605); live (open) signals do not affect it. | "when no top-grade setup is forming and two or more forming setups tie on the shown +10% odds at the top, each tied card reads ..." |

Full rows (quote, code reference, sentence) are in `findings.csv`.

## Documents with zero findings

- In scope: `docs/artifacts/member-site/index.html` (every How-to-read sentence, label, heading, badge, banner, footer, picker, chart and side-box text, and the FEED_SCHEMA comments), `docs/FEED_SPEC.md` (every table row, every rule, the alert-log, held and fail-closed, seal, input-check, strict-check and member-page sections), `README.md`, `docs/artifacts/member-site/README.md`, `cloudflare/README.md`, CONTEXT.md current-rule sections ("read this first", Who and what, Confirmation lag with its correction, The setup, Regime gate, Traps, Where things live, Live artifacts, Where the current regime sits, Open items, Standing instructions, the 4 Nov sections with their superseded notes).
- Outside scope: `cloudflare/BRIEF_site.md`, `BRIEF_monitor.md`, `BRIEF_dashboard.md`, `BRIEF_trades.md` (each pinned build's size and first line re-checked); docstrings and comments in refresh.py, grade_live.py, stack_live.py, verify_cards.py, extras_live.py, feed_live.py, feedcheck.py, seal.py, engine.py, measures.py, rounding.py, clock.py, fetch.py, regimes.py, analysis/tagstats.py, analysis/carddesign.py, .github/scripts/*, .github/workflows/daily.yml; every tests/*.py, *.sh, *.mjs header.

## Could not check, and why

- Live Cloudflare state: which versions are deployed (656d67c3, 40a4475b, 8704c084, 7f50beb7), the Access policies, KV and R2 contents, the restore drill's 480 files, Telegram delivery. Nothing in the repo shows them.
- That the GitHub repository is public, and GitHub's own run history quoted in dated notes.
- Pine claims (the v15 indicator and v9 scanner "keep the asterisk ETH grade"): not runnable here.
- Figures in PRETRADE's research tables and the dated research record: research results, left out by the brief; the numbers part is checked separately.
- `tests/numbers_check.py` and `tests/test_feed_damage.py` were not run (numbers and damage are separate parts); their headers were checked against their code.
