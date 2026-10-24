"""Capabilities pack: every setup layer recomputed under today's rules.

Built 24 Oct 2026 for Joe's AI (ETHKROS). Jared reviews before anything is
sent. Replaces quoting old emails and the 9-16 Oct odds pages: every figure
here is recomputed from data/ with the current definitions.

DECLARED BEFORE RUNNING

Signals   E.signals on ETH and BTC 1D 2D 3D 5D 8D, gate
          R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41). Entry = close of the
          confirmation bar, dated the day that bar closes (bucket_end).
Outcomes  daily candles, 60 days after entry, full windows only:
            win     reach +20% (max high) within 60 days      <- headline
            green   close above entry on day 60 (the old v3/v4 "WIN")
            safe    +20% before touching -20%
            ddpk    worst low before the 60-day high (median reported)
            t20/t30 touched -20% / -30% within 60 days
Periods   2016-21 and 2022 on, always shown separately.

Layer 1   base rate per chart.
Layer 2   tags per chart: A, B, C, D, any diamond, filled diamond (<50),
          hollow diamond (>=50), A+diamond, B+diamond, prime dot,
          prime+diamond. Lift = tag minus the chart's own base.
Layer 3   Tier 1 and promising filters per chart and pooled per asset:
          CT > Signal by 5+, CT>Signal + prime, CT>Signal + diamond, higher
          entry than the previous signal, 2+ other same-asset charts already
          confirmed (10 days before), 8D CT rising, and 8D rising paired with
          higher entry / CT>Signal / prime / diamond.
Layer 4   confluence, BACKWARD ONLY: the confirming chart's signal must have
          confirmed 0-10 days before this signal's entry. Grid = trade chart
          (10) x trade tag (layer 2 list + all) x confirming chart (9 others)
          x confirming tag (any, A, B, diamond, prime). Cells need 8+ in each
          arm. "Without" = same trade tag, no such confirmer.
          SURVIVOR = n with >= 15, lift >= +10 points on win, lift > 0 in both
          periods (each period n with >= 5).
          SMALL SAMPLE = 8 <= n with < 15, with-rate >= 75%, lift >= +15.
          Several thousand cells: some survivors will be luck. Survivors are
          candidates, not validated.
Layer 4b  the 44 confluence rows on the v4 odds page, each recomputed twice:
          (old) the v4 method on today's data -- trough dates within +/-10
          days either side, win = green at 60 days -- and (now) backward only,
          both metrics. Shows which old rows survive.
Layer 5   reads as the trade matures (trades not yet at +20% on the check
          day): green on day 5, green on day 10, chart CT above Signal on
          day 10, low undercut the trough bar's low by day 10, down 10%+ by
          day 10. Reported as win with vs without, by period.

ENTRY QUALITY ONLY. No exit, so no strategy return. Signals are computed,
never fills.

  python3 -I analysis/grokpack.py      -> RESULTS_grokpack.txt, grokpack.json
"""
import sys, os, json, datetime as dt, statistics as st, re, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure
from sweep import closed_index

GATE = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D')
SPLIT = dt.date(2022, 1, 1)
TAGS = [('all', lambda s: True), ('A', lambda s: s['bk'] == 'A'), ('B', lambda s: s['bk'] == 'B'),
        ('C', lambda s: s['bk'] == 'C'), ('D', lambda s: s['bk'] == 'D'),
        ('diamond', lambda s: s['dis']), ('filled diamond', lambda s: s['strong']),
        ('hollow diamond', lambda s: s['dis'] and not s['strong']),
        ('A+diamond', lambda s: s['dis'] and s['bk'] == 'A'), ('B+diamond', lambda s: s['dis'] and s['bk'] == 'B'),
        ('prime', lambda s: s['prime']), ('prime+diamond', lambda s: s['prime'] and s['dis'])]
CTAGS = [('any', lambda s: True), ('A', lambda s: s['bk'] == 'A'), ('B', lambda s: s['bk'] == 'B'),
         ('diamond', lambda s: s['dis']), ('prime', lambda s: s['prime'])]


