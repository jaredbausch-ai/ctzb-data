"""The whole stack, live, every run (28 Oct 2026). Runs in the GitHub Action after
grade_live.py. Built after Jared had to correct a missed confluence: nothing that
is documented may be left unchecked against a live or open signal.

REGISTRY below is the single list of every documented read, indexed from
docs/PRETRADE.md (Tier 1, Promising, flags, conviction grade, in-trade reads,
positioning), CONTEXT.md (forward-watch candidates) and analysis/grokpack.json
(every confluence cell from layer 4, 4-small and the 44 v4 rows). check_coverage()
fails the run if a PRETRADE heading is not mapped to a registry id, or a registry
id is not evaluated.

For every SUBJECT -- every forming low on all 10 charts (ETH and BTC, 1D-8D) and
every signal confirmed in the last 60 days -- it evaluates every registry item and,
for each one that is on, the record on that chart with it on and with it off.
Drawdown is from entry: the median dip before the 60-day high, and the median
largest dip within 60 days. Forming lows are PROVISIONAL until they confirm;
window reads are evaluated at the date the low would confirm.

Writes datasets/:
  liveread.csv  subject, item, status, record (n, +20%, touched -30%, dip before
                high, largest dip in 60d), sample
  prints.csv    every chart: last signals and anything forming, with confirm dates
  windows.csv   every confluence window open now: which print opened it, what it
                applies to, and when it closes
Historical rates for entry quality only. Computed signals, never fills.
  python3 -I stack_live.py
"""
import csv, json, os, re, sys, datetime as dt, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'analysis'))
import engine as E
import regimes as R
import grokpack as GP
import pcrtest as PT
import refresh as RF
from sweep import closed_index
from htfdiv import divergences
from confirmlag import weekly
from derivtest import series
from grade3 import funding_series

OUT = os.path.join(HERE, 'datasets')
ASSETS = ('ETH', 'BTC'); TFS = ('1D', '2D', '3D', '5D', '8D')
SPLIT = dt.date(2022, 1, 1)
WIN = 10

