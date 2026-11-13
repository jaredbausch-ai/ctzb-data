"""Checks 4-7: odds_fade, cards (forming / example / open), open_signals, prints, top-level, past_paths."""
import sys, statistics as st, datetime as dt
from common import *
import mycalc as M

CARD_NUM = ['past_trades', 'rose10_never_fell25_within60d_pct', 'beat_normal_move_pct', 'rose20_within60d_pct', 'rose10_within60d_pct',
            'typical_biggest_rise_pct', 'typical_dip_before_rise_pct', 'typical_deepest_dip_pct', 'fell30_within60d_pct',
            'typical_day_first_rose10', 'typical_day_first_rose20', 'typical_day_of_60d_high', 'typical_day_of_deepest_dip']
EXACT = ['typical_biggest_rise_exact_pct', 'typical_dip_before_rise_exact_pct', 'typical_deepest_dip_exact_pct']


def lens_codes(card):
    t = card['confirmations']
    return frozenset() if t in ('none', '', None) else frozenset(M.PLAIN[x] for x in t.split('; '))


def cmp_card(C, loc, card, figs, text, g):
    C.add(loc, 'sample text', card['sample'], text, group=g)
    C.add(loc, 'sample text states n', f" {card['past_trades']} " in f" {card['sample']} ", True, group=g)
    for f in CARD_NUM:
        C.add(loc, f, card[f], figs[f], group=g)
    C.add(loc, 'past_signals twin', card['past_signals'], figs['past_trades'], group=g)
    for f in EXACT:
        # exact medians: full precision median stored to 6 places
        C.add(loc, f, card[f], figs[f], group=g, tol=0.0)
    # display rounding from the stored exact value must equal the rounded field
    for f in ('typical_biggest_rise', 'typical_dip_before_rise', 'typical_deepest_dip'):
        C.add(loc, f + ': round(exact,1) == rounded field', L.rhaz(card[f + '_exact_pct'], 1), card[f + '_pct'], group=g)
    for era in ('before_2022', 'since_2022'):
        for f in ('past_trades', 'rose10_never_fell25_within60d_pct'):
            C.add(loc, f'{era}.{f}', card[era][f], figs[era][f], group=g)
        C.add(loc, f'{era}.past_signals', card[era]['past_signals'], figs[era]['past_trades'], group=g)
    C.add(loc, 'eras add up to n', card['before_2022']['past_trades'] + card['since_2022']['past_trades'], card['past_trades'], group=g)
    fe = card['from_entry']
    for f in ('past_trades', 'still_rose10_pct', 'went_on_to_fall25_pct', 'still_rose10_exact_pct'):
        C.add(loc, f'from_entry.{f}', fe[f], figs['from_entry'][f], group=g)
    C.add(loc, 'from_entry.past_signals', fe['past_signals'], figs['from_entry']['past_trades'], group=g)
    for row, mine in zip(card['if_it_falls_first'], figs['if_it_falls_first']):
        for f in ('fell_pct', 'past_trades', 'still_rose10_pct', 'went_on_to_fall25_pct', 'still_rose10_exact_pct'):
            C.add(loc, f"ladder {row['fell_pct']}%.{f}", row[f], mine[f], group=g)
        C.add(loc, f"ladder {row['fell_pct']}%.past_signals", row['past_signals'], mine['past_trades'], group=g)
    C.add(loc, 'ladder rows', [r['fell_pct'] for r in card['if_it_falls_first']], [5, 10, 15, 20], group=g)
    # edge from the feed's own exact shares == edge from my full-precision shares
    fx = fe['still_rose10_exact_pct']
    their_edge = 0 if fx is not None and fx < 70 else next((-r['fell_pct'] for r in card['if_it_falls_first'] if r['still_rose10_exact_pct'] is not None and r['still_rose10_exact_pct'] < 70), None)
    C.add(loc, 'edge level (first exact share below 70)', their_edge, figs['_edge'], group=g)
    C.add(loc, 'label', 'not a fill' in card['label'] and 'Entry quality only' in card['label'], True, group=g)


