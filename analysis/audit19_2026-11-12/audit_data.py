"""Audit 19 data checks (1-7): feed + ledger of one state against my own computation from raw candles.
usage: audit_data.py <state dir> <clock ISO> <state label> <out csv>"""
import csv, json, os, sys, datetime as dt, math
from fractions import Fraction as Fr
from decimal import Decimal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

EX_D0 = dt.date(2024, 9, 22)
D = dt.date.fromisoformat


def funding(root):
    fb, fs = {}, {}
    for a in ASSETS:
        f, g = {}, {}
        for r in csv.DictReader(open(os.path.join(root, 'data', 'derivs', f'{a}_funding_daily.csv'))):
            v = r.get('funding_oi_weighted') or r.get('funding_mean')
            if v not in ('', None): f[D(r['date'])] = float(v)
            w = r.get('funding_mean')
            if w not in ('', None): g[D(r['date'])] = float(w)
        fb[a] = {d for d in f if sum(1 for k in range(1, 91) if (d - k * DAY) in f) >= 60}
        fs[a] = g
    return fb, fs


def fcool_ok(fs, d0):
    return sum(1 for k in range(7) if (d0 - k * DAY) in fs) >= 5 and sum(1 for k in range(7) if (d0 - (14 + k) * DAY) in fs) >= 5


def yn(b): return 'yes' if b else 'no'


def lensset(s): return frozenset(x for x in s.split(' + ') if x and x != '-')


def gp(g): return 'the top grade' if g == 'A+' else 'the same grade'


def card_figures(S, G):
    """G: list of (signal, measure). Returns the card's figures as my values."""
    n = len(G); o = {}
    o['past_trades'] = n
    sh = lambda k, m=None: share(k, n if m is None else m)
    o['rose10_never_fell25_within60d_pct'] = sh(sum(m['surv10'] for s, m in G))
    sc = [x for x in (S.scaled20(s, m) for s, m in G) if x is not None]
    o['beat_normal_move_pct'] = share(sum(sc), len(sc))
    o['rose20_within60d_pct'] = sh(sum(m['r20'] for s, m in G)); o['rose10_within60d_pct'] = sh(sum(m['r10'] for s, m in G))
    for k, f in (('typical_biggest_rise', 'up'), ('typical_dip_before_rise', 'ddpk'), ('typical_deepest_dip', 'dd')):
        md = med([m[f] for s, m in G])
        o[k + '_pct'] = None if md is None else rha(md, 1); o[k + '_exact_pct'] = None if md is None else rha(md, 6)
    o['fell30_within60d_pct'] = sh(sum(m['t30'] for s, m in G))
    old = [(s, m) for s, m in G if s['d0'] < dt.date(2022, 1, 1)]; new = [(s, m) for s, m in G if s['d0'] >= dt.date(2022, 1, 1)]
    o['before_2022.past_trades'] = len(old); o['before_2022.rose10_never_fell25_within60d_pct'] = share(sum(m['surv10'] for s, m in old), len(old))
    o['since_2022.past_trades'] = len(new); o['since_2022.rose10_never_fell25_within60d_pct'] = share(sum(m['surv10'] for s, m in new), len(new))
    rmed = lambda xs: None if not xs else int(rha(Fr(med(xs)), 0))
    o['typical_day_first_rose10'] = rmed([x for x in (S.days_to(s, 10, m['ks']) for s, m in G) if x is not None])
    o['typical_day_first_rose20'] = rmed([x for x in (S.days_to(s, 20, m['ks']) for s, m in G) if x is not None])
    o['typical_day_of_60d_high'] = rmed([m['dpk'] for s, m in G]); o['typical_day_of_deepest_dip'] = rmed([m['ddday'] for s, m in G])
    fe = [S.from_entry(s, m['ks']) for s, m in G]
    o['from_entry.past_trades'] = n
    o['from_entry.still_rose10_pct'] = sh(fe.count('ok')); o['from_entry.went_on_to_fall25_pct'] = sh(fe.count('liq'))
    o['from_entry.still_rose10_exact_pct'] = share(fe.count('ok'), n, 6)
    for th in (5, 10, 15, 20):
        r = [x for x in (S.falls_first(s, m['ks'], th) for s, m in G) if x is not None]
        p = f'falls{th}.'
        o[p + 'past_trades'] = len(r); o[p + 'still_rose10_pct'] = share(r.count('ok'), len(r)); o[p + 'went_on_to_fall25_pct'] = share(r.count('liq'), len(r))
        o[p + 'still_rose10_exact_pct'] = share(r.count('ok'), len(r), 6)
    return o


def edge_level(o):
    x = o['from_entry.still_rose10_exact_pct']
    if x is not None and x < 70: return 0
    for th in (5, 10, 15, 20):
        x = o[f'falls{th}.still_rose10_exact_pct']
        if x is not None and x < 70: return -th
    return None


def flat_card(c):
    o = {k: v for k, v in c.items() if not isinstance(v, (dict, list))}
    for era in ('before_2022', 'since_2022'):
        for k, v in c[era].items(): o[f'{era}.{k}'] = v
    for k, v in c['from_entry'].items(): o[f'from_entry.{k}'] = v
    for r in c['if_it_falls_first']:
        for k, v in r.items(): o[f"falls{r['fell_pct']}.{k}"] = v
    return o