# ------------------------------------------------------------------ registry
# id, label, asset scope, chart scope, kind, where documented
REGISTRY = [
    # conviction grade lenses (counted)
    ('GAP', 'CT above its Signal line by 5+', 'ETH BTC', 'all', 'grade lens + Tier 1 #1', 'PRETRADE Tier 1 #1; grade'),
    ('HIGH', 'Entry above the previous signal (higher low)', 'ETH BTC', 'all', 'grade lens (ETH) + Tier 1 #4', 'PRETRADE Tier 1 #4; grade'),
    ('AGREE', '2+ other same-asset charts confirmed 0-10 days before', 'ETH BTC', 'all', 'grade lens (ETH) + Tier 1 #5', 'PRETRADE Tier 1 #5; grade'),
    ('BTC3', 'BTC 3D confirmed 0-10 days before', 'ETH', '1D 2D', 'grade lens + Promising', 'PRETRADE Promising; grade'),
    ('FUND', 'Funding at or above its 90-day median', 'ETH BTC', 'all', 'grade lens (ETH) + positioning', 'PRETRADE grade; Positioning read'),
    ('FCOOL', 'Funding not cooling (7-day mean >= 14 days earlier)', 'ETH BTC', 'all', 'grade lens (ETH)', 'PRETRADE grade'),
    ('UP8', '8D CT RSI rising on its last closed bar', 'ETH BTC', 'all', 'grade lens (BTC) + Promising', 'PRETRADE Promising; grade'),
    ('BTCX', 'ETH 2D confirmed 0-10 days before', 'BTC', '1D 2D', 'grade lens + Promising', 'PRETRADE Promising; grade'),
    # flags beside the grade
    ('DIVH', 'Bullish Stoch divergence on a higher chart, last 10 days', 'ETH BTC', 'all', 'flag', 'PRETRADE grade flags'),
    ('MARKER', 'A diamond or a prime dot', 'ETH BTC', 'all', 'flag', 'PRETRADE grade flags'),
    # Tier 1 not already above
    ('T1PRIME', 'CT above Signal and a prime dot', 'ETH BTC', 'all', 'Tier 1 #2', 'PRETRADE Tier 1 #2'),
    ('T1DIAM', 'CT above Signal and a diamond', 'ETH BTC', 'all', 'Tier 1 #3', 'PRETRADE Tier 1 #3'),
    ('REGIME', 'Regime gate on (BTC 2D RSI regime)', 'ETH BTC', 'all', 'Tier 1 #6', 'PRETRADE Tier 1 #6'),
    ('REGAGE', 'Regime age (higher-low filter is late-regime)', 'ETH BTC', 'all', 'context for Tier 1 #4', 'PRETRADE Tier 1 #4'),
    # Promising not already above
    ('SHALLOW', 'Shallow pullback: entry near its 30-day high (top third per chart)', 'ETH BTC', 'all', 'Promising', 'PRETRADE Promising'),
    ('E3B1', 'ETH 3D confirmed 0-10 days before (near miss)', 'BTC', '1D', 'near miss', 'PRETRADE Promising (near miss); grade4'),
    ('FASTCT', 'Fast CT recovery, trough to confirmation (top third per chart)', 'ETH BTC', 'all', 'grade lens (BTC)', 'PRETRADE grade; grade6'),
    ('B3E3', 'BTC 3D confirmed 0-10 days before (near miss: sample)', 'ETH', '3D', 'near miss', 'PRETRADE grade; grade6'),
    # tags
    ('BUCKET', 'Bucket at the trough (A <40, B 40-55, C 55-65, D 65+)', 'ETH BTC', 'all', 'tag', 'indicator'),
    ('DIAMOND', 'Diamond (filled / hollow)', 'ETH BTC', 'all', 'tag', 'indicator'),
    ('PRIME', 'Prime dot', 'ETH BTC', 'all', 'tag', 'indicator'),
    # forward-watch candidates (CONTEXT / PRETRADE failed-list near misses)
    ('K1', 'BTC put/call top band (pct >= 95) at the last weekly close', 'BTC', 'all', 'watch lens (agreed 28 Oct)', 'PRETRADE failed list near miss; CONTEXT'),
    ('W5B', 'Weekly momentum above its signal line', 'ETH', 'all', 'forward watch', 'PRETRADE failed list near miss (5b)'),
    ('STD1', 'ETH 2D higher entry + 8D rising', 'ETH', '2D', 'forward watch', 'CONTEXT standard.py'),
    ('STD2', 'BTC 1D CT>Signal by 5+ and OBV above its 20-bar average', 'BTC', '1D', 'forward watch', 'CONTEXT standard.py'),
    ('STD3', 'Prime dot + 2+ own charts agreeing', 'ETH', 'all', 'forward watch', 'CONTEXT standard.py'),
    ('LSFALL', 'Prime dot + long/short ratio falling over 14 days', 'ETH', 'all', 'forward watch', 'CONTEXT derivtest.py'),
    # positioning (caution read)
    ('POS', 'Positioning: funding vs median, direction, long/short, OI 14d', 'ETH BTC', 'all', 'caution read', 'PRETRADE Positioning read'),
    # confluence cells (grokpack layer 4 / small / v4 rows), evaluated generically
    ('CELLS', 'Every documented confluence cell (chart+tag after confirmer+tag, 0-10 days)', 'ETH BTC', 'all', 'confluence cells', 'analysis/grokpack.json'),
    # in-trade reads (open signals)
    ('D5', 'Green on day 5', 'ETH BTC', 'all', 'in-trade', 'PRETRADE In-trade reads'),
    ('D10', 'Green on day 10', 'ETH BTC', 'all', 'in-trade', 'PRETRADE In-trade reads'),
    ('CT10', 'CT above its Signal line on day 10', 'ETH BTC', 'all', 'in-trade', 'PRETRADE In-trade reads'),
    ('UNDER10', 'Price undercut the trough low by day 10', 'ETH BTC', 'all', 'in-trade', 'PRETRADE In-trade reads'),
    ('DOWN10', 'Down 10% or more by day 10', 'ETH BTC', 'all', 'in-trade', 'PRETRADE In-trade reads'),
    ('A50', 'A signals: CT broke 50 first, or rejected from 40-50 first', 'ETH BTC', 'all', 'in-trade (partial)', 'PRETRADE A signals'),
]
REG_IDS = [r[0] for r in REGISTRY]
# PRETRADE headings that must map to registry ids (checked every run)
DOC_MAP = {
    '1. CT RSI more than 5 points above the Signal line': ['GAP'],
    '2. CT above the Signal line **and** a prime dot': ['T1PRIME'],
    '3. CT above the Signal line **and** a diamond': ['T1DIAM'],
    '4. Higher low versus the previous signal\'s entry': ['HIGH', 'REGAGE'],
    '5. Cross-timeframe agreement — ETH only': ['AGREE'],
    '6. Regime gate on': ['REGIME'],
    'BTC 3D signal already confirmed within 10 days before an ETH 1D / 2D signal': ['BTC3'],
    'ETH 2D signal already confirmed within 10 days before a BTC 1D signal': ['BTCX'],
    'Higher-timeframe CT rising — the asset\'s 8D CT RSI up on its last completed bar': ['UP8'],
    'Shallow pullback — entry close near its 30-day high (top third per chart)': ['SHALLOW'],
    'A signals only: does CT close at 50 before it turns down? (26 Oct 2026, partial)': ['A50'],
}
WATCH_NOTE = ('CT RSI day-ten three-state read (CONTEXT open items): the definition of '
              '"both agree" is not written in the repo, so it cannot be computed yet.')


