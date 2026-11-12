"""Checks 5 and 6: every card; open signals; prints."""
from lib3 import *
EX = dt.date(2024, 9, 22)
GRADE_OF = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'

def lens_set(c):
    return frozenset() if c['confirmations'] in ('none', '-', '') else frozenset(PLAIN[x] for x in c['confirmations'].split('; '))

def run(name):
    S = State(name); mine = build_mine(S); F = S.feed; L = list(mine.values())
    R = Rec(name, 'c5')
    figs = {}
    # ---------- forming cards
    form = {}
    for a in ASSETS:
        for tf in TFS:
            f = forming(S, a, tf)
            if f: form[(a, tf)] = f
    R.add('feed.cards', 'number of forming cards (one per forming low, every chart)', len(F['cards']), len(form), cause=str(sorted(form)))
    for c in F['cards']:
        a, tf = c['asset'], c['timeframe']; loc = f"feed.cards {c['signal_id']}"
        f = form.get((a, tf))
        if not f: R.add(loc, 'forming low exists on this chart', 'yes', 'no'); continue
        R.add(loc, 'signal_id', c['signal_id'], f"{a}-{tf}-{f['conf']}")
        R.add(loc, 'chart', c['chart'], f'{a} {tf}')
        R.add(loc, 'low_date (trough bar open)', c['low_date'], str(f['tdate']))
        R.add(loc, 'low_day', c['low_day'], str(low_day(S, a, tf, f['tdate'])))
        R.add(loc, 'confirms_on', c['confirms_on'], str(f['conf']))
        R.add(loc, 'bars_to_confirm', c['bars_to_confirm'], f['need'])
        R.add(loc, 'must_close_above', c['must_close_above'], None if f['kill'] is None else rnd(repr(f['kill']), 2), cause='' if f['kill'] is None else f'threshold {f["kill"]:.6f}')
        R.add(loc, 'price_now (latest price)', c['price_now'], rnd(f['sprice'], 2))
        R.add(loc, 'entry_close (none while forming)', c['entry_close'], None)
        R.add(loc, 'gate on at the trough date', 'on', 'on' if f['gate'] else 'off')
        R.add(loc, 'grade matches the count of confirmations', c['grade'], GRADE_OF(len(lens_set(c))))
        G, txt = pick_sample(L, a, tf, c['grade'], lens_set(c))
        R.add(loc, 'sample', c['sample'], txt)
        fig = card_figures(S, G); figs[c['signal_id']] = fig
        check_card(R, loc, c, fig)
    # ---------- example card
    c = F['example_card']; loc = 'feed.example_card'
    exs = next(x for x in L if x['chart'] == 'ETH 2D' and x['edate'] == EX)
    known = [x for x in L if x['edate'] + dt.timedelta(days=60) <= EX]
    R.add(loc, 'signal_id', c['signal_id'], 'ETH-2D-2024-09-22'); R.add(loc, 'chart', c['chart'], 'ETH 2D'); R.add(loc, 'example flag', c['example'], True)
    R.add(loc, 'low_date', c['low_date'], str(exs['tdate'])); R.add(loc, 'low_day', c['low_day'], str(low_day(S, 'ETH', '2D', exs['tdate'])))
    R.add(loc, 'confirms_on', c['confirms_on'], str(exs['edate'])); R.add(loc, 'bars_to_confirm', c['bars_to_confirm'], None)
    R.add(loc, 'must_close_above', c['must_close_above'], None); R.add(loc, 'price_now (none on the example)', c['price_now'], None)
    R.add(loc, 'entry_close', c['entry_close'], rnd(exs['sentry'], 2))
    R.add(loc, 'grade as in the ledger row', c['grade'], exs['grade']); R.add(loc, 'confirmations as in the ledger row', ' + '.join(sorted(lens_set(c))), ' + '.join(sorted(exs['lenses'])))
    G, txt = pick_sample(known, 'ETH', '2D', c['grade'], lens_set(c), example=True)
    R.add(loc, 'sample', c['sample'], txt)
    R.add(loc, 'sample uses only signals whose 60th day had closed by 2024-09-22 (latest entry + 60)', 'yes', 'yes' if max(x['edate'] for x in G) + dt.timedelta(days=60) <= EX else 'no')
    fig = card_figures(S, G); figs['example'] = fig
    check_card(R, loc, c, fig)
    # ---------- open signals and their cards
    R6 = Rec(name, 'c6')
    mine_open = []
    for a in ASSETS:
        for tf in GRADED:
            for s in S.signals(a, tf):
                if 0 <= (S.today - s['edate']).days <= 60 and not S.complete(a, s['edate']): mine_open.append(s)
    mine_open.sort(key=lambda s: (str(s['edate']), s['chart']))
    R6.add('feed.open_signals', 'count', len(F['open_signals']), len(mine_open))
    R6.add('feed.open_signals', 'ids in order', ' '.join(o['signal_id'] for o in F['open_signals']), ' '.join(f"{s['a']}-{s['tf']}-{s['edate']}" for s in mine_open))
    mo = {f"{s['a']}-{s['tf']}-{s['edate']}": s for s in mine_open}
    for o in F['open_signals']:
        loc = f"feed.open_signals {o['signal_id']}"; s = mo.get(o['signal_id'])
        if s is None: R6.add(loc, 'is an open signal by my detection', 'yes', 'no'); continue
        a, tf = s['a'], s['tf']; dd = S.day[a]; e = s['entry']; De = Decimal(s['sentry'])
        R6.add(loc, 'chart', o['chart'], s['chart']); R6.add(loc, 'entry_date', o['entry_date'], str(s['edate']))
        R6.add(loc, 'entry_close', o['entry_close'], rnd(s['sentry'], 2)); R6.add(loc, 'tags', o['tags'], tagstr(s))
        R6.add(loc, 'days_elapsed', o['days_elapsed'], (S.today - s['edate']).days)
        w = S.window(a, s['edate'])
        for dN in (10, 30, 60):
            k = next((k for n, k in w if n == dN), None)
            R6.add(loc, f'day{dN}_pct (closed daily bar only)', o[f'day{dN}_pct'], None if k is None else rnd(repr((dd.c[k] / e - 1) * 100), 1))
        R6.add(loc, 'best_so_far_pct', o['best_so_far_pct'], rnd(repr((max(dd.h[k] for _, k in w) / e - 1) * 100), 1) if w else None)
        R6.add(loc, 'worst_so_far_pct', o['worst_so_far_pct'], rnd(repr((min(dd.l[k] for _, k in w) / e - 1) * 100), 1) if w else None)
        R6.add(loc, 'gate on at the trough date', 'on', 'on' if s['gate'] else 'off')
        R6.add(loc, 'label says computed / entry quality only', 'yes' if 'Entry quality only' in o['label'] and 'not a fill' in o['label'] else 'no', 'yes')
        # its card
        c = o['card']; cl = f"feed.open_signals[{o['signal_id']}].card"
        R.add(cl, 'signal_id', c['signal_id'], o['signal_id']); R.add(cl, 'chart', c['chart'], s['chart'])
        R.add(cl, 'low_date', c['low_date'], str(s['tdate'])); R.add(cl, 'low_day', c['low_day'], str(low_day(S, a, tf, s['tdate'])))
        R.add(cl, 'confirms_on', c['confirms_on'], str(s['edate'])); R.add(cl, 'bars_to_confirm', c['bars_to_confirm'], None); R.add(cl, 'must_close_above', c['must_close_above'], None)
        R.add(cl, 'price_now (latest price)', c['price_now'], rnd(dd.sc[-1], 2)); R.add(cl, 'entry_close', c['entry_close'], rnd(s['sentry'], 2))
        R.add(cl, 'grade same as the open signal', c['grade'], o['grade'])
        R.add(cl, 'grade matches the count of confirmations', c['grade'], GRADE_OF(len(lens_set(c))))
        R.add(cl, 'confirmations same as the open signal', ' + '.join(sorted(lens_set(c))), ' + '.join(sorted(x for x in o['confirmations'].split(' + ') if x != '-')))
        G, txt = pick_sample(L, a, tf, c['grade'], lens_set(c))
        R.add(cl, 'sample', c['sample'], txt)
        fig = card_figures(S, G); figs[o['signal_id']] = fig
        check_card(R, cl, c, fig)
        # edge level and status (FEED_SPEC audit #9)
        lvl = fig['edge']
        R6.add(loc, 'edge_level_pct', o['edge_level_pct'], lvl)
        if lvl == 0: stt = 'lost'
        elif lvl is None: stt = 'intact'
        else:
            stt = 'intact'
            for _, k in w:
                if Decimal(dd.sl[k]) <= De * (Decimal(1) + Decimal(lvl) / 100): stt = 'lost'; break
                if Decimal(dd.sh[k]) >= De * Decimal('1.10'): stt = 'intact'; break
        R6.add(loc, 'edge_status', o['edge_status'], stt)
    # ---------- prints
    exp = []
    for a in ASSETS:
        for tf in TFS:
            sg = S.signals(a, tf)
            for s in sg[-3:]:
                exp.append(dict(signal_id=f"{a}-{tf}-{s['edate']}", chart=f'{a} {tf}', state='confirmed', provisional=False, low_date=str(s['tdate']), confirms_on=str(s['edate']),
                                entry_close=rnd(s['sentry'], 2), tags=tagstr(s), note='regime on' if s['gate'] else 'regime off'))
            f = form.get((a, tf))
            if f:
                exp.append(dict(signal_id=f"{a}-{tf}-{f['conf']}", chart=f'{a} {tf}', state='forming', provisional=True, low_date=str(f['tdate']), confirms_on=str(f['conf']),
                                entry_close=rnd(f['sprice'], 2), tags=tagstr(f), note=('regime on' if f['gate'] else 'regime off') + f"; {f['need']} bar(s) to confirm"))
    R6.add('feed.prints', 'count (last 3 confirmed per chart + forming lows)', len(F['prints']), len(exp))
    for p, x in zip(F['prints'], exp):
        loc = f"feed.prints {x['signal_id']} ({x['state']})"
        for k in ('signal_id', 'chart', 'state', 'provisional', 'low_date', 'confirms_on', 'entry_close', 'tags', 'note'):
            R6.add(loc, k, p[k], x[k])
    # ids shared across stages: forming print id == forming card id
    for c in F['cards']:
        R6.add(f"feed.cards {c['signal_id']}", 'a forming print carries the same signal_id', 'yes', 'yes' if any(p['signal_id'] == c['signal_id'] and p['state'] == 'forming' for p in F['prints']) else 'no')
    R.save(); R6.save()
    import pickle
    pickle.dump({k: {kk: vv for kk, vv in v.items()} for k, v in figs.items()}, open(f'{OUTDIR}/figs_{name}.pkl', 'wb'))
    return S, figs, form

if __name__ == '__main__':
    for name in STATES:
        S, figs, form = run(name)
        print(name, 'forming:', {k: (str(v['tdate']), v['need'], str(v['conf']), v['kill'], round(v['ct'], 3), None if v['k'] is None else round(v['k'], 3)) for k, v in form.items()})
        print(name, 'edges:', {k: v['edge'] for k, v in figs.items()})
