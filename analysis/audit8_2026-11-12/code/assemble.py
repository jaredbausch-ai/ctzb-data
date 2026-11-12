import csv, collections
OUT = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8'
rows = []
for p in ('_ledger', '_feed', '_cards', '_page_now', '_page_chart', '_extra', '_extra2'):
    rows += list(csv.DictReader(open(f'{OUT}/{p}.csv')))
FIELDS = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
extra = []
for st in ('REPLAY', 'CURRENT'):
    extra.append(dict(state=st, location='feed odds_fade.sample (and the page fallback ladder note)', label='"ETH signals in the walk-forward tier, every chart, 2016 on"',
                      shown='walk-forward tier', yours='tier fixed on 2026-01-01 applied to every ETH signal 2016-2026; 167 of 168 signals predate the anchor and are the signals it was chosen on (in-sample)',
                      ok='no', cause='label vs meaning'))
DOCS = [
    ('CONTEXT.md (28 Oct card paragraph) + CARD_SPEC "What keeps it airtight" 2', 'verify_cards "re-derives every card ... any mismatch fails the run"',
     'claim: every figure', 'verify_cards.py checks n, surv10, reach20, touched30, bestMove, maxDip60 and 4 timing medians only; not reach10 (the big number), scaled20, dipBeforeHigh, *_exact, eras, from_entry, the ladder, low_day, price_now, entry_close, must_close_above'),
    ('CONTEXT.md line ~1388', 'card paragraph: "The big number is rose 10% and never fell 25%"', 'rose 10% and never fell 25%', 'since 11 Nov the big number is rose10_within60d_pct; the level is 25.3%'),
    ('CONTEXT.md +10% switch paragraph (line ~521)', '"Still on +20% and to move: the if it misses stat and the 70% below the posting bar status"', 'still on +20%', 'code already on +10%: missstats miss = reached10 no; carddesign.fade edge on reached10'),
    ('docs/FEED_SPEC.md "+10% switch"', 'edge_measured_on', 'rose 10% within 60 days', 'feed writes "rose 10% after day 10 (days 11 to 60)"'),
    ('docs/FEED_SPEC.md Rules', '"shows past_trades beside every percentage and labels forming lows provisional"', 'n beside every percentage; "provisional"',
     'page: Typical high/drop, Dip before the high and the "If it misses" line carry no n of their own sample; forming cards say "Setup forming ... can still vanish", never "provisional"'),
    ('docs/CARD_SPEC.md Wording rules', '"Every percentage that depends on a time window says within 60 days"; n "in the card\'s corner"', 'within 60 days on every windowed %',
     'page labels Typical high, Typical drop from entry, Dip before the high, ladder rows, era bars, If it misses and the chart level labels omit it; n sits under the big number'),
    ('CONTEXT.md audit corrections (1) / FEED_SPEC', '"rounded once, on the exact value"', 'once', 'page re-rounds the 6-place feed/ledger values with toFixed; the 70% edge tests (carddesign.fade, page setupFade) compare already-rounded integers. No displayed value differs in either state (latent)'),
    ('analysis/carddesign.py docstring; verify_cards.py comment', 'misses "A+ signals"; "the ledger\'s dips are rounded to 0.1"', 'A+ only; 0.1', 'extras_live writes all four grades; ledger stores 6 places'),
    ('docs/FEED_SPEC.md schema 5 odds_fade', '"ETH walk-forward tier signals only"', 'walk-forward', 'the 2026 tier applied to 2016-2026 signals (in-sample), see label finding'),
]
for loc, lab, shown, yours in DOCS:
    extra.append(dict(state='REPO', location=loc, label=lab, shown=shown, yours=yours, ok='no', cause='docs vs code'))
allr = rows + extra
with open(f'{OUT}/all_checks.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(allr)
with open(f'{OUT}/disagreements.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows([r for r in allr if r['ok'] == 'no'])


def item(r):
    l = r['location']
    if l.startswith('ledger'): return '1 ledger rows'
    if l.startswith('feed grade_odds'): return '2 grade_odds'
    if l.startswith('feed if_it_misses'): return '3 if_it_misses'
    if l.startswith('feed odds_fade'): return '4 odds_fade'
    if l.startswith('feed open_signals') and 'card' not in l: return '6 open_signals'
    if l.startswith(('feed cards', 'feed example_card', 'feed open_signals')): return '5 cards'
    if l.startswith(('feed past_paths', 'feed example_past_paths')): return '7 past paths'
    if l.startswith('page how-to-read'): return '9 labels / how to read'
    if l.startswith(('feed labels', 'feed')): return '10 entry quality / feed state'
    return '8 page'
c = collections.Counter(); cs = collections.Counter()
for r in rows:
    c[item(r)] += 1; cs[(item(r), r['state'])] += 1
print(len(allr), 'rows;', sum(1 for r in allr if r['ok'] == 'no'), 'not ok;', 'numeric/page rows', len(rows), 'bad', sum(1 for r in rows if r['ok'] == 'no'))
for k in sorted(c, key=lambda x: int(x.split()[0])): print(k, c[k], cs[(k, 'REPLAY')], cs[(k, 'CURRENT')])
