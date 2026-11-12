"""Check 4: feed odds_fade. Recompute the walk-forward tier and the early-dip / day-10 tables independently.
Variant R ('repo method'): chart bars, days counted from the confirmation bar's OPEN date, horizon = bars opening
within 60 days, early dip = lows of bars opening day 1-10, +10% from bars opening day 10-60 (early dip) /
day 1-60 (day-10 table). Variant D ('stated'): daily candles from the entry date (confirmation close), days 1-60,
+10% counted from day 10 to day 60 for both tables, only windows whose 60th day has closed."""
import pickle, json, sys
from mine import *
from checks import rec, num_eq, dump, ROWS

TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]


def zmin_series(ct):
    out, z = [], None
    for v in ct:
        if v is None: out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v))
        out.append(z)
    return out


def tags(s, zm):
    t = [s['bk'], 'any trough']
    if s['dis']: t += ['diamond', 'filled' if s['filled'] else 'hollow']
    if s['prime']: t.append('prime dot')
    if s['dis'] and s['prime']: t.append('diamond+dot')
    z = zm[s['ti']]
    if s['bk'] == 'B' and s['ct'] < 60 and z is not None and z >= 50: t.append('zone-exit B')
    return t


def run(state, clamp, closed_only, out):
    root = STATES[state]; now = NOWS[state]
    gate = gate_fn(root)
    pool = []
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        bars = load(root, 'ETH', tf, clamp=clamp)
        sig, ct, k = signals(bars, gate)
        zm = zmin_series(ct)
        D = [b['d'] for b in bars]
        for s in sig:
            if not s['gated']: continue
            ei = s['ei']; e = bars[ei]['c']; end = D[ei] + dt.timedelta(days=60)
            if D[-1] < end: continue
            win_bars = [j for j in range(ei + 1, len(bars)) if D[j] <= end]
            if closed_only:
                last = win_bars[-1]
                close_t = dt.datetime.combine(D[last + 1] if last + 1 < len(bars) else D[last] + dt.timedelta(days=int(tf[:-1])), dt.time(), dt.timezone.utc)
                if last == len(bars) - 1 and close_t > now: continue
            ret = bars[win_bars[-1]]['c'] / e - 1
            r = dict(tf=tf, d=D[ei], tags=set(tags(s, zm)), win=ret > 0, s=s, bars=bars, ei=ei, e=e)
            # repo-style early/day10 measures on chart bars
            lo = hi_after = hi = lo_all = None; cl10 = None
            for j in win_bars:
                age = (D[j] - D[ei]).days
                if age <= 10:
                    lo = bars[j]['l'] if lo is None else min(lo, bars[j]['l'])
                    cl10 = (bars[j]['c'] / e - 1) * 100
                if age >= 10:
                    hi_after = bars[j]['h'] if hi_after is None else max(hi_after, bars[j]['h'])
                hi = bars[j]['h'] if hi is None else max(hi, bars[j]['h'])
            r.update(R_dip=None if lo is None else (lo / e - 1) * 100, R_mfe=None if hi_after is None else (hi_after / e - 1) * 100,
                     R_cl10=cl10, R_run=None if hi is None else (hi / e - 1) * 100)
            pool.append(r)
    keep = set()
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        for t in TAGS:
            sub = [r for r in pool if r['tf'] == tf and t in r['tags'] and r['d'] < dt.date(2026, 1, 1)]
            if len(sub) >= 8 and 100 * sum(r['win'] for r in sub) / len(sub) >= 70: keep.add((f'ETH {tf}', t))
    P = [r for r in pool if any((f"ETH {r['tf']}", t) in keep for t in r['tags'])]
    out['keep'] = sorted(keep); out['P'] = P
    return P


BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]