def build():
    day = {a: E.load(f'data/{a}_1D.csv') for a in ASSETS}
    pos = {a: {d: i for i, d in enumerate(day[a]['date'])} for a in ASSETS}
    b8 = {a: E.load(f'data/{a}_8D.csv') for a in ASSETS}
    ct8 = {a: E.rsi(b8[a]['close'], 14) for a in ASSETS}
    allsig = {}; rows = []
    for a in ASSETS:
        for tf in TFS:
            sig, b = E.signals(f'data/{a}_{tf}.csv', regime=GATE)
            ct = E.rsi(b['close'], 14); em = E.ema(ct, 14)
            lst = []; prev = None
            for s in sig:
                d0 = bucket_end(b['date'], s['ei'])
                if d0 is None:
                    continue
                g = ct[s['ei']] - em[s['ei']] if ct[s['ei']] is not None and em[s['ei']] is not None else None
                r = dict(ch=f'{a} {tf}', a=a, tf=tf, d0=d0, tdate=s['date'], entry=s['entry'],
                         bk=s['bk'], dis=s['dis'], strong=s['strong'], prime=s['prime'],
                         gap=g, higher=prev is not None and s['entry'] > prev,
                         tlow=b['low'][s['ti']], ei=s['ei'])
                k8 = closed_index(b8[a]['date'], d0)
                r['up8'] = k8 >= 1 and ct8[a][k8] is not None and ct8[a][k8 - 1] is not None and ct8[a][k8] > ct8[a][k8 - 1]
                prev = s['entry']
                m = measure(day[a], pos[a], d0, s['entry'], 60) if d0 in pos[a] else None
                if m:
                    r.update(m=m, per='16-21' if d0 < SPLIT else '22-26', yr=d0.year,
                             win=m['up'] >= 20, green=m['ret'] > 0, t20=m['dd'] <= -20, t30=m['dd'] <= -30)
                    sw = False
                    for k in range(1, 61):
                        j = pos[a].get(d0 + dt.timedelta(days=k))
                        if j is None: continue
                        if day[a]['low'][j] <= s['entry'] * 0.8: break
                        if day[a]['high'][j] >= s['entry'] * 1.2: sw = True; break
                    r['safe'] = sw
                    # maturing reads
                    def c_at(n):
                        j = pos[a].get(d0 + dt.timedelta(days=n)); return None if j is None else day[a]['close'][j]
                    def lows_to(n):
                        return [day[a]['low'][pos[a][d0 + dt.timedelta(days=k)]] for k in range(1, n + 1)
                                if d0 + dt.timedelta(days=k) in pos[a]]
                    def highs_to(n):
                        return [day[a]['high'][pos[a][d0 + dt.timedelta(days=k)]] for k in range(1, n + 1)
                                if d0 + dt.timedelta(days=k) in pos[a]]
                    r['hit5'] = max(highs_to(5), default=0) >= s['entry'] * 1.2
                    r['hit10'] = max(highs_to(10), default=0) >= s['entry'] * 1.2
                    c5, c10 = c_at(5), c_at(10)
                    r['g5'] = c5 is not None and c5 >= s['entry']
                    r['g10'] = c10 is not None and c10 >= s['entry']
                    l10 = lows_to(10)
                    r['under10'] = min(l10, default=1e18) < b['low'][s['ti']]
                    r['down10'] = min(l10, default=1e18) <= s['entry'] * 0.9
                    kk = closed_index(b['date'], d0 + dt.timedelta(days=10))
                    r['ctabove10'] = ct[kk] is not None and em[kk] is not None and ct[kk] > em[kk]
                lst.append(r)
            allsig[(a, tf)] = lst
            rows += [r for r in lst if 'm' in r]
    # same-asset agreement, backward 0-10 days
    for r in rows:
        r['agree'] = sum(1 for t in TFS if t != r['tf'] and
                         any(0 <= (r['d0'] - x['d0']).days <= 10 for x in allsig[(r['a'], t)]))
    return rows, allsig