def forming_lows(S):
    """the pivot low still waiting on right-hand bars, per chart: among the 3 bars before the open bar, the first
    (nearest) whose CT is strictly below the 3 bars before it and not above any bar after it so far."""
    out = {}
    for key, b in S.bars.items():
        ct = S.ct[key]; k = S.k[key]; n = len(b.c)
        for back in (1, 2, 3):
            ti = n - 1 - back
            if ti - 3 < 0 or ct[ti] is None: continue
            if any(ct[j] is None or ct[j] <= ct[ti] for j in range(ti - 3, ti)): continue
            if any(ct[j] < ct[ti] for j in range(ti + 1, n)): continue
            out[key] = dict(ti=ti, need=3 - back, tdate=b.date[ti], ct=ct[ti], k=k[ti]); break
    return out


def kill_close(b, ti, need, ctv):
    """the confirmation-bar close at or below which CT would not stay above the trough's CT, floored to the cent.
    need 0: the confirmation bar is the open bar (its close is replaced); need 1: the next bar (appended, today's
    open bar taken at its current price)."""
    if need == 0: base = b.c[:-1]
    elif need == 1: base = list(b.c)
    else: return None
    lo, hi = b.c[-1] * 0.5, b.c[-1] * 1.5
    for _ in range(80):
        mid = (lo + hi) / 2
        if rsi(base + [mid])[-1] <= ctv: lo = mid
        else: hi = mid
    return Decimal(math.floor(lo * 100 + 1e-9)) / 100