def tables(P, variant, day=None, now=None):
    pts = []
    for r in P:
        if variant == 'R':
            if r['R_dip'] is None or r['R_mfe'] is None: continue
            pts.append(dict(dip=r['R_dip'], mfe=r['R_mfe'], cl10=r['R_cl10'], run=r['R_run'], mfe10=r['R_mfe']))
        else:
            s = r['s']
            if s['d0'] is None: continue
            w = window(day, s['d0'], s['entry'], now)
            if not w: continue
            e = s['entry']
            dd = lambda b: (b['d'] - s['d0']).days
            dip = (min(b['l'] for b in w if dd(b) <= 10) / e - 1) * 100
            mfe = (max(b['h'] for b in w if dd(b) >= 10) / e - 1) * 100
            c10 = [b for b in w if dd(b) == 10]
            pts.append(dict(dip=dip, mfe=mfe, cl10=(c10[0]['c'] / e - 1) * 100, run=(max(b['h'] for b in w) / e - 1) * 100, mfe10=mfe))
    early = []
    for hi, lo, lab in BANDS:
        g = [p for p in pts if lo < p['dip'] <= hi]
        if len(g) < 5: continue
        early.append(dict(band=lab, n=len(g), r10=100 * sum(p['mfe'] >= 10 for p in g) / len(g), r20=100 * sum(p['mfe'] >= 20 for p in g) / len(g)))
    d10 = []
    for lab, f in (('green on day 10', lambda p: p['cl10'] >= 0), ('red on day 10', lambda p: p['cl10'] < 0)):
        g = [p for p in pts if p['cl10'] is not None and f(p)]
        if variant == 'R':
            d10.append(dict(check=lab, n=len(g), r10=100 * sum(p['run'] >= 10 for p in g) / len(g), r20=100 * sum(p['run'] >= 20 for p in g) / len(g),
                            r10_after10=100 * sum(p['mfe10'] >= 10 for p in g) / len(g)))
        else:
            d10.append(dict(check=lab, n=len(g), r10=100 * sum(p['mfe10'] >= 10 for p in g) / len(g), r20=100 * sum(p['mfe10'] >= 20 for p in g) / len(g),
                            r10_any=100 * sum(p['run'] >= 10 for p in g) / len(g)))
    return early, d10


if __name__ == '__main__':
    res = {}
    for state in ('REPLAY', 'CURRENT'):
        root = STATES[state]; now = NOWS[state]
        feed = json.load(open(f'{root}/feed/ctzb_feed.json'))
        of = feed['odds_fade']
        day = Daily(load(root, 'ETH', '1D'))
        o = {}
        variants = {}
        for clamp in (False, True):
            for closed in (False, True):
                P = run(state, clamp, closed, o)
                variants[('R', clamp, closed)] = tables(P, 'R')
                if not clamp and closed: keepR = o['keep']; PR = P
        variants[('D',)] = tables(PR, 'D', day, now)
        res[state] = dict(keep=keepR, variants=variants)
        print(state, 'tier', keepR)
        for k, v in variants.items():
            print(state, k, [(x['band'], x['n'], round(x['r10'], 2), round(x['r20'], 2)) for x in v[0]],
                  [(x['check'], x['n'], round(x['r10'], 2), round(x['r20'], 2), round(x.get('r10_after10', x.get('r10_any', 0)), 2)) for x in v[1]])
        # compare feed against the raw, closed-window, repo method; attribute causes from the other variants
        base = variants[('R', False, True)]
        alt = {k: v for k, v in variants.items()}
        rec(state, '4', 'feed odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70, of['posting_bar_pct'] == 70, '')
        for kind, rows, key in (('early_dip', of['early_dip'], 'band'), ('day10', of['day10'], 'check')):
            mine_rows = base[0] if kind == 'early_dip' else base[1]
            rec(state, '4', f'feed odds_fade {kind}', 'rows', len(rows), len(mine_rows), len(rows) == len(mine_rows), 'row count differs')
            for fr, mr in zip(rows, mine_rows):
                loc = f"feed odds_fade {kind} {fr[key]}"
                rec(state, '4', loc, key, fr[key], mr[key], fr[key] == mr[key], 'label differs')
                for lab, mk, nd in (('past_trades', 'n', None), ('rose10_within60d_pct', 'r10', 0), ('rose20_within60d_pct', 'r20', 0)):
                    v = mr[mk]
                    ok = (fr[lab] == v) if nd is None else num_eq(fr[lab], v, 0)
                    cause = f'{lab} differs'
                    if not ok:
                        for vk, vv in alt.items():
                            rr = (vv[0] if kind == 'early_dip' else vv[1])
                            m2 = [x for x in rr if x[key] == fr[key]]
                            if m2 and ((fr[lab] == m2[0][mk]) if nd is None else num_eq(fr[lab], m2[0][mk], 0)):
                                cause = f'matches variant {vk}'; break
                    rec(state, '4', loc, lab, fr[lab], v, ok, cause)
                edge = 'intact' if rhaz(mr['r10']) >= 70 else 'gone'
                rec(state, '4', loc, 'edge', fr['edge'], edge, fr['edge'] == edge, 'edge mark differs')
    pickle.dump(res, open(f'{S}/audit3/fade.pkl', 'wb'))
    dump('part4.csv')
    for r in ROWS:
        if r['ok'] == 'no': print(r)
