"""Check 1: every ledger row, every column, and membership."""
import sys, datetime as dt, csv
from lib import *

def funding_ok(S, a):
    """ETH membership: funding exists at entry with a 90-day median (>=60 of the prior 90 days), and the
    two 7-day windows of the 'not cooling' lens each have >=5 days."""
    rows = list(csv.DictReader(open(f'{S.root}/data/derivs/{a}_funding_daily.csv')))
    fw = {}; fm = {}
    for r in rows:
        d = dt.date.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): fw[d] = float(v)
        if r.get('funding_mean') not in ('', None): fm[d] = float(r['funding_mean'])
    def ok(d0):
        if d0 not in fw: return False
        back = [1 for k in range(1, 91) if d0 - dt.timedelta(days=k) in fw]
        if len(back) < 60: return False
        w7 = [1 for k in range(7) if d0 - dt.timedelta(days=k) in fm]
        w7b = [1 for k in range(7) if d0 - dt.timedelta(days=14 + k) in fm]
        return len(w7) >= 5 and len(w7b) >= 5
    return ok

def run(name):
    S = State(name); R = Rec(name, 'c1')
    led = S.ledger
    mine = {}
    for a in ASSETS:
        fok = funding_ok(S, a)
        for tf in GRADED:
            for s in S.signals(a, tf):
                m = S.measure(a, s['edate'], s['entry'], s['sentry'])
                if m is None: continue
                if a == 'ETH' and not fok(s['edate']): continue
                s = dict(s, m=m); mine[(s['chart'], str(s['edate']))] = s
    lk = {(r['chart'], r['entry']): r for r in led}
    R.add('ledger.csv', 'row count', len(led), len(mine))
    R.add('ledger.csv', 'duplicate (chart, entry) keys', len(led) - len(lk), 0)
    miss = sorted(set(mine) - set(lk)); extra = sorted(set(lk) - set(mine))
    R.add('ledger.csv', 'signals I find that the ledger lacks', len(miss), 0, cause=str(miss[:8]))
    R.add('ledger.csv', 'ledger rows I do not find', len(extra), 0, cause=str(extra[:8]))
    # sort order
    # per-row
    S.mine_led = mine
    per = {}
    for r in led:
        key = (r['chart'], r['entry']); loc = f"ledger {r['chart']} {r['entry']}"
        s = mine.get(key)
        if s is None: continue
        m = s['m']
        R.add(loc, 'asset', r['asset'], s['a'])
        R.add(loc, 'low (trough bar date)', r['low'], str(s['tdate']))
        R.add(loc, 'entryPrice', r['entryPrice'], rnd(s['sentry'], 2))
        R.add(loc, 'tags', r['tags'], tagstr(s))
        R.add(loc, 'year', r['year'], s['edate'].year)
        R.add(loc, 'bestMove', r['bestMove'], rnd(repr(m['up']), 6))
        R.add(loc, 'maxDrawdown', r['maxDrawdown'], rnd(repr(m['dd']), 6))
        R.add(loc, 'dipBeforeHigh', r['dipBeforeHigh'], rnd(repr(m['ddpk']), 6))
        R.add(loc, 'return60d', r['return60d'], rnd(repr(m['ret']), 6))
        R.add(loc, 'daysToHigh', r['daysToHigh'], m['dpk'])
        R.add(loc, 'reached10', r['reached10'], yn(m['r10']))
        R.add(loc, 'reached15', r['reached15'], yn(m['r15']))
        R.add(loc, 'reached20', r['reached20'], yn(m['r20']))
        R.add(loc, 'touched30', r['touched30'], yn(m['t30']))
        R.add(loc, 'surv10', r['surv10'], yn(m['surv10']))
        R.add(loc, 'scaled20', r['scaled20'], '' if m['scaled20'] is None else yn(m['scaled20']))
        R.add(loc, 'gate on at the trough date', 'on', 'on' if s['gate'] else 'off')
    # grade columns (whole-sample grade odds, asset+grade as given)
    for a in ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            G = [mine[(r['chart'], r['entry'])] for r in led if r['asset'] == a and r['grade'] == g and (r['chart'], r['entry']) in mine]
            if not G: continue
            n = len(G)
            g20 = share(sum(x['m']['r20'] for x in G), n); g30 = share(sum(x['m']['t30'] for x in G), n)
            gmd = rnd(repr(st.median(x['m']['dd'] for x in G)), 1)
            for r in led:
                if r['asset'] == a and r['grade'] == g:
                    loc = f"ledger {r['chart']} {r['entry']}"
                    R.add(loc, 'gradeReach20', r['gradeReach20'], g20)
                    R.add(loc, 'gradeTouched30', r['gradeTouched30'], g30)
                    R.add(loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], gmd)
    # odds on the day: prior signals of the asset known by then (entry + 60 <= this entry)
    for r in led:
        key = (r['chart'], r['entry']); loc = f"ledger {r['chart']} {r['entry']}"
        if key not in mine: continue
        d0 = dt.date.fromisoformat(r['entry'])
        prior = [(q, mine[(q['chart'], q['entry'])]) for q in led if q['asset'] == r['asset'] and (q['chart'], q['entry']) in mine
                 and dt.date.fromisoformat(q['entry']) + dt.timedelta(days=60) <= d0]
        G = [x for x in prior if x[0]['grade'] == r['grade']]
        R.add(loc, 'dayN', r['dayN'], len(G))
        def rate(fn, okf=lambda m: True):
            if len(G) < 10 or not prior: return ''
            P = [x for x in prior if okf(x[1]['m'])]; Gk = [x for x in G if okf(x[1]['m'])]
            if not P or not Gk: return ''
            base = Fraction(sum(1 for x in P if fn(x[1]['m'])), len(P))
            return rnd_exact(100 * (sum(1 for x in Gk if fn(x[1]['m'])) + 5 * base) / (len(Gk) + 5))
        R.add(loc, 'dayReach10', r['dayReach10'], rate(lambda m: m['r10']))
        R.add(loc, 'dayReach20', r['dayReach20'], rate(lambda m: m['r20']))
        R.add(loc, 'dayReach30', r['dayReach30'], rate(lambda m: m['r30']))
        R.add(loc, 'dayTouched30', r['dayTouched30'], rate(lambda m: m['t30']))
        R.add(loc, 'daySurv10', r['daySurv10'], rate(lambda m: m['surv10']))
        R.add(loc, 'dayScaled20', r['dayScaled20'], rate(lambda m: bool(m['scaled20']), okf=lambda m: m['scaled20'] is not None))
    # row order: by asset (ETH then BTC), then entry date
    R.save()
    return S, mine

if __name__ == '__main__':
    for name in STATES:
        S, mine = run(name)
        # near-tie diagnostics
        import decimal
        close = []
        for k, s in mine.items():
            m = s['m']
            for lab, lvl in (('+10', '1.10'), ('+15', '1.15'), ('+20', '1.20'), ('+30', '1.30')):
                if abs(m['Dhi'] / (m['De'] * Decimal(lvl)) - 1) < Decimal('0.0002'): close.append((k, lab, str(m['Dhi']), str(m['De'] * Decimal(lvl))))
            for lab, lvl in (('-30', '0.70'), ('-25.3', '0.747')):
                if abs(m['Dlo'] / (m['De'] * Decimal(lvl)) - 1) < Decimal('0.0002'): close.append((k, lab, str(m['Dlo']), str(m['De'] * Decimal(lvl))))
            if m['scaled_margin'] is not None and abs(m['scaled_margin']) < 0.05: close.append((k, 'scaled20', m['up'], 20 * m['volr']))
        print('near-threshold cases:', close)
