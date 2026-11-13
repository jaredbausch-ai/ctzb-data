"""Compare one state's feed and ledger against my own recomputation. Writes check rows."""
import csv, json, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mycalc import *


def norm(v):
    if v is None or v == '':
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return v
    return v


class Checks:
    def __init__(self, state):
        self.state, self.rows = state, []

    def c(self, loc, label, shown, yours, cause=''):
        ok = norm(shown) == norm(yours)
        self.rows.append(dict(state=self.state, location=loc, label=label, shown='' if shown is None else str(shown),
                              yours='' if yours is None else str(yours), ok='yes' if ok else 'NO', cause='' if ok else cause))
        return ok


def yn(b):
    return 'yes' if b else 'no'


def check_state(sdir, now, name, S=None):
    S = S or State(sdir, now)
    K = Checks(name)
    feed = json.load(open(os.path.join(sdir, 'feed', 'ctzb_feed.json')))
    today = S.today
    # ---------------------------------------------------------------- top level
    K.c('feed', 'schema_version', feed.get('schema_version'), 6)
    K.c('feed', 'posting_bar_pct', feed.get('posting_bar_pct'), 70)
    K.c('feed', 'scored_as_of', feed.get('scored_as_of'), str(today))
    K.c('feed', 'generated_at (clock)', feed.get('generated_at'), now.strftime('%Y-%m-%dT%H:%M:%SZ'))
    K.c('feed', 'market_regime (gate on today)', feed.get('market_regime'), 'Bullish' if S.gate(today) else 'Bearish')
    K.c('feed', 'cards_withheld', feed.get('cards_withheld'), False)
    of = S.odds_fade()
    K.c('feed', 'trades_a_year', feed.get('trades_a_year'), f"{of['per_year']} on average" if of['per_year'] is not None else '—')
    K.c('feed', 'signals_a_year', feed.get('signals_a_year'), feed.get('trades_a_year'))
    # every card, print, open signal and grade row carries the computed-signal label (FEED_SPEC rules)
    lab_items = [('cards', x) for x in feed.get('cards', [])] + [('prints', x) for x in feed.get('prints', [])] + \
        [('open_signals', x) for x in feed.get('open_signals', [])] + [('open_signals.card', x['card']) for x in feed.get('open_signals', []) if x.get('card')] + \
        [('grade_odds', x) for x in feed.get('grade_odds', [])] + ([('example_card', feed['example_card'])] if feed.get('example_card') else [])
    for where, x in lab_items:
        lb = x.get('label') or ''
        K.c(f'labels {where} {x.get("signal_id") or x.get("asset", "")} {x.get("grade", "")}', 'label: computed signal, not a fill, entry quality only',
            all(w in lb for w in ('not a fill', 'Entry quality only')), True, 'label wording')
    # ---------------------------------------------------------------- ledger
    pl = S.pl
    mine = {(s['ch'], str(s['d0'])): s for s in S.led}
    for k in sorted(set(pl) | set(mine)):
        K.c('ledger', f'membership {k[0]} {k[1]}', 'present' if k in pl else 'absent', 'present' if k in mine else 'absent', 'membership')
    for k in sorted(set(pl) & set(mine)):
        r, s = pl[k], mine[k]; m = s['m']; loc = f'ledger {k[0]} {k[1]}'
        gr = S.grades[(s['a'], s['grade'])]
        exp = dict(asset=s['a'], low=str(s['tdate']), entryPrice=disp(s['e'], 2), tags=s['tags'],
                   gradeReach20=gr.get('reach20'), gradeTouched30=gr.get('touched30'), gradeMedDrawdown=gr.get('medDip'),
                   reached20=yn(m['r20']), touched30=yn(m['t30']), bestMove=r6(m['up']), maxDrawdown=r6(m['dd']),
                   dipBeforeHigh=r6(m['ddpk']), return60d=r6(m['ret']), daysToHigh=m['dpk'], year=s['d0'].year,
                   reached10=yn(m['r10']), reached15=yn(m['r15']), surv10=yn(m['surv10']),
                   scaled20='' if m['sc'] is None else yn(m['sc']))
        exp.update(S.day_odds(s))
        for f, v in exp.items():
            K.c(loc, f, r[f], v)
    # ---------------------------------------------------------------- grade_odds
    go = {(g['asset'], g['grade']): g for g in feed.get('grade_odds', [])}
    for key, rec in S.grades.items():
        g = go.get(key); loc = f'grade_odds {key[0]} {key[1]}'
        if g is None:
            K.c(loc, 'row present', 'absent', 'present', 'missing row'); continue
        K.c(loc, 'past_trades', g['past_trades'], rec['n']); K.c(loc, 'past_signals', g.get('past_signals'), rec['n'])
        if rec['n']:
            for f, mk in (('rose10_within60d_pct', 'reach10'), ('rose10_never_fell25_within60d_pct', 'surv10'),
                          ('rose20_within60d_pct', 'reach20'), ('median_deepest_dip_pct', 'medDip'), ('sample', 'sample')):
                K.c(loc, f, g[f], rec[mk])
    # ---------------------------------------------------------------- if_it_misses
    im = {(m['asset'], m['grade']): m for m in feed.get('if_it_misses', [])}
    expected_keys = set()
    for a in ASSETS:
        if not any(s['a'] == a and s['grade'] == 'A+' for s in S.led):
            continue
        for g in ('A+', 'A', 'B', 'C'):
            G = [s for s in S.led if s['a'] == a and s['grade'] == g]
            if not G:
                continue
            expected_keys.add((a, g))
            mm = S.misses(G); r = im.get((a, g)); loc = f'if_it_misses {a} {g}'
            if r is None:
                K.c(loc, 'row present', 'absent', 'present', 'missing row'); continue
            for f, v in (('signals', mm['signals']), ('misses', mm['misses']), ('up_first', mm['up_first']),
                         ('median_peak_pct', mm['median_peak']), ('mean_peak_pct', mm['mean_peak']),
                         ('peaked_5_or_more', mm['p5']), ('peaked_10_or_more', mm['p10']),
                         ('median_worst_drop_pct', mm['worst']), ('median_day60_pct', mm['d60'])):
                K.c(loc, f, r[f], v)
    for k in set(im) - expected_keys:
        K.c(f'if_it_misses {k}', 'row present', 'present', 'absent', 'extra row')
    exG = [s for s in S.led if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= EX_D0]
    xm = feed.get('example_if_it_misses')
    if exG:
        mm = S.misses(exG)
        if xm is None:
            K.c('example_if_it_misses', 'present', 'absent', 'present', 'missing')
        else:
            for f, v in (('signals', mm['signals']), ('misses', mm['misses']), ('up_first', mm['up_first']),
                         ('median_peak_pct', mm['median_peak']), ('median_worst_drop_pct', mm['worst']),
                         ('median_day60_pct', mm['d60'])):
                K.c('example_if_it_misses', f, xm[f], v)
    else:
        K.c('example_if_it_misses', 'present', 'absent' if xm is None else 'present', 'absent')
    # ---------------------------------------------------------------- past paths
    pp = {p['asset']: p for p in feed.get('past_paths', [])}
    for a in ASSETS:
        G = [s for s in S.led if s['a'] == a and s['grade'] == 'A+']
        if not G:
            K.c(f'past_paths {a}', 'present', 'present' if a in pp else 'absent', 'absent'); continue
        P = S.paths(G); f = pp.get(a)
        if f is None:
            K.c(f'past_paths {a}', 'present', 'absent', 'present', 'missing'); continue
        K.c(f'past_paths {a}', 'signals', f['signals'], P['n'])
        for d, dd in zip(f['days'], P['days']):
            for fk, mk in (('day', 'day'), ('q25_pct', 'q25'), ('median_pct', 'med'), ('q75_pct', 'q75')):
                K.c(f'past_paths {a} day {dd["day"]}', fk, d[fk], dd[mk])
    xp = feed.get('example_past_paths')
    if exG:
        P = S.paths(exG)
        if xp is None:
            K.c('example_past_paths', 'present', 'absent', 'present', 'missing')
        else:
            K.c('example_past_paths', 'signals', xp['signals'], P['n'])
            for d, dd in zip(xp['days'], P['days']):
                for fk, mk in (('day', 'day'), ('q25_pct', 'q25'), ('median_pct', 'med'), ('q75_pct', 'q75')):
                    K.c(f'example_past_paths day {dd["day"]}', fk, d[fk], dd[mk])
    else:
        K.c('example_past_paths', 'present', 'absent' if xp is None else 'present', 'absent')
    # ---------------------------------------------------------------- odds fade
    o = feed.get('odds_fade') or {}
    K.c('odds_fade', 'tier_fixed_on', o.get('tier_fixed_on'), of['tier_fixed_on'])
    K.c('odds_fade', 'posting_bar_pct', o.get('posting_bar_pct'), 70)
    tday = dt.date.fromisoformat(of['tier_fixed_on'])
    K.c('odds_fade', 'sample names the tier date', f"fixed on {tday.day} {tday:%b %Y}" in (o.get('sample') or ''), True)
    for lst, mine_l, key in (('early_dip', of['early'], 'band'), ('day10', of['day10'], 'check')):
        got = o.get(lst) or []
        K.c(f'odds_fade {lst}', 'rows (in order)', [x[key] for x in got], [x[key] for x in mine_l])
        gm = {x[key]: x for x in got}
        for x in mine_l:
            r = gm.get(x[key]); loc = f'odds_fade {lst} {x[key]}'
            if r is None:
                continue
            for f, v in (('past_trades', x['n']), ('past_signals', x['n']), ('rose10_after_day10_pct', x['r10']),
                         ('rose20_after_day10_pct', x['r20']), ('rose10_within60d_pct', x['r10']),
                         ('rose20_within60d_pct', x['r20']), ('edge', x['edge'])):
                K.c(loc, f, r.get(f), v)
    # ---------------------------------------------------------------- forming cards
    fcards = {c['signal_id']: c for c in feed.get('cards', [])}
    myform = {}
    allform = {}
    for a in ASSETS:
        for tf in TFS:
            f = S.forming(a, tf)
            if f:
                allform[(a, tf)] = f
                if tf in GRADED and f['gate']:
                    myform[f'{a}-{tf}-{f["d0"]}'] = f
    exp_ids = set()
    for sid, f in myform.items():
        c = fcards.get(sid)
        if c is None:
            # a card exists only with a non-empty sample; the grade is the pipeline's, so a missing card is checked for that only
            K.c(f'cards {sid}', 'card present', 'absent', 'present (unless its sample is empty)', 'missing card'); continue
        exp_ids.add(sid)
        check_card(K, S, c, f'cards {sid}', kind='forming', f=f)
    for sid in set(fcards) - set(myform):
        K.c(f'cards {sid}', 'card present', 'present', 'absent', 'extra card')
    # ---------------------------------------------------------------- open signals
    myopen = {}
    for a in ASSETS:
        for tf in GRADED:
            for s in S.ch[(a, tf)].sig:
                if s['d0'] is not None and 0 <= (today - s['d0']).days <= 60:
                    myopen[f'{a}-{tf}-{s["d0"]}'] = s
    fo = {o_['signal_id']: o_ for o_ in feed.get('open_signals', [])}
    for sid in sorted(set(fo) | set(myopen)):
        K.c(f'open_signals {sid}', 'listed', 'present' if sid in fo else 'absent', 'present' if sid in myopen else 'absent', 'membership')
    for sid in sorted(set(fo) & set(myopen)):
        o_, s = fo[sid], myopen[sid]; loc = f'open_signals {sid}'
        day = S.day[s['a']]
        win = day.closed_window(s['d0'], today)
        E = s['E']
        mark = lambda m_: next((disp((b['C'] / E - 1) * 100, 1) for k_, b in enumerate(win) if k_ + 1 == m_), None)
        K.c(loc, 'chart', o_['chart'], s['ch']); K.c(loc, 'entry_date', o_['entry_date'], str(s['d0']))
        K.c(loc, 'entry_close', o_['entry_close'], disp(s['e'], 2)); K.c(loc, 'tags', o_['tags'], s['tags'])
        K.c(loc, 'days_elapsed', o_['days_elapsed'], (today - s['d0']).days)
        K.c(loc, 'day10_pct', o_['day10_pct'], mark(10)); K.c(loc, 'day30_pct', o_['day30_pct'], mark(30))
        K.c(loc, 'day60_pct', o_['day60_pct'], mark(60))
        K.c(loc, 'best_so_far_pct', o_['best_so_far_pct'], disp((max(b['H'] for b in win) / E - 1) * 100, 1) if win else None)
        K.c(loc, 'worst_so_far_pct', o_['worst_so_far_pct'], disp((min(b['L'] for b in win) / E - 1) * 100, 1) if win else None)
        c = o_.get('card')
        if c is None:
            K.c(loc, 'card present', 'absent', 'present', 'live signal without a card'); continue
        cc = check_card(K, S, c, f'open_signals {sid} card', kind='open', s=s, grade=o_['grade'])
        K.c(loc, 'grade same as its card', o_['grade'], c['grade'])
        lvl = None if cc is None else cc.get('edge')
        K.c(loc, 'edge_level_pct', o_['edge_level_pct'], lvl)
        if cc is not None:
            if lvl == 0:
                stt = 'lost'
            else:
                stt = 'intact'
                for b in win:
                    if lvl is not None and b['L'] <= E * (1 + D(lvl) / 100):
                        stt = 'lost'; break
                    if b['H'] >= E * D('1.10'):
                        stt = 'rose10'; break
            K.c(loc, 'edge_status', o_['edge_status'], stt)
    # ---------------------------------------------------------------- example card
    xc = feed.get('example_card')
    exs = next((s for s in S.led if s['ch'] == 'ETH 2D' and s['d0'] == EX_D0), None)
    if exs is not None and S.today >= dt.date(2024, 11, 22):
        if xc is None:
            K.c('example_card', 'present', 'absent', 'present', 'missing example')
        else:
            check_card(K, S, xc, 'example_card', kind='example', s=exs, grade=xc['grade'])
            K.c('example_card', 'example', xc.get('example'), True)
    else:
        K.c('example_card', 'present', 'absent' if xc is None else 'present', 'absent')
    # ---------------------------------------------------------------- prints
    fp = {}
    for p in feed.get('prints', []):
        fp[(p['signal_id'], p['state'])] = p
    myp = {}
    for a in ASSETS:
        for tf in TFS:
            sig = [s for s in S.ch[(a, tf)].sig if s['d0'] is not None]
            for s in sig[-3:]:
                myp[(f'{a}-{tf}-{s["d0"]}', 'confirmed')] = dict(chart=s['ch'], low_date=str(s['tdate']), confirms_on=str(s['d0']),
                                                                 entry_close=disp(s['e'], 2), tags=s['tags'], note='regime on', provisional=False)
            f = allform.get((a, tf))
            if f:
                myp[(f'{a}-{tf}-{f["d0"]}', 'forming')] = dict(chart=f'{a} {tf}', low_date=str(f['tdate']), confirms_on=str(f['d0']),
                                                              entry_close=disp(f['price'], 2), tags=f['tags'],
                                                              note=('regime on' if f['gate'] else 'regime off') + f'; {f["need"]} bar(s) to confirm',
                                                              provisional=True)
    for k in sorted(set(fp) | set(myp)):
        K.c(f'prints {k[0]} {k[1]}', 'listed', 'present' if k in fp else 'absent', 'present' if k in myp else 'absent', 'membership')
    for k in sorted(set(fp) & set(myp)):
        for f, v in myp[k].items():
            K.c(f'prints {k[0]} {k[1]}', f, fp[k][f], v)
    return K, S, dict(myform=myform, myopen=myopen, exs=exs, of=of)


