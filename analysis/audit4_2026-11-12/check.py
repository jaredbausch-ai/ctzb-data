"""Audit #4: compare every feed / ledger figure against independent values. Writes checks_<state>.json
and mine_<state>.json (values the page check uses). python3 check.py <tag> <state_dir> <now>"""
import csv, datetime as dt, json, os, sys, re, statistics as stt
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from mine import State, all_rows, ASSETS, TFS, GRADED, SPLIT

OUT = os.path.dirname(os.path.abspath(__file__))
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
RPLAIN = {v: k for k, v in PLAIN.items()}


class Checks:
    def __init__(self, tag):
        self.tag = tag; self.rows = []

    def add(self, loc, label, shown, yours, cause='', tol=None):
        ok = same(shown, yours)
        self.rows.append(dict(state=self.tag, location=loc, label=label, shown=fmtv(shown), yours=fmtv(yours),
                              ok='yes' if ok else 'NO', cause='' if ok else cause))
        return ok


def fmtv(v):
    if isinstance(v, F): return str(float(v))
    if v is None: return ''
    return str(v)


def same(a, b):
    if a is None or a == '': a = None
    if b is None or b == '': b = None
    if a is None or b is None: return a is None and b is None
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def grade_of_count(c):
    return 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'


def main(tag, sdir, now_s):
    now = dt.datetime.fromisoformat(now_s.replace('Z', '+00:00'))
    S = State(sdir, now); C = Checks(tag); today = now.date()
    rows = all_rows(S)
    led = S.ledger; feed = S.feed
    L = {(r['chart'], r['entry']): r for r in led}

    # ---------------------------------------------------------------- 1. ledger
    graded = [r for r in rows if r['tf'] in GRADED and r['m'] and (r['a'] == 'BTC' or S.eth_available(r['d0']))]
    G = {(r['chart'], str(r['d0'])): r for r in graded}
    for k in sorted(set(G) - set(L)):
        C.add('ledger', f'membership {k[0]} {k[1]}', 'absent', 'present', 'gated signal with a closed 60-day window missing from ledger')
    for k in sorted(set(L) - set(G)):
        r = next((x for x in rows if (x['chart'], str(x['d0'])) == k), None)
        why = 'no such gated signal' if r is None else ('60th day not closed' if not r['m'] else 'ETH funding/fcool data unavailable')
        C.add('ledger', f'membership {k[0]} {k[1]}', 'present', 'absent', why)
    ungraded_eth = [r for r in rows if r['a'] == 'ETH' and r['tf'] in GRADED and r['m'] and not S.eth_available(r['d0'])]
    eth_first_ledger = min(x['entry'] for x in led if x['asset'] == 'ETH')
    late_excl = [str(r['d0']) + ' ' + r['chart'] for r in ungraded_eth if str(r['d0']) >= eth_first_ledger]
    C.add('ledger', 'ETH graded signals excluded for missing funding data AFTER the first ETH ledger row', '', ';'.join(late_excl), 'ETH sample excludes signals inside the funding era')
    for k in sorted(set(G) & set(L)):
        r, x = G[k], L[k]; m = r['m']; loc = f'ledger {k[0]} {k[1]}'
        C.add(loc, 'row count (membership)', 1, 1)
        C.add(loc, 'low (trough bar open date)', x['low'], str(r['tdate']), 'trough date')
        C.add(loc, 'entryPrice', x['entryPrice'], rnd(r['entry'], 2), 'entry close')
        C.add(loc, 'tags', x['tags'], r['tags'], 'tag (bucket/diamond EPS/prime)')
        C.add(loc, 'year', x['year'], r['d0'].year)
        C.add(loc, 'bestMove (6dp)', x['bestMove'], rnd(m['up'], 6), 'best move')
        C.add(loc, 'maxDrawdown (6dp)', x['maxDrawdown'], rnd(m['dd'], 6), 'deepest dip')
        C.add(loc, 'dipBeforeHigh (6dp)', x['dipBeforeHigh'], rnd(m['ddpk'], 6), 'dip before high')
        C.add(loc, 'return60d (6dp)', x['return60d'], rnd(m['ret'], 6), 'day-60 close')
        C.add(loc, 'daysToHigh', x['daysToHigh'], m['dpk'], 'day of high')
        yn = lambda b: 'yes' if b else 'no'
        C.add(loc, 'reached20', x['reached20'], yn(m['r20']), 'rose 20% threshold')
        C.add(loc, 'reached10', x['reached10'], yn(m['r10']), 'rose 10% threshold')
        C.add(loc, 'reached15', x['reached15'], yn(m['r15']), 'rose 15% threshold')
        C.add(loc, 'touched30', x['touched30'], yn(m['t30']), 'fell 30% threshold')
        C.add(loc, 'surv10', x['surv10'], yn(m['surv10']), 'rose 10% never fell 25.3%')
        C.add(loc, 'scaled20', x['scaled20'], '' if m['scaled20'] is None else yn(m['scaled20']), 'vol-scaled +20%')
        r['grade'] = x['grade']; r['lenses'] = set() if x['lenses'] == '-' else set(x['lenses'].split(' + '))
    mine_led = [G[k] for k in sorted(set(G) & set(L))]

    # day-0 odds columns of the ledger (odds on the day: same asset+grade, 60 days finished before entry)
    def day_odds(a, g, d0):
        prior = [h for h in mine_led if h['a'] == a and h['d0'] + dt.timedelta(days=61) <= d0]
        Gg = [h for h in prior if h['grade'] == g]
        if len(Gg) < 10 or not prior: return ['', '', '', '', len(Gg), '', '']
        def rate(fn):
            base = F(sum(1 for h in prior if fn(h)), len(prior))
            return rnd(100 * (sum(1 for h in Gg if fn(h)) + 5 * base) / (len(Gg) + 5))
        return [rate(lambda h: h['m']['r10']), rate(lambda h: h['m']['r20']), rate(lambda h: h['m']['up'] >= 30),
                rate(lambda h: h['m']['t30']), len(Gg), rate(lambda h: h['m']['surv10']), rate(lambda h: bool(h['m']['scaled20']))]
    for r in mine_led:
        x = L[(r['chart'], str(r['d0']))]
        v = day_odds(r['a'], r['grade'], r['d0'])
        for col, val in zip(['dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10', 'dayScaled20'], v):
            C.add(f"ledger {r['chart']} {r['d0']}", col + ' (odds on the day, not displayed)', x[col], val, 'odds-on-the-day column')

    # ---------------------------------------------------------------- grade stats (grade_odds + ledger grade columns)
    def gstats(Gr):
        n = len(Gr)
        return dict(n=n, reach10=rnd(F(100 * sum(r['m']['r10'] for r in Gr), n)), surv10=rnd(F(100 * sum(r['m']['surv10'] for r in Gr), n)),
                    reach20=rnd(F(100 * sum(r['m']['r20'] for r in Gr), n)), t30=rnd(F(100 * sum(r['m']['t30'] for r in Gr), n)),
                    medDip=rnd(median([r['m']['dd'] for r in Gr]), 1),
                    sample=f"{min(r['d0'] for r in Gr)} to {max(r['d0'] for r in Gr)}")
    GS = {}
    for a in ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            Gr = [r for r in mine_led if r['a'] == a and r['grade'] == g]
            GS[(a, g)] = gstats(Gr)
    for go in feed['grade_odds']:
        loc = f"feed grade_odds {go['asset']} {go['grade']}"
        if go['grade'] in ('diamond or prime dot', 'no diamond or prime dot'):
            want = go['grade'] == 'diamond or prime dot'
            Gr = [r for r in mine_led if r['a'] == 'ETH' and (r['prime'] or r['dis']) == want]
            s = gstats(Gr)
        elif (go['asset'], go['grade']) in GS:
            s = GS[(go['asset'], go['grade'])]
        else:
            tot = sum(x['past_trades'] for x in feed['grade_odds'] if x['grade'] in ('HTF divergence', 'no HTF divergence'))
            C.add(loc, 'HTF divergence pair sums to ETH total (membership is lens logic, not recomputed)', tot,
                  sum(GS[('ETH', g)]['n'] for g in ('A+', 'A', 'B', 'C')), 'HTF groups do not partition ETH')
            continue
        C.add(loc, 'past_trades', go['past_trades'], s['n'], 'sample size')
        C.add(loc, 'rose10_within60d_pct', go['rose10_within60d_pct'], s['reach10'], 'share rose 10%')
        C.add(loc, 'rose10_never_fell25_within60d_pct', go['rose10_never_fell25_within60d_pct'], s['surv10'], 'share rose 10% never fell 25.3%')
        C.add(loc, 'rose20_within60d_pct', go['rose20_within60d_pct'], s['reach20'], 'share rose 20%')
        C.add(loc, 'median_deepest_dip_pct', go['median_deepest_dip_pct'], s['medDip'], 'median deepest dip')
        C.add(loc, 'sample', go['sample'], s['sample'], 'first-to-last')
    for r in mine_led:
        x = L[(r['chart'], str(r['d0']))]; s = GS[(r['a'], r['grade'])]
        loc = f"ledger {r['chart']} {r['d0']}"
        C.add(loc, 'gradeReach20 (not displayed)', x['gradeReach20'], s['reach20'], 'grade column')
        C.add(loc, 'gradeTouched30 (not displayed)', x['gradeTouched30'], s['t30'], 'grade column')
        C.add(loc, 'gradeMedDrawdown (not displayed)', x['gradeMedDrawdown'], s['medDip'], 'grade column')

    # ---------------------------------------------------------------- 3. if_it_misses
    MI = {}
    for a in ASSETS:
        for g in ('A+', 'A', 'B', 'C'):
            Gr = [r for r in mine_led if r['a'] == a and r['grade'] == g]
            ms = [r for r in Gr if not r['m']['r10']]
            b = [r['m']['up'] for r in ms]
            MI[(a, g)] = dict(signals=len(Gr), misses=len(ms), up_first=sum(1 for v in b if v > 0),
                              median_peak_pct=rnd(median(b), 1) if b else None, mean_peak_pct=rnd(sum(b) / len(b), 1) if b else None,
                              peaked_5_or_more=sum(1 for v in b if v >= 5), peaked_10_or_more=sum(1 for v in b if v >= 10),
                              median_worst_drop_pct=rnd(median([r['m']['dd'] for r in ms]), 1) if ms else None,
                              median_day60_pct=rnd(median([r['m']['ret'] for r in ms]), 1) if ms else None)
    for mi in feed['if_it_misses']:
        mine = MI[(mi['asset'], mi['grade'])]
        for k in mine:
            C.add(f"feed if_it_misses {mi['asset']} {mi['grade']}", k, mi[k], mine[k], 'misses figure')

    # ---------------------------------------------------------------- 4. odds_fade (ETH walk-forward tier)
    fade, tier_note = odds_fade(S, now)
    of = feed['odds_fade']
    C.add('feed odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70)
    for kind, key in (('early_dip', 'band'), ('day10', 'check')):
        mine = fade[kind]
        C.add(f'feed odds_fade {kind}', 'row set', '|'.join(x[key] for x in of[kind]), '|'.join(x['band'] for x in mine), 'bands with n>=5')
        for x in of[kind]:
            y = next((z for z in mine if z['band'] == x[key]), None)
            if y is None: continue
            loc = f'feed odds_fade {kind} {x[key]}'
            C.add(loc, 'past_trades', x['past_trades'], y['n'], 'tier set / window')
            C.add(loc, 'rose10 (days 11-60)', x['rose10_within60d_pct'], y['r10'], 'share rose 10% after day 10')
            C.add(loc, 'rose20 (days 11-60)', x['rose20_within60d_pct'], y['r20'], 'share rose 20% after day 10')
            C.add(loc, 'edge', x['edge'], 'intact' if y['r10'] >= 70 else 'gone', 'edge vs 70%')

    # ---------------------------------------------------------------- 5. cards
    mine_cards = {}
    def build_card(a, tf, lens_codes, g, pool, wording):
        Cf = [r for r in pool if r['a'] == a and r['tf'] == tf]
        ex = [r for r in Cf if r['lenses'] == lens_codes]
        sg = [r for r in Cf if r['grade'] == g]
        ag = [r for r in pool if r['a'] == a and r['grade'] == g]
        if len(ex) >= 15: rule, Gr = 'exact', ex
        elif len(sg) >= 15: rule, Gr = 'chart+grade', sg
        else: rule, Gr = 'asset+grade', ag
        return card_figs(S, Gr, rule, len(ex), len(sg))

    def compare_card(loc, c, mc):
        C.add(loc, 'sample rule', sample_rule(c['sample']), mc['rule'], 'sample rule chosen')
        C.add(loc, 'sample text count', sample_n(c['sample']), mc['n'], 'sample size in text')
        if mc['rule'] != 'exact':
            C.add(loc, 'sample text: count of the narrower group', sample_sub(c['sample']), mc['nex'] if mc['rule'] == 'chart+grade' else mc['nsg'], 'narrower-group count in text')
        C.add(loc, 'past_trades', c['past_trades'], mc['n'], 'sample size')
        for f, k in (('rose10_never_fell25_within60d_pct', 'surv10'), ('beat_normal_move_pct', 'scaled20'), ('rose20_within60d_pct', 'reach20'),
                     ('rose10_within60d_pct', 'reach10'), ('typical_biggest_rise_pct', 'best'), ('typical_dip_before_rise_pct', 'dbh'),
                     ('typical_deepest_dip_pct', 'dd'), ('typical_biggest_rise_exact_pct', 'best6'), ('typical_dip_before_rise_exact_pct', 'dbh6'),
                     ('typical_deepest_dip_exact_pct', 'dd6'), ('fell30_within60d_pct', 't30'), ('typical_day_first_rose10', 'd10'),
                     ('typical_day_first_rose20', 'd20'), ('typical_day_of_60d_high', 'dhigh'), ('typical_day_of_deepest_dip', 'dlow')):
            if f in c:
                C.add(loc, f, c[f], mc[k], k)
            else:
                C.add(loc, f + ' (field present)', 'missing', 'expected', 'field missing from card')
        C.add(loc, 'before_2022.past_trades', c['before_2022']['past_trades'], mc['nOld'], 'era split')
        C.add(loc, 'before_2022.pct', c['before_2022']['rose10_never_fell25_within60d_pct'], mc['sOld'], 'era split')
        C.add(loc, 'since_2022.past_trades', c['since_2022']['past_trades'], mc['nNew'], 'era split')
        C.add(loc, 'since_2022.pct', c['since_2022']['rose10_never_fell25_within60d_pct'], mc['sNew'], 'era split')
        for row, mine in zip(c['if_it_falls_first'], mc['ladder']):
            C.add(loc, f"ladder {row['fell_pct']}% n", row['past_trades'], mine['n'], 'ladder')
            C.add(loc, f"ladder {row['fell_pct']}% still rose 10%", row['still_rose10_pct'], mine['ok'], 'ladder')
            C.add(loc, f"ladder {row['fell_pct']}% went on to fall 25.3%", row['went_on_to_fall25_pct'], mine['liq'], 'ladder')

    pool_now = mine_led
    # forming cards (REPLAY)
    fcards = forming(S, now)
    C.add('feed cards', 'forming card set', '|'.join(sorted(c['signal_id'] for c in feed['cards'])), '|'.join(sorted(fcards)), 'forming lows on charts')
    for c in feed['cards']:
        a, tf = c['asset'], c['timeframe']; loc = f"feed card {c['signal_id']}"
        lens = set() if c['confirmations'] == 'none' else {RPLAIN.get(x, '?' + x) for x in c['confirmations'].split('; ')}
        C.add(loc, 'grade consistent with confirmations count', c['grade'], grade_of_count(len(lens)), 'grade vs lenses')
        mc = build_card(a, tf, lens, c['grade'], pool_now, 'past'); mine_cards[c['signal_id']] = dict(mc, kind='forming')
        compare_card(loc, c, mc)
        fm = fcards.get(c['signal_id'])
        if fm:
            C.add(loc, 'low_date', c['low_date'], fm['low_date'], 'trough date'); C.add(loc, 'confirms_on', c['confirms_on'], fm['confirms_on'], 'confirmation close date')
            C.add(loc, 'bars_to_confirm', c['bars_to_confirm'], fm['need'], 'bars to confirm')
            C.add(loc, 'price_now', c['price_now'], fm['price_now'], 'last close')
            C.add(loc, 'must_close_above', c['must_close_above'], fm['kill'], 'kill close')
            mine_cards[c['signal_id']].update(fm)
    # open signals and their cards
    osig = open_signals(S, now)
    C.add('feed open_signals', 'id set', '|'.join(sorted(o['signal_id'] for o in feed['open_signals'])), '|'.join(sorted(osig)), 'open-signal membership')
    for o in feed['open_signals']:
        loc = f"feed open_signal {o['signal_id']}"; mo = osig.get(o['signal_id'])
        if not mo: continue
        for f in ('entry_date', 'entry_close', 'days_elapsed', 'day10_pct', 'day30_pct', 'day60_pct', 'best_so_far_pct', 'worst_so_far_pct', 'tags'):
            C.add(loc, f, o[f], mo[f], f)
        c = o['card']
        if not c:
            C.add(loc, 'card present', 'missing', 'present', 'no card'); continue
        a, tf = o['chart'].split()
        lens = set() if o['confirmations'] == '-' else set(o['confirmations'].split(' + '))
        clens = set() if c['confirmations'] == 'none' else {RPLAIN.get(x, '?' + x) for x in c['confirmations'].split('; ')}
        C.add(loc + ' card', 'confirmations match open signal', '+'.join(sorted(clens)), '+'.join(sorted(lens)), 'card lenses vs open signal')
        C.add(loc + ' card', 'grade', c['grade'], o['grade'], 'card grade vs open signal')
        C.add(loc + ' card', 'low_date', c['low_date'], mo['low_date'], 'trough date')
        C.add(loc + ' card', 'confirms_on', c['confirms_on'], o['entry_date'], 'confirmation date')
        C.add(loc + ' card', 'price_now (= entry close)', c['price_now'], mo['entry_close'], 'entry close')
        mc = build_card(a, tf, lens, o['grade'], pool_now, 'past'); compare_card(loc + ' card', c, mc)
        mine_cards[o['signal_id']] = dict(mc, kind='open', **mo)
    # example card
    xc = feed['example_card']
    ex_sig = next(r for r in rows if r['chart'] == 'ETH 2D' and r['d0'] == dt.date(2024, 9, 22))
    known = [r for r in mine_led if r['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
    exl = L.get(('ETH 2D', '2024-09-22'))
    C.add('feed example_card', 'example signal exists (gated, ETH 2D, confirmed 2024-09-22)', 'yes', 'yes' if ex_sig and exl else 'no')
    C.add('feed example_card', 'entry_close', xc['entry_close'], rnd(ex_sig['entry'], 2), 'entry close')
    C.add('feed example_card', 'low_date', xc['low_date'], str(ex_sig['tdate']), 'trough date')
    C.add('feed example_card', 'confirms_on', xc['confirms_on'], str(ex_sig['d0']), 'confirmation date')
    C.add('feed example_card', 'grade = ledger grade', xc['grade'], exl['grade'], 'grade')
    xl = {RPLAIN.get(x, '?' + x) for x in xc['confirmations'].split('; ')}
    C.add('feed example_card', 'confirmations = ledger lenses', '+'.join(sorted(xl)), '+'.join(sorted(L[('ETH 2D', '2024-09-22')]['lenses'].split(' + '))), 'lenses')
    mc = build_card('ETH', '2D', xl, xc['grade'], known, 'by then')
    compare_card('feed example_card', xc, mc)
    mine_cards['example'] = dict(mc, kind='example', entry=ex_sig['entry'], d0=str(ex_sig['d0']))
    # example misses known by then (page computes them from the ledger)
    kn = [r for r in known if r['a'] == 'ETH' and r['grade'] == 'A+']
    kms = [r for r in kn if not r['m']['r10']]
    mine_cards['example']['misses_known'] = dict(signals=len(kn), misses=len(kms), up_first=sum(1 for r in kms if r['m']['up'] > 0),
                                                 median_peak=rnd(median([r['m']['up'] for r in kms]), 1) if kms else None,
                                                 worst=rnd(median([r['m']['dd'] for r in kms]), 1) if kms else None,
                                                 day60=rnd(median([r['m']['ret'] for r in kms]), 1) if kms else None)
    kall = [r for r in known if r['a'] == 'ETH']; kallm = [r for r in kall if not r['m']['r10']]
    mine_cards['example']['misses_known_allgrades'] = dict(signals=len(kall), misses=len(kallm), up_first=sum(1 for r in kallm if r['m']['up'] > 0),
                                                           median_peak=rnd(median([r['m']['up'] for r in kallm]), 1))

    # ---------------------------------------------------------------- 7. past_paths
    PP = {}
    for a in ASSETS:
        Gr = [r for r in mine_led if r['a'] == a and r['grade'] == 'A+']
        paths = []
        for r in Gr:
            day = S.day[a]; p = [F(0)]
            for k in range(1, 61):
                j = day.pos.get(r['d0'] + dt.timedelta(days=k))
                p.append(pct(day.c[j], r['entry']))
            paths.append(p)
        PP[a] = dict(n=len(Gr), days=[dict(q25=rnd(quantile([p[d] for p in paths], F(1, 4)), 1), med=rnd(quantile([p[d] for p in paths], F(1, 2)), 1),
                                            q75=rnd(quantile([p[d] for p in paths], F(3, 4)), 1)) for d in range(61)])
    for pp in feed['past_paths']:
        a = pp['asset']; C.add(f'feed past_paths {a}', 'signals', pp['signals'], PP[a]['n'], 'A+ count')
        C.add(f'feed past_paths {a}', 'grade', pp['grade'], 'A+')
        for d in pp['days']:
            m = PP[a]['days'][d['day']]
            for f, k in (('q25_pct', 'q25'), ('median_pct', 'med'), ('q75_pct', 'q75')):
                C.add(f'feed past_paths {a} day {d["day"]}', f, d[f], m[k], 'path quantile')

    # ---------------------------------------------------------------- 10/9 labels in the feed
    for c in feed['cards'] + [o['card'] for o in feed['open_signals'] if o['card']] + [xc]:
        C.add(f"feed card {c['signal_id']} label", 'says computed signal / not a track record',
              'yes' if 'not a strategy return or a track record' in c['label'] else 'no', 'yes', 'label')
        C.add(f"feed card {c['signal_id']} sample wording", 'uses "signals" not "trades"', 'yes' if 'trade' not in c['sample'] else 'no', 'yes', 'wording')

    # mine values for the page
    def ser(x):
        if isinstance(x, F): return float(x)
        if isinstance(x, (dt.date,)): return str(x)
        if isinstance(x, set): return sorted(x)
        if isinstance(x, dict): return {k: ser(v) for k, v in x.items() if k not in ('w', 'members')}
        if isinstance(x, list): return [ser(v) for v in x]
        return x
    ledger_mine = [dict(chart=r['chart'], asset=r['a'], entry=str(r['d0']), grade=r['grade'], entryPrice=rnd(r['entry'], 2), entry_exact=str(r['entry']),
                        best=rnd(r['m']['up'], 1), dd=rnd(r['m']['dd'], 1), ret=rnd(r['m']['ret'], 1), dpk=r['m']['dpk'], r10=r['m']['r10'], r20=r['m']['r20'],
                        best_exact=str(r['m']['up']), dd_exact=str(r['m']['dd']), ret_exact=str(r['m']['ret'])) for r in mine_led]
    mine = dict(GS={f'{a} {g}': v for (a, g), v in GS.items()}, MI={f'{a} {g}': v for (a, g), v in MI.items()}, fade=fade,
                cards=ser(mine_cards), open=ser(osig), PP=PP, ledger=ledger_mine, tier=tier_note)
    json.dump(ser(mine), open(os.path.join(OUT, f'mine_{tag}.json'), 'w'), default=str, indent=0)
    json.dump(C.rows, open(os.path.join(OUT, f'checks_{tag}.json'), 'w'), indent=0)
    bad = [r for r in C.rows if r['ok'] != 'yes']
    print(tag, len(C.rows), 'checks', len(bad), 'disagreements')
    for r in bad[:80]: print('  ', r)


def sample_rule(t):
    if 'exactly the same confirmations' in t and 'too few' not in t: return 'exact'
    if 'graded' in t: return 'chart+grade'
    if 'across all' in t: return 'asset+grade'
    return '?'


def sample_n(t):
    m = re.match(r'all (\d+) ', t); return int(m.group(1)) if m else None


def sample_sub(t):
    m = re.search(r'\((?:only (\d+)|none) had', t)
    if m: return int(m.group(1)) if m.group(1) else 0
    m = re.search(r'alone ha(?:s|d) only (\d+)', t)
    return int(m.group(1)) if m else None


def card_figs(S, Gr, rule, nex, nsg):
    n = len(Gr)
    P = lambda k: rnd(F(100 * k, n)) if n else None
    sc = [r['m']['scaled20'] for r in Gr if r['m']['scaled20'] is not None]
    old = [r for r in Gr if r['d0'] < SPLIT]; new = [r for r in Gr if r['d0'] >= SPLIT]
    sv = lambda X: rnd(F(100 * sum(r['m']['surv10'] for r in X), len(X))) if X else None
    lad = []
    amb = 0
    for th in (5, 10, 15, 20):
        hit = ok = liq = 0
        for r in Gr:
            res, a_ = ladder(S.day[r['a']], r['d0'], r['entry'], r['m']['w'], th); amb += a_
            if res is None: continue
            hit += 1; ok += res == 'ok'; liq += res == 'liq'
        lad.append(dict(n=hit, ok=rnd(F(100 * ok, hit)) if hit else None, liq=rnd(F(100 * liq, hit)) if hit else None))
    t10 = [r['m']['t10'] for r in Gr if r['m']['t10'] is not None]; t20 = [r['m']['t20'] for r in Gr if r['m']['t20'] is not None]
    med = lambda xs: rnd(F(median(xs))) if xs else None
    return dict(rule=rule, n=n, nex=nex, nsg=nsg, surv10=P(sum(r['m']['surv10'] for r in Gr)), scaled20=rnd(F(100 * sum(sc), len(sc))) if sc else None,
                reach20=P(sum(r['m']['r20'] for r in Gr)), reach10=P(sum(r['m']['r10'] for r in Gr)),
                best=rnd(median([r['m']['up'] for r in Gr]), 1), dbh=rnd(median([r['m']['ddpk'] for r in Gr]), 1), dd=rnd(median([r['m']['dd'] for r in Gr]), 1),
                best6=rnd(median([r['m']['up'] for r in Gr]), 6), dbh6=rnd(median([r['m']['ddpk'] for r in Gr]), 6), dd6=rnd(median([r['m']['dd'] for r in Gr]), 6),
                best_exact=str(median([r['m']['up'] for r in Gr])), dbh_exact=str(median([r['m']['ddpk'] for r in Gr])), dd_exact=str(median([r['m']['dd'] for r in Gr])),
                t30=P(sum(r['m']['t30'] for r in Gr)), nOld=len(old), sOld=sv(old), nNew=len(new), sNew=sv(new), ladder=lad, ladder_ambiguous_days=amb,
                d10=med(t10), d20=med(t20), dhigh=med([r['m']['dpk'] for r in Gr]), dlow=med([r['m']['ddday'] for r in Gr]),
                members=[(r['chart'], str(r['d0'])) for r in Gr])


def forming(S, now):
    """Forming (provisional) lows on every chart now: a CT pivot low still waiting on right-hand bars."""
    out = {}
    for (a, tf), b in S.bars.items():
        ct = rsi(b.cf, 14); n = len(ct)
        for back in (1, 2, 3):
            ti = n - 1 - back
            v = ct[ti]
            if v is None or any(ct[j] is None or ct[j] <= v for j in range(ti - 3, ti)): continue
            if any(ct[j] < v for j in range(ti + 1, n)): continue
            if not S.gate(now.date()): continue
            need = 3 - ((n - 1) - ti)
            step = int(stt.median([(b.date[i] - b.date[i - 1]).days for i in range(n - 20, n)]))
            conf_open = b.date[-1] + dt.timedelta(days=step * need)
            d0 = conf_open + dt.timedelta(days=step - 1)
            kill = None
            if need in (0, 1):
                base = b.cf[:-1] if need == 0 else b.cf[:]
                lo, hi = b.cf[-1] * 0.5, b.cf[-1] * 1.5
                for _ in range(200):
                    mid = (lo + hi) / 2
                    if rsi(base + [mid], 14)[-1] <= v: lo = mid
                    else: hi = mid
                kill = rnd(F(lo), 2)
            out[f'{a}-{tf}-{d0}'] = dict(low_date=str(b.date[ti]), confirms_on=str(d0), need=need, price_now=rnd(b.c[-1], 2), kill=kill,
                                         low_price=float(b.l[ti]), chart=f'{a} {tf}')
            break
    return out


def open_signals(S, now):
    today = now.date(); out = {}
    for (a, tf), lst in S.sig.items():
        if tf not in GRADED: continue
        for s in lst:
            if s['d0'] is None: continue
            el = (today - s['d0']).days
            if not 0 <= el <= 60: continue
            if s['m'] is not None: continue
            day = S.day[a]; e = s['entry']
            win = []
            for k in range(1, 61):
                j = day.pos.get(s['d0'] + dt.timedelta(days=k))
                if j is not None and closed_by(day.date[j], now): win.append((k, j))
            mark = lambda m: next((rnd(pct(day.c[j], e), 1) for k, j in win if k == m), None)
            out[f'{a}-{tf}-{s["d0"]}'] = dict(entry_date=str(s['d0']), entry_close=rnd(e, 2), entry_exact=float(e), days_elapsed=el, day10_pct=mark(10), day30_pct=mark(30),
                                               day60_pct=mark(60), best_so_far_pct=rnd(pct(max(day.h[j] for k, j in win), e), 1) if win else None,
                                               worst_so_far_pct=rnd(pct(min(day.l[j] for k, j in win), e), 1) if win else None, tags=s['tags'],
                                               low_date=str(s['tdate']), chart=f'{a} {tf}', conf_open=str(s['edate_open']))
    return out


# ------------------------------------------------------------------ odds fade
TAGS = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]


def zser(ct):
    out, z = [], None
    for v in ct:
        if v is None: out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v)); out.append(z)
    return out


