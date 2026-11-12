import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8/code')
from cards8 import *
import chk

LABEL = ("Computed signal, not a fill. No trade was taken. Entry quality only: "
         "the data has no exits, so this is not a strategy return or a track record.")
MY = {}
for st in ('REPLAY', 'CURRENT'):
    feed = json.load(open(STATES[st] + '/feed/ctzb_feed.json'))
    L = ledger_with_grades(st)
    S = all_signals(st)
    b1 = {a: daily(st, a)[0] for a in ('ETH', 'BTC')}
    # ---- forming setups: my own detection on all 10 charts
    myform = {}
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D', '8D'):
            p = provisional(st, a, tf)
            if p:
                bars = S[(a, tf)]['bars']
                cd = conf_close_day(bars, p['ti'], tf)
                myform[f'{a}-{tf}-{cd}'] = (a, tf, p, cd)
    chk.add(st, 'feed cards', 'forming setups (ids)', ' '.join(sorted(c['signal_id'] for c in feed['cards'])), ' '.join(sorted(myform)))
    cardsets = [('feed cards', c, 'forming') for c in feed['cards']] + [('feed example_card', feed['example_card'], 'example')] + \
               [(f"feed open_signals {o['signal_id']} card", o['card'], 'open') for o in feed['open_signals']]
    for loc, c, kind in cardsets:
        if kind == 'forming': loc = f"feed cards {c['signal_id']}"
        a, tf = c['asset'], c['timeframe']; chart = f'{a} {tf}'
        lenses = frozenset() if c['confirmations'] == 'none' else frozenset(PLAIN[x] for x in c['confirmations'].split('; '))
        exp = {'label': LABEL, 'chart': chart}
        if kind == 'example':
            sig = L[('ETH 2D', '2024-09-22')]
            basis, G = choose(L, chart, a, tf, c['grade'], lenses, known_by=dt.date(2024, 9, 22))
            exp.update(signal_id='ETH-2D-2024-09-22', low_date=str(sig['tdate']), low_day=low_day(st, a, tf, sig['tdate']),
                       confirms_on='2024-09-22', bars_to_confirm=None, must_close_above=None, price_now=None,
                       entry_close=rhaz(sig['entry'], 2), example=True)
            exp['grade_vs_ledger'] = None
            chk.add(st, loc, 'grade equals the ledger row grade', c['grade'], sig['grade'])
            chk.add(st, loc, 'confirmations equal the ledger row lenses', ' + '.join(sorted(lenses)), ' + '.join(sorted(sig['lensset'])))
            del exp['grade_vs_ledger']
        elif kind == 'open':
            d0 = dt.date.fromisoformat(c['confirms_on'])
            sig = next(s for s in S[(a, tf)]['tr'] if s['d0'] == d0 and s['gated'] and s['closed'])
            basis, G = choose(L, chart, a, tf, c['grade'], lenses)
            exp.update(signal_id=f'{a}-{tf}-{d0}', low_date=str(sig['tdate']), low_day=low_day(st, a, tf, sig['tdate']),
                       confirms_on=str(d0), bars_to_confirm=None, must_close_above=None,
                       price_now=rhaz(b1[a][-1]['c'], 2), entry_close=rhaz(sig['entry'], 2))
        else:
            fa, ftf, p, cd = myform.get(c['signal_id'], (None, None, None, None))
            basis, G = choose(L, chart, a, tf, c['grade'], lenses)
            if p:
                kc = kill_close(st, a, tf, p)
                exp.update(signal_id=f'{a}-{tf}-{cd}', low_date=str(p['tdate']), low_day=low_day(st, a, tf, p['tdate']),
                           confirms_on=str(cd), bars_to_confirm=p['need'], must_close_above=None if kc is None else rhaz(F(kc), 2),
                           price_now=rhaz(S[(a, tf)]['bars'][-1]['c'], 2), entry_close=None)
        exp['sample'] = basis
        fig = figures(st, G)
        MY[(st, c['signal_id'] if kind != 'example' else 'example')] = dict(fig=fig, G=G, basis=basis)
        exp.update({k: v for k, v in fig.items() if k != '_exact'})
        fc = flat(c)
        for k, v in exp.items():
            chk.add(st, loc, k, fc.get(k), v, 'card field')
        # every field the card carries is checked or declared
        for k in fc:
            if k not in exp and k not in ('grade', 'confirmations', 'asset', 'timeframe') and not k.startswith('active_confluences'):
                chk.add(st, loc, f'{k} (unchecked field)', fc[k], 'not checked', ok=False, cause='unchecked field')
        chk.add(st, loc, 'asset/timeframe', f"{c['asset']} {c['timeframe']}", chart)
        if c['active_confluences']:
            chk.add(st, loc, 'active_confluences (out of scope, note h)', 'skipped', 'skipped')
        # internal consistency of the card
        chk.add(st, loc, 'eras add up to n', c['before_2022']['past_trades'] + c['since_2022']['past_trades'], c['past_trades'])
    # ---- open signals list
    expected_open = []
    for a in ('ETH', 'BTC'):
        for tf in ('1D', '2D', '3D', '5D'):
            for s in S[(a, tf)]['tr']:
                if s['gated'] and s['closed'] and 0 <= (TODAY[st] - s['d0']).days <= 60:
                    expected_open.append(s)
    chk.add(st, 'feed open_signals', 'ids', ' '.join(sorted(o['signal_id'] for o in feed['open_signals'])),
            ' '.join(sorted(f"{s['asset']}-{s['tf']}-{s['d0']}" for s in expected_open)))
    for o in feed['open_signals']:
        a, tf = o['chart'].split(); d0 = dt.date.fromisoformat(o['entry_date'])
        s = next(x for x in expected_open if x['asset'] == a and x['tf'] == tf and x['d0'] == d0)
        w = window(st, a, d0)
        E = s['entry']; loc = f"feed open_signals {o['signal_id']}"
        mark = lambda k: next((rhaz((x['c'] / E - 1) * 100, 1) for d, x in w if d == k), None)
        exp = dict(label=LABEL, signal_id=f'{a}-{tf}-{d0}', chart=f'{a} {tf}', entry_date=str(d0), entry_close=rhaz(E, 2), tags=tags(s),
                   days_elapsed=(TODAY[st] - d0).days, day10_pct=mark(10), day30_pct=mark(30), day60_pct=mark(60),
                   best_so_far_pct=rhaz((max(x['h'] for d, x in w) / E - 1) * 100, 1) if w else None,
                   worst_so_far_pct=rhaz((min(x['l'] for d, x in w) / E - 1) * 100, 1) if w else None)
        for k, v in exp.items():
            chk.add(st, loc, k, o.get(k), v, 'open signal')
        chk.add(st, loc, 'card grade/confirmations match the row', f"{o['card']['grade']}|{o['card']['confirmations']}",
                f"{o['grade']}|{'none' if o['confirmations'] == '-' else '; '.join(o['card']['confirmations'].split('; '))}")
import pickle
pickle.dump(MY, open(chk.OUT + '/code/_mycards.pkl', 'wb'))
chk.dump('_cards.csv')
bad = [c for c in chk.CHECKS if c['ok'] == 'no']
print(len(chk.CHECKS), 'checks', len(bad), 'bad')
for c in bad[:80]: print(c)
