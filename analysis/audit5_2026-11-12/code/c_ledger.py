"""Check 1: every ledger row, and (as helper) my per-signal record keyed like the ledger."""
import csv, datetime as dt
from fractions import Fraction as Fr
import core as K
from rec import chk

GRADED = ('1D', '2D', '3D', '5D')


def mine_by_key(W):
    out = {}
    for (a, tf), lst in W['sig'].items():
        for s in lst:
            out[(f'{a} {tf}', str(s['d0']))] = s
    return out


_FF = {}


def first_fund(root):
    """First date with a funding read: 60+ of the previous 90 days carry ETH funding (raw data)."""
    if root not in _FF:
        f = set()
        for r in csv.DictReader(open(f'{root}/data/derivs/ETH_funding_daily.csv')):
            if (r.get('funding_oi_weighted') or r.get('funding_mean')) not in ('', None):
                f.add(dt.date.fromisoformat(r['date']))
        d = min(f)
        while sum((d - dt.timedelta(days=k)) in f for k in range(1, 91)) < 60 or d not in f:
            d += dt.timedelta(days=1)
        _FF[root] = d
    return _FF[root]


def grade_rec(rows):
    """rows: list of (ledger row, my signal). Whole-sample record of a grade."""
    n = len(rows)
    ms = [s['m'] for _, s in rows]
    return dict(n=n, reach20=K.share(sum(m['r20'] for m in ms), n), touched30=K.share(sum(m['t30'] for m in ms), n),
                medDip=K.rhaz(K.median([m['dd'] for m in ms]), 1), reach10=K.share(sum(m['r10'] for m in ms), n),
                surv10=K.share(sum(m['surv10'] for m in ms), n),
                first=min(s['d0'] for _, s in rows), last=max(s['d0'] for _, s in rows))


def check(st, W, root):
    led = list(csv.DictReader(open(f'{root}/datasets/ledger.csv')))
    mine = mine_by_key(W)
    loc = 'datasets/ledger.csv'
    keys = set()
    pairs = []
    for r in led:
        key = (r['chart'], r['entry']); keys.add(key)
        s = mine.get(key)
        lab = f"{r['chart']} {r['entry']}"
        if not chk(st, loc, f'{lab} membership: a gated, confirmed signal with 60 closed days', 'in ledger',
                   'in ledger' if (s and s['complete']) else ('not a signal' if not s else 'not complete'), 'row is not a gated confirmed signal with a closed 60-day window'):
            continue
        pairs.append((r, s))
        m = s['m']
        chk(st, loc, f'{lab} low (trough bar open date)', r['low'], str(s['trough']), 'trough date')
        chk(st, loc, f'{lab} entryPrice', r['entryPrice'], K.rhaz(s['entry'], 2), 'entry price')
        chk(st, loc, f'{lab} entry close = daily close on entry date', 'equal', 'equal' if s['daily_close_d0'] == s['entry'] else f"daily {s['daily_close_d0']}", 'bar close differs from daily close')
        chk(st, loc, f'{lab} tags', r['tags'], s['tags'], 'tags')
        chk(st, loc, f'{lab} year', r['year'], str(s['d0'].year), 'year')
        for col, key, nd in (('bestMove', 'up', 6), ('maxDrawdown', 'dd', 6), ('dipBeforeHigh', 'ddpk', 6), ('return60d', 'ret', 6)):
            chk(st, loc, f'{lab} {col}', r[col], K.rhaz(m[key], nd), f'{col} differs')
        chk(st, loc, f'{lab} daysToHigh', r['daysToHigh'], m['dpk'], 'day of high')
        for col, key in (('reached20', 'r20'), ('touched30', 't30'), ('reached10', 'r10'), ('reached15', 'r15'), ('surv10', 'surv10')):
            chk(st, loc, f'{lab} {col}', r[col], 'yes' if m[key] else 'no', f'{col} threshold')
        chk(st, loc, f'{lab} scaled20', r['scaled20'], '' if s['scaled20'] is None else ('yes' if s['scaled20'] else 'no'), 'scaled20')
    # missing rows: every gated, complete signal on a graded chart
    for (a, tf), lst in W['sig'].items():
        if tf not in GRADED:
            continue
        for s in lst:
            if s['complete'] and (f'{a} {tf}', str(s['d0'])) not in keys:
                why = 'ETH before funding read' if a == 'ETH' and s['d0'] < first_fund(root) else 'MISSING'
                chk(st, loc, f'{a} {tf} {s["d0"]} membership (gated complete signal absent from ledger)', 'absent', 'absent' if why != 'MISSING' else 'should be in ledger',
                    'signal missing from ledger')
    # grade columns and the day odds
    by = {}
    for r, s in pairs:
        by.setdefault((r['asset'], r['grade']), []).append((r, s))
    grec = {k: grade_rec(v) for k, v in by.items()}
    for r, s in pairs:
        g = grec[(r['asset'], r['grade'])]
        lab = f"{r['chart']} {r['entry']}"
        chk(st, loc, f'{lab} gradeReach20', r['gradeReach20'], g['reach20'], 'grade record')
        chk(st, loc, f'{lab} gradeTouched30', r['gradeTouched30'], g['touched30'], 'grade record')
        chk(st, loc, f'{lab} gradeMedDrawdown', r['gradeMedDrawdown'], g['medDip'], 'grade record')
    # odds on the day (shrunk 5 toward the prior base), prior = 60 days finished a day before entry
    hist = [(r['asset'], s['d0'], r['grade'], s) for r, s in pairs]
    for r, s in pairs:
        a, g, d0 = r['asset'], r['grade'], s['d0']
        prior = [h for h in hist if h[0] == a and h[1] + dt.timedelta(days=61) <= d0]
        G = [h for h in prior if h[2] == g]
        lab = f"{r['chart']} {r['entry']}"
        if len(G) < 10 or not prior:
            exp = ['', '', '', '', len(G), '', '']
        else:
            def rate(fn):
                base = Fr(sum(fn(h[3]) for h in prior), len(prior))
                return K.rhaz(Fr(100) * (sum(fn(h[3]) for h in G) + 5 * base) / (len(G) + 5))
            exp = [rate(lambda x: x['m']['r10']), rate(lambda x: x['m']['r20']), rate(lambda x: x['m']['up'] >= 30),
                   rate(lambda x: x['m']['t30']), len(G), rate(lambda x: x['m']['surv10']), rate(lambda x: bool(x['scaled20']))]
        for col, v in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10', 'dayScaled20'), exp):
            chk(st, loc, f'{lab} {col}', r[col], v, 'odds on the day')
    return pairs, grec