def odds_fade(S, now, strict=False):
    """ETH walk-forward tier (as it stood on 1 Jan of the current year), then the early-dip / day-10 tables on daily candles."""
    rows = []
    for tf in TFS:
        b = S.bars[('ETH', tf)]; ct = rsi(b.cf, 14); zm = zser(ct)
        for s in S.sig[('ETH', tf)]:
            tg = {s['bk'], 'any trough'}
            if s['dis']: tg |= {'diamond', 'filled' if s['filled'] else 'hollow'}
            if s['prime']: tg.add('prime dot')
            if s['dis'] and s['prime']: tg.add('diamond+dot')
            if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: tg.add('zone-exit B')
            s['tg'] = tg
            # tier win: chart bars, close at the end of the 60-day window (from the confirmation bar's open date) above entry
            ei = s['ei']; end = b.date[ei] + dt.timedelta(days=60)
            if b.date[-1] < end: continue
            j = ei + 1; last = None
            while j < len(b.date) and b.date[j] <= end:
                last = b.c[j]; j += 1
            if last is None: continue
            rows.append(dict(chart=f'ETH {tf}', tg=tg, d=b.date[ei], win=last > s['entry'], s=s, wend=(b.date[j] - dt.timedelta(days=1)) if j < len(b.date) else b.date[j - 1] + dt.timedelta(days=99)))
    anchor = dt.date(now.year, 1, 1)
    keep = []
    for tf in TFS:
        for t in TAGS:
            sub = [r for r in rows if r['chart'] == f'ETH {tf}' and t in r['tg'] and r['d'] < anchor and (not strict or r['wend'] < anchor)]
            if len(sub) >= 8 and F(100 * sum(r['win'] for r in sub), len(sub)) >= 70:
                keep.append((f'ETH {tf}', t))
    pool = []
    for tf in TFS:
        for s in S.sig[('ETH', tf)]:
            if not any(f'ETH {tf}' == k[0] and k[1] in s['tg'] for k in keep): continue
            if s['d0'] is None: continue
            w = window(S.day['ETH'], s['d0'], now)
            if w is None: continue
            day = S.day['ETH']; e = s['entry']
            lo10 = min(day.l[j] for k, j in w if k <= 10); hi_after = max(day.h[j] for k, j in w if k > 10)
            k10 = next((j for k, j in w if k == 10), None)
            pool.append(dict(dip=pct(lo10, e), mfe=pct(hi_after, e), cl10=None if k10 is None else pct(day.c[k10], e), chart=f'ETH {tf}', d0=s['d0']))
    bands = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
    early = []
    for hi, lo, lab in bands:
        g = [p for p in pool if lo < p['dip'] <= hi]
        if len(g) < 5: continue
        early.append(dict(band=lab, n=len(g), r10=rnd(F(100 * sum(p['mfe'] >= 10 for p in g), len(g))), r20=rnd(F(100 * sum(p['mfe'] >= 20 for p in g), len(g)))))
    d10 = []
    for lab, f in (('green on day 10', lambda p: p['cl10'] >= 0), ('red on day 10', lambda p: p['cl10'] < 0)):
        g = [p for p in pool if p['cl10'] is not None and f(p)]
        if len(g) < 5: continue
        d10.append(dict(band=lab, n=len(g), r10=rnd(F(100 * sum(p['mfe'] >= 10 for p in g), len(g))), r20=rnd(F(100 * sum(p['mfe'] >= 20 for p in g), len(g)))))
    return dict(early_dip=early, day10=d10, keep=keep, pool_n=len(pool)), dict(keep=keep)


if __name__ == '__main__':
    main(*sys.argv[1:4])