def run(name):
    S = load_state(name); C = Checks(name); F = S.feed
    mine = dict(cards=[], open=[], example=None, paths={})
    # ---------------- 4. odds_fade
    keep, rows, pool, early, d10 = M.odds_fade(S)
    of = F['odds_fade']; g = '4 odds_fade'
    C.add('feed.odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70, group=g)
    C.add('feed.odds_fade', 'tier_fixed_on', of['tier_fixed_on'], f'{S.today.year}-01-01', group=g)
    C.add('feed.odds_fade', 'early_dip bands', [b['band'] for b in of['early_dip']], [b['band'] for b in early], group=g)
    C.add('feed.odds_fade', 'day10 rows', [b['check'] for b in of['day10']], [b['check'] for b in d10], group=g)
    for theirs, my in list(zip(of['early_dip'], early)) + list(zip(of['day10'], d10)):
        loc = 'feed.odds_fade ' + (theirs.get('band') or theirs.get('check'))
        C.add(loc, 'past_trades', theirs['past_trades'], my['past_trades'], group=g)
        C.add(loc, 'past_signals', theirs['past_signals'], my['past_trades'], group=g)
        C.add(loc, 'rose10_after_day10_pct', theirs['rose10_after_day10_pct'], my['rose10'], group=g)
        C.add(loc, 'rose20_after_day10_pct', theirs['rose20_after_day10_pct'], my['rose20'], group=g)
        C.add(loc, 'rose10_within60d_pct (alias)', theirs['rose10_within60d_pct'], my['rose10'], group=g)
        C.add(loc, 'rose20_within60d_pct (alias)', theirs['rose20_within60d_pct'], my['rose20'], group=g)
        C.add(loc, 'edge vs 70 on exact share', theirs['edge'], my['edge'], group=g)
    # oddsfade.csv / earlydip exact share
    for r in S.csvrows('earlydip.csv'):
        my = next((b for b in early if b['band'] == r['band']), None)
        C.add('earlydip.csv ' + r['band'], 'reached10Exact', r['reached10Exact'], L.rhaz(my['exact'], 6) if my else None, group=g)
    for r in S.csvrows('holdcheck.csv'):
        my = next((b for b in d10 if b['check'] == r['check']), None)
        C.add('holdcheck.csv ' + r['check'], 'reached10Exact', r['reached10Exact'], L.rhaz(my['exact'], 6) if my else None, group=g)
    C.add('feed.odds_fade', 'sample text says in-sample, tier year, days 11 to 60',
          all(t in of['sample'] for t in ('In-sample', f'1 Jan {S.today.year}', 'days 11 to 60', 'every signal from 2016')), True, group=g)
    C.add('feed.odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)', group=g)
    mine['odds_fade'] = dict(early=early, d10=d10, keep=keep, pool_n=len(pool))
    # ---------------- top-level
    g = '6 top-level'
    C.add('feed', 'schema_version', F['schema_version'], 6, group=g)
    C.add('feed', 'posting_bar_pct', F['posting_bar_pct'], 70, group=g)
    py, nT = M.trades_a_year(S, keep, rows)
    C.add('feed', 'trades_a_year', F['trades_a_year'], f'{L.rhaz(py)} on average', group=g)
    C.add('feed', 'signals_a_year', F['signals_a_year'], f'{L.rhaz(py)} on average', group=g)
    C.add('feed', 'market_regime (gate today)', F['market_regime'], 'Bullish' if S.gate(S.today) else 'Bearish', group=g)
    C.add('feed', 'scored_as_of', F['scored_as_of'], str(S.today), group=g)
    C.add('feed', 'cards_withheld', F['cards_withheld'], False, group=g)
    C.add('feed', 'extras_withheld', F['extras_withheld'], False, group=g)
    mine['per_year_feed'] = py
    # ---------------- 5. forming cards
    P = M.pool(S)
    forming = [f for f in (M.forming(S, a, tf) for a in L.ASSETS for tf in L.TFS_ALL) if f]
    mine['forming_all'] = forming
    want_cards = [f for f in forming if f['tf'] in L.TFS_G and f['gate_on']]
    fc = {c['signal_id']: c for c in F['cards']}
    g = '5 forming cards'
    C.add('feed.cards', 'which lows have a card (graded chart, gate on at trough)', sorted(fc), sorted(f"{f['asset']}-{f['tf']}-{f['confirms']}" for f in want_cards), group=g)
    for c in F['cards']:
        C.add(f"feed.cards {c['signal_id']}", 'on a graded chart with gate on at trough date', c['timeframe'] in L.TFS_G and S.gate(dt.date.fromisoformat(c['low_date'])), True, group=g)
    for f in want_cards:
        sid = f"{f['asset']}-{f['tf']}-{f['confirms']}"; c = fc.get(sid)
        if not c: continue
        loc = f'feed.cards {sid}'
        C.add(loc, 'chart/asset/timeframe', (c['chart'], c['asset'], c['timeframe']), (f['chart'], f['asset'], f['tf']), group=g)
        C.add(loc, 'low_date (trough bar open)', c['low_date'], str(f['tdate']), group=g)
        C.add(loc, 'low_day', c['low_day'], str(f['low_day']), group=g)
        C.add(loc, 'confirms_on', c['confirms_on'], str(f['confirms']), group=g)
        C.add(loc, 'bars_to_confirm', c['bars_to_confirm'], f['need'], group=g)
        C.add(loc, 'price_now (latest price)', c['price_now'], L.rhaz(f['price'], 2), group=g)
        C.add(loc, 'price_now = latest daily close', c['price_now'], L.rhaz(S.day[f['asset']].c[-1], 2), group=g)
        C.add(loc, 'entry_close empty', c['entry_close'], None, group=g)
        C.add(loc, 'must_close_above', c['must_close_above'], None if f['kill'] is None else L.rhaz(f['kill'], 2), group=g)
        if f['kill'] is not None:
            import math
            C.add(loc, 'must_close_above: a close 1 cent above it confirms, a close at it does not', c['must_close_above'], math.floor(f['kill'] * 100) / 100, group='9 must-close-above wording',
                  cause='rounded up past the threshold: a close exactly at the shown price would confirm')
        G, text, rule = M.pick_sample(P, f['asset'], f['tf'], c['grade'], lens_codes(c))
        figs = M.card_figs(S, G)
        cmp_card(C, loc, c, figs, text, g)
        mine['cards'].append(dict(sid=sid, f=f, figs=figs, text=text, grade=c['grade']))
    # ---------------- 5. example card
    g = '5 example card'
    xc = F['example_card']; lim = dt.date(2024, 9, 22)
    Pk = M.pool(S, known_by=lim)
    exs = S.by.get(('ETH 2D', '2024-09-22'))
    exrow = next((r for r in S.ledger if r['chart'] == 'ETH 2D' and r['entry'] == '2024-09-22'), None)
    C.add('feed.example_card', 'exists once the example signal has closed its 60 days', xc is not None, exrow is not None, group=g)
    if xc is not None and exrow is not None:
        C.add('feed.example_card', 'grade as the ledger row', xc['grade'], exrow['grade'], group=g)
        C.add('feed.example_card', 'confirmations as the ledger row', sorted(lens_codes(xc)), sorted(k for k in exrow['lenses'].split(' + ') if k != '-'), group=g)
        G, text, rule = M.pick_sample(Pk, 'ETH', '2D', xc['grade'], lens_codes(xc), example=True)
        C.add('feed.example_card', 'every sample signal had closed its 60th day by 2024-09-22', all(x['d0'] + dt.timedelta(days=60) <= lim for x in G), True, group=g)
        figs = M.card_figs(S, G)
        cmp_card(C, 'feed.example_card', xc, figs, text, g)
        C.add('feed.example_card', 'signal_id', xc['signal_id'], 'ETH-2D-2024-09-22', group=g)
        C.add('feed.example_card', 'low_date', xc['low_date'], str(exs['tdate']), group=g)
        C.add('feed.example_card', 'low_day', xc['low_day'], str(M.low_day(S, 'ETH', '2D', exs['tdate'])), group=g)
        C.add('feed.example_card', 'confirms_on', xc['confirms_on'], '2024-09-22', group=g)
        C.add('feed.example_card', 'entry_close', xc['entry_close'], L.rhaz(exs['entry'], 2), group=g)
        C.add('feed.example_card', 'price_now none', xc['price_now'], None, group=g)
        C.add('feed.example_card', 'bars_to_confirm / must_close_above none', (xc['bars_to_confirm'], xc['must_close_above']), (None, None), group=g)
        C.add('feed.example_card', 'example flag', xc.get('example'), True, group=g)
        mine['example'] = dict(figs=figs, text=text, s=exs, grade=xc['grade'], sample=G)
    # ---------------- 6. open signals + their cards
    g = '6 open_signals'
    mo = M.open_list(S)
    fo = {o['signal_id']: o for o in F['open_signals']}
    C.add('feed.open_signals', 'ids (graded charts, ETH and BTC, inside 60 days)', [o['signal_id'] for o in F['open_signals']],
          [f"{s['asset']}-{s['tf']}-{s['d0']}" for s in mo], group=g)
    for s in mo:
        sid = f"{s['asset']}-{s['tf']}-{s['d0']}"; o = fo.get(sid)
        if not o: continue
        loc = f'feed.open_signals {sid}'
        pr = M.open_progress(S, s)
        C.add(loc, 'chart', o['chart'], s['chart'], group=g)
        C.add(loc, 'entry_date', o['entry_date'], str(s['d0']), group=g)
        C.add(loc, 'entry_close', o['entry_close'], L.rhaz(s['entry'], 2), group=g)
        C.add(loc, 'tags', o['tags'], s['tags'], group=g)
        for f in ('days_elapsed', 'day10_pct', 'day30_pct', 'day60_pct', 'best_so_far_pct', 'worst_so_far_pct'):
            C.add(loc, f, o[f], pr[f], group=g)
        c = o['card']; lens = frozenset(k for k in o['confirmations'].split(' + ') if k and k != '-')
        C.add(loc, 'card present', c is not None, True, group=g)
        if c is None: continue
        g2 = '5 open-signal cards'; loc2 = f'feed.open_signals[{sid}].card'
        C.add(loc2, 'card confirmations = signal confirmations', sorted(lens_codes(c)), sorted(lens), group=g2)
        C.add(loc2, 'card grade = signal grade', c['grade'], o['grade'], group=g2)
        C.add(loc2, 'signal_id', c['signal_id'], sid, group=g2)
        C.add(loc2, 'chart/asset/timeframe', (c['chart'], c['asset'], c['timeframe']), (s['chart'], s['asset'], s['tf']), group=g2)
        C.add(loc2, 'low_date', c['low_date'], str(s['tdate']), group=g2)
        C.add(loc2, 'low_day', c['low_day'], str(M.low_day(S, s['asset'], s['tf'], s['tdate'])), group=g2)
        C.add(loc2, 'confirms_on', c['confirms_on'], str(s['d0']), group=g2)
        C.add(loc2, 'entry_close', c['entry_close'], L.rhaz(s['entry'], 2), group=g2)
        C.add(loc2, 'price_now (latest daily close)', c['price_now'], L.rhaz(S.day[s['asset']].c[-1], 2), group=g2)
        C.add(loc2, 'bars_to_confirm / must_close_above none', (c['bars_to_confirm'], c['must_close_above']), (None, None), group=g2)
        G, text, rule = M.pick_sample(P, s['asset'], s['tf'], o['grade'], lens)
        figs = M.card_figs(S, G)
        cmp_card(C, loc2, c, figs, text, g2)
        C.add(loc, 'edge_level_pct', o['edge_level_pct'], figs['_edge'], group=g)
        C.add(loc, 'edge_status', o['edge_status'], M.edge_status(S, s, figs['_edge'], pr['ks']), group=g)
        mine['open'].append(dict(sid=sid, s=s, pr=pr, figs=figs, text=text, grade=o['grade'], edge=figs['_edge'], status=M.edge_status(S, s, figs['_edge'], pr['ks'])))
    # ---------------- 6. prints
    g = '6 prints'
    mp = []
    for a in L.ASSETS:
        for tf in L.TFS_ALL:
            conf = [s for s in S.ch[(a, tf)].sig if s['d0'] is not None][-3:]
            for s in conf:
                mp.append(dict(signal_id=f"{a}-{tf}-{s['d0']}", chart=s['chart'], state='confirmed', provisional=False, low_date=str(s['tdate']), confirms_on=str(s['d0']),
                               entry_close=L.rhaz(s['entry'], 2), tags=s['tags'], note='regime on' if S.gate(s['tdate']) else 'regime off'))
            f = M.forming(S, a, tf)
            if f:
                mp.append(dict(signal_id=f"{a}-{tf}-{f['confirms']}", chart=f['chart'], state='forming', provisional=True, low_date=str(f['tdate']), confirms_on=str(f['confirms']),
                               entry_close=L.rhaz(f['price'], 2), tags=f['tags'], note=('regime on' if f['gate_on'] else 'regime off') + f"; {f['need']} bar(s) to confirm"))
    C.add('feed.prints', 'ids in order', [p['signal_id'] + ':' + p['state'] for p in F['prints']], [p['signal_id'] + ':' + p['state'] for p in mp], group=g)
    tp = {(p['signal_id'], p['state']): p for p in F['prints']}
    for p in mp:
        t = tp.get((p['signal_id'], p['state']))
        if not t: continue
        for f in ('chart', 'provisional', 'low_date', 'confirms_on', 'entry_close', 'tags', 'note'):
            C.add(f"feed.prints {p['signal_id']} {p['state']}", f, t[f], p[f], group=g)
    mine['prints'] = mp
    # ---------------- 7. past paths
    g = '7 past_paths'
    for pp in F['past_paths']:
        G = [x for x in P if x['asset'] == pp['asset'] and x['grade'] == 'A+']
        n, days = M.paths(S, G)
        C.add(f"feed.past_paths {pp['asset']}", 'signals', pp['signals'], n, group=g)
        C.add(f"feed.past_paths {pp['asset']}", 'signals = all top-grade signals', pp['signals'], len(G), group=g)
        C.add(f"feed.past_paths {pp['asset']}", 'days listed', [d['day'] for d in pp['days']], list(range(61)), group=g)
        for t, m in zip(pp['days'], days):
            for f in ('q25_pct', 'median_pct', 'q75_pct'):
                C.add(f"feed.past_paths {pp['asset']} day {m['day']}", f, t[f], m[f], group=g)
        mine['paths'][pp['asset']] = (n, days)
    C.add('feed.past_paths', 'assets', [p['asset'] for p in F['past_paths']], [a for a in ('ETH', 'BTC') if any(x['asset'] == a and x['grade'] == 'A+' for x in P)], group=g)
    ep = F['example_past_paths']
    G = [x for x in Pk if x['asset'] == 'ETH' and x['grade'] == 'A+']
    n, days = M.paths(S, G)
    C.add('feed.example_past_paths', 'present when there are known signals', ep is not None, n > 0, group='7 example_past_paths')
    if ep is not None:
        C.add('feed.example_past_paths', 'signals', ep['signals'], n, group='7 example_past_paths')
        C.add('feed.example_past_paths', 'signals = ETH top-grade signals known by 2024-09-22', ep['signals'], len(G), group='7 example_past_paths')
        for t, m in zip(ep['days'], days):
            for f in ('q25_pct', 'median_pct', 'q75_pct'):
                C.add(f"feed.example_past_paths day {m['day']}", f, t[f], m[f], group='7 example_past_paths')
    mine.setdefault('paths', {})['example'] = (n, days)
    mine['pool'] = P
    return S, C, mine

if __name__ == '__main__':
    from collections import Counter
    for name in STATES:
        S, C, mine = run(name)
        C.save(f'checks_feed_{name}.csv')
        print(name, len(C.rows), 'checks', len(C.bad()), 'bad')
        print(Counter(r['group'] for r in C.rows))
        for r in C.bad()[:40]: print('  ', r['location'], '|', r['label'], '|', r['shown'], '|', r['yours'], '|', r['cause'])
        print('  tier', mine['odds_fade']['keep'], mine['odds_fade']['pool_n'], 'per_year', mine['per_year_feed'])
        print('  forming', [(f['chart'], str(f['tdate']), f['need'], str(f['confirms']), f['gate_on'], f['kill']) for f in mine['forming_all']])