def stats(G):
    if not G:
        return None
    n = len(G)
    out = dict(n=n, win=100 * sum(r['win'] for r in G) / n, green=100 * sum(r['green'] for r in G) / n,
               safe=100 * sum(r['safe'] for r in G) / n, t20=100 * sum(r['t20'] for r in G) / n,
               t30=100 * sum(r['t30'] for r in G) / n, ddpk=st.median(r['m']['ddpk'] for r in G))
    for p in ('16-21', '22-26'):
        x = [r for r in G if r['per'] == p]
        out[p] = (100 * sum(r['win'] for r in x) / len(x), len(x)) if x else (None, 0)
    return out


def yrs_ahead(W, A):
    ys = sorted({r['yr'] for r in W} & {r['yr'] for r in A}); k = 0
    for y in ys:
        w = [r['win'] for r in W if r['yr'] == y]; o = [r['win'] for r in A if r['yr'] == y]
        k += (sum(w) / len(w)) > (sum(o) / len(o))
    return k, len(ys)


def fmt(s):
    if not s:
        return 'n=0'
    p1 = f'{s["16-21"][0]:.0f}% ({s["16-21"][1]})' if s['16-21'][0] is not None else '- (0)'
    p2 = f'{s["22-26"][0]:.0f}% ({s["22-26"][1]})' if s['22-26'][0] is not None else '- (0)'
    return (f'n={s["n"]:>4} win {s["win"]:4.0f}%  [16-21 {p1:>10} | 22-26 {p2:>10}]  green60 {s["green"]:3.0f}%  '
            f'safe {s["safe"]:3.0f}%  ddpk {s["ddpk"]:+6.1f}%  t20 {s["t20"]:3.0f}%  t30 {s["t30"]:3.0f}%')