def check_coverage(evaluated):
    txt = open(os.path.join(HERE, 'docs', 'PRETRADE.md')).read()
    sec = txt.split('## Tier 1')[1].split('## Positioning read')[0]
    heads = [h.strip() for h in re.findall(r'^### (.+)$', sec, re.M)]
    missing = [h for h in heads if h not in DOC_MAP]
    unknown = [i for ids in DOC_MAP.values() for i in ids if i not in REG_IDS]
    unevaluated = [i for i in REG_IDS if i not in evaluated]
    if missing or unknown or unevaluated:
        msg = ('COVERAGE FAILURE -- ' + '; '.join(missing + unknown + unevaluated))
        open(os.path.join(OUT, 'stack_status.txt'), 'w').write(f'{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC FAILED {msg}\n')
        raise SystemExit('COVERAGE FAILURE -- a documented read is not in the live stack:\n'
                         + ''.join(f'  PRETRADE heading not mapped: {h}\n' for h in missing)
                         + ''.join(f'  mapped id not in REGISTRY: {i}\n' for i in unknown)
                         + ''.join(f'  registry id never evaluated: {i}\n' for i in unevaluated))
    return heads


# ------------------------------------------------------------------ helpers
def rec(G):
    n = len(G)
    if not n: return [0, '', '', '', '', '', '', '']
    return [n, round(100 * sum(r['win'] for r in G) / n), round(100 * sum(r['t30'] for r in G) / n),
            round(st.median(r['m']['ddpk'] for r in G), 1), round(st.median(r['m']['dd'] for r in G), 1),
            round(100 * sum(r['m']['up'] >= 10 for r in G) / n), round(100 * sum(r['m']['up'] >= 15 for r in G) / n),
            round(st.median(r['m']['up'] for r in G), 1)]


def near(d0, lst, w=WIN):
    return [d for d in lst if 0 <= (d0 - d).days <= w]


