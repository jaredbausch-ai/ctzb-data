"""Are the two A-cluster reads new information, or existing reads under another
name? Declared 26 Oct 2026 before running. Follows analysis/aclusters.py.

Universe: regime-on bucket A signals (CT at the trough < 40), gate
R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41), confirmation entry, win = +20%
within 60 days, all 10 ETH/BTC charts 1D-8D. ETH reported first.

READ 1 (in-trade): after entry, CT closes >= 50 first (BREAK) or turns down
from a bar in 40-50 first (REJECT), as in aclusters.py Part 2.
  Tested inside each existing in-trade read from docs/PRETRADE.md, on trades
  not at +20% by day 10 (and not by the event date):
    green on day 5 / red; green on day 10 / red; chart CT above its Signal
    line on day 10 / below; price undercut the trough bar's low by day 10 /
    not; down 10% or more (daily close) by day 10 / not.
  NEW INFORMATION if REJECT is at least 10 points below BREAK inside BOTH
  halves of at least 4 of the 5 reads, each cell n >= 8.

READ 2 (at entry): the later signal in an A cluster, split by whether the
bounce since the previous A signal closed CT >= 50.
  Tested inside the Tier 1 entry features: higher entry than the previous
  signal / not; CT > Signal by 5+ / not; 2+ other same-asset charts before /
  not; 8D CT rising / not.
  NEW INFORMATION if "bounce closed >= 50" is at least 15 points below
  "peaked under 50" inside BOTH halves of at least 3 of the 4 features, each
  cell n >= 5 (the broke-50 group is n=24 in total, so most cells will be
  too thin; that is reported as untestable, not as a pass).

Either way these are reads reported with the signal, never filters.
ENTRY QUALITY ONLY. Signals are computed, never fills.
  python3 -I analysis/areads.py -> analysis/RESULTS_areads.txt
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
from sweep import closed_index
import aclusters as AC
import grokpack as GP

L = []
P = lambda *x: (L.append(' '.join(str(i) for i in x)), print(*x))


def w(G):
    return (100 * sum(r['win'] for r in G) / len(G), len(G)) if G else (None, 0)


def cell(G):
    v, n = w(G)
    return f'{v:3.0f}% ({n:>3})' if n else '   -   (  0)'


def main():
    sigs, clusters = AC.build()
    gp = GP.build()[0]
    key = {(r['ch'], r['d0']): r for r in gp}
    CH = {}
    for a in AC.ASSETS:
        for tf in AC.TFS:
            b = E.load(f'data/{a}_{tf}.csv'); ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
            CH[f'{a} {tf}'] = (b, ct, em)
    day = AC.DAY; pos = AC.POS
    # in-trade states
    for r in sigs:
        a = r['a']; i = pos[a][r['d0']]
        cl = lambda k: day[a]['close'][i + k] if i + k < len(day[a]['close']) else None
        lows10 = [day[a]['low'][i + k] for k in range(1, 11) if i + k < len(day[a]['low'])]
        b, ct, em = CH[r['ch']]
        ti = r['ei'] - 3
        r['g5'] = cl(5) is not None and cl(5) > r['c0']
        r['g10'] = cl(10) is not None and cl(10) > r['c0']
        j = closed_index(b['date'], r['d0'] + dt.timedelta(days=10))
        r['ctab10'] = ct[j] is not None and em[j] is not None and ct[j] > em[j]
        r['under'] = bool(lows10) and min(lows10) < b['low'][ti]
        r['dn10'] = any(day[a]['close'][i + k] <= 0.9 * r['c0'] for k in range(1, 11) if i + k < len(day[a]['close']))
        cut = r['d0'] + dt.timedelta(days=10)
        r['open10'] = (r['hd'] is None or r['hd'] > cut) and (r['ev'] == 'NEITHER' or not r['known'])
        g = key.get((r['ch'], r['d0']))
        r['gp'] = g

    P('READ 1  BREAK-first vs REJECT-first, inside the existing in-trade reads (trades not at +20% by day 10)')
    reads = [('green day 5', 'g5'), ('green day 10', 'g10'), ('CT above Signal day 10', 'ctab10'),
             ('undercut trough low by day 10', 'under'), ('down 10%+ by day 10', 'dn10')]
    ok1 = 0
    for asset in ('ETH', 'BTC', 'ALL'):
        P(f'  {asset}')
        for lab, k in reads:
            line = f'    {lab:32}'
            good = True
            for state in (True, False):
                G = [r for r in sigs if r['open10'] and (asset == 'ALL' or r['a'] == asset) and r[k] == state]
                bv, bn = w([r for r in G if r['ev'] == 'BREAK']); rv, rn = w([r for r in G if r['ev'] == 'REJECT'])
                gap = bv - rv if bn and rn else None
                line += f' | {"yes" if state else "no ":3} BREAK {cell([r for r in G if r["ev"] == "BREAK"])} REJECT {cell([r for r in G if r["ev"] == "REJECT"])}'
                line += f' gap {gap:+4.0f}' if gap is not None else ' gap   - '
                if not (bn >= 8 and rn >= 8 and gap is not None and gap >= 10): good = False
            P(line + ('   NEW' if good else ''))
            if asset == 'ALL' and good: ok1 += 1
    P(f'  READ 1: separates inside both halves on {ok1}/5 reads (need 4) -> {"NEW INFORMATION" if ok1 >= 4 else "NOT NEW"}')

    P('\nREAD 2  later A signal in a cluster: bounce since the previous A signal closed >= 50, inside the Tier 1 entry features')
    pairs = []
    for c in clusters:
        b, ct, em = CH[c[0]['ch']]
        for p, q in zip(c, c[1:]):
            ti = q['ei'] - 3
            pk = max(ct[j] for j in range(p['ei'], ti + 1) if ct[j] is not None)
            pairs.append(dict(q, pk=pk, gp=key.get((q['ch'], q['d0']))))
    pairs = [r for r in pairs if r['gp']]
    feats = [('higher entry than previous signal', lambda g: g['higher']),
             ('CT > Signal by 5+', lambda g: g['gap'] is not None and g['gap'] > 5),
             ('2+ other same-asset charts before', lambda g: g['agree'] >= 2),
             ('8D CT rising', lambda g: g['up8'])]
    ok2 = 0; test2 = 0
    for asset in ('ETH', 'BTC', 'ALL'):
        P(f'  {asset}')
        for lab, fn in feats:
            line = f'    {lab:34}'; good = True; thin = False
            for state in (True, False):
                G = [r for r in pairs if (asset == 'ALL' or r['a'] == asset) and fn(r['gp']) == state]
                U = [r for r in G if r['pk'] < 50]; O = [r for r in G if r['pk'] >= 50]
                uv, un = w(U); ov, on = w(O)
                gap = uv - ov if un and on else None
                line += f' | {"yes" if state else "no ":3} under 50 {cell(U)} broke 50 {cell(O)}'
                line += f' gap {gap:+4.0f}' if gap is not None else ' gap   - '
                if un < 5 or on < 5: thin = True
                elif gap < 15: good = False
            tag = '   THIN' if thin else ('   NEW' if good else '')
            P(line + tag)
            if asset == 'ALL' and not thin:
                test2 += 1; ok2 += good
    P(f'  READ 2: testable on {test2}/4 features, separates on {ok2} (need 3 of 4) -> '
      f'{"NEW INFORMATION" if ok2 >= 3 else "UNTESTABLE (too few broke-50 cases)" if test2 < 3 else "NOT NEW"}')
    P('\n  ENTRY QUALITY ONLY. Computed signals, not fills.')
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULTS_areads.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