def v4_rows():
    out = []
    s = open('docs/artifacts/odds_v4.html', encoding='utf-8').read()
    txt = lambda c: html.unescape(re.sub('<[^>]+>', '', c)).strip()
    for tbl in re.findall(r'<table>(.*?)</table>', s, flags=re.S):
        rws = re.findall(r'<tr>(.*?)</tr>', tbl, flags=re.S)
        hdr = [txt(c) for c in re.findall(r'<th[^>]*>(.*?)</th>', rws[0], flags=re.S)]
        if 'CONFIRM' not in hdr:
            continue
        for r in rws[1:]:
            out.append(dict(zip(hdr, [txt(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', r, flags=re.S)])))
    return out


V4TAG = {'ALL troughs': 'all', 'A  trough <40': 'A', 'B  trough 40-55': 'B', 'C  trough 55-65': 'C',
         'D  trough >65': 'D', 'Any diamond': 'diamond', 'GOLD diamond <50': 'filled diamond',
         'HOLLOW diamond >=50': 'hollow diamond', 'A + diamond': 'A+diamond', 'B + diamond': 'B+diamond',
         'Prime K 20-50': 'prime'}
V4CTAG = {'any trough': 'any', 'A bucket': 'A', 'B bucket': 'B', 'diamond': 'diamond'}


def main():
    rows, allsig = build()
    T = dict(TAGS); CT = dict(CTAGS)
    J = dict(layer1=[], layer2=[], layer3=[], layer4=[], layer4_small=[], layer4b=[], layer5=[])
    P = print
    P('CAPABILITIES PACK -- recomputed', dt.date.today(), '| entry quality only, signals not fills\n')
    P('LAYER 1  base rate, regime on, reach +20% within 60 days')
    base = {}
    for a in ASSETS:
        for tf in TFS:
            G = [r for r in rows if r['ch'] == f'{a} {tf}']; s = stats(G); base[f'{a} {tf}'] = s
            P(f'  {a} {tf:<3} {fmt(s)}'); J['layer1'].append(dict(chart=f'{a} {tf}', **s))
    P('\nLAYER 2  tags per chart (lift = tag win minus chart base)')
    for a in ASSETS:
        for tf in TFS:
            ch = f'{a} {tf}'; G = [r for r in rows if r['ch'] == ch]
            for name, f in TAGS[1:]:
                s = stats([r for r in G if f(r)])
                if not s or s['n'] < 5: continue
                lift = s['win'] - base[ch]['win']
                P(f'  {ch:<7} {name:<15} lift {lift:+4.0f}  {fmt(s)}')
                J['layer2'].append(dict(chart=ch, tag=name, lift=round(lift), **s))
    P('\nLAYER 3  filters (lift vs the same group without the filter)')
    F = [('CT>Signal by 5+', lambda r: r['gap'] is not None and r['gap'] > 5),
         ('CT>Signal + prime', lambda r: r['gap'] is not None and r['gap'] > 0 and r['prime']),
         ('CT>Signal + diamond', lambda r: r['gap'] is not None and r['gap'] > 0 and r['dis']),
         ('higher entry', lambda r: r['higher']),
         ('2+ own charts before', lambda r: r['agree'] >= 2),
         ('8D rising', lambda r: r['up8']),
         ('8D rising + higher entry', lambda r: r['up8'] and r['higher']),
         ('8D rising + CT>Signal', lambda r: r['up8'] and r['gap'] is not None and r['gap'] > 0),
         ('8D rising + prime', lambda r: r['up8'] and r['prime']),
         ('8D rising + diamond', lambda r: r['up8'] and r['dis'])]
    groups = [(c, [r for r in rows if r['ch'] == c]) for c in base] + \
             [(f'{a} pooled', [r for r in rows if r['a'] == a]) for a in ASSETS]
    for name, f in F:
        for gname, G in groups:
            W = [r for r in G if f(r)]; A = [r for r in G if not f(r)]
            if len(W) < 8 or len(A) < 8: continue
            sw, sa = stats(W), stats(A); k, ny = yrs_ahead(W, A)
            P(f'  {name:<24} {gname:<10} lift {sw["win"]-sa["win"]:+4.0f} (without {sa["win"]:.0f}%, {ny and f"{k}/{ny}"} yrs ahead)  {fmt(sw)}')
            J['layer3'].append(dict(filter=name, group=gname, lift=round(sw['win'] - sa['win']), without=round(sa['win']),
                                    years_ahead=f'{k}/{ny}', **sw))
    P('\nLAYER 4  confluence, backward only (confirmer confirmed 0-10 days before entry)')
    cells = []
    for (a, tf) in allsig:
        ch = f'{a} {tf}'; G = [r for r in rows if r['ch'] == ch]
        for tname, tf_ in TAGS:
            sub = [r for r in G if tf_(r)]
            if len(sub) < 16: continue
            for (ca, ctf), clist in allsig.items():
                if (ca, ctf) == (a, tf): continue
                for cname, cf in CTAGS:
                    cd = [x['d0'] for x in clist if cf(x)]
                    W = [r for r in sub if any(0 <= (r['d0'] - d).days <= 10 for d in cd)]
                    wid = {id(r) for r in W}; A = [r for r in sub if id(r) not in wid]
                    if len(W) < 8 or len(A) < 8: continue
                    sw, sa = stats(W), stats(A); k, ny = yrs_ahead(W, A)
                    l1 = (sw['16-21'][0] - sa['16-21'][0]) if sw['16-21'][1] >= 5 and sa['16-21'][0] is not None else None
                    l2 = (sw['22-26'][0] - sa['22-26'][0]) if sw['22-26'][1] >= 5 and sa['22-26'][0] is not None else None
                    lift = sw['win'] - sa['win']
                    c = dict(trade=ch, tag=tname, confirm=f'{ca} {ctf}', ctag=cname, lift=round(lift),
                             without=round(sa['win']), lift16=None if l1 is None else round(l1),
                             lift22=None if l2 is None else round(l2), years_ahead=f'{k}/{ny}', **sw)
                    c['survivor'] = sw['n'] >= 15 and lift >= 10 and l1 is not None and l2 is not None and l1 > 0 and l2 > 0
                    c['small'] = 8 <= sw['n'] < 15 and sw['win'] >= 75 and lift >= 15
                    cells.append(c)
    surv = sorted([c for c in cells if c['survivor']], key=lambda c: (-c['win'], -c['n']))
    small = sorted([c for c in cells if c['small']], key=lambda c: (-c['win'], -c['n']))
    P(f'  {len(cells)} cells tested; {len(surv)} survivors; {len(small)} small-sample highs')
    for c in surv:
        P(f'  SURV {c["trade"]:<7} {c["tag"]:<15} <- {c["confirm"]:<7} {c["ctag"]:<8} lift {c["lift"]:+4d} '
          f'(without {c["without"]}%; by period {c["lift16"]:+d}/{c["lift22"]:+d}; {c["years_ahead"]} yrs)  {fmt(c)}')
    for c in small:
        P(f'  SMALL {c["trade"]:<7} {c["tag"]:<15} <- {c["confirm"]:<7} {c["ctag"]:<8} lift {c["lift"]:+4d} '
          f'(without {c["without"]}%)  {fmt(c)}')
    J['layer4'] = surv; J['layer4_small'] = small; J['layer4_cells_tested'] = len(cells)
    P('\nLAYER 4b  the 44 v4 confluence rows, recomputed')
    P('  v4 page figure | v4 method on today\'s data (trough dates +/-10d, green60) | backward only: green60 and win (+20%)')
    for v in v4_rows():
        ta, ttf = v['TRADE'].split(); ca, ctf = v['CONFIRM'].split()
        tname = V4TAG[v['TAG']]; cname = V4CTAG[v['CONFIRM TAG']]
        sub = [r for r in rows if r['ch'] == v['TRADE'] and T[tname](r)]
        cl = [x for x in allsig[(ca, ctf)] if CT[cname](x)]
        Wo = [r for r in sub if any(abs((r['tdate'] - x['tdate']).days) <= 10 for x in cl)]
        wo = {id(r) for r in Wo}; Ao = [r for r in sub if id(r) not in wo]
        Wn = [r for r in sub if any(0 <= (r['d0'] - x['d0']).days <= 10 for x in cl)]
        wn = {id(r) for r in Wn}; An = [r for r in sub if id(r) not in wn]
        g = lambda X, k: (100 * sum(r[k] for r in X) / len(X)) if X else None
        f = lambda x: '  -' if x is None else f'{x:3.0f}'
        rec = dict(trade=v['TRADE'], tag=tname, confirm=v['CONFIRM'], ctag=cname,
                   page=dict(n=int(v['n']), win=int(v['WIN'].rstrip('%')), alone=int(v['ALONE'].rstrip('%'))),
                   old=dict(n=len(Wo), green=g(Wo, 'green'), alone=g(Ao, 'green')),
                   now=dict(n=len(Wn), green=g(Wn, 'green'), green_alone=g(An, 'green'),
                            win=g(Wn, 'win'), win_alone=g(An, 'win'), stats=stats(Wn)))
        J['layer4b'].append(rec)
        P(f'  {v["TRADE"]:<7} {tname:<15} <- {v["CONFIRM"]:<7} {cname:<8} | page n={v["n"]:>3} {v["WIN"]:>4} vs {v["ALONE"]:>4} '
          f'| old n={len(Wo):>3} {f(g(Wo,"green"))}% vs {f(g(Ao,"green"))}% '
          f'| now n={len(Wn):>3} green {f(g(Wn,"green"))}% vs {f(g(An,"green"))}%  win {f(g(Wn,"win"))}% vs {f(g(An,"win"))}%')
    P('\nLAYER 5  reads as the trade matures (trades not yet at +20% on the check day)')
    for name, key, chk in [('green on day 5', 'g5', 'hit5'), ('green on day 10', 'g10', 'hit10'),
                           ('CT above Signal on day 10', 'ctabove10', 'hit10'),
                           ('undercut trough low by day 10', 'under10', 'hit10'),
                           ('down 10%+ by day 10', 'down10', 'hit10')]:
        for gname, G in [('ETH', [r for r in rows if r['a'] == 'ETH']), ('BTC', [r for r in rows if r['a'] == 'BTC'])]:
            G = [r for r in G if not r[chk]]
            W = [r for r in G if r[key]]; A = [r for r in G if not r[key]]
            sw, sa = stats(W), stats(A)
            P(f'  {name:<30} {gname}  yes: {fmt(sw)}\n  {"":<30} {gname}  no:  {fmt(sa)}')
            J['layer5'].append(dict(read=name, asset=gname, yes=sw, no=sa))
    json.dump(J, open('analysis/grokpack.json', 'w'), default=str, indent=1)


if __name__ == '__main__':
    main()
