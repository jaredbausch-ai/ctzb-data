"""Everything a member sees, recomputed from the raw candles of one state (own code)."""
import csv, datetime as dt, os, json
from fractions import Fraction
from decimal import Decimal as D
from mycore import *

TAGS_R = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
EARLY_BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"),
               (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]


def rows(p):
    with open(p, newline='') as f:
        return list(csv.DictReader(f))


class State:
    def __init__(self, sdir, now):
        self.sdir, self.now = sdir, now
        self.today = now.date()
        self.gate = gate_fn(sdir)
        self.ch = {(a, tf): Chart(sdir, a, tf, self.gate) for a in ASSETS for tf in TFS}
        self.day = {a: Daily(sdir, a) for a in ASSETS}
        self.fund = {a: funding(sdir, a) for a in ASSETS}
        # every signal with its 60-day measures
        for (a, tf), c in self.ch.items():
            for s in c.sig:
                s['m'] = measures(self.day[a], s, self.today) if s['d0'] is not None else None
        self.pl = {(r['chart'], r['entry']): r for r in rows(os.path.join(sdir, 'datasets', 'ledger.csv'))}
        self.build_ledger()

    # ------------------------------------------------------------ ledger
    def build_ledger(self):
        L = []
        for a in ASSETS:
            for tf in GRADED:
                for s in self.ch[(a, tf)].sig:
                    if s['d0'] is None or s['m'] is None:
                        continue
                    if a == 'ETH' and not eth_member(*self.fund['ETH'], s['d0']):
                        continue
                    L.append(s)
        L.sort(key=lambda s: (s['d0'], s['tf']))
        for s in L:
            p = self.pl.get((s['ch'], str(s['d0'])))
            s['grade'] = p['grade'] if p else None
            s['lens'] = frozenset() if (not p or p['lenses'] == '-') else frozenset(p['lenses'].split(' + '))
        self.led = L
        # per asset / grade records (whole sample)
        self.grades = {}
        for a in ASSETS:
            for g in ('A+', 'A', 'B', 'C'):
                G = [s for s in L if s['a'] == a and s['grade'] == g]
                self.grades[(a, g)] = self.grec(G)
        G0 = [s for s in L if s['a'] == 'ETH']
        self.grades[('ETH', 'diamond or prime dot')] = self.grec([s for s in G0 if s['prime'] or s['dis']])
        self.grades[('ETH', 'no diamond or prime dot')] = self.grec([s for s in G0 if not (s['prime'] or s['dis'])])

    def grec(self, G):
        n = len(G)
        if not n:
            return dict(n=0)
        return dict(n=n, reach10=share(sum(s['m']['r10'] for s in G), n), reach20=share(sum(s['m']['r20'] for s in G), n),
                    surv10=share(sum(s['m']['surv10'] for s in G), n), touched30=share(sum(s['m']['t30'] for s in G), n),
                    medDip=disp(med([s['m']['dd'] for s in G]), 1),
                    sample=f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}")

    def day_odds(self, s):
        prior = [h for h in self.led if h['a'] == s['a'] and h['d0'] + dt.timedelta(days=60) <= s['d0']]
        G = [h for h in prior if h['grade'] == s['grade']]
        out = dict(dayN=len(G))
        if len(G) < 10 or not prior:
            for k in ('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'daySurv10', 'dayScaled20'):
                out[k] = None
            return out

        def rate(fn, ok=lambda m: True):
            P = [h for h in prior if ok(h['m'])]; Gk = [h for h in G if ok(h['m'])]
            if not P or not Gk:
                return None
            base = Fraction(sum(bool(fn(h['m'])) for h in P), len(P))
            v = 100 * (sum(bool(fn(h['m'])) for h in Gk) + 5 * base) / (len(Gk) + 5)
            return rnd(float(v), 0)
        out.update(dayReach10=rate(lambda m: m['r10']), dayReach20=rate(lambda m: m['r20']), dayReach30=rate(lambda m: m['r30']),
                   dayTouched30=rate(lambda m: m['t30']), daySurv10=rate(lambda m: m['surv10']),
                   dayScaled20=rate(lambda m: m['sc'], ok=lambda m: m['sc'] is not None))
        return out

    # ------------------------------------------------------------ card
    def sample(self, a, tf, grade, lens, known=None, example=False):
        pool = [s for s in self.led if s['a'] == a and (known is None or s['d0'] + dt.timedelta(days=60) <= known)]
        Cr = [s for s in pool if s['tf'] == tf]
        ex = [s for s in Cr if s['lens'] == lens]
        sg = [s for s in Cr if s['grade'] == grade]
        ag = [s for s in pool if s['grade'] == grade]
        gp = 'the top grade' if grade == 'A+' else 'the same grade'
        tail = ' whose 60 days had closed by then' if example else ''
        if len(ex) >= 15:
            return ex, 1, (f'all {len(ex)} {a} {tf} signals with exactly the same confirmations{tail}' if example
                           else f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations')
        if len(sg) >= 15:
            few = 'none' if not ex else f'only {len(ex)}'
            return sg, 2, (f'all {len(sg)} {a} {tf} signals of {gp}{tail} ({few} had exactly the same confirmations, too few to use)' if example
                           else f'all {len(sg)} past {a} {tf} signals of {gp} ({few} had exactly the same confirmations, too few to use)')
        return ag, 3, (f'all {len(ag)} signals of {gp} across all {a} charts{tail} ({a} {tf} alone had only {len(sg)}, too few to use)' if example
                       else f'all {len(ag)} past signals of {gp} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)')

    def ladder(self, G):
        E10 = D('1.10'); LQ = D('0.747')
        ok = liq = 0
        for s in G:
            E = s['E']
            for b in s['m']['w']:
                if b['L'] <= E * LQ: liq += 1; break
                if b['H'] >= E * E10: ok += 1; break
        n = len(G)
        fe = dict(n=n, ok=share(ok, n), liq=share(liq, n), okx=share6(ok, n))
        rowsl = []
        for th in (5, 10, 15, 20):
            hit = okk = lq = 0
            lv = 1 - D(th) / 100
            for s in G:
                E = s['E']; w = s['m']['w']
                for j, b in enumerate(w):
                    if b['L'] <= E * lv:
                        hit += 1
                        for bb in w[j:]:
                            if bb['L'] <= E * LQ: lq += 1; break
                            if bb['H'] >= E * E10: okk += 1; break
                        break
                    if b['H'] >= E * E10:
                        break
            rowsl.append(dict(fell=th, n=hit, ok=share(okk, hit), liq=share(lq, hit), okx=share6(okk, hit)))
        return fe, rowsl

    def card(self, a, tf, grade, lens, known=None, example=False):
        G, rule, text = self.sample(a, tf, grade, lens, known, example)
        n = len(G)
        c = dict(n=n, rule=rule, sample=text, G=G)
        if not n:
            return c
        M = lambda k: [s['m'][k] for s in G]
        cnt = lambda k: sum(bool(x) for x in M(k))
        sc = [x for x in M('sc') if x is not None]
        bx, dx, mx = r6(med(M('up'))), r6(med(M('ddpk'))), r6(med(M('dd')))
        old = [s for s in G if s['d0'] < SPLIT]; new = [s for s in G if s['d0'] >= SPLIT]
        t10 = [s['m']['t10'] for s in G if s['m']['t10'] is not None]
        t20 = [s['m']['t20'] for s in G if s['m']['t20'] is not None]
        fe, lad = self.ladder(G)
        c.update(surv10=share(cnt('surv10'), n), scaled20=share(sum(sc), len(sc)) if sc else None,
                 reach20=share(cnt('r20'), n), reach10=share(cnt('r10'), n), touched30=share(cnt('t30'), n),
                 bestX=bx, dipX=dx, maxX=mx, best=rnd(bx, 1), dip=rnd(dx, 1), mx=rnd(mx, 1),
                 best_full=disp(med(M('up')), 1), dip_full=disp(med(M('ddpk')), 1), mx_full=disp(med(M('dd')), 1),
                 nOld=len(old), sOld=share(sum(s['m']['surv10'] for s in old), len(old)) if old else None,
                 nNew=len(new), sNew=share(sum(s['m']['surv10'] for s in new), len(new)) if new else None,
                 d10=disp(med(t10), 0) if t10 else None, d20=disp(med(t20), 0) if t20 else None,
                 dHigh=disp(med(M('dpk')), 0), dLow=disp(med(M('ddday')), 0), fe=fe, lad=lad)
        if fe['okx'] < 70:
            c['edge'] = 0
        else:
            c['edge'] = next((-r['fell'] for r in lad if r['okx'] is not None and r['okx'] < 70), None)
        return c

    def low_day(self, a, tf, tdate):
        tfd = int(tf[:-1])
        nxt = next_open(tdate, tfd) if tfd > 1 else tdate + ONE_DAY
        day = self.day[a]
        cand = []
        d = tdate
        while d < nxt:
            if d in day.pos:
                cand.append((day.bars[day.pos[d]]['L'], d))
            d += ONE_DAY
        return min(cand)[1] if cand else tdate

    def forming(self, a, tf):
        c = self.ch[(a, tf)]
        f = c.forming()
        if not f:
            return None
        ti, need = f
        n = len(c.bars)
        conf_open = c.dates[-1]
        for _ in range(need):
            conf_open = next_open(conf_open, c.tfd)
        d0f = next_open(conf_open, c.tfd) - ONE_DAY
        prevp = [p for p in c.pivots if p < ti]
        cx, kx = c.ct[ti], c.k[ti]
        dis = False
        if prevp and kx is not None:
            dct, dk = cx - c.ct[prevp[-1]], kx - c.k[prevp[-1]]
            dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
        strong = dis and cx < 50
        prime = kx is not None and 20 <= kx < 50
        kill = None
        if need in (0, 1):
            base = [b['c'] for b in c.bars[:-1]] if need == 0 else [b['c'] for b in c.bars]
            kill = kill_close(base, cx)
        return dict(a=a, tf=tf, ti=ti, need=need, tdate=c.dates[ti], d0=d0f, bk=bucket(cx), dis=dis, strong=strong, prime=prime,
                    tags=tagtext(bucket(cx), dis, strong, prime), price=c.bars[-1]['c'], gate=self.gate(c.dates[ti]), kill=kill,
                    low_day=self.low_day(a, tf, c.dates[ti]))

    # ------------------------------------------------------------ odds fade (refresh.py's tier rule, my code)
    def tier_rows(self):
        out = []
        for tf in TFS:
            c = self.ch[('ETH', tf)]
            for s in c.sig:
                ei = s['ei']; d_open = c.dates[ei]
                end = d_open + dt.timedelta(days=60)
                if c.dates[-1] < end:
                    continue
                last = None
                j = ei + 1
                while j < len(c.bars) and c.dates[j] <= end:
                    last = c.bars[j]['c']; j += 1
                if last is None:
                    continue
                tg = {s['bk'], 'any trough'}
                if s['dis']:
                    tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
                if s['prime']:
                    tg.add('prime dot')
                if s['dis'] and s['prime']:
                    tg.add('diamond+dot')
                zm = c.zm[s['ti']]
                if s['bk'] == 'B' and s['ct'] < 60 and zm is not None and zm >= 50:
                    tg.add('zone-exit B')
                s['tg'] = tg
                out.append(dict(chart=f'ETH {tf}', tf=tf, tg=tg, d=d_open, win=last > s['e'], s=s))
        return out

    def odds_fade(self):
        R = self.tier_rows()
        upto = dt.date(self.today.year, 1, 1)
        keep = []
        for tf in TFS:
            for t in TAGS_R:
                sub = [r for r in R if r['tf'] == tf and t in r['tg'] and r['d'] + dt.timedelta(days=int(tf[:-1]) - 1 + 60) < upto]
                if len(sub) >= 8 and Fraction(sum(r['win'] for r in sub) * 100, len(sub)) >= 70:
                    keep.append((tf, t))
        # trades a year
        sel = [r for r in R if any(r['tf'] == k[0] and k[1] in r['tg'] for k in keep)]
        T = {(r['chart'], r['d']) for r in sel}
        data_end = max(self.ch[('ETH', tf)].dates[-1] for tf in TFS)
        span = max(0.25, ((data_end - dt.timedelta(days=60)) - min(d for _, d in T)).days / 365.25) if T else None
        per_year = rnd(len(T) / span, 0) if T else None
        # the fade pool: every kept ETH signal, all history, daily windows from the entry close
        pool = []
        for tf in TFS:
            c = self.ch[('ETH', tf)]
            for s in c.sig:
                if s['d0'] is None:
                    continue
                tg = s.get('tg')
                if tg is None:   # signals without a chart-bar outcome still carry tags
                    tg = {s['bk'], 'any trough'}
                    if s['dis']: tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
                    if s['prime']: tg.add('prime dot')
                    if s['dis'] and s['prime']: tg.add('diamond+dot')
                    zm = c.zm[s['ti']]
                    if s['bk'] == 'B' and s['ct'] < 60 and zm is not None and zm >= 50: tg.add('zone-exit B')
                if not any(tf == k[0] and k[1] in tg for k in keep):
                    continue
                w = self.day['ETH'].window(s['d0'], self.today)
                if w is None:
                    continue
                E = s['E']
                lo10 = min(b['L'] for b in w[:10])
                hi_after = max(b['H'] for b in w[10:])
                pool.append(dict(dip=(lo10 / E - 1) * 100, r10=hi_after >= E * D('1.10'), r20=hi_after >= E * D('1.20'),
                                 green=w[9]['C'] >= E))
        early = []
        for hi, lo, lab in EARLY_BANDS:
            g = [p for p in pool if D(lo) < p['dip'] <= D(hi)]
            if len(g) < 5:
                continue
            k10 = sum(p['r10'] for p in g); k20 = sum(p['r20'] for p in g)
            early.append(dict(band=lab, n=len(g), r10=share(k10, len(g)), r20=share(k20, len(g)),
                              edge='intact' if Fraction(100 * k10, len(g)) >= 70 else 'gone', x=100 * k10 / len(g)))
        d10 = []
        for lab, f in (('green on day 10', lambda p: p['green']), ('red on day 10', lambda p: not p['green'])):
            g = [p for p in pool if f(p)]
            if len(g) < 5:
                continue
            k10 = sum(p['r10'] for p in g); k20 = sum(p['r20'] for p in g)
            d10.append(dict(check=lab, n=len(g), r10=share(k10, len(g)), r20=share(k20, len(g)),
                            edge='intact' if Fraction(100 * k10, len(g)) >= 70 else 'gone', x=100 * k10 / len(g)))
        return dict(keep=keep, per_year=per_year, early=early, day10=d10, tier_fixed_on=str(upto), npool=len(pool))

    # ------------------------------------------------------------ misses and paths
    def misses(self, G):
        m = [s for s in G if not s['m']['r10']]
        best = [r6(s['m']['up']) for s in m]
        return dict(signals=len(G), misses=len(m), up_first=sum(b > 0 for b in best),
                    median_peak=disp(med(best), 1) if best else None,
                    mean_peak=disp(sum(best) / len(best), 1) if best else None,
                    p5=sum(b >= 5 for b in best), p10=sum(b >= 10 for b in best),
                    worst=disp(med([r6(s['m']['dd']) for s in m]), 1) if m else None,
                    d60=disp(med([r6(s['m']['ret']) for s in m]), 1) if m else None)

    def paths(self, G):
        P = []
        for s in G:
            P.append([D(0)] + [(b['C'] / s['E'] - 1) * 100 for b in s['m']['w']])

        def q(vals, f):
            v = sorted(vals); k = (len(v) - 1) * D(str(f)); lo = int(k); hi = min(lo + 1, len(v) - 1)
            return v[lo] + (v[hi] - v[lo]) * (k - lo)
        days = []
        for d in range(61):
            col = [p[d] for p in P]
            days.append(dict(day=d, q25=disp(q(col, 0.25), 1), med=disp(q(col, 0.5), 1), q75=disp(q(col, 0.75), 1)))
        return dict(n=len(P), days=days)


def kill_close(base, ct_trough):
    """the confirmation-bar close at which CT equals the trough CT (bisection on my own RSI), rounded DOWN to the cent"""
    lo, hi = base[-1] * 0.2, base[-1] * 3
    for _ in range(200):
        mid = (lo + hi) / 2
        if rsi(base + [mid])[-1] <= ct_trough:
            lo = mid
        else:
            hi = mid
    # every close above the shown price confirms: the largest cent value whose next cent up confirms
    import math
    x = math.floor(hi * 100) / 100
    # step to the exact cent boundary
    while rsi(base + [x])[-1] > ct_trough:
        x = round(x - 0.01, 2)
    while rsi(base + [round(x + 0.01, 2)])[-1] <= ct_trough:
        x = round(x + 0.01, 2)
    return dict(threshold=hi, cent=x)
