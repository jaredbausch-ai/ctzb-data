import datetime as dt, json, re, collections, sys
sys.argv = ['x']
import audit as A
CK = A.CK
# data checks (both states)
exec(open('run_data.py').read().split("pickle.dump")[0].replace("import datetime as dt, pickle, collections", "import datetime as dt, collections"))
nd = len(CK.rows)
# page checks (both states); run_page.run re-runs some data checks to build my cards: drop those duplicates
import run_page  # runs both states on import
rows = CK.rows[:nd] + [r for r in CK.rows[nd:] if r['location'].startswith('page')]
CK.rows = rows
# feed labels on every record
for st in ('replay_0414', 'current'):
    F = json.load(open(f'/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/a7/{st}/feed/ctzb_feed.json'))
    recs = [('cards', c) for c in F['cards']] + [('open_signals', o) for o in F['open_signals']] + [('open card', o['card']) for o in F['open_signals']] \
        + [('grade_odds', g) for g in F['grade_odds']] + [('if_it_misses', m) for m in F['if_it_misses']] + [('past_paths', p) for p in F['past_paths']] \
        + [('example_past_paths', F['example_past_paths']), ('example_card', F['example_card']), ('odds_fade', F['odds_fade']), ('feed', F)]
    for k, r in recs:
        CK.add(st, f'feed {k} label', 'computed-signal label present', r.get('label'), A.LABEL, 'label')
    # labels vs meaning (feed): "trades" for computed signals
    CK.add(st, 'feed field names', 'trades_a_year / past_trades', f"trades_a_year: {F['trades_a_year']!r}; past_trades on every card",
           'signals (none was traded)', 'label: feed names call computed signals "trades" (fields cannot be renamed under FEED_SPEC)', ok=False)
    # labels vs meaning (page tiles)
    CK.add(st, 'page card tiles', '"Reached +20%" / "Touched −30%" tiles', 'no "within 60 days", no n beside the tile',
           'within 60 days, with past_trades beside it', 'label: CARD_SPEC wording rule ("every percentage that depends on a time window says within 60 days") and FEED_SPEC ("past_trades beside every percentage")', ok=False)
# docs vs code
CK.add('docs', 'docs/CARD_SPEC.md line 26', 'first graded ETH signal', '18 Apr 2020', '2020-03-21 (ETH 3D, grade C); 18 Apr 2020 is the first ETH A+', 'docs vs code', ok=False)
CK.add('docs', 'docs/CARD_SPEC.md eras row', 'Before 2022 / since 2022', 'the big-number measure split by entry date', 'surv10 (rose 10% and never fell 25.3%); the big number is now reach10 (rose 10%)', 'docs vs code (stale since 11 Nov); the page labels the eras correctly', ok=False)
CK.add('docs', 'docs/FEED_SPEC.md schema 5; extras_live.py; analysis/carddesign.py', 'up_first', 'how many were above entry first', 'code counts misses whose 60-day high was above entry at any point (bestMove > 0)', 'docs vs code (same as the "up first" label)', ok=False)
CK.add('docs', 'CONTEXT.md +10% switch paragraph (11 Nov)', 'line under the big number', 'X% did it without ever falling 25%', '25.3% (page, CARD_SPEC, and the 12 Nov audit #3 paragraph)', 'docs stale (superseded later in CONTEXT)', ok=False)
CK.add('docs', 'CONTEXT.md gate state 2025-26', 'gate dates', 'on to 2025-12-04, off 2025-12-05 to 2026-09-01, on from 2026-09-02', 'on to 2025-12-04, off 2025-12-05 to 2026-09-01, on from 2026-09-02', 'value')
CK.add('docs', 'page empty-card text (not displayed in either state)', 'top-grade setups a year, 2020-2025 average', 'about 22', '21.7 (130 A+ in 6 years; 2022 had 0, gate off)', 'value', ok=True)
CK.write(f'{A.OUT}/all_checks.csv', f'{A.OUT}/disagreements.csv')
bad = [r for r in CK.rows if r['ok'] == 'no']
print('comparisons', len(CK.rows), 'disagreeing rows', len(bad))
print(collections.Counter(r['state'] for r in CK.rows))
print(collections.Counter((r['state'], r['cause'][:40], r['label'][:50]) for r in bad).most_common())