def main():
    gate = R.rsi_regime(os.path.join(HERE, 'data/BTC_2D.csv'), 8, 13, 60, 41)
    rows, allsig = GP.build()
    every = [r for lst in allsig.values() for r in lst]
    fb = PT.funding_below()
    FS = {a: funding_series(a) for a in ASSETS}
    LS = {a: series(f'data/derivs/{a}_lsratio_daily.csv', 'ls_ratio_mean') for a in ASSETS}
    OI = {a: series(f'data/derivs/{a}_oi_daily.csv', 'oi_usd_total') for a in ASSETS}
    PCR = PT.reads(PT.load_pcr('BTC'))
    DV = {(a, tf): [d for d, _ in divergences(f'data/{a}_{tf}.csv', osc='k')] for a in ASSETS for tf in TFS}
    DAY = {a: E.load(f'data/{a}_1D.csv') for a in ASSETS}
    CTS = {(a, tf): E.rsi(E.load(f'data/{a}_{tf}.csv')['close'], 14) for a in ASSETS for tf in TFS}
    DPOS = {a: {d: i for i, d in enumerate(DAY[a]['date'])} for a in ASSETS}
    WK = {}
    for a in ASSETS:
        w = weekly(DAY[a], 1); cw = E.rsi(w['close'], 14); ew = E.ema(cw, 14); WK[a] = (w['end'], cw, ew)
    B8 = {a: E.load(f'data/{a}_8D.csv') for a in ASSETS}
    C8 = {a: E.rsi(B8[a]['close'], 14) for a in ASSETS}
    VOL = {}
    for a in ASSETS:
        b = E.load(f'data/{a}_1D.csv'); vv = [float(x['volume'] or 0) for x in csv.DictReader(open(f'data/{a}_1D.csv'))]
        obv = [0.0]
        for i in range(1, len(b['close'])):
            v = vv[i] if i < len(vv) else 0
            obv.append(obv[-1] + (v if b['close'][i] > b['close'][i - 1] else -v if b['close'][i] < b['close'][i - 1] else 0))
        VOL[a] = (b['date'], obv, E.sma(obv, 20))
    D0S = {k: [x['d0'] for x in v] for k, v in allsig.items()}
    today = max(DAY['ETH']['date'])

    # regime age
    def regime_age(d):
        if not gate(d): return None
        k = 0
        while gate(d - dt.timedelta(days=k + 1)) and k < 3000: k += 1
        return k

    def funding_at(a, d):
        v = fb.get((a, d))
        if v is None:
            ds = [x for (aa, x) in fb if aa == a and x <= d]
            v = fb[(a, max(ds))] if ds else None
        return None if v is None else (not v)

    def fcool_at(a, d):
        f = FS[a]
        w7 = [f[d - dt.timedelta(days=k)] for k in range(7) if d - dt.timedelta(days=k) in f]
        w7b = [f[d - dt.timedelta(days=14 + k)] for k in range(7) if d - dt.timedelta(days=14 + k) in f]
        if len(w7) < 5 or len(w7b) < 5:
            last = max((x for x in f if x <= d), default=None)
            if last is None or last == d: return None
            return fcool_at(a, last)
        return sum(w7) / len(w7) >= sum(w7b) / len(w7b)

    def k1_at(d):
        sun = d - dt.timedelta(days=(d.weekday() + 1) % 7)
        x = PCR.get(sun)
        return None if x is None else x['pct'] >= 95

    def w5b_at(a, d):
        ends, cw, ew = WK[a]
        ks = [i for i, e in enumerate(ends) if e <= d]
        if not ks: return None
        i = ks[-1]
        return cw[i] is not None and ew[i] is not None and cw[i] > ew[i]

    def obv_at(a, d):
        ds, obv, s = VOL[a]
        ks = [i for i, x in enumerate(ds) if x <= d]
        if not ks: return None
        i = ks[-1]
        return s[i] is not None and obv[i] > s[i]

    def lsfall_at(a, d):
        l = LS[a]; x = l.get(d) or l.get(d - dt.timedelta(days=1)); y = l.get(d - dt.timedelta(days=14)) or l.get(d - dt.timedelta(days=15))
        return None if x is None or y is None else x < y

    def shallow_val(a, d0, entry):
        i = DPOS[a].get(d0)
        if i is None: return None
        return entry / max(DAY[a]['close'][max(0, i - 30):i + 1])

    # features on every historical signal (for the records)
    for r in every:
        a, tf, d0 = r['a'], r['tf'], r['d0']
        r.setdefault('agree', sum(1 for t in TFS if t != tf and near(d0, D0S[(a, t)])))
        r['btc3'] = a == 'ETH' and tf in ('1D', '2D') and bool(near(d0, D0S[('BTC', '3D')]))
        r['btcx'] = a == 'BTC' and tf in ('1D', '2D') and bool(near(d0, D0S[('ETH', '2D')]))
        r['e3b1'] = a == 'BTC' and tf == '1D' and bool(near(d0, D0S[('ETH', '3D')]))
        r['fund'] = (lambda v: None if v is None else (not v))(fb.get((a, d0)))
        r['fcool'] = fcool_at(a, d0) if d0 in FS[a] or any(d0 - dt.timedelta(days=k) in FS[a] for k in range(7)) else None
        r['divh'] = any(near(d0, DV[(a, t)]) for t in TFS[TFS.index(tf) + 1:])
        r['k1'] = k1_at(d0) if a == 'BTC' else None
        r['w5b'] = w5b_at(a, d0)
        r['obv'] = obv_at(a, d0)
        r['lsfall'] = lsfall_at(a, d0)
        r['f5'] = shallow_val(a, d0, r['entry'])
        r['b3e3'] = a == 'ETH' and tf == '3D' and bool(near(d0, D0S[('BTC', '3D')]))
        cc = CTS[(a, tf)]; ei = r['ei']
        r['f17'] = cc[ei] - cc[ei - 3] if cc[ei] is not None and cc[ei - 3] is not None else None
    # shallow pullback cut points: top third per chart from 2016-21 (sweep.py's discovery cut)
    CUT = {}
    for k in allsig:
        v = sorted(r['f5'] for r in allsig[k] if r['f5'] is not None and r['d0'] < SPLIT)
        CUT[k] = v[int(2 * len(v) / 3)] if len(v) >= 9 else None
    FCUT = {}
    for k in allsig:
        v = sorted(r['f17'] for r in rows if (r['a'], r['tf']) == k and r.get('f17') is not None and r['d0'] < SPLIT)
        FCUT[k] = v[int(2 * len(v) / 3)] if len(v) >= 9 else None
    for r in every:
        fc = FCUT.get((r['a'], r['tf'])); r['fastct'] = None if fc is None or r['f17'] is None else r['f17'] >= fc
    for r in every:
        c = CUT.get((r['a'], r['tf'])); r['shallow'] = None if c is None or r['f5'] is None else r['f5'] >= c

    def feats(r):
        g = r['gap']
        return {
            'GAP': g is not None and g > 5, 'HIGH': bool(r['higher']), 'AGREE': r['agree'] >= 2,
            'BTC3': bool(r['btc3']), 'FUND': r['fund'], 'FCOOL': r['fcool'], 'UP8': bool(r['up8']),
            'BTCX': bool(r['btcx']), 'DIVH': bool(r['divh']), 'MARKER': bool(r['prime'] or r['dis']),
            'T1PRIME': g is not None and g > 0 and bool(r['prime']), 'T1DIAM': g is not None and g > 0 and bool(r['dis']),
            'SHALLOW': r['shallow'], 'E3B1': bool(r['e3b1']), 'FASTCT': r['fastct'], 'B3E3': bool(r.get('b3e3')), 'PRIME': bool(r['prime']), 'DIAMOND': bool(r['dis']),
            'K1': r['k1'], 'W5B': r['w5b'], 'STD1': bool(r['higher']) and bool(r['up8']),
            'STD2': (g is not None and g > 5) and bool(r['obv']), 'STD3': bool(r['prime']) and r['agree'] >= 2,
            'LSFALL': (bool(r['prime']) and r['lsfall']) if r['lsfall'] is not None else None,
        }
    scope = {x[0]: (x[2].split(), x[3]) for x in REGISTRY}

    def applies(i, a, tf):
        A, C = scope[i]
        return a in A and (C == 'all' or tf in C.split())

    # ------------------------------------------------ subjects: forming + open
    subjects = []
    prints = []
    for a in ASSETS:
        for tf in TFS:
            path = f'data/{a}_{tf}.csv'
            b = E.load(path); C, D = b['close'], b['date']; n = len(C)
            ct = E.rsi(C, 14); em = E.ema(ct, 14); kL = E.sma(E.stoch_of(ct, 14), 3); zm = RF.zser(ct)
            step = int(st.median([(D[i] - D[i - 1]).days for i in range(max(1, n - 20), n)]))
            sig = allsig[(a, tf)]
            for s in sig[-3:]:
                prints.append([f'{a} {tf}', 'confirmed', str(s['tdate']), str(s['d0']), round(s['entry'], 2),
                               ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else [])),
                               'regime on' if gate(s['d0']) else 'regime off'])
            p = RF.provisional(ct, kL, zm, D, n)
            if p:
                conf_open = D[-1] + dt.timedelta(days=step * p['need'])
                d0f = conf_open + dt.timedelta(days=step - 1)
                piv, _ = E.signals(path, regime=lambda d: True)
                prevp = [x for x in piv if x['ti'] < p['ti']]
                dis = bool(prevp) and p['k'] is not None and ((p['ct'] - prevp[-1]['ct']) * (p['k'] - prevp[-1]['k']) < 0)
                strong = dis and p['ct'] < 50
                prev_entry = sig[-1]['entry'] if sig else None
                k8 = closed_index(B8[a]['date'], today)
                i = n - 1
                r = dict(a=a, tf=tf, ch=f'{a} {tf}', d0=d0f, entry=C[i], bk=p['bucket'], dis=dis, strong=strong,
                         prime=p['k'] is not None and 20 <= p['k'] < 50,
                         gap=(ct[i] - em[i]) if ct[i] is not None and em[i] is not None else None,
                         higher=prev_entry is not None and C[i] > prev_entry,
                         up8=k8 >= 1 and C8[a][k8] is not None and C8[a][k8 - 1] is not None and C8[a][k8] > C8[a][k8 - 1],
                         agree=sum(1 for t in TFS if t != tf and near(d0f, D0S[(a, t)])),
                         btc3=a == 'ETH' and tf in ('1D', '2D') and bool(near(d0f, D0S[('BTC', '3D')])),
                         btcx=a == 'BTC' and tf in ('1D', '2D') and bool(near(d0f, D0S[('ETH', '2D')])),
                         e3b1=a == 'BTC' and tf == '1D' and bool(near(d0f, D0S[('ETH', '3D')])),
                         fund=funding_at(a, today), fcool=fcool_at(a, today),
                         divh=any(near(d0f, DV[(a, t)]) for t in TFS[TFS.index(tf) + 1:]),
                         k1=k1_at(d0f) if a == 'BTC' else None, w5b=w5b_at(a, today), obv=obv_at(a, today),
                         lsfall=lsfall_at(a, today), f5=shallow_val(a, today, C[i]))
                c = CUT.get((a, tf)); r['shallow'] = None if c is None or r['f5'] is None else r['f5'] >= c
                fc = FCUT.get((a, tf)); r['b3e3'] = a == 'ETH' and tf == '3D' and bool(near(d0f, D0S[('BTC', '3D')]))
                r['fastct'] = None if fc is None or ct[i] is None else (ct[i] - ct[p['ti']]) >= fc
                tags = ' + '.join([p['bucket']] + (['filled diamond'] if strong else ['hollow diamond'] if dis else []) + (['prime dot'] if r['prime'] else []))
                prints.append([f'{a} {tf}', 'forming', str(p['date']), str(d0f), round(C[i], 2), tags,
                               ('regime on' if gate(today) else 'regime off') + f'; {p["need"]} bar(s) to confirm'])
                subjects.append(('forming (provisional)', r, tags))
            for s in sig:
                if 0 <= (today - s['d0']).days <= 60:
                    tags = ' + '.join([s['bk']] + (['filled diamond'] if s['strong'] else ['hollow diamond'] if s['dis'] else []) + (['prime dot'] if s['prime'] else []))
                    subjects.append((f'open, day {(today - s["d0"]).days}', s, tags))

    # ------------------------------------------------ evaluate
    out = []; evaluated = set()
    cells = []
    J = json.load(open(os.path.join(HERE, 'analysis', 'grokpack.json')))
    for lay in ('layer4', 'layer4_small', 'layer4b'):
        for c in J[lay]: cells.append((lay, c))
    TAG = dict(GP.TAGS); CTAG = dict(GP.CTAGS)
    LENS = json.load(open(os.path.join(HERE, 'analysis', 'grade.json')))['lenses']
    for k, v in json.load(open(os.path.join(HERE, 'analysis', 'grade2.json'))).items():
        LENS[k] = LENS[k] + [x for x in v if x != 'DIVH']
    for k, v in json.load(open(os.path.join(HERE, 'analysis', 'grade3.json')))['counted'].items():
        LENS[k] = LENS[k] + v
    for k, v in json.load(open(os.path.join(HERE, 'analysis', 'grade6.json')))['added'].items():
        LENS[k] = LENS[k] + v
    for state, r, tags in subjects:
        a, tf, d0 = r['a'], r['tf'], r['d0']
        subj = f'{a} {tf} {state}, confirms {d0}' if state.startswith('forming') else f'{a} {tf} {state}, entry {d0}'
        F = feats(r)
        Cr = [s for s in rows if s['a'] == a and s['tf'] == tf]
        # grade + this setup's own record
        have = [k for k in LENS[a] if F.get(k)]
        g = 'C' if len(have) <= 1 else 'B' if len(have) == 2 else 'A' if len(have) == 3 else 'A+'
        Cf = [s for s in Cr if s.get('fund') is not None and s.get('fcool') is not None] if a == 'ETH' else Cr
        sets = lambda s: {k for k in LENS[a] if feats(s).get(k)}
        out.append([subj, f'Grade {g}: {" + ".join(have) or "no lenses"}', 'grade'] + ['', '', '', '', '', '', '', ''] + [''])
        out.append([subj, 'This chart with at least these lenses', 'record'] + rec([s for s in Cf if set(have) <= sets(s)]) + ['from 2020' if a == 'ETH' else 'full history'])
        out.append([subj, 'This chart with exactly these lenses', 'record'] + rec([s for s in Cf if set(have) == sets(s)]) + ['from 2020' if a == 'ETH' else 'full history'])
        out.append([subj, 'This chart, every signal', 'record'] + rec(Cr) + ['full history'])
        # every registry item
        for rid, label, A_, C_, kind, src in REGISTRY:
            if rid in ('CELLS', 'POS', 'REGIME', 'REGAGE', 'BUCKET', 'D5', 'D10', 'CT10', 'UNDER10', 'DOWN10', 'A50'):
                continue
            evaluated.add(rid)
            if not applies(rid, a, tf):
                continue
            v = F.get(rid)
            status = 'ON' if v else 'off' if v is not None else 'no data'
            base = [s for s in Cr if feats(s).get(rid) is not None]
            on = [s for s in base if feats(s).get(rid)]; off = [s for s in base if feats(s).get(rid) is False]
            samp = 'full history' if len(base) == len(Cr) else f'from {min(s["d0"] for s in base)}' if base else ''
            out.append([subj, f'{label} [{kind}]', status] + rec(on if v else off) + [samp + (' (record with it on)' if v else ' (record with it off)')])
        # bucket, regime
        evaluated.update({'BUCKET', 'REGIME', 'REGAGE'})
        out.append([subj, f'Bucket {r["bk"]} on this chart [tag]', 'ON'] + rec([s for s in Cr if s['bk'] == r['bk']]) + ['full history'])
        ra = regime_age(d0 if d0 <= today else today)
        out.append([subj, 'Regime gate [Tier 1 #6]', 'ON' if ra is not None else 'OFF', '', '', '', '', '', '', '', '', f'on for {ra} days' if ra is not None else ''])
        # confluence cells
        evaluated.add('CELLS')
        for lay, c in cells:
            if c['trade'] != f'{a} {tf}' or not TAG.get(c['tag'], lambda s: False)(r):
                continue
            ca, ctf = c['confirm'].split()
            conf = [x for x in allsig[(ca, ctf)] if 0 <= (d0 - x['d0']).days <= WIN and CTAG.get(c['ctag'], lambda s: False)(x)]
            if not conf: continue
            hist = [s for s in Cr if TAG[c['tag']](s) and any(0 <= (s['d0'] - x['d0']).days <= WIN and CTAG[c['ctag']](x) for x in allsig[(ca, ctf)])]
            out.append([subj, f'Confluence cell: {c["trade"]} {c["tag"]} after {c["confirm"]} {c["ctag"]} ({conf[-1]["d0"]}) [{lay}]', 'ON'] + rec(hist) + ['full history'])
        # positioning read
        evaluated.add('POS')
        pd_ = min(d0, today - dt.timedelta(days=1))
        f = FS[a]; fd = max((x for x in f if x <= pd_), default=None)
        if fd:
            l = LS[a].get(fd); l14 = LS[a].get(fd - dt.timedelta(days=14)); o = OI[a].get(fd); o14 = OI[a].get(fd - dt.timedelta(days=14))
            txt = (f'funding {"at/above" if F["FUND"] else "BELOW (caution)"} its 90d median; '
                   f'{"not cooling" if F["FCOOL"] else "cooling"}; '
                   + (f'L/S {l:.2f} vs {l14:.2f} 2 wks ago; ' if l and l14 else '')
                   + (f'OI {100 * (o / o14 - 1):+.1f}% in 14d' if o and o14 else ''))
            out.append([subj, f'Positioning read ({fd}) [caution read]', txt, '', '', '', '', '', '', '', '', ''])
        # in-trade reads for open signals
        evaluated.update({'D5', 'D10', 'CT10', 'UNDER10', 'DOWN10', 'A50'})
        if not state.startswith('forming'):
            age = (today - d0).days
            px = DAY[a]; pos = DPOS[a]
            def c_at(nd):
                j = pos.get(d0 + dt.timedelta(days=nd)); return None if j is None else px['close'][j]
            lows = [px['low'][pos[d0 + dt.timedelta(days=k)]] for k in range(1, min(10, age) + 1) if d0 + dt.timedelta(days=k) in pos]
            reads = []
            if age >= 5: reads.append(('D5', 'Green on day 5', c_at(5) is not None and c_at(5) >= r['entry'], 'g5'))
            if age >= 10:
                reads.append(('D10', 'Green on day 10', c_at(10) is not None and c_at(10) >= r['entry'], 'g10'))
                bb = E.load(f'data/{a}_{tf}.csv'); cc = E.rsi(bb['close'], 14); ee = E.ema(cc, 14)
                kk = closed_index(bb['date'], d0 + dt.timedelta(days=10))
                reads.append(('CT10', 'CT above its Signal on day 10', cc[kk] is not None and ee[kk] is not None and cc[kk] > ee[kk], 'ctabove10'))
            if lows:
                reads.append(('UNDER10', f'Undercut the trough low (day {min(10, age)} so far)', min(lows) < r['tlow'], 'under10'))
                reads.append(('DOWN10', f'Down 10%+ (day {min(10, age)} so far)', min(lows) <= r['entry'] * 0.9, 'down10'))
            for rid, lab, v, key in reads:
                hist = [s for s in Cr if s.get(key) == v]
                out.append([subj, f'{lab} [in-trade]', 'YES' if v else 'no'] + rec(hist) + ['full history (record with the same answer)'])
            if r['bk'] == 'A':
                bb = E.load(f'data/{a}_{tf}.csv'); cc = E.rsi(bb['close'], 14)
                j0 = r['ei']; ev = 'neither yet'
                for j in range(j0 + 1, len(cc)):
                    if cc[j] is None: continue
                    if cc[j] >= 50: ev = 'broke 50 first'; break
                    if cc[j - 1] is not None and 40 <= cc[j - 1] < 50 and cc[j] < cc[j - 1]: ev = 'rejected from 40-50 first'; break
                out.append([subj, 'A signal: CT broke 50 first or rejected first [in-trade, partial]', ev, '', '', '', '', '', '', '', '',
                            'record: broke first 67% ETH / 59% BTC; rejected first 43% / 38% (PRETRADE)'])
    out.append(['(all)', WATCH_NOTE, 'not computed', '', '', '', '', '', '', '', '', ''])
    heads = check_coverage(evaluated)

    # ------------------------------------------------ windows open now
    wins = []
    for (a, tf), lst in allsig.items():
        for x in lst:
            age = (today - x['d0']).days
            if not 0 <= age <= WIN: continue
            closes = x['d0'] + dt.timedelta(days=WIN)
            others = ', '.join(f'{a} {t}' for t in TFS if t != tf)
            wins.append([f'{a} {tf}', str(x['d0']), str(closes), f'agreement count for {others}'])
            if (a, tf) == ('BTC', '3D'): wins.append([f'{a} {tf}', str(x['d0']), str(closes), 'BTC3 lens for ETH 1D / ETH 2D'])
            if (a, tf) == ('ETH', '2D'): wins.append([f'{a} {tf}', str(x['d0']), str(closes), 'BTCX lens for BTC 1D / BTC 2D'])
            if (a, tf) == ('ETH', '3D'): wins.append([f'{a} {tf}', str(x['d0']), str(closes), 'near miss: ETH 3D before BTC 1D'])
            for lay, c in cells:
                if c['confirm'] == f'{a} {tf}' and CTAG.get(c['ctag'], lambda s: False)(x):
                    wins.append([f'{a} {tf}', str(x['d0']), str(closes), f'confluence cell: {c["trade"]} {c["tag"]} ({lay})'])
    for (a, tf), lst in DV.items():
        for d in lst:
            if 0 <= (today - d).days <= WIN:
                lower = ', '.join(f'{a} {t}' for t in TFS[:TFS.index(tf)])
                if lower: wins.append([f'{a} {tf}', str(d), str(d + dt.timedelta(days=WIN)), f'DIVH flag (bullish Stoch divergence) for {lower}'])

    w = lambda p, h, rr: csv.writer(open(os.path.join(OUT, p), 'w', newline='')).writerows([h] + rr)
    w('liveread.csv', ['subject', 'read', 'status', 'n', 'reach20', 'touched30', 'dipBeforeHigh', 'maxDip60', 'reach10', 'reach15', 'bestMove', 'sample'], out)
    w('prints.csv', ['chart', 'state', 'trough', 'confirms', 'entry', 'tags', 'note'], prints)
    w('windows.csv', ['openedBy', 'confirmed', 'closes', 'appliesTo'], sorted(wins, key=lambda x: x[2]))
    json.dump([dict(zip(('id', 'label', 'assets', 'charts', 'kind', 'documented'), x)) for x in REGISTRY],
              open(os.path.join(HERE, 'analysis', 'registry.json'), 'w'), indent=1)
    open(os.path.join(OUT, 'stack_status.txt'), 'w').write(
        f'{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC OK {len(subjects)} subjects, {len(out)} reads, {len(wins)} open windows, '
        f'{len(REG_IDS)} registry ids, {len(cells)} confluence cells, data to {today}\n')
    print(f'stack_live: {len(subjects)} subjects, {len(out)} reads, {len(wins)} open windows, '
          f'{len(heads)} PRETRADE headings covered, {len(REG_IDS)} registry ids, {len(cells)} confluence cells')


if __name__ == '__main__':
    main()
