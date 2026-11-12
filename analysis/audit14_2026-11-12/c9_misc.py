"""Check 2b / misc: feed top-level fields a reader could meet; rounding-tie scan; other scans."""
from lib2 import *
from c4_fade import chart_tags, TAGS
import re
for name in STATES:
    S = State(name); F = S.feed; R = Rec(name, 'c9')
    R.add('feed', 'schema_version', F['schema_version'], 5)
    R.add('feed', 'generated_at is the state clock', F['generated_at'], S.now.strftime('%Y-%m-%dT%H:%M:%SZ'))
    R.add('feed', 'scored_as_of is the clock date', F['scored_as_of'], str(S.today))
    R.add('feed', 'cards_withheld / alerts_withheld / extras_withheld all false with checks passed', f"{F['cards_withheld']} {F['alerts_withheld']} {F['extras_withheld']} {F['checks']['all_passed']}", 'False False False True')
    R.add('feed', 'label', F['label'], 'Computed signal, not a fill. No trade was taken. Entry quality only: the data has no exits, so this is not a strategy return or a track record.')
    # trades_a_year: tier signals per year (all 70%+ tier signals scored on their own chart's bars / years they could have been scored in)
    upto = dt.date(S.today.year, 1, 1); T = []; data_end = max(S.ch[('ETH', tf)].date[-1] for tf in TFS)
    for tf in TFS:
        ch, sg = chart_tags(S, tf); n = int(tf[0]); scored = []
        for s in sg:
            ei = s['ei']
            if ei >= ch.n: continue
            end = ch.date[ei] + dt.timedelta(days=60)
            if ch.date[-1] < end: continue
            js = [j for j in range(ei + 1, ch.n) if ch.date[j] <= end]
            if not js: continue
            scored.append((s, ch.c[js[-1]] / ch.c[ei] - 1 > 0, ch.date[ei] + dt.timedelta(days=n - 1 + 60) < upto, ch.date[ei]))
        kt = set()
        for t in TAGS:
            sub = [w for s, w, cb, d in scored if t in s['tags'] and cb]
            if len(sub) >= 8 and 100 * sum(sub) / len(sub) >= 70: kt.add(t)
        T += [(tf, d) for s, w, cb, d in scored if s['tags'] & kt]
    T = sorted(set(T)); span = max(0.25, ((data_end - dt.timedelta(days=60)) - min(d for _, d in T)).days / 365.25)
    per = len(T) / span
    R.add('feed', 'trades_a_year (tier signals a year; legacy dashboard figure)', F['trades_a_year'], f'{rnd(repr(per), 0)} on average', cause=f'{len(T)} tier signals / {span:.3f} years = {per:.4f}')
    R.add('feed', 'signals_a_year twin', F['signals_a_year'], F['trades_a_year'])
    # every label field carries the computed-signal wording
    def walk(o, path=''):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == 'label' and isinstance(v, str): yield path, v
                else: yield from walk(v, path + '.' + k)
        elif isinstance(o, list):
            for i, v in enumerate(o): yield from walk(v, path + f'[{i}]')
    labs = list(walk(F))
    R.add('feed', f'label fields without "Computed signal, not a fill" + "Entry quality only" (of {len(labs)})', sum(1 for p, v in labs if not ('not a fill' in v and 'Entry quality only' in v)), 0)
    # text fields in the feed that say "trade(s)" about signals
    def walks(o, path=''):
        if isinstance(o, dict):
            for k, v in o.items(): yield from walks(v, path + '.' + k)
        elif isinstance(o, list):
            for i, v in enumerate(o): yield from walks(v, path + f'[{i}]')
        elif isinstance(o, str): yield path, o
    hits = sorted({(re.sub(r'\[\d+\]', '[]', p), v[:90]) for p, v in walks(F) if re.search(r'\btrades?\b', v, re.I) and 'No trade was taken' not in v})
    R.add('feed', 'text values calling signals "trades" (other than the label\'s "No trade was taken")', len(hits), 0, cause=str(hits[:6]))
    grades_in_text = sorted({(re.sub(r'\[\d+\]', '[]', p), v[:80]) for p, v in walks(F) if re.search(r'graded [ABC]|grade [ABC]\b|grade A\+', v) and not p.endswith('.grade')})
    R.add('feed', 'member-readable text values carrying a grade letter (sample, note)', len([x for x in grades_in_text if x[0].endswith(('.sample', '.note'))]), 0, cause=str(grades_in_text[:5]))
    # rounding-tie scan: any stored 6-place value that sits exactly on a display half (x.x50000)
    ties = []
    for r in S.ledger:
        for k in ('bestMove', 'maxDrawdown', 'dipBeforeHigh', 'return60d'):
            d = Decimal(r[k])
            if (d * 10) % 1 == Decimal('0.5'): ties.append((r['chart'], r['entry'], k, r[k]))
    def cards():
        for c in F['cards']: yield c
        yield F['example_card']
        for o in F['open_signals']: yield o['card']
    for c in cards():
        for k in ('typical_biggest_rise_exact_pct', 'typical_dip_before_rise_exact_pct', 'typical_deepest_dip_exact_pct'):
            d = Decimal(str(c[k]))
            if (d * 10) % 1 == Decimal('0.5'): ties.append((c['signal_id'], k, c[k]))
    R.add('ledger + cards', 'stored 6-place figures sitting exactly on a one-decimal half (where binary and decimal half-away rounding could part)', len(ties), 0, cause=str(ties[:5]))
    # shares that display as 70 but are below it exactly / display 69 but above: the edge bar on the exact share
    near = []
    for c in cards():
        for row in [c['from_entry']] + c['if_it_falls_first']:
            x = row.get('still_rose10_exact_pct')
            if x is not None and 69.5 <= x < 70.5: near.append((c['signal_id'], row.get('fell_pct', 0), row['still_rose10_pct'], x))
    print(name, 'ladder shares within half a point of the 70 bar:', near)
    zero = [(r['chart'], r['entry'], k, r[k]) for r in S.ledger if r['grade'] == 'A+' for k in ('bestMove', 'maxDrawdown', 'return60d') if abs(float(r[k])) < 0.05]
    print(name, 'top-grade ledger figures that display as 0.0:', zero)
    R.save()
