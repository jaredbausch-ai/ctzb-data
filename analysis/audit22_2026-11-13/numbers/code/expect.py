"""Expected values for every feed / ledger field, from mine.State plus each ledger row's GIVEN grade and lenses
(grades and lens logic are out of scope). Entry quality only."""
import datetime as dt, statistics as st
from mine import rnd, median, quant, px_at, floor_cent, tags_of, GRADED, TFS, SPLIT, EX_D0, ONE

PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before',
         'FUND': 'funding at or above its 90-day median', 'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising',
         'FASTCT': 'CT recovering fast from the low'}
RPLAIN = {v: k for k, v in PLAIN.items()}
TIER_TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]


def gof(n):
    return 'C' if n <= 1 else 'B' if n == 2 else 'A' if n == 3 else 'A+'


def gp(g):
    return 'the top grade' if g == 'A+' else 'the same grade'


def lens_set_from_ledger(s):
    return frozenset() if s in ('-', '') else frozenset(x.strip() for x in s.split(' + '))


def lens_set_from_plain(s):
    if s in ('none', '', None):
        return frozenset()
    return frozenset(RPLAIN.get(x.strip(), '?' + x.strip()) for x in s.split('; '))


class Expect:
    def __init__(self, S, ledger):
        self.S = S
        self.ledger = ledger
        self.lkey = {(r['chart'], r['entry']): r for r in ledger}
        # my signals with closed 60-day windows on graded charts
        self.cands = []
        for (a, tf), lst in S.sig.items():
            if tf not in GRADED:
                continue
            for s in lst:
                m = S.measure(a, s['d0'], S.daily_close(a, s['d0']))
                if m is None:
                    continue
                s = dict(s, m=m, c0=S.daily_close(a, s['d0']))
                self.cands.append(s)
        self.cands.sort(key=lambda s: (s['d0'], s['tf']))
        eth_led = [r for r in ledger if r['asset'] == 'ETH']
        self.eth_start = min(dt.date.fromisoformat(r['entry']) for r in eth_led) if eth_led else None
        self.rows = []          # my rows that the ledger also holds (grade / lenses given)
        self.missing = []       # my candidates absent from the ledger
        for s in self.cands:
            k = (f"{s['a']} {s['tf']}", str(s['d0']))
            r = self.lkey.get(k)
            if r is None:
                self.missing.append(s); continue
            self.rows.append(dict(s, grade=r['grade'], lens=lens_set_from_ledger(r['lenses'])))
        mine_keys = {(f"{s['a']} {s['tf']}", str(s['d0'])) for s in self.cands}
        self.extra = [r for r in ledger if (r['chart'], r['entry']) not in mine_keys]

    # ---------------------------------------------------------- ledger
    def ledger_row(self, s):
        m = s['m']; S = self.S
        sc = S.scaled20(s['a'], s['d0'], m)
        return dict(asset=s['a'], chart=f"{s['a']} {s['tf']}", low=str(s['tdate']), entry=str(s['d0']),
                    entryPrice=rnd(s['c0'], 2), tags=tags_of(s),
                    reached20='yes' if m['r20'] else 'no', touched30='yes' if m['t30'] else 'no',
                    bestMove=rnd(m['up'], 6), maxDrawdown=rnd(m['dd'], 6), dipBeforeHigh=rnd(m['ddpk'], 6),
                    return60d=rnd(m['ret'], 6), daysToHigh=m['dpk'], year=s['d0'].year,
                    reached10='yes' if m['r10'] else 'no', reached15='yes' if m['r15'] else 'no',
                    surv10='yes' if m['surv10'] else 'no', scaled20='' if sc is None else 'yes' if sc else 'no')

    def grade_record(self, a, g):
        G = [s for s in self.rows if s['a'] == a and s['grade'] == g]
        if not G:
            return None
        n = len(G)
        return dict(n=n, reach20=rnd(100 * sum(s['m']['r20'] for s in G) / n), touched30=rnd(100 * sum(s['m']['t30'] for s in G) / n),
                    medDip=rnd(median([s['m']['dd'] for s in G]), 1), reach10=rnd(100 * sum(s['m']['r10'] for s in G) / n),
                    surv10=rnd(100 * sum(s['m']['surv10'] for s in G) / n),
                    sample=f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}")

    def marker_record(self, want):
        G = [s for s in self.rows if s['a'] == 'ETH' and bool(s['prime'] or s['dis']) == want]
        n = len(G)
        if not n:
            return None
        return dict(n=n, reach20=rnd(100 * sum(s['m']['r20'] for s in G) / n), touched30=rnd(100 * sum(s['m']['t30'] for s in G) / n),
                    medDip=rnd(median([s['m']['dd'] for s in G]), 1), reach10=rnd(100 * sum(s['m']['r10'] for s in G) / n),
                    surv10=rnd(100 * sum(s['m']['surv10'] for s in G) / n),
                    sample=f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}")

    def day_odds(self, s):
        prior = [h for h in self.rows if h['a'] == s['a'] and h['d0'] + dt.timedelta(days=60) <= s['d0']]
        G = [h for h in prior if h['grade'] == s['grade']]
        out = dict(dayN=len(G))
        keys = ('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'daySurv10', 'dayScaled20')
        if len(G) < 10 or not prior:
            out.update({k: '' for k in keys}); return out
        def rate(fn, ok=lambda h: True):
            P = [h for h in prior if ok(h)]; Gk = [h for h in G if ok(h)]
            if not P or not Gk:
                return ''
            base = sum(fn(h) for h in P) / len(P)
            return rnd(100 * (sum(fn(h) for h in Gk) + 5 * base) / (len(Gk) + 5))
        sc = lambda h: self.S.scaled20(h['a'], h['d0'], h['m'])
        out.update(dayReach10=rate(lambda h: h['m']['r10']), dayReach20=rate(lambda h: h['m']['r20']),
                   dayReach30=rate(lambda h: h['m']['r30']), dayTouched30=rate(lambda h: h['m']['t30']),
                   daySurv10=rate(lambda h: h['m']['surv10']), dayScaled20=rate(lambda h: bool(sc(h)), ok=lambda h: sc(h) is not None))
        return out

    # ---------------------------------------------------------- misses and paths
    def misses(self, G):
        r6 = lambda x: rnd(x, 6)
        M = [s for s in G if not s['m']['r10']]
        best = [r6(s['m']['up']) for s in M]
        med1 = lambda xs: rnd(median(xs), 1) if xs else None
        return dict(signals=len(G), misses=len(M), up_first=sum(b > 0 for b in best), median_peak_pct=med1(best),
                    mean_peak_pct=rnd(sum(best) / len(best), 1) if best else None,
                    peaked_5_or_more=sum(b >= 5 for b in best), peaked_10_or_more=sum(b >= 10 for b in best),
                    median_worst_drop_pct=med1([r6(s['m']['dd']) for s in M]), median_day60_pct=med1([r6(s['m']['ret']) for s in M]))

    def paths(self, G):
        S = self.S
        P = []
        for s in G:
            d = S.daily[s['a']]; i0 = d['pos'][s['d0']]
            ep = rnd(s['c0'], 2)
            p = [0.0]
            ok = True
            for k in range(1, 61):
                j = d['pos'].get(s['d0'] + dt.timedelta(days=k))
                if j is None or d['date'][j] >= S.today:
                    ok = False; break
                p.append((d['c'][j] / ep - 1) * 100)
            if ok:
                P.append(p)
        days = []
        for k in range(61):
            v = [p[k] for p in P]
            days.append(dict(day=k, q25_pct=rnd(quant(v, .25), 1), median_pct=rnd(quant(v, .5), 1), q75_pct=rnd(quant(v, .75), 1)))
        return dict(signals=len(P), days=days)

    # ---------------------------------------------------------- the card
    def card_figures(self, G):
        S = self.S
        n = len(G)
        pct = lambda k: rnd(100 * k / n) if n else None
        sc = [x for x in (S.scaled20(s['a'], s['d0'], s['m']) for s in G) if x is not None]
        old = [s for s in G if s['d0'] < SPLIT]; new = [s for s in G if s['d0'] >= SPLIT]
        sv = lambda X: rnd(100 * sum(s['m']['surv10'] for s in X) / len(X)) if X else None
        f = dict(past_trades=n, rose10_never_fell25_within60d_pct=pct(sum(s['m']['surv10'] for s in G)),
                 beat_normal_move_pct=rnd(100 * sum(sc) / len(sc)) if sc else None,
                 rose20_within60d_pct=pct(sum(s['m']['r20'] for s in G)), rose10_within60d_pct=pct(sum(s['m']['r10'] for s in G)),
                 fell30_within60d_pct=pct(sum(s['m']['t30'] for s in G)))
        for key, fld in (('up', 'typical_biggest_rise'), ('ddpk', 'typical_dip_before_rise'), ('dd', 'typical_deepest_dip')):
            md = median([s['m'][key] for s in G])
            f[fld + '_pct'] = rnd(md, 1)
            f[fld + '_exact_pct'] = rnd(md, 6)
            f[fld + '_shown'] = rnd(rnd(md, 6), 1)    # what the page shows: the stored exact, rounded once
        f['before_2022'] = dict(past_trades=len(old), rose10_never_fell25_within60d_pct=sv(old))
        f['since_2022'] = dict(past_trades=len(new), rose10_never_fell25_within60d_pct=sv(new))
        t10 = [s['m']['t10'] for s in G if s['m']['t10'] is not None]
        t20 = [s['m']['t20'] for s in G if s['m']['t20'] is not None]
        f['typical_day_first_rose10'] = rnd(median(t10)) if t10 else None
        f['typical_day_first_rose20'] = rnd(median(t20)) if t20 else None
        f['typical_day_of_60d_high'] = rnd(median([s['m']['dpk'] for s in G]))
        f['typical_day_of_deepest_dip'] = rnd(median([s['m']['ddday'] for s in G]))
        res = [S.ladder_one(s['a'], s['d0'], s['c0'], 0) for s in G]
        ok, liq = sum(r == 'ok' for r in res), sum(r == 'liq' for r in res)
        f['from_entry'] = dict(past_trades=n, still_rose10_pct=pct(ok), went_on_to_fall25_pct=pct(liq),
                               still_rose10_exact_pct=rnd(100 * ok / n, 6) if n else None)
        lad = []
        for th in (5, 10, 15, 20):
            res = [S.ladder_one(s['a'], s['d0'], s['c0'], th) for s in G]
            hit = sum(r is not None for r in res); ok = sum(r == 'ok' for r in res); liq = sum(r == 'liq' for r in res)
            lad.append(dict(fell_pct=th, past_trades=hit, still_rose10_pct=rnd(100 * ok / hit) if hit else None,
                            went_on_to_fall25_pct=rnd(100 * liq / hit) if hit else None,
                            still_rose10_exact_pct=rnd(100 * ok / hit, 6) if hit else None))
        f['if_it_falls_first'] = lad
        # edge level on the exact shares
        fe = f['from_entry']['still_rose10_exact_pct']
        if fe is not None and fe < 70:
            f['_edge'] = 0
        else:
            f['_edge'] = next((-r['fell_pct'] for r in lad if r['still_rose10_exact_pct'] is not None and r['still_rose10_exact_pct'] < 70), None)
        return f

    def sample(self, a, tf, grade, lens, known, example=False):
        Cr = [s for s in known if s['a'] == a and s['tf'] == tf]
        ex = [s for s in Cr if s['lens'] == lens]
        sg = [s for s in Cr if s['grade'] == grade]
        ag = [s for s in known if s['a'] == a and s['tf'] in GRADED and s['grade'] == grade]
        if not example:
            if len(ex) >= 15:
                return f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex, 1
            if len(sg) >= 15:
                return f'all {len(sg)} past {a} {tf} signals of {gp(grade)} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg, 2
            return f'all {len(ag)} past signals of {gp(grade)} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag, 3
        if len(ex) >= 15:
            return f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', ex, 1
        if len(sg) >= 15:
            return f'all {len(sg)} {a} {tf} signals of {gp(grade)} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg, 2
        return f'all {len(ag)} signals of {gp(grade)} across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', ag, 3

    # ---------------------------------------------------------- walk-forward tier (refresh.py's original rule, own bars)
    def tier_rows(self):
        S = self.S
        out = []
        for tf in TFS:
            B = S.bars[('ETH', tf)]
            for s in S.piv[('ETH', tf)]:
                if not s['gated']:
                    continue
                ei = s['ei']
                end = B[ei]['open'] + dt.timedelta(days=60)
                if B[-1]['open'] < end:
                    continue
                j = ei + 1; last = None
                while j < len(B) and B[j]['open'] <= end:
                    last = B[j]['c']; j += 1
                if last is None:
                    continue
                tg = {s['bk'], 'any trough'}
                if s['dis']:
                    tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
                if s['prime']:
                    tg.add('prime dot')
                if s['dis'] and s['prime']:
                    tg.add('diamond+dot')
                if s['bk'] == 'B' and s['ct'] < 60 and s['zm'] is not None and s['zm'] >= 50:
                    tg.add('zone-exit B')
                out.append(dict(chart=f'ETH {tf}', tf=int(tf[:-1]), d=B[ei]['open'], win=(last / B[ei]['c'] - 1) * 100 > 0, tags=tg, sig=s))
        return out

    def keep(self, rows_all, upto):
        keep = []
        for tf in TFS:
            nm = f'ETH {tf}'
            for t in TIER_TAGS:
                sub = [r for r in rows_all if r['chart'] == nm and t in r['tags'] and r['d'] + dt.timedelta(days=r['tf'] - 1 + 60) < upto]
                if len(sub) >= 8 and 100 * sum(r['win'] for r in sub) / len(sub) >= 70:
                    keep.append((nm, t))
        return keep

    def odds_fade(self):
        S = self.S
        rows_all = self.tier_rows()
        anchor = dt.date(S.today.year, 1, 1)
        keep = self.keep(rows_all, anchor)
        d = S.daily['ETH']
        early = []; hold = {'green on day 10': [], 'red on day 10': []}
        for tf in TFS:
            nm = f'ETH {tf}'
            for s in S.sig[('ETH', tf)]:
                tg = next((r['tags'] for r in rows_all if r['sig'] is s), None)
                if tg is None:
                    tg = {s['bk'], 'any trough'} | ({'diamond', 'filled' if s['strong'] else 'hollow'} if s['dis'] else set()) | ({'prime dot'} if s['prime'] else set()) | ({'diamond+dot'} if s['dis'] and s['prime'] else set()) | ({'zone-exit B'} if s['bk'] == 'B' and s['ct'] < 60 and s['zm'] is not None and s['zm'] >= 50 else set())
                if not any(nm == k and t in tg for k, t in keep):
                    continue
                if s['d0'] not in d['pos'] or not S.closed60('ETH', s['d0']):
                    continue
                e = d['c'][d['pos'][s['d0']]]
                _, ks = S.window('ETH', s['d0'])
                lo = min(d['l'][k] for k, off in ks if off <= 10)
                hi_after = max(d['h'][k] for k, off in ks if off > 10)
                early.append(((lo / e - 1) * 100, hi_after >= e * 1.10, hi_after >= e * 1.20))
                k10 = [k for k, off in ks if off == 10]
                if k10:
                    g = 'green on day 10' if d['c'][k10[0]] >= e else 'red on day 10'
                    hold[g].append((hi_after >= e * 1.10, hi_after >= e * 1.20))
        bands = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
        ed = []
        for hi, lo, lab in bands:
            g = [x for x in early if lo < x[0] <= hi]
            if len(g) < 5:
                continue
            n = len(g); r10 = sum(x[1] for x in g); r20 = sum(x[2] for x in g)
            ed.append(dict(band=lab, past_trades=n, rose10_after_day10_pct=rnd(100 * r10 / n), rose20_after_day10_pct=rnd(100 * r20 / n),
                           exact=100 * r10 / n, edge='intact' if 100 * r10 / n >= 70 else 'gone'))
        d10 = []
        for lab in ('green on day 10', 'red on day 10'):
            g = hold[lab]
            if len(g) < 5:
                continue
            n = len(g); r10 = sum(x[0] for x in g); r20 = sum(x[1] for x in g)
            d10.append(dict(check=lab, past_trades=n, rose10_after_day10_pct=rnd(100 * r10 / n), rose20_after_day10_pct=rnd(100 * r20 / n),
                            exact=100 * r10 / n, edge='intact' if 100 * r10 / n >= 70 else 'gone'))
        # trades a year (walk-forward tier of 1 Jan this year, every tier signal, one per chart per date)
        T = [r for r in rows_all if any(r['chart'] == c and t in r['tags'] for c, t in keep)]
        T = {(r['chart'], r['d']): r for r in T}
        data_end = max(S.bars[('ETH', tf)][-1]['open'] for tf in TFS)
        span = max(0.25, ((data_end - dt.timedelta(days=60)) - min(r['d'] for r in T.values())).days / 365.25) if T else None
        per_year = len(T) / span if T else None
        return dict(early_dip=ed, day10=d10, tier_fixed_on=str(anchor), keep=keep,
                    trades_a_year=f'{rnd(per_year)} on average' if per_year else None)
