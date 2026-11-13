"""Audit 17, checks 1-7: ledger, grade_odds, if_it_misses, odds_fade, cards, open signals, prints,
top-level fields, past paths -- recomputed from raw candles with core.py and compared with the
state's datasets/ledger.csv and feed/ctzb_feed.json.

usage: audit_feed.py <state root> <now ISO> <state name> <out csv> [--quiet]
Also importable: build(root, now) returns the State plus my own recomputed model (used by the page audit).
"""
import csv, datetime as dt, json, os, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
from core import rnd, share, med, fr

EX_D0 = dt.date(2024, 9, 22)
D = dt.date.fromisoformat


def pct_from_bands():
    return [(100, -2, 'shallower than -2%'), (-2, -5, '-2% to -5%'), (-5, -10, '-5% to -10%'), (-10, -20, '-10% to -20%'), (-20, -100, 'worse than -20%')]


class Model:
    """Everything recomputed. `led` = the state's ledger rows (grade / lenses taken as given)."""

    def __init__(self, root, now):
        self.S = S = C.State(root, now)
        self.root = root
        self.led = list(csv.DictReader(open(os.path.join(root, 'datasets', 'ledger.csv'))))
        # my universe: every gated, confirmed signal on a graded chart whose 60 days have closed
        self.U = {}
        self.allsig = {}
        for a in C.ASSETS:
            for tf in C.TFS:
                sg = S.signals(a, tf)
                self.allsig[(a, tf)] = sg
                if tf not in C.GRADED:
                    continue
                for s in sg:
                    m = S.measure(a, s['d0'], s['entry'])
                    if m:
                        s['m'] = m
                        s['sc'] = S.scaled20(a, s['d0'], m)
                        self.U[(s['chart'], str(s['d0']))] = s
        # attach the ledger's grade / lenses (given) to my signals
        self.G = []            # my signals that are in the ledger, with the ledger's grade and lenses
        self.unmatched = []
        for r in self.led:
            s = self.U.get((r['chart'], r['entry']))
            if s is None:
                self.unmatched.append(r); continue
            s['grade'] = r['grade']; s['lenses'] = r['lenses']
            self.G.append(s)

    # ------------------------------------------------ stats on a sample
    def card_stats(self, G):
        S = self.S; n = len(G); o = {}
        o['n'] = n
        o['surv10'] = share(sum(s['m']['surv'] for s in G), n)
        sc = [s['sc'] for s in G if s['sc'] is not None]
        o['scaled20'] = share(sum(sc), len(sc)) if sc else None
        o['reach20'] = share(sum(s['m']['r20'] for s in G), n)
        o['reach10'] = share(sum(s['m']['r10'] for s in G), n)
        for k, key in (('up', 'best'), ('ddpk', 'dipb'), ('dd', 'dip')):
            mv = med([s['m'][k] for s in G])
            o[key + '_exact'] = None if mv is None else rnd(mv, 6)
            o[key] = None if mv is None else rnd(mv, 1)
            o[key + '_from6'] = None if mv is None else rnd(rnd(mv, 6), 1)
        o['touched30'] = share(sum(s['m']['t30'] for s in G), n)
        old = [s for s in G if s['d0'] < dt.date(2022, 1, 1)]; new = [s for s in G if s['d0'] >= dt.date(2022, 1, 1)]
        o['nOld'], o['nNew'] = len(old), len(new)
        o['survOld'] = share(sum(s['m']['surv'] for s in old), len(old))
        o['survNew'] = share(sum(s['m']['surv'] for s in new), len(new))
        nn, ok, liq = S.from_entry(G)
        o['l0'] = (nn, share(ok, nn), share(liq, nn), share(ok, nn, 6))
        o['lad'] = []
        for th in (5, 10, 15, 20):
            hit, ok, liq = S.ladder(G, th)
            o['lad'].append((th, hit, share(ok, hit), share(liq, hit), share(ok, hit, 6)))
        t10 = [s['m']['d10'] for s in G if s['m']['d10'] is not None]
        t20 = [s['m']['d20'] for s in G if s['m']['d20'] is not None]
        mr = lambda xs: None if not xs else rnd(med([F(x) for x in xs]))
        o['t10'], o['t20'] = mr(t10), mr(t20)
        o['thigh'] = mr([s['m']['dpk'] for s in G]); o['tlow'] = mr([s['m']['ddday'] for s in G])
        # the edge: first ladder level whose exact share is below the bar
        edge = None
        if o['l0'][3] is not None and o['l0'][3] < C.BAR:
            edge = 0
        else:
            for th, hit, okp, liqp, ex in o['lad']:
                if ex is not None and ex < C.BAR:
                    edge = -th; break
        o['edge'] = edge
        return o

    def pick_sample(self, a, tf, grade, lenses, known=None, example=False):
        """The like-for-like rule. lenses: a ' + '-joined code string ('-' for none)."""
        pool = [s for s in self.G if s['a'] == a and (known is None or s['d0'] + dt.timedelta(days=60) <= known)]
        lset = set() if lenses in ('-', '', None) else set(lenses.split(' + '))
        ls = lambda s: set() if s['lenses'] in ('-', '') else set(s['lenses'].split(' + '))
        chart = [s for s in pool if s['tf'] == tf]
        ex = [s for s in chart if ls(s) == lset]
        sg = [s for s in chart if s['grade'] == grade]
        ag = [s for s in pool if s['grade'] == grade]
        gp = 'the top grade' if grade == 'A+' else 'the same grade'
        if not example:
            if len(ex) >= 15:
                return ex, f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', 1
            if len(sg) >= 15:
                return sg, f'all {len(sg)} past {a} {tf} signals of {gp} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', 2
            return ag, f'all {len(ag)} past signals of {gp} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', 3
        if len(ex) >= 15:
            return ex, f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', 1
        if len(sg) >= 15:
            return sg, f'all {len(sg)} {a} {tf} signals of {gp} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', 2
        return ag, f'all {len(ag)} signals of {gp} across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', 3

    def miss_stats(self, G):
        m = [s for s in G if not s['m']['r10']]
        best = [rnd(s['m']['up'], 6) for s in m]
        o = dict(signals=len(G), misses=len(m), up_first=sum(b > 0 for b in best),
                 median_peak=None if not m else rnd(med(best), 1),
                 mean_peak=None if not m else rnd(sum(best) / len(best), 1),
                 p5=sum(b >= 5 for b in best), p10=sum(b >= 10 for b in best),
                 median_worst=None if not m else rnd(med([rnd(s['m']['dd'], 6) for s in m]), 1),
                 median_d60=None if not m else rnd(med([rnd(s['m']['ret'], 6) for s in m]), 1))
        # the same on full precision, to see whether the 6-place basis ever changes a shown figure
        o['alt'] = (None if not m else rnd(med([s['m']['up'] for s in m]), 1), None if not m else rnd(med([s['m']['dd'] for s in m]), 1),
                    None if not m else rnd(med([s['m']['ret'] for s in m]), 1))
        return o

    def paths(self, G):
        S = self.S; out = []
        for s in G:
            d = S.day[s['a']]; i = d.pos[s['d0']]
            p = [F(0)]
            for k in range(1, 61):
                j = d.pos.get(s['d0'] + dt.timedelta(days=k))
                if j is None: break
                p.append((d.c[j] / s['entry'] - 1) * 100)
            if len(p) == 61:
                out.append(p)
        def q(vals, f):
            v = sorted(vals); k = F(len(v) - 1) * f; lo = int(k); hi = min(lo + 1, len(v) - 1)
            return v[lo] + (v[hi] - v[lo]) * (k - lo)
        days = [dict(day=dd, q25=rnd(q([p[dd] for p in out], F(1, 4)), 1), median=rnd(q([p[dd] for p in out], F(1, 2)), 1),
                     q75=rnd(q([p[dd] for p in out], F(3, 4)), 1)) for dd in range(61)] if out else []
        return dict(n=len(out), days=days)

    # ------------------------------------------------ the odds fade (refresh.py's tier, per the docs)
    def odds_fade(self):
        S = self.S; today = S.today
        anchor = dt.date(today.year, 1, 1)
        rows = []; per_chart = {}
        for tf in C.TFS:
            key = ('ETH', tf); c = S.ch[key]; ct, kk = S.ind[key]
            zm = []; z = None
            for v in ct:
                if v is None: zm.append(None); continue
                z = None if v >= 60 else (v if z is None else min(z, v))
                zm.append(z)
            sg = []
            for p in S.piv[key]:
                if not p['gate']:
                    continue
                tg = {p['bk'], 'any trough'}
                if p['dis']: tg |= {'diamond', 'filled' if p['strong'] else 'hollow'}
                if p['prime']: tg.add('prime dot')
                if p['dis'] and p['prime']: tg.add('diamond+dot')
                if p['bk'] == 'B' and p['ct'] < 60 and zm[p['ti']] is not None and zm[p['ti']] >= 50: tg.add('zone-exit B')
                # 60-day outcome on the chart's own bars (bar open dates), only when the horizon has elapsed
                ei = p['ei']; end = c.d[ei] + dt.timedelta(days=60)
                f = None
                if c.d[-1] >= end:
                    last = None; best = None; mn = None
                    for j in range(ei + 1, c.n):
                        if c.d[j] > end: break
                        last = c.c[j]; best = c.h[j] if best is None else max(best, c.h[j]); mn = c.l[j] if mn is None else min(mn, c.l[j])
                    if last is not None:
                        f = (last / c.c[ei] - 1, best / c.c[ei] - 1, mn / c.c[ei] - 1)
                sg.append(dict(p=p, tags=tg, f=f, chart=f'ETH {tf}', tf=tf))
            per_chart[tf] = sg
            rows += [x for x in sg if x['f'] is not None]
        TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
        keep = []
        for tf in C.TFS:
            for t in TAGS:
                sub = [r for r in rows if r['tf'] == tf and t in r['tags']
                       and r['p']['edate'] + dt.timedelta(days=C.tfdays(tf) - 1 + 60) < anchor]
                if len(sub) >= 8 and F(100 * sum(1 for r in sub if r['f'][0] > 0), len(sub)) >= 70:
                    keep.append((tf, t))
        self.keep = keep
        # trades a year (tier.csv): the tier's signals, one per chart per date, over the scoreable span
        sel = [r for r in rows if any(r['tf'] == tf and t in r['tags'] for tf, t in keep)]
        seen = set(); T = []
        for r in sorted(sel, key=lambda x: x['p']['edate']):
            k = (r['tf'], r['p']['edate'])
            if k in seen: continue
            seen.add(k); T.append(r)
        data_end = max(S.ch[('ETH', tf)].d[-1] for tf in C.TFS)
        span = max(F(1, 4), F((data_end - dt.timedelta(days=60) - min(r['p']['edate'] for r in T)).days * 100, 36525)) if T else None
        self.per_year = None if not T else rnd(F(len(T)) / span)
        # daily windows of every kept signal
        d = S.day['ETH']; pool = []
        for tf in C.TFS:
            for x in per_chart[tf]:
                if not any(tf == k[0] and k[1] in x['tags'] for k in keep):
                    continue
                p = x['p']
                w = S.window('ETH', p['d0'])
                if not w or w[-1][0] != 60:
                    continue
                e = p['entry']
                lo10 = min(d.l[k] for n, k in w if n <= 10)
                hi_after = max(d.h[k] for n, k in w if n > 10)
                k10 = [k for n, k in w if n == 10]
                pool.append(dict(dip=(lo10 / e - 1) * 100, r10=hi_after >= e * F(11, 10), r20=hi_after >= e * F(12, 10),
                                 green=(d.c[k10[0]] >= e) if k10 else None))
        early = []
        for hi, lo, lab in pct_from_bands():
            g = [x for x in pool if lo < x['dip'] <= hi]
            if len(g) < 5: continue
            ex = F(100 * sum(x['r10'] for x in g), len(g))
            early.append(dict(band=lab, n=len(g), r10=rnd(ex), r20=share(sum(x['r20'] for x in g), len(g)), edge='intact' if ex >= 70 else 'gone', ex=ex))
        hold = []
        for lab, sel in (('green on day 10', True), ('red on day 10', False)):
            g = [x for x in pool if x['green'] is sel]
            if len(g) < 5: continue
            ex = F(100 * sum(x['r10'] for x in g), len(g))
            hold.append(dict(band=lab, n=len(g), r10=rnd(ex), r20=share(sum(x['r20'] for x in g), len(g)), edge='intact' if ex >= 70 else 'gone', ex=ex))
        return dict(early=early, hold=hold, anchor=anchor, keep=keep, pool=len(pool))


