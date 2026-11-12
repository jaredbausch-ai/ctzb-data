"""Check 4: odds_fade. (a) reproduce the signal set refresh.py describes, my own code;
(b) recompute the bands on daily candles per CONTEXT (60 days after the entry bar ends)."""
import csv, json, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C

OUT = os.path.dirname(os.path.abspath(__file__))
G = C.gate()
F = json.load(open(os.path.join(C.REPO, 'feed', 'ctzb_feed.json')))
TODAY = dt.date(2026, 11, 12)
ANCHOR = dt.date(TODAY.year, 1, 1)

sigs = []
for tf in ('1D', '2D', '3D', '5D', '8D'):
    tr, b = C.troughs('ETH', tf)
    D = [x['d'] for x in b]
    for t in tr:
        if not G(t['tdate']): continue
        tags = {t['bk'], 'any trough'}
        if t['dis']: tags |= {'diamond', 'filled' if t['strong'] else 'hollow'}
        if t['prime']: tags.add('prime dot')
        if t['dis'] and t['prime']: tags.add('diamond+dot')
        if t['zexit']: tags.add('zone-exit B')
        ei = t['ei']; e = t['entry']; end = D[ei] + dt.timedelta(days=60)
        rec = dict(chart=f'ETH {tf}', tf=tf, ei=ei, d_open=D[ei], d0=t['d0'], e=e, tags=tags, tdate=t['tdate'])
        if D[-1] >= end:
            js = [j for j in range(ei + 1, len(b)) if D[j] <= end]
            rec['win'] = b[js[-1]]['c'] > e
            # chart-bar measures, as the repo's earlydip/holdcheck take them
            lo10 = [b[j]['l'] for j in js if (D[j] - D[ei]).days <= 10]
            hi_aft = [b[j]['h'] for j in js if (D[j] - D[ei]).days >= 10]
            c10 = [b[j]['c'] for j in js if (D[j] - D[ei]).days <= 10]
            rec['bar'] = dict(dip=(min(lo10) / e - 1) * 100 if lo10 else None, mfe_after=(max(hi_aft) / e - 1) * 100 if hi_aft else None,
                              run=(max(b[j]['h'] for j in js) / e - 1) * 100, c10=(c10[-1] / e - 1) * 100 if c10 else None)
        sigs.append(rec)

scored = [s for s in sigs if 'win' in s]
TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
keep = []
for ch in ('ETH 1D', 'ETH 2D', 'ETH 3D', 'ETH 5D', 'ETH 8D'):
    for tg in TAGS:
        sub = [s for s in scored if s['chart'] == ch and tg in s['tags'] and s['d_open'] < ANCHOR]
        if len(sub) >= 8 and 100 * sum(s['win'] for s in sub) / len(sub) >= 70:
            keep.append((ch, tg))
print('keep (walk-forward, anchor', ANCHOR, '):', keep)
kept = [s for s in scored if any(s['chart'] == k[0] and k[1] in s['tags'] for k in keep)]
print('kept scored signals', len(kept))

BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
out = []
rp = lambda g, f: C.r_half(100 * sum(1 for x in g if f(x)) / len(g)) if g else None
# (a) repo's method, my code
A = [s for s in kept if s['bar']['dip'] is not None and s['bar']['mfe_after'] is not None]
for hi, lo, lab in BANDS:
    g = [s for s in A if lo < s['bar']['dip'] <= hi]
    out.append(dict(kind='early_dip', band=lab, method='chart bars from conf-bar OPEN; high day10-60', n=len(g),
                    r10=rp(g, lambda s: s['bar']['mfe_after'] >= 10), r20=rp(g, lambda s: s['bar']['mfe_after'] >= 20)))
H = [s for s in kept if s['bar']['c10'] is not None]
for lab, f in (('green on day 10', lambda s: s['bar']['c10'] >= 0), ('red on day 10', lambda s: s['bar']['c10'] < 0)):
    g = [s for s in H if f(s)]
    out.append(dict(kind='day10', band=lab, method='chart bars from conf-bar OPEN; high day1-60', n=len(g),
                    r10=rp(g, lambda s: s['bar']['run'] >= 10), r20=rp(g, lambda s: s['bar']['run'] >= 20)))
# (b) CONTEXT definition: daily candles, days 1..60 after the entry bar ENDS; rose 10% = any daily high in days 1..60
lastday = C.daily('ETH')[0][-1]['d']
Dd = []
for s in kept:
    m = C.fwd('ETH', s['d0'], s['e'])
    if m is None: continue
    s['day'] = dict(dip=(min(m['lows'][:10]) / s['e'] - 1) * 100, up=m['up'], up_after=(max(m['highs'][9:]) / s['e'] - 1) * 100,
                    c10=(m['closes'][9] / s['e'] - 1) * 100)
    Dd.append(s)
for hi, lo, lab in BANDS:
    g = [s for s in Dd if lo < s['day']['dip'] <= hi]
    out.append(dict(kind='early_dip', band=lab, method='daily from entry close; rose 10% any day 1-60', n=len(g),
                    r10=rp(g, lambda s: s['day']['up'] >= 10), r20=rp(g, lambda s: s['day']['up'] >= 20)))
for lab, f in (('green on day 10', lambda s: s['day']['c10'] >= 0), ('red on day 10', lambda s: s['day']['c10'] < 0)):
    g = [s for s in Dd if f(s)]
    out.append(dict(kind='day10', band=lab, method='daily from entry close; rose 10% any day 1-60', n=len(g),
                    r10=rp(g, lambda s: s['day']['up'] >= 10), r20=rp(g, lambda s: s['day']['up'] >= 20)))
for x in out: x['edge_on_r10'] = 'intact' if x['r10'] >= 70 else 'gone'
for x in out: print(x)
from collections import Counter
print('kept by chart', Counter(s['chart'] for s in kept), 'years', min(s['d0'] for s in kept), max(s['d0'] for s in kept))
print('in daily set', len(Dd), 'excluded (window not complete on daily):', [(s['chart'], str(s['d0'])) for s in kept if s not in Dd])
# overlap with the graded ledger
led = {(r['chart'], r['entry']): r['grade'] for r in csv.DictReader(open(os.path.join(C.REPO, 'datasets', 'ledger.csv')))}
print('kept signals by ledger grade', Counter(led.get((s['chart'], str(s['d0'])), 'not in ledger') for s in kept))
# FP diamond signal
print('ETH 2D 2023-03-15 in kept set:', any(s['chart'] == 'ETH 2D' and str(s['d0']) == '2023-03-15' for s in kept))
json.dump(dict(keep=keep, n=len(kept), rows=out), open(os.path.join(OUT, 'check4.json'), 'w'), default=str, indent=0)