def run(root, clock, label, R=None):
    R = R or Rec(label)
    now = dt.datetime.fromisoformat(clock.replace('Z', '+00:00')).astimezone(dt.timezone.utc); today = now.date()
    S = State(root, today)
    feed = json.load(open(os.path.join(root, 'feed', 'ctzb_feed.json')))
    ds = lambda n: list(csv.DictReader(open(os.path.join(root, 'datasets', n))))
    led = ds('ledger.csv')
    info = dict(today=today, cards=len(feed.get('cards') or []), open=len(feed.get('open_signals') or []), withheld=feed.get('cards_withheld'))
    # envelope
    R.add('envelope', 'last daily bar is today (ETH)', S.day['ETH'].date[-1], today, S.day['ETH'].date[-1] == today)
    R.add('envelope', 'last daily bar is today (BTC)', S.day['BTC'].date[-1], today, S.day['BTC'].date[-1] == today)
    # multi-day bars are the daily bars bucketed within each calendar year
    for (a, tf), b in S.bars.items():
        if tf == '1D': continue
        d1 = S.day[a]; bad = 0; raw = {}
        for i, d in enumerate(d1.date): raw.setdefault(bar_open_of(d, tf), []).append(i)
        rawc = list(csv.DictReader(open(os.path.join(root, 'data', f'{a}_{tf}.csv'))))
        d1raw = list(csv.DictReader(open(os.path.join(root, 'data', f'{a}_1D.csv'))))
        for r in rawc:
            d = dt.datetime.fromtimestamp(int(float(r['time'])), dt.timezone.utc).date(); idx = raw.get(bar_open_of(d, tf))
            if not idx or d1.date[idx[0]] != d: bad += 1; continue      # a bar is stamped with the first day present in its bucket
            exp = (float(d1raw[idx[0]]['open']), max(float(d1raw[i]['high']) for i in idx), min(float(d1raw[i]['low']) for i in idx), float(d1raw[idx[-1]]['close']))
            if exp != (float(r['open']), float(r['high']), float(r['low']), float(r['close'])): bad += 1
        first = dt.datetime.fromtimestamp(int(float(rawc[0]['time'])), dt.timezone.utc).date()
        if len(rawc) != sum(1 for d in raw if d >= bar_open_of(first, tf)): bad += 1
        R.add('data', f'{a} {tf} bars = daily candles bucketed within the calendar year (bad bars)', bad, 0)
    R.add('feed.top', 'scored_as_of', feed.get('scored_as_of'), str(today), feed.get('scored_as_of') == str(today))
    R.add('feed.top', 'schema_version', feed.get('schema_version'), 6)
    R.add('feed.top', 'posting_bar_pct', feed.get('posting_bar_pct'), 70)
    R.add('feed.top', 'market_regime', feed.get('market_regime'), 'Bullish' if S.gate(today) else 'Bearish', feed.get('market_regime') == ('Bullish' if S.gate(today) else 'Bearish'))

    # ---------------- my signals, measures ----------------
    fb, fs = funding(root)
    mine = {}
    for key in S.sig:
        for s in S.sig[key]:
            mine[(s['chart'], str(s['d0']))] = s
    meas = {}
    def M(s):
        k = (s['chart'], str(s['d0']))
        if k not in meas: meas[k] = S.measure(s)
        return meas[k]
    elig = {}
    for k, s in mine.items():
        if s['tf'] not in GRADED or M(s) is None: continue
        if s['a'] == 'ETH' and not (s['d0'] in fb['ETH'] and fcool_ok(fs['ETH'], s['d0'])): continue
        elig[k] = s
    # ---------------- 1. ledger ----------------
    lk = {(r['chart'], r['entry']): r for r in led}
    R.add('ledger', 'row count', len(led), len(elig))
    for k in sorted(set(lk) - set(elig)): R.add('ledger', f'membership {k[0]} {k[1]}', 'in ledger', 'not a completed gated signal by my code', False, 'membership')
    for k in sorted(set(elig) - set(lk)): R.add('ledger', f'membership {k[0]} {k[1]}', 'absent', 'a completed gated signal by my code', False, 'membership')
    R.add('ledger', 'duplicate keys', len(led) - len(lk), 0)
    # pooled grade rates from the ledger's grades (given) and my measures
    byg = {}
    for k, r in lk.items():
        if k in elig: byg.setdefault((r['asset'], r['grade']), []).append((elig[k], M(elig[k])))
    gstat = {}
    for g, G in byg.items():
        n = len(G)
        gstat[g] = dict(n=n, reach20=share(sum(m['r20'] for s, m in G), n), touched30=share(sum(m['t30'] for s, m in G), n), medDip=rha(med([m['dd'] for s, m in G]), 1),
                        reach10=share(sum(m['r10'] for s, m in G), n), surv10=share(sum(m['surv10'] for s, m in G), n),
                        sample=f"{min(s['d0'] for s, m in G)} to {max(s['d0'] for s, m in G)}")
    hist = sorted(((r['asset'], elig[k]['d0'], r['grade'], elig[k], M(elig[k])) for k, r in lk.items() if k in elig), key=lambda x: x[1])
    for k, r in lk.items():
        s = elig.get(k)
        if s is None: continue
        m = M(s); loc = f"ledger {k[0]} {k[1]}"
        R.add(loc, 'asset', r['asset'], s['a'], r['asset'] == s['a'])
        R.add(loc, 'low', r['low'], str(s['tdate']), r['low'] == str(s['tdate']))
        R.add(loc, 'entryPrice', r['entryPrice'], rha(Fr(s['entry_s']), 2))
        R.add(loc, 'entry close = daily close on the entry date', S.day[s['a']].sc[S.day[s['a']].pos[s['d0']]], s['entry_s'])
        R.add(loc, 'tags', r['tags'], tagtext(s), r['tags'] == tagtext(s))
        R.add(loc, 'bestMove', r['bestMove'], rha(m['up'], 6)); R.add(loc, 'maxDrawdown', r['maxDrawdown'], rha(m['dd'], 6))
        R.add(loc, 'dipBeforeHigh', r['dipBeforeHigh'], rha(m['ddpk'], 6)); R.add(loc, 'return60d', r['return60d'], rha(m['ret'], 6))
        R.add(loc, 'daysToHigh', r['daysToHigh'], m['dpk']); R.add(loc, 'year', r['year'], s['d0'].year)
        for col, v in (('reached20', m['r20']), ('touched30', m['t30']), ('reached10', m['r10']), ('reached15', m['r15']), ('surv10', m['surv10'])):
            R.add(loc, col, r[col], yn(v), r[col] == yn(v))
        sc = S.scaled20(s, m); R.add(loc, 'scaled20', r['scaled20'], '' if sc is None else yn(sc), r['scaled20'] == ('' if sc is None else yn(sc)))
        g = gstat[(r['asset'], r['grade'])]
        R.add(loc, 'gradeReach20', r['gradeReach20'], g['reach20']); R.add(loc, 'gradeTouched30', r['gradeTouched30'], g['touched30']); R.add(loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], g['medDip'])
        # odds on the day: same asset, 60th day closed by this entry date; shrunk toward the base rate with weight 5
        prior = [h for h in hist if h[0] == r['asset'] and h[1] + 60 * DAY <= s['d0']]
        G = [h for h in prior if h[2] == r['grade']]
        R.add(loc, 'dayN', r['dayN'], len(G))
        def rate(fn, okf=lambda h: True):
            P = [h for h in prior if okf(h)]; Gk = [h for h in G if okf(h)]
            if not P or not Gk: return None
            base = Fr(sum(fn(h) for h in P), len(P))
            return rha(100 * (sum(fn(h) for h in Gk) + 5 * base) / (len(Gk) + 5), 0)
        if len(G) < 10 or not prior:
            exp = dict.fromkeys(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'daySurv10', 'dayScaled20'))
        else:
            scv = lambda h: S.scaled20(h[3], h[4])
            exp = dict(dayReach10=rate(lambda h: h[4]['r10']), dayReach20=rate(lambda h: h[4]['r20']), dayReach30=rate(lambda h: h[4]['r30']),
                       dayTouched30=rate(lambda h: h[4]['t30']), daySurv10=rate(lambda h: h[4]['surv10']),
                       dayScaled20=rate(lambda h: bool(scv(h)), lambda h: scv(h) is not None))
        for col, v in exp.items(): R.add(loc, col, r[col], v)
    # ---------------- 2. grade_odds ----------------
    for go in feed.get('grade_odds') or []:
        a, g = go['asset'], go['grade']; loc = f'feed.grade_odds {a} {g}'
        if g in ('HTF divergence', 'no HTF divergence'): continue     # lens logic, out of scope (note h)
        if g in ('diamond or prime dot', 'no diamond or prime dot'):
            G = [(elig[k], M(elig[k])) for k, r in lk.items() if k in elig and r['asset'] == a and ((elig[k]['dis'] or elig[k]['prime']) == (g == 'diamond or prime dot'))]
            n = len(G)
            st_ = dict(n=n, reach20=share(sum(m['r20'] for s, m in G), n), medDip=rha(med([m['dd'] for s, m in G]), 1) if n else None,
                       reach10=share(sum(m['r10'] for s, m in G), n), surv10=share(sum(m['surv10'] for s, m in G), n),
                       sample=f"{min(s['d0'] for s, m in G)} to {max(s['d0'] for s, m in G)}" if n else '')
        else: st_ = gstat.get((a, g))
        if st_ is None:
            R.add(loc, 'past_trades', go['past_trades'], 0); continue
        R.add(loc, 'past_trades', go['past_trades'], st_['n']); R.add(loc, 'past_signals', go.get('past_signals'), st_['n'])
        R.add(loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], st_['reach10']); R.add(loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], st_['surv10'])
        R.add(loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], st_['reach20']); R.add(loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], st_['medDip'])
        R.add(loc, 'sample', go['sample'], st_['sample'], go['sample'] == st_['sample'])
    present = {(g['asset'], g['grade']) for g in feed.get('grade_odds') or []}
    for g in gstat:
        if g not in present and not feed.get('feed_error'): R.add(f'feed.grade_odds {g[0]} {g[1]}', 'present', 'absent', 'expected', False)

    # ---------------- 3. if_it_misses ----------------
    def miss_stats(G):
        mm = [(s, m) for s, m in G if not m['r10']]
        best = [rha(m['up'], 6) for s, m in mm]; m1 = lambda xs: None if not xs else rha(med(xs), 1)
        return dict(signals=len(G), misses=len(mm), up_first=sum(b > 0 for b in best), median_peak_pct=m1(best),
                    mean_peak_pct=None if not best else rha(Fr(sum(best)) / len(best), 1), peaked_5_or_more=sum(b >= 5 for b in best), peaked_10_or_more=sum(b >= 10 for b in best),
                    median_worst_drop_pct=m1([rha(m['dd'], 6) for s, m in mm]), median_day60_pct=m1([rha(m['ret'], 6) for s, m in mm]))
    if not feed.get('extras_withheld'):
        seen = set()
        for mi in feed.get('if_it_misses') or []:
            key = (mi['asset'], mi['grade']); seen.add(key); G = byg.get(key, []); e = miss_stats(G)
            for f, v in e.items(): R.add(f'feed.if_it_misses {key[0]} {key[1]}', f, mi.get(f), v)
            R.add(f'feed.if_it_misses {key[0]} {key[1]}', 'miss_rule', mi.get('miss_rule'), 'did not rise 10% within 60 days', mi.get('miss_rule') == 'did not rise 10% within 60 days')
        aplus_assets = {a for (a, g) in byg if g == 'A+'}
        for key in byg:
            if key[0] in aplus_assets and key not in seen: R.add(f'feed.if_it_misses {key[0]} {key[1]}', 'present', 'absent', 'expected', False)
        knownA = [(elig[k], M(elig[k])) for k, r in lk.items() if k in elig and r['asset'] == 'ETH' and r['grade'] == 'A+' and elig[k]['d0'] + 60 * DAY <= EX_D0]
        xm = feed.get('example_if_it_misses')
        if xm:
            e = miss_stats(knownA)
            for f in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'): R.add('feed.example_if_it_misses', f, xm.get(f), e[f])
        elif knownA: R.add('feed.example_if_it_misses', 'present', 'absent', 'expected', False)

    # ---------------- 4. odds_fade (walk-forward tier on each ETH chart's own bars; outcomes on daily candles) ----------------
    anchor = dt.date(today.year, 1, 1); TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
    pool = []; tagsof = {}
    for tf in TFS:
        b = S.bars[('ETH', tf)]; ct = S.ct[('ETH', tf)]; zm = []; z = None
        for v in ct:
            if v is None: zm.append(None); continue
            z = None if v >= 60 else (v if z is None else min(z, v)); zm.append(z)
        for s in S.tr[('ETH', tf)]:
            if not S.gate(s['tdate']): continue
            tg = {s['bk'], 'any trough'}
            if s['dis']: tg |= {'diamond', 'filled' if s['strong'] else 'hollow'}
            if s['prime']: tg.add('prime dot')
            if s['dis'] and s['prime']: tg.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: tg.add('zone-exit B')
            tagsof[(tf, s['ti'])] = tg
            ei = s['ei']; end = b.date[ei] + 60 * DAY
            if b.date[-1] < end: continue
            js = [j for j in range(ei + 1, len(b.date)) if b.date[j] <= end]
            if not js: continue
            pool.append(dict(tf=tf, tags=tg, d=b.date[ei], win=Fr(b.sc[js[-1]]) > Fr(b.sc[ei])))
    keep = set()
    for tf in TFS:
        for t in TAGS:
            sub = [r for r in pool if r['tf'] == tf and t in r['tags'] and r['d'] + (tf_days(tf) - 1 + 60) * DAY < anchor]
            if len(sub) >= 8 and Fr(100 * sum(r['win'] for r in sub), len(sub)) >= 70: keep.add((tf, t))
    wins = []
    for tf in TFS:
        b = S.bars[('ETH', tf)]
        for s in S.tr[('ETH', tf)]:
            tg = tagsof.get((tf, s['ti']))
            if tg is None or not any((tf, t) in keep for t in tg): continue
            ei = s['ei']
            if ei + 1 >= len(b.date): continue
            d0 = b.date[ei + 1] - DAY; d1 = S.day['ETH']
            if d0 not in d1.pos: continue
            ks = S.window('ETH', d0)
            if not ks or d1.date[ks[-1]] != d0 + 60 * DAY: continue
            e = Fr(d1.sc[d1.pos[d0]])
            early = [k for k in ks if (d1.date[k] - d0).days <= 10]; late = [k for k in ks if (d1.date[k] - d0).days > 10]
            lo = min(Fr(d1.sl[k]) for k in early); hi = max(Fr(d1.sh[k]) for k in late)
            k10 = [k for k in ks if (d1.date[k] - d0).days == 10]
            wins.append(dict(dip=(lo / e - 1) * 100, r10=hi >= e * Fr(11, 10), r20=hi >= e * Fr(12, 10), green=(Fr(d1.sc[k10[0]]) >= e) if k10 else None))
    of = feed.get('odds_fade') or {}
    if not feed.get('extras_withheld'):
        R.add('feed.odds_fade', 'posting_bar_pct', of.get('posting_bar_pct'), 70)
        R.add('feed.odds_fade', 'tier_fixed_on', of.get('tier_fixed_on'), str(anchor), of.get('tier_fixed_on') == str(anchor))
        R.add('feed.odds_fade', 'sample names the tier date', (of.get('sample') or '')[:120], f'{anchor.day} {anchor:%b %Y}', f'as fixed on {anchor.day} {anchor:%b %Y}' in (of.get('sample') or ''))
        R.add('feed.odds_fade', 'edge_measured_on', of.get('edge_measured_on'), 'rose 10% after day 10 (days 11 to 60)', of.get('edge_measured_on') == 'rose 10% after day 10 (days 11 to 60)')
        bands = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
        exp = []
        for hi_, lo_, lab in bands:
            g = [w for w in wins if lo_ < w['dip'] <= hi_]
            if len(g) >= 5: exp.append((lab, g))
        got = {r['band']: r for r in of.get('early_dip') or []}
        R.add('feed.odds_fade.early_dip', 'bands', '|'.join(got), '|'.join(l for l, g in exp), list(got) == [l for l, g in exp])
        def cmp_row(loc, r, g):
            n = len(g); x10 = Fr(100 * sum(w['r10'] for w in g), n)
            R.add(loc, 'past_trades', r.get('past_trades'), n); R.add(loc, 'past_signals', r.get('past_signals'), n)
            for f in ('rose10_after_day10_pct', 'rose10_within60d_pct'): R.add(loc, f, r.get(f), rha(x10, 0))
            for f in ('rose20_after_day10_pct', 'rose20_within60d_pct'): R.add(loc, f, r.get(f), share(sum(w['r20'] for w in g), n))
            R.add(loc, 'edge (exact share vs 70)', r.get('edge'), 'intact' if x10 >= 70 else 'gone', r.get('edge') == ('intact' if x10 >= 70 else 'gone'))
        for lab, g in exp:
            if lab in got: cmp_row(f'feed.odds_fade.early_dip {lab}', got[lab], g)
        got = {r['check']: r for r in of.get('day10') or []}
        for lab, sel in (('green on day 10', True), ('red on day 10', False)):
            g = [w for w in wins if w['green'] is sel]
            if len(g) >= 5:
                if lab in got: cmp_row(f'feed.odds_fade.day10 {lab}', got[lab], g)
                else: R.add(f'feed.odds_fade.day10 {lab}', 'present', 'absent', len(g), False)
            elif lab in got: R.add(f'feed.odds_fade.day10 {lab}', 'present', 'present', 'fewer than 5', False)
    # trades_a_year: the tier's deduped signals per year over the scoreable span
    sel = {}
    for r in pool:
        if any((r['tf'], t) in keep for t in r['tags']): sel[(r['tf'], r['d'])] = r
    if sel:
        span = max(Fr(1, 4), Fr((max(S.bars[('ETH', tf)].date[-1] for tf in TFS) - 60 * DAY - min(r['d'] for r in sel.values())).days * 100, 36525))
        tay = f"{rha(Fr(len(sel)) / span, 0)} on average"
        R.add('feed.top', 'trades_a_year', feed.get('trades_a_year'), tay, feed.get('trades_a_year') == tay)
        R.add('feed.top', 'signals_a_year', feed.get('signals_a_year'), tay, feed.get('signals_a_year') == tay)

    # ---------------- sample rule (like for like), from the ledger's grades and lenses as given ----------------
    def sample_for(a, tf, g, lenses, known=None):
        rows = [(k, r) for k, r in lk.items() if r['asset'] == a and k in elig and (known is None or elig[k]['d0'] + 60 * DAY <= known)]
        ch = [(k, r) for k, r in rows if r['chart'] == f'{a} {tf}']
        ex = [(k, r) for k, r in ch if lensset(r['lenses']) == lenses]; sg = [(k, r) for k, r in ch if r['grade'] == g]; ag = [(k, r) for k, r in rows if r['grade'] == g]
        if known is None:
            if len(ex) >= 15: basis, G = f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex
            elif len(sg) >= 15: basis, G = f'all {len(sg)} past {a} {tf} signals of {gp(g)} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
            else: basis, G = f'all {len(ag)} past signals of {gp(g)} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag
        else:
            if len(ex) >= 15: basis, G = f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', ex
            elif len(sg) >= 15: basis, G = f'all {len(sg)} {a} {tf} signals of {gp(g)} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
            else: basis, G = f'all {len(ag)} signals of {gp(g)} across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', ag
        return basis, [(elig[k], M(elig[k])) for k, r in G]

    def low_day(a, tf, tdate):
        d1 = S.day[a]; days = []; d = tdate
        while d < next_open(tdate, tf): days.append(d); d += DAY
        cand = [(d1.l[d1.pos[x]], x) for x in days if x in d1.pos]
        return str(min(cand)[1]) if cand else str(tdate)

    def check_card(loc, c, a, tf, g, lenses, ident, known=None):
        basis, G = sample_for(a, tf, g, lenses, known); o = card_figures(S, G); fc = flat_card(c)
        R.add(loc, 'sample (text)', fc.get('sample'), basis, fc.get('sample') == basis)
        for k, v in o.items():
            R.add(loc, k, fc.get(k), v)
            if k.endswith('past_trades'): R.add(loc, k.replace('past_trades', 'past_signals'), fc.get(k.replace('past_trades', 'past_signals')), v)
        for k, v in ident.items(): R.add(loc, k, fc.get(k), v, None if not isinstance(v, str) else fc.get(k) == v)
        R.add(loc, 'label says computed/entry quality only', (c.get('label') or '')[:30], 'Computed signal, not a fill', (c.get('label') or '').startswith('Computed signal, not a fill') and 'not a strategy return or a track record' in c.get('label', ''))
        return o, G, basis

    info['mycards'] = {}
    if not feed.get('cards_withheld'):
        # ---------------- 5. cards: forming ----------------
        fl = forming_lows(S); expect = {}
        for (a, tf), p in fl.items():
            b = S.bars[(a, tf)]; co = b.date[-1]
            for _ in range(p['need']): co = next_open(co, tf)
            p['d0f'] = next_open(co, tf) - DAY; p['sid'] = f'{a}-{tf}-{p["d0f"]}'
            p['gate'] = S.gate(p['tdate'])
            if tf in GRADED and p['gate']: expect[p['sid']] = (a, tf, p)
        got = {c['signal_id']: c for c in feed.get('cards') or []}
        for sid in sorted(set(got) - set(expect)): R.add(f'feed.cards {sid}', 'card exists only for a gated forming low on a graded chart', 'card', 'no such forming low', False)
        for sid, (a, tf, p) in expect.items():
            if sid not in got:
                # allowed only when its sample is empty (cannot be decided without the lens logic): flag for review
                R.add(f'feed.cards {sid}', 'forming low on a graded chart, gate on at the trough, has a card', 'absent', 'expected unless its sample is empty', False, 'check sample'); continue
            c = got[sid]; b = S.bars[(a, tf)]; loc = f'feed.cards {sid}'
            lenses = frozenset(UNPLAIN.get(x, x) for x in c['confirmations'].split('; ') if x and x != 'none')
            ident = dict(chart=f'{a} {tf}', asset=a, timeframe=tf, low_date=str(p['tdate']), low_day=low_day(a, tf, p['tdate']), confirms_on=str(p['d0f']),
                         bars_to_confirm=p['need'], must_close_above=kill_close(b, p['ti'], p['need'], p['ct']), price_now=rha(Fr(b.sc[-1]), 2), entry_close=None)
            o, G, basis = check_card(loc, c, a, tf, c['grade'], lenses, ident)
            R.add(loc, 'sample is not empty', len(G) > 0, True, len(G) > 0)
            if c.get('must_close_above') is not None and p['need'] in (0, 1):
                # what the words promise: a close AT the shown price does not confirm, a close one cent above does
                base = b.c[:-1] if p['need'] == 0 else list(b.c); x = float(c['must_close_above'])
                at_, above_ = rsi(base + [x])[-1] > p['ct'], rsi(base + [round(x + 0.01, 2)])[-1] > p['ct']
                R.add(loc, 'must_close_above: a close at it does not confirm, one cent above does', (at_, above_), (False, True), (at_, above_) == (False, True))
            R.add(loc, 'gate on at the trough date', p['gate'], True, p['gate'] is True)
            info['mycards'][sid] = dict(o=o, ident=ident, kind='forming', grade=c['grade'], a=a, tf=tf, basis=basis, tlow=min(S.day[a].l[S.day[a].pos[x]] for x in [p['tdate'] + i * DAY for i in range((next_open(p['tdate'], tf) - p['tdate']).days)] if x in S.day[a].pos))
        # ---------------- 5. example card ----------------
        xc = feed.get('example_card'); xs = mine.get(('ETH 2D', '2024-09-22'))
        if xs is not None and M(xs) is None: xs = None      # the example exists once its own 60 days have closed (from 22 Nov 2024)
        if xc and not xs: R.add('feed.example_card', 'present', 'present', 'not expected', False)
        if xc and xs:
            xr = lk[('ETH 2D', '2024-09-22')]
            ident = dict(chart='ETH 2D', asset='ETH', timeframe='2D', low_date=str(xs['tdate']), low_day=low_day('ETH', '2D', xs['tdate']), confirms_on='2024-09-22', bars_to_confirm=None,
                         must_close_above=None, price_now=None, entry_close=rha(Fr(xs['entry_s']), 2), signal_id='ETH-2D-2024-09-22', grade=xr['grade'])
            o, G, basis = check_card('feed.example_card', xc, 'ETH', '2D', xr['grade'], lensset(xr['lenses']), ident, known=EX_D0)
            R.add('feed.example_card', 'every sample signal had closed its 60 days by 2024-09-22', all(s['d0'] + 60 * DAY <= EX_D0 for s, m in G), True, all(s['d0'] + 60 * DAY <= EX_D0 for s, m in G))
            R.add('feed.example_card', 'example flag', xc.get('example'), True, xc.get('example') is True)
            info['mycards']['example'] = dict(o=o, ident=ident, kind='example', grade=xr['grade'], a='ETH', tf='2D', entry=Fr(xs['entry_s']), sig=xs, basis=basis)
        elif xs and not xc: R.add('feed.example_card', 'present', 'absent', 'expected', False)
        # ---------------- 6. open signals ----------------
        exp_open = {}
        for key, sg in S.sig.items():
            if key[1] not in GRADED: continue
            for s in sg:
                if 0 <= (today - s['d0']).days <= 60 and s['d0'] in S.day[s['a']].pos: exp_open[f"{s['a']}-{s['tf']}-{s['d0']}"] = s
        got = {o['signal_id']: o for o in feed.get('open_signals') or []}
        R.add('feed.open_signals', 'ids', len(got), len(exp_open), set(got) == set(exp_open), '' if set(got) == set(exp_open) else f'only feed {sorted(set(got) - set(exp_open))} only mine {sorted(set(exp_open) - set(got))}')
        order = [o['signal_id'] for o in feed.get('open_signals') or []]
        myorder = [k for k, s in sorted(exp_open.items(), key=lambda kv: (str(kv[1]['d0']), kv[1]['chart']))]
        R.add('feed.open_signals', 'order (entry date, chart)', ','.join(order)[:60], ','.join(myorder)[:60], order == myorder)
        for sid, s in exp_open.items():
            if sid not in got: continue
            o = got[sid]; loc = f'feed.open_signals {sid}'; a = s['a']; d1 = S.day[a]; e = Fr(s['entry_s'])
            ks = S.window(a, s['d0'])
            R.add(loc, 'chart', o['chart'], s['chart'], o['chart'] == s['chart']); R.add(loc, 'entry_date', o['entry_date'], str(s['d0']), o['entry_date'] == str(s['d0']))
            R.add(loc, 'entry_close', o['entry_close'], rha(e, 2)); R.add(loc, 'tags', o['tags'], tagtext(s), o['tags'] == tagtext(s))
            R.add(loc, 'days_elapsed', o['days_elapsed'], (today - s['d0']).days)
            for n_, f in ((10, 'day10_pct'), (30, 'day30_pct'), (60, 'day60_pct')):
                k = [k for k in ks if (d1.date[k] - s['d0']).days == n_]
                R.add(loc, f, o[f], rha((Fr(d1.sc[k[0]]) / e - 1) * 100, 1) if k else None)
            R.add(loc, 'best_so_far_pct', o['best_so_far_pct'], rha((max(Fr(d1.sh[k]) for k in ks) / e - 1) * 100, 1) if ks else None)
            R.add(loc, 'worst_so_far_pct', o['worst_so_far_pct'], rha((min(Fr(d1.sl[k]) for k in ks) / e - 1) * 100, 1) if ks else None)
            R.add(loc, 'label', (o.get('label') or '')[:27], 'Computed signal, not a fill', (o.get('label') or '').startswith('Computed signal, not a fill'))
            c = o.get('card')
            if not c: R.add(loc, 'card present', 'absent', 'expected', False); continue
            lenses = lensset(o['confirmations'])
            ident = dict(chart=s['chart'], asset=a, timeframe=s['tf'], low_date=str(s['tdate']), low_day=low_day(a, s['tf'], s['tdate']), confirms_on=str(s['d0']), bars_to_confirm=None,
                         must_close_above=None, price_now=rha(Fr(d1.sc[-1]), 2), entry_close=rha(e, 2), signal_id=sid, grade=o['grade'])
            oc, G, basis = check_card(loc + ' card', c, a, s['tf'], o['grade'], lenses, ident)
            R.add(loc + ' card', 'confirmations (plain words of the lens codes)', c['confirmations'], '; '.join(PLAIN.get(x, x) for x in o['confirmations'].split(' + ') if x != '-') or 'none',
                  c['confirmations'] == ('; '.join(PLAIN.get(x, x) for x in o['confirmations'].split(' + ') if x != '-') or 'none'))
            lvl = edge_level(oc)
            if lvl == 0: st_ = 'lost'
            else:
                st_ = 'intact'
                for k in ks:
                    if lvl is not None and Fr(d1.sl[k]) <= e * Fr(100 + lvl, 100): st_ = 'lost'; break
                    if Fr(d1.sh[k]) >= e * Fr(11, 10): st_ = 'rose10'; break
            R.add(loc, 'edge_level_pct', o['edge_level_pct'], lvl); R.add(loc, 'edge_status', o['edge_status'], st_, o['edge_status'] == st_)
            info['mycards'][sid] = dict(o=oc, ident=ident, kind='open', grade=o['grade'], a=a, tf=s['tf'], entry=e, sig=s, days=(today - s['d0']).days, basis=basis,
                                        best=rha((max(Fr(d1.sh[k]) for k in ks) / e - 1) * 100, 1) if ks else None, worst=rha((min(Fr(d1.sl[k]) for k in ks) / e - 1) * 100, 1) if ks else None,
                                        d10=next((rha((Fr(d1.sc[k]) / e - 1) * 100, 1) for k in ks if (d1.date[k] - s['d0']).days == 10), None), lvl=lvl, status=st_)
        # ---------------- 6. prints ----------------
        expp = {}
        for (a, tf), sg in S.sig.items():
            for s in sg[-3:]:
                expp[(f'{a} {tf}', 'confirmed', str(s['d0']))] = dict(low_date=str(s['tdate']), entry_close=rha(Fr(s['entry_s']), 2), tags=tagtext(s), note='regime on', provisional=False, signal_id=f"{a}-{tf}-{s['d0']}")
            p = fl.get((a, tf))
            if p:
                prev = [t for t in S.tr[(a, tf)] if t['ti'] < p['ti']]; dis = False
                if prev and p['k'] is not None:
                    dct, dk = p['ct'] - prev[-1]['ct'], p['k'] - prev[-1]['k']
                    dis = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
                t = dict(bk=bucket(p['ct']), dis=dis, strong=dis and p['ct'] < 50, prime=p['k'] is not None and 20 <= p['k'] < 50)
                expp[(f'{a} {tf}', 'forming', str(p['d0f']))] = dict(low_date=str(p['tdate']), entry_close=rha(Fr(S.bars[(a, tf)].sc[-1]), 2), tags=tagtext(t),
                                                                    note=('regime on' if p['gate'] else 'regime off') + f"; {p['need']} bar(s) to confirm", provisional=True, signal_id=p['sid'])
        gotp = {(p['chart'], p['state'], p['confirms_on']): p for p in feed.get('prints') or []}
        R.add('feed.prints', 'set of prints', len(gotp), len(expp), set(gotp) == set(expp), '' if set(gotp) == set(expp) else f'only feed {sorted(set(gotp) - set(expp))[:4]} only mine {sorted(set(expp) - set(gotp))[:4]}')
        for k, e_ in expp.items():
            if k not in gotp: continue
            for f, v in e_.items(): R.add(f'feed.prints {k[0]} {k[1]} {k[2]}', f, gotp[k].get(f), v, None if not isinstance(v, (str, bool)) else gotp[k].get(f) == v)
    # ---------------- 7. past paths ----------------
    def paths(G):
        out = []
        for s, m in G:
            d1 = S.day[s['a']]; e = Fr(s['entry_s']); p = [Fr(0)]
            for k in range(1, 61):
                i = d1.pos.get(s['d0'] + k * DAY)
                if i is None: p = None; break
                p.append((Fr(d1.sc[i]) / e - 1) * 100)
            if p: out.append(p)
        return out
    def cmp_paths(loc, pp, G):
        P = paths(G); R.add(loc, 'signals', pp.get('signals'), len(P))
        R.add(loc, 'days listed', len(pp.get('days') or []), 61)
        for drow in pp.get('days') or []:
            k = drow['day']
            for f, q in (('q25_pct', Fr(1, 4)), ('median_pct', Fr(1, 2)), ('q75_pct', Fr(3, 4))):
                R.add(f'{loc} day {k}', f, drow[f], rha(quantile([p[k] for p in P], q), 1) if P else None)
    if not feed.get('extras_withheld'):
        for pp in feed.get('past_paths') or []:
            R.add(f"feed.past_paths {pp['asset']}", 'grade', pp.get('grade'), 'A+', pp.get('grade') == 'A+')
            cmp_paths(f"feed.past_paths {pp['asset']}", pp, byg.get((pp['asset'], 'A+'), []))
        if feed.get('example_past_paths'): cmp_paths('feed.example_past_paths', feed['example_past_paths'], knownA)
    info.update(S=S, feed=feed, lk=lk, elig=elig, M=M, byg=byg, gstat=gstat, miss_stats=miss_stats, knownA=knownA if not feed.get('extras_withheld') else [], paths=paths, sample_for=sample_for, wins=wins, keep=keep)
    return R, info


if __name__ == '__main__':
    root, clock, label, out = sys.argv[1:5]
    R, info = run(root, clock, label)
    with open(out, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writerows(R.rows)
    bad = R.bad()
    print(label, 'comparisons', len(R.rows), 'disagreements', len(bad), 'cards', info['cards'], 'open', info['open'], 'withheld', info['withheld'], 'tier', sorted(info['keep']))
    for r in bad[:40]: print('  ', r[1:])