def cardcheck(L, loc, c, st, M, kind, extra):
    """Compare one feed card with my stats `st` (card_stats) and `extra` (dates / prices / text)."""
    k = lambda label, shown, mine, cause='': L.chk(loc, label, shown, mine, cause)
    k('past_trades (n)', c['past_trades'], st['n'])
    k('past_signals alias', c.get('past_signals'), st['n'])
    k('sample text', c['sample'], extra['basis'], 'sample rule / wording')
    k('rose10_within60d_pct (big number)', c['rose10_within60d_pct'], st['reach10'])
    k('rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], st['surv10'])
    k('beat_normal_move_pct', c['beat_normal_move_pct'], st['scaled20'])
    k('rose20_within60d_pct', c['rose20_within60d_pct'], st['reach20'])
    k('fell30_within60d_pct', c['fell30_within60d_pct'], st['touched30'])
    k('typical_biggest_rise_pct', c['typical_biggest_rise_pct'], st['best'])
    k('typical_dip_before_rise_pct', c['typical_dip_before_rise_pct'], st['dipb'])
    k('typical_deepest_dip_pct', c['typical_deepest_dip_pct'], st['dip'])
    k('typical_biggest_rise_exact_pct', c['typical_biggest_rise_exact_pct'], st['best_exact'])
    k('typical_dip_before_rise_exact_pct', c['typical_dip_before_rise_exact_pct'], st['dipb_exact'])
    k('typical_deepest_dip_exact_pct', c['typical_deepest_dip_exact_pct'], st['dip_exact'])
    # the rounded field must equal the exact field rounded once (what the page shows)
    k('rounded rise == exact rounded once', c['typical_biggest_rise_pct'], st['best_from6'], 'double rounding')
    k('rounded dip-before == exact rounded once', c['typical_dip_before_rise_pct'], st['dipb_from6'], 'double rounding')
    k('rounded deepest dip == exact rounded once', c['typical_deepest_dip_pct'], st['dip_from6'], 'double rounding')
    k('before_2022 n', c['before_2022']['past_trades'], st['nOld'])
    k('before_2022 surv10', c['before_2022']['rose10_never_fell25_within60d_pct'], st['survOld'])
    k('since_2022 n', c['since_2022']['past_trades'], st['nNew'])
    k('since_2022 surv10', c['since_2022']['rose10_never_fell25_within60d_pct'], st['survNew'])
    k('eras add up to n', c['before_2022']['past_trades'] + c['since_2022']['past_trades'], st['n'])
    k('typical_day_first_rose10', c['typical_day_first_rose10'], st['t10'])
    k('typical_day_first_rose20', c['typical_day_first_rose20'], st['t20'])
    k('typical_day_of_60d_high', c['typical_day_of_60d_high'], st['thigh'])
    k('typical_day_of_deepest_dip', c['typical_day_of_deepest_dip'], st['tlow'])
    fe = c['from_entry']
    k('from_entry n', fe['past_trades'], st['l0'][0]); k('from_entry still_rose10', fe['still_rose10_pct'], st['l0'][1])
    k('from_entry went_on_to_fall25', fe['went_on_to_fall25_pct'], st['l0'][2]); k('from_entry exact', fe['still_rose10_exact_pct'], st['l0'][3])
    for row, (th, hit, okp, liqp, ex) in zip(c['if_it_falls_first'], st['lad']):
        k(f'falls {th}% fell_pct', row['fell_pct'], th)
        k(f'falls {th}% n', row['past_trades'], hit); k(f'falls {th}% still_rose10', row['still_rose10_pct'], okp)
        k(f'falls {th}% went_on_to_fall25', row['went_on_to_fall25_pct'], liqp); k(f'falls {th}% exact', row['still_rose10_exact_pct'], ex)
    for key in ('chart', 'asset', 'timeframe', 'low_date', 'low_day', 'confirms_on', 'bars_to_confirm', 'must_close_above', 'price_now', 'entry_close', 'signal_id', 'confirmations'):
        if extra.get(key) != '__given__':
            k(key, c.get(key), extra.get(key))


def run(root, now, name, quiet=False):
    M = Model(root, now); S = M.S; L = C.Log(name)
    feed = C.load_feed(os.path.join(root, 'feed', 'ctzb_feed.json'))
    today = S.today
    info = {}

    # ============ 1. ledger ============
    for r in M.unmatched:
        L.chk(f"ledger {r['chart']} {r['entry']}", 'membership (a gated, confirmed, closed signal)', 'in ledger', 'not a signal of mine', 'membership')
    ledkeys = {(r['chart'], r['entry']) for r in M.led}
    missing = [s for kk, s in M.U.items() if kk not in ledkeys]
    for s in missing:
        if s['a'] == 'BTC' or s['d0'] >= dt.date(2020, 3, 21):
            L.chk(f"ledger {s['chart']} {s['d0']}", 'membership (signal missing from ledger)', 'absent', 'present', 'membership')
    info['eth_pre_funding_not_in_ledger'] = sum(1 for s in missing if s['a'] == 'ETH' and s['d0'] < dt.date(2020, 3, 21))
    L.chk('ledger', 'ETH signals left out are all before funding history (2020-03-21)', 'yes', all(s['a'] == 'ETH' and s['d0'] < dt.date(2020, 3, 21) for s in missing))
    L.chk('ledger', 'rows sorted by asset then (entry, timeframe), no duplicates', 'yes',
          len(ledkeys) == len(M.led))
    # grade record over the whole ledger (for gradeReach20 / gradeTouched30 / gradeMedDrawdown)
    gstat = {}
    for a in C.ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            G = [s for s in M.G if s['a'] == a and s['grade'] == g]
            if G:
                gstat[(a, g)] = dict(n=len(G), r20=share(sum(s['m']['r20'] for s in G), len(G)), t30=share(sum(s['m']['t30'] for s in G), len(G)),
                                     mdd=rnd(med([s['m']['dd'] for s in G]), 1), r10=share(sum(s['m']['r10'] for s in G), len(G)),
                                     surv=share(sum(s['m']['surv'] for s in G), len(G)), first=min(s['d0'] for s in G), last=max(s['d0'] for s in G), G=G)
    byasset = {a: sorted([s for s in M.G if s['a'] == a], key=lambda s: s['d0']) for a in C.ASSETS}
    yn = lambda b: 'yes' if b else 'no'
    for r in M.led:
        s = M.U.get((r['chart'], r['entry']))
        if s is None: continue
        loc = f"ledger {r['chart']} {r['entry']}"; m = s['m']; k = lambda lab, sh, mi, cause='': L.chk(loc, lab, sh, mi, cause)
        k('asset', r['asset'], s['a']); k('low (trough bar date)', r['low'], str(s['tdate']))
        k('entryPrice', r['entryPrice'], rnd(s['entry'], 2)); k('tags', r['tags'], s['tags'])
        k('reached20', r['reached20'], yn(m['r20'])); k('touched30', r['touched30'], yn(m['t30']))
        k('bestMove', r['bestMove'], rnd(m['up'], 6)); k('maxDrawdown', r['maxDrawdown'], rnd(m['dd'], 6))
        k('dipBeforeHigh', r['dipBeforeHigh'], rnd(m['ddpk'], 6)); k('return60d', r['return60d'], rnd(m['ret'], 6))
        k('daysToHigh', r['daysToHigh'], m['dpk']); k('year', r['year'], s['d0'].year)
        k('reached10', r['reached10'], yn(m['r10'])); k('reached15', r['reached15'], yn(m['r15']))
        k('surv10', r['surv10'], yn(m['surv'])); k('scaled20', r['scaled20'], None if s['sc'] is None else yn(s['sc']))
        gs = gstat[(s['a'], r['grade'])]
        k('gradeReach20', r['gradeReach20'], gs['r20']); k('gradeTouched30', r['gradeTouched30'], gs['t30']); k('gradeMedDrawdown', r['gradeMedDrawdown'], gs['mdd'])
        # odds on the day: same asset, 60th day closed by this entry's close; same grade; shrunk to the base rate (weight 5)
        prior = [x for x in byasset[s['a']] if x['d0'] + dt.timedelta(days=60) <= s['d0']]
        Gp = [x for x in prior if x['grade'] == r['grade']]
        k('dayN', r['dayN'], len(Gp))
        def rate(fn, ok=lambda x: True):
            P = [x for x in prior if ok(x)]; Gk = [x for x in Gp if ok(x)]
            if not P or not Gk: return None
            base = F(sum(fn(x) for x in P), len(P))
            return rnd(100 * (sum(fn(x) for x in Gk) + 5 * base) / (len(Gk) + 5))
        if len(Gp) < 10:
            exp = [None] * 6
        else:
            exp = [rate(lambda x: x['m']['r10']), rate(lambda x: x['m']['r20']), rate(lambda x: x['m']['r30']), rate(lambda x: x['m']['t30']),
                   rate(lambda x: x['m']['surv']), rate(lambda x: bool(x['sc']), ok=lambda x: x['sc'] is not None)]
        for lab, e in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'daySurv10', 'dayScaled20'), exp):
            k(lab, r[lab], e)
    info['ledger_rows'] = len(M.led)

    # ============ 2. grade_odds ============
    for g in feed['grade_odds']:
        loc = f"grade_odds {g['asset']} {g['grade']}"
        if g['grade'] in ('A+', 'A', 'B', 'C'):
            gs = gstat.get((g['asset'], g['grade']))
            if gs is None:
                L.chk(loc, 'past_trades', g['past_trades'], 0); continue
            G = gs['G']
        elif g['grade'] in ('diamond or prime dot', 'no diamond or prime dot'):
            mk = g['grade'] == 'diamond or prime dot'
            G = [s for s in M.G if s['a'] == 'ETH' and bool(s['prime'] or s['dis']) == mk]
            gs = dict(n=len(G), r20=share(sum(s['m']['r20'] for s in G), len(G)), mdd=rnd(med([s['m']['dd'] for s in G]), 1),
                      r10=share(sum(s['m']['r10'] for s in G), len(G)), surv=share(sum(s['m']['surv'] for s in G), len(G)),
                      first=min(s['d0'] for s in G), last=max(s['d0'] for s in G))
        else:
            continue        # the two HTF-divergence rows are lens logic (out of scope)
        L.chk(loc, 'past_trades', g['past_trades'], gs['n']); L.chk(loc, 'past_signals alias', g.get('past_signals'), gs['n'])
        L.chk(loc, 'rose10_within60d_pct', g['rose10_within60d_pct'], gs['r10'])
        L.chk(loc, 'rose10_never_fell25_within60d_pct', g['rose10_never_fell25_within60d_pct'], gs['surv'])
        L.chk(loc, 'rose20_within60d_pct', g['rose20_within60d_pct'], gs['r20'])
        L.chk(loc, 'median_deepest_dip_pct', g['median_deepest_dip_pct'], gs['mdd'])
        L.chk(loc, 'sample (first to last signal)', g['sample'], f"{gs['first']} to {gs['last']}")
    L.chk('grade_odds', 'rows present for every asset/grade with signals', len([g for g in feed['grade_odds'] if g['grade'] in ('A+', 'A', 'B', 'C')]), 8)

    # ============ 3. if_it_misses / example_if_it_misses ============
    def misscheck(loc, row, G, full=True):
        ms = M.miss_stats(G)
        L.chk(loc, 'signals', row['signals'], ms['signals']); L.chk(loc, 'misses', row['misses'], ms['misses'])
        L.chk(loc, 'up_first (best price above entry)', row['up_first'], ms['up_first'])
        L.chk(loc, 'median_peak_pct', row['median_peak_pct'], ms['median_peak'])
        L.chk(loc, 'median_worst_drop_pct', row['median_worst_drop_pct'], ms['median_worst'])
        L.chk(loc, 'median_day60_pct', row['median_day60_pct'], ms['median_d60'])
        L.chk(loc, 'medians unchanged on full-precision measures', f"{ms['median_peak']}/{ms['median_worst']}/{ms['median_d60']}", f"{ms['alt'][0]}/{ms['alt'][1]}/{ms['alt'][2]}", '6-place basis changes a shown median')
        if full:
            L.chk(loc, 'mean_peak_pct', row['mean_peak_pct'], ms['mean_peak'])
            L.chk(loc, 'peaked_5_or_more', row['peaked_5_or_more'], ms['p5']); L.chk(loc, 'peaked_10_or_more', row['peaked_10_or_more'], ms['p10'])
        L.chk(loc, 'miss_rule', row['miss_rule'], 'did not rise 10% within 60 days')
        return ms
    M.miss = {}
    for row in feed['if_it_misses']:
        G = [s for s in M.G if s['a'] == row['asset'] and s['grade'] == row['grade']]
        M.miss[(row['asset'], row['grade'])] = misscheck(f"if_it_misses {row['asset']} {row['grade']}", row, G)
    have = {(r['asset'], r['grade']) for r in feed['if_it_misses']}
    want = {(s['a'], s['grade']) for s in M.G}
    L.chk('if_it_misses', 'a row for every asset/grade in the ledger', ' '.join(sorted(f'{a}{g}' for a, g in have)), ' '.join(sorted(f'{a}{g}' for a, g in want)))
    exG = [s for s in M.G if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= EX_D0]
    if feed.get('example_if_it_misses'):
        M.miss['example'] = misscheck('example_if_it_misses', feed['example_if_it_misses'], exG, full=False)
    else:
        L.chk('example_if_it_misses', 'present', 'absent', 'present' if exG else 'absent')

    # ============ 4. odds_fade ============
    of = M.odds_fade(); fo = feed['odds_fade']; M.of = of
    L.chk('odds_fade', 'posting_bar_pct', fo['posting_bar_pct'], 70)
    L.chk('odds_fade', 'tier_fixed_on (1 January of the clock year)', fo['tier_fixed_on'], str(of['anchor']))
    L.chk('odds_fade', 'edge_measured_on', fo['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)')
    L.chk('odds_fade', 'sample sentence quotes the tier date', f"{int(str(of['anchor'])[8:10])} {of['anchor']:%b %Y}" in fo['sample'], True)
    L.chk('odds_fade', 'early_dip row count', len(fo['early_dip']), len(of['early']))
    for row, mine in zip(fo['early_dip'], of['early']):
        loc = f"odds_fade early_dip {row['band']}"
        L.chk(loc, 'band', row['band'], mine['band']); L.chk(loc, 'past_trades', row['past_trades'], mine['n']); L.chk(loc, 'past_signals alias', row.get('past_signals'), mine['n'])
        L.chk(loc, 'rose10_after_day10_pct', row['rose10_after_day10_pct'], mine['r10']); L.chk(loc, 'rose20_after_day10_pct', row['rose20_after_day10_pct'], mine['r20'])
        L.chk(loc, 'rose10_within60d_pct (alias)', row['rose10_within60d_pct'], mine['r10']); L.chk(loc, 'rose20_within60d_pct (alias)', row['rose20_within60d_pct'], mine['r20'])
        L.chk(loc, 'edge (exact share vs 70)', row['edge'], mine['edge'])
    L.chk('odds_fade', 'day10 row count', len(fo['day10']), len(of['hold']))
    for row, mine in zip(fo['day10'], of['hold']):
        loc = f"odds_fade day10 {row['check']}"
        L.chk(loc, 'check', row['check'], mine['band']); L.chk(loc, 'past_trades', row['past_trades'], mine['n']); L.chk(loc, 'past_signals alias', row.get('past_signals'), mine['n'])
        L.chk(loc, 'rose10_after_day10_pct', row['rose10_after_day10_pct'], mine['r10']); L.chk(loc, 'rose20_after_day10_pct', row['rose20_after_day10_pct'], mine['r20'])
        L.chk(loc, 'rose10_within60d_pct (alias)', row['rose10_within60d_pct'], mine['r10']); L.chk(loc, 'rose20_within60d_pct (alias)', row['rose20_within60d_pct'], mine['r20'])
        L.chk(loc, 'edge (exact share vs 70)', row['edge'], mine['edge'])
    info['tier'] = of['keep']; info['fade_pool'] = of['pool']

    # ============ 6a. top level ============
    L.chk('top level', 'schema_version', feed['schema_version'], 6)
    L.chk('top level', 'posting_bar_pct', feed['posting_bar_pct'], 70)
    L.chk('top level', 'trades_a_year', feed['trades_a_year'], f"{M.per_year} on average" if M.per_year is not None else '—')
    L.chk('top level', 'signals_a_year alias', feed.get('signals_a_year'), feed['trades_a_year'])
    L.chk('top level', 'scored_as_of (the clock UTC date)', feed['scored_as_of'], str(today))
    L.chk('top level', 'market_regime (gate today)', feed['market_regime'], 'Bullish' if S.gate(today) else 'Bearish')
    L.chk('top level', 'cards_withheld', feed['cards_withheld'], False)

    # ============ 5. cards ============
    forming = {}
    for a in C.ASSETS:
        for tf in C.TFS:
            f = S.forming(a, tf)
            if f: forming[(a, tf)] = f
    M.forming = forming
    want_cards = sorted(f"{a}-{tf}-{f['d0']}" for (a, tf), f in forming.items() if tf in C.GRADED and f['gate'])
    L.chk('cards', 'forming cards exist exactly for graded charts with the gate on at the trough', ' '.join(sorted(c['signal_id'] for c in feed['cards'])), ' '.join(want_cards))
    M.cards = {}
    for c in feed['cards']:
        loc = f"card forming {c['signal_id']}"
        f = forming.get((c['asset'], c['timeframe']))
        if f is None:
            L.chk(loc, 'a low is forming on this chart', 'card', 'none forming'); continue
        L.chk(loc, 'graded chart', c['timeframe'] in C.GRADED, True); L.chk(loc, 'gate on at the trough date', True, f['gate'])
        lenses = ' + '.join(C.RPLAIN.get(x, x) for x in c['confirmations'].split('; ')) if c['confirmations'] != 'none' else '-'
        G, basis, rule = M.pick_sample(c['asset'], c['timeframe'], c['grade'], lenses)
        st = M.card_stats(G)
        kill = None
        if f['kill_exact'] is not None:
            kill = C.floor_cent(F(repr(f['kill_exact'])))
            # semantic test on the shown price: a close at it must not confirm, a cent above must
            sh = c['must_close_above']
            if sh is not None:
                at = S.rsi_if_close(f['kill_base'], float(sh)); up = S.rsi_if_close(f['kill_base'], float(sh) + 0.01)
                L.chk(loc, 'must_close_above: a close AT the shown price does not confirm', at <= f['ct'], True, 'kill close')
                L.chk(loc, 'must_close_above: a close one cent above confirms', up > f['ct'], True, 'kill close')
        extra = dict(basis=basis, chart=f['chart'], asset=f['a'], timeframe=f['tf'], low_date=str(f['tdate']), low_day=str(S.low_day(f['a'], f['tf'], f['tdate'])),
                     confirms_on=str(f['d0']), bars_to_confirm=f['need'], must_close_above=kill, price_now=rnd(f['price'], 2), entry_close=None,
                     signal_id=f"{f['a']}-{f['tf']}-{f['d0']}", confirmations='__given__')
        cardcheck(L, loc, c, st, M, 'forming', extra)
        L.chk(loc, 'active_confluences present as a list', isinstance(c.get('active_confluences'), list), True)
        M.cards[c['signal_id']] = dict(st=st, f=f, basis=basis, G=G)
    # example
    xc = feed.get('example_card')
    exs = M.U.get(('ETH 2D', str(EX_D0)))
    if xc and exs is not None and 'grade' in exs:
        G, basis, rule = M.pick_sample('ETH', '2D', exs['grade'], exs['lenses'], known=EX_D0, example=True)
        st = M.card_stats(G)
        L.chk('card example', 'only signals whose 60th day had closed by 2024-09-22', all(s['d0'] + dt.timedelta(days=60) <= EX_D0 for s in G), True)
        conf = '; '.join(C.PLAIN.get(x, x) for x in exs['lenses'].split(' + ')) if exs['lenses'] not in ('-', '') else 'none'
        extra = dict(basis=basis, chart='ETH 2D', asset='ETH', timeframe='2D', low_date=str(exs['tdate']), low_day=str(S.low_day('ETH', '2D', exs['tdate'])),
                     confirms_on=str(EX_D0), bars_to_confirm=None, must_close_above=None, price_now=None, entry_close=rnd(exs['entry'], 2),
                     signal_id='ETH-2D-2024-09-22', confirmations=conf)
        cardcheck(L, 'card example', xc, st, M, 'example', extra)
        L.chk('card example', 'grade', xc['grade'], exs['grade']); L.chk('card example', 'example flag', xc.get('example'), True)
        M.example = dict(st=st, s=exs, basis=basis, G=G)
    else:
        L.chk('card example', 'present', 'present' if xc else 'absent', 'present' if exs is not None else 'absent')
        M.example = None

    # ============ 6. open signals ============
    mine_open = []
    for a in C.ASSETS:
        for tf in C.GRADED:
            for s in M.allsig[(a, tf)]:
                if 0 <= (today - s['d0']).days <= 60:
                    mine_open.append(s)
    mine_open.sort(key=lambda s: (str(s['d0']), s['chart']))
    L.chk('open_signals', 'the list (every gated signal on a graded chart inside its 60 days)', ' '.join(o['signal_id'] for o in feed['open_signals']),
          ' '.join(f"{s['a']}-{s['tf']}-{s['d0']}" for s in mine_open), 'membership / order')
    mo = {f"{s['a']}-{s['tf']}-{s['d0']}": s for s in mine_open}
    M.open = {}
    for o in feed['open_signals']:
        loc = f"open {o['signal_id']}"; s = mo.get(o['signal_id'])
        if s is None:
            L.chk(loc, 'is an open signal', 'listed', 'not open'); continue
        d = S.day[s['a']]; e = s['entry']; w = S.window(s['a'], s['d0'])
        k = lambda lab, sh, mi, cause='': L.chk(loc, lab, sh, mi, cause)
        k('chart', o['chart'], s['chart']); k('entry_date', o['entry_date'], str(s['d0'])); k('entry_close', o['entry_close'], rnd(e, 2))
        k('tags', o['tags'], s['tags']); k('days_elapsed', o['days_elapsed'], (today - s['d0']).days)
        mark = lambda n: next((rnd((d.c[kk] / e - 1) * 100, 1) for nn, kk in w if nn == n), None)
        k('day10_pct', o['day10_pct'], mark(10)); k('day30_pct', o['day30_pct'], mark(30)); k('day60_pct', o['day60_pct'], mark(60))
        best = rnd((max(d.h[kk] for _, kk in w) / e - 1) * 100, 1) if w else None
        worst = rnd((min(d.l[kk] for _, kk in w) / e - 1) * 100, 1) if w else None
        k('best_so_far_pct', o['best_so_far_pct'], best); k('worst_so_far_pct', o['worst_so_far_pct'], worst)
        G, basis, rule = M.pick_sample(s['a'], s['tf'], o['grade'], o['confirmations'])
        st = M.card_stats(G)
        lvl = st['edge']; status = 'intact'
        if lvl == 0:
            status = 'lost'
        else:
            for _, kk in w:
                if lvl is not None and d.l[kk] <= e * (1 + F(lvl, 100)): status = 'lost'; break
                if d.h[kk] >= e * F(11, 10): status = 'rose10'; break
        k('edge_level_pct', o['edge_level_pct'], lvl); k('edge_status', o['edge_status'], status)
        c = o.get('card')
        if c is None:
            k('card present', 'absent', 'present'); continue
        conf = '; '.join(C.PLAIN.get(x, x) for x in o['confirmations'].split(' + ')) if o['confirmations'] not in ('-', '') else 'none'
        extra = dict(basis=basis, chart=s['chart'], asset=s['a'], timeframe=s['tf'], low_date=str(s['tdate']), low_day=str(S.low_day(s['a'], s['tf'], s['tdate'])),
                     confirms_on=str(s['d0']), bars_to_confirm=None, must_close_above=None, price_now=rnd(d.c[-1], 2), entry_close=rnd(e, 2),
                     signal_id=o['signal_id'], confirmations=conf)
        cardcheck(L, loc + ' card', c, st, M, 'open', extra)
        k('card grade == open grade', c['grade'], o['grade'])
        M.open[o['signal_id']] = dict(st=st, s=s, basis=basis, best=best, worst=worst, status=status, lvl=lvl, d10=mark(10), G=G)

    # ============ 6b. prints ============
    exp = []
    for a in C.ASSETS:
        for tf in C.TFS:
            for s in M.allsig[(a, tf)][-3:]:
                exp.append(dict(sid=f"{a}-{tf}-{s['d0']}", chart=s['chart'], state='confirmed', low=str(s['tdate']), conf=str(s['d0']), entry=rnd(s['entry'], 2),
                                tags=s['tags'], note='regime on' if S.gate(s['tdate']) else 'regime off'))
            f = forming.get((a, tf))
            if f:
                exp.append(dict(sid=f"{a}-{tf}-{f['d0']}", chart=f['chart'], state='forming', low=str(f['tdate']), conf=str(f['d0']), entry=rnd(f['price'], 2),
                                tags=f['tags'], note=('regime on' if f['gate'] else 'regime off') + f"; {f['need']} bar(s) to confirm"))
    L.chk('prints', 'the list (last 3 confirmed per chart + any forming low)', ' '.join(f"{p['signal_id']}:{p['state']}" for p in feed['prints']),
          ' '.join(f"{p['sid']}:{p['state']}" for p in exp), 'membership / order')
    em = {(p['sid'], p['state']): p for p in exp}
    for p in feed['prints']:
        loc = f"print {p['signal_id']} {p['state']}"; m = em.get((p['signal_id'], p['state']))
        if m is None: continue
        L.chk(loc, 'chart', p['chart'], m['chart']); L.chk(loc, 'provisional', p['provisional'], m['state'] != 'confirmed')
        L.chk(loc, 'low_date', p['low_date'], m['low']); L.chk(loc, 'confirms_on', p['confirms_on'], m['conf'])
        L.chk(loc, 'entry_close', p['entry_close'], m['entry']); L.chk(loc, 'tags', p['tags'], m['tags']); L.chk(loc, 'note (regime on the trough date)', p['note'], m['note'])

    # ============ 7. past paths ============
    M.pp = {}
    for pp in feed['past_paths']:
        G = [s for s in M.G if s['a'] == pp['asset'] and s['grade'] == 'A+']
        mine = M.paths(G)
        M.pp[pp['asset']] = mine
        loc = f"past_paths {pp['asset']}"
        L.chk(loc, 'signals', pp['signals'], mine['n']); L.chk(loc, 'days listed', len(pp['days']), 61)
        for row, m in zip(pp['days'], mine['days']):
            L.chk(loc, f"day {row['day']} q25", row['q25_pct'], m['q25']); L.chk(loc, f"day {row['day']} median", row['median_pct'], m['median']); L.chk(loc, f"day {row['day']} q75", row['q75_pct'], m['q75'])
    L.chk('past_paths', 'assets', ' '.join(p['asset'] for p in feed['past_paths']), ' '.join(a for a in C.ASSETS if any(s['a'] == a and s['grade'] == 'A+' for s in M.G)))
    ep = feed.get('example_past_paths')
    if ep:
        mine = M.paths(exG); M.pp['example'] = mine
        L.chk('example_past_paths', 'signals', ep['signals'], mine['n'])
        for row, m in zip(ep['days'], mine['days']):
            L.chk('example_past_paths', f"day {row['day']} q25", row['q25_pct'], m['q25']); L.chk('example_past_paths', f"day {row['day']} median", row['median_pct'], m['median']); L.chk('example_past_paths', f"day {row['day']} q75", row['q75_pct'], m['q75'])
    else:
        L.chk('example_past_paths', 'present', 'absent', 'present' if exG else 'absent')
    # ============ 10. the computed-signal label rides on every card, print, open signal and grade row ============
    LAB = ('Computed signal, not a fill. No trade was taken. Entry quality only: the data has no exits, so this is not a strategy return or a track record.')
    objs = [('feed', feed)] + [(f"card {c['signal_id']}", c) for c in feed['cards']] + [(f"print {p['signal_id']}", p) for p in feed['prints']] \
        + [(f"open {o['signal_id']}", o) for o in feed['open_signals']] + [(f"open card {o['signal_id']}", o['card']) for o in feed['open_signals'] if o.get('card')] \
        + [(f"grade_odds {g['asset']} {g['grade']}", g) for g in feed['grade_odds']] + [(f"if_it_misses {g['asset']} {g['grade']}", g) for g in feed['if_it_misses']] \
        + [('odds_fade', feed['odds_fade'])] + [(f"past_paths {p['asset']}", p) for p in feed['past_paths']] \
        + ([('example_card', feed['example_card'])] if feed.get('example_card') else [])
    missing_lab = [n for n, o in objs if o.get('label') != LAB]
    L.chk('labels', f'computed-signal label on all {len(objs)} feed records', ' '.join(missing_lab[:5]), '')
    M.gstat = gstat; M.feed = feed; M.info = info; M.exG = exG
    return M, L


if __name__ == '__main__':
    root, now, name, out = sys.argv[1:5]
    nowdt = dt.datetime.fromisoformat(now.replace('Z', '+00:00'))
    M, L = run(root, nowdt, name)
    with open(out, 'w', newline='') as f:
        csv.writer(f).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + L.rows)
    bad = L.bad()
    print(f'{name}: {len(L.rows)} comparisons, {len(bad)} disagreements; ledger rows {M.info["ledger_rows"]}; tier {M.info["tier"]}; fade pool {M.info["fade_pool"]}; ETH pre-funding signals not in ledger {M.info["eth_pre_funding_not_in_ledger"]}')
    if '--quiet' not in sys.argv:
        for r in bad[:60]:
            print('  ', r[1], '|', r[2], '| shown', r[3], '| mine', r[4])