def check_card(K, S, c, loc, kind, f=None, s=None, grade=None):
    a, tf = c['asset'], c['timeframe']
    lens_txt = c['confirmations']
    lens = frozenset() if lens_txt in ('none', '-', '') else frozenset(UNPLAIN.get(x, x) for x in lens_txt.split('; '))
    if any(x not in PLAIN for x in lens):
        K.c(loc, 'confirmations decode', lens_txt, 'known lens words', 'unknown lens word')
    known = EX_D0 if kind == 'example' else None
    cc = S.card(a, tf, c['grade'], lens, known=known, example=(kind == 'example'))
    if kind == 'forming':
        K.c(loc, 'chart', c['chart'], f'{f["a"]} {f["tf"]}')
        K.c(loc, 'low_date', c['low_date'], str(f['tdate'])); K.c(loc, 'low_day', c['low_day'], str(f['low_day']))
        K.c(loc, 'confirms_on', c['confirms_on'], str(f['d0'])); K.c(loc, 'bars_to_confirm', c['bars_to_confirm'], f['need'])
        K.c(loc, 'must_close_above (rounded down)', c['must_close_above'], f['kill']['cent'] if f['kill'] else None)
        K.c(loc, 'price_now', c['price_now'], disp(f['price'], 2)); K.c(loc, 'entry_close', c['entry_close'], None)
    else:
        K.c(loc, 'chart', c['chart'], s['ch'])
        K.c(loc, 'low_date', c['low_date'], str(s['tdate'])); K.c(loc, 'low_day', c['low_day'], str(S.low_day(s['a'], s['tf'], s['tdate'])))
        K.c(loc, 'confirms_on', c['confirms_on'], str(s['d0'])); K.c(loc, 'bars_to_confirm', c['bars_to_confirm'], None)
        K.c(loc, 'must_close_above', c['must_close_above'], None)
        K.c(loc, 'price_now', c['price_now'], None if kind == 'example' else disp(S.day[a].bars[-1]['c'], 2))
        K.c(loc, 'entry_close', c['entry_close'], disp(s['e'], 2))
        K.c(loc, 'signal_id', c['signal_id'], f'{a}-{tf}-{s["d0"]}')
    K.c(loc, 'sample', c['sample'], cc['sample'])
    for fk in ('past_trades', 'past_signals'):
        K.c(loc, fk, c[fk], cc['n'])
    if not cc['n']:
        return cc
    for fk, mk in (('rose10_never_fell25_within60d_pct', 'surv10'), ('beat_normal_move_pct', 'scaled20'),
                   ('rose20_within60d_pct', 'reach20'), ('rose10_within60d_pct', 'reach10'),
                   ('typical_biggest_rise_pct', 'best'), ('typical_dip_before_rise_pct', 'dip'), ('typical_deepest_dip_pct', 'mx'),
                   ('typical_biggest_rise_exact_pct', 'bestX'), ('typical_dip_before_rise_exact_pct', 'dipX'),
                   ('typical_deepest_dip_exact_pct', 'maxX'), ('fell30_within60d_pct', 'touched30'),
                   ('typical_day_first_rose10', 'd10'), ('typical_day_first_rose20', 'd20'),
                   ('typical_day_of_60d_high', 'dHigh'), ('typical_day_of_deepest_dip', 'dLow')):
        K.c(loc, fk, c[fk], cc[mk])
    K.c(loc, 'before_2022.past_trades', c['before_2022']['past_trades'], cc['nOld'])
    K.c(loc, 'before_2022.rose10_never_fell25', c['before_2022']['rose10_never_fell25_within60d_pct'], cc['sOld'])
    K.c(loc, 'since_2022.past_trades', c['since_2022']['past_trades'], cc['nNew'])
    K.c(loc, 'since_2022.rose10_never_fell25', c['since_2022']['rose10_never_fell25_within60d_pct'], cc['sNew'])
    fe = c['from_entry']
    K.c(loc, 'from_entry.past_trades', fe['past_trades'], cc['fe']['n'])
    K.c(loc, 'from_entry.still_rose10_pct', fe['still_rose10_pct'], cc['fe']['ok'])
    K.c(loc, 'from_entry.went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], cc['fe']['liq'])
    K.c(loc, 'from_entry.still_rose10_exact_pct', fe['still_rose10_exact_pct'], cc['fe']['okx'])
    for r, mr in zip(c['if_it_falls_first'], cc['lad']):
        l2 = f'{loc} falls {mr["fell"]}%'
        K.c(l2, 'fell_pct', r['fell_pct'], mr['fell']); K.c(l2, 'past_trades', r['past_trades'], mr['n'])
        K.c(l2, 'still_rose10_pct', r['still_rose10_pct'], mr['ok']); K.c(l2, 'went_on_to_fall25_pct', r['went_on_to_fall25_pct'], mr['liq'])
        K.c(l2, 'still_rose10_exact_pct', r['still_rose10_exact_pct'], mr['okx'])
    # the rounded medians as the feed stores them, against the full-precision rounding too (informational)
    return cc


if __name__ == '__main__':
    sdir, now, name, out = sys.argv[1], dt.datetime.fromisoformat(sys.argv[2].replace('Z', '+00:00')), sys.argv[3], sys.argv[4]
    K, S, extra = check_state(sdir, now, name)
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
        w.writeheader(); w.writerows(K.rows)
    bad = [r for r in K.rows if r['ok'] != 'yes']
    print(name, len(K.rows), 'checks', len(bad), 'disagreements')
    for r in bad[:40]:
        print('  ', r['location'], '|', r['label'], '| shown', r['shown'], '| mine', r['yours'])
