"""Audit 13 part 2: every card (forming, open, example), open_signals, forming completeness."""
import csv, datetime as dt, json, os, pickle, sys
from fractions import Fraction
from decimal import Decimal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib13 import *
from model13 import Model, GRADED, ASSETS
from audit_data import build, share, r6, rfrac, yn
import rec13 as R

OUT = os.path.dirname(os.path.abspath(__file__))
PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}
SPLIT = dt.date(2022, 1, 1)
gp = lambda g: 'the top grade' if g == 'A+' else 'the same grade'


def lens_codes(txt):
    return set() if txt in ('none', '', None) else {PLAIN[x] for x in txt.split('; ')}


def sample_for(M, a, tf, grade, lenses, known=None, example=False):
    pool = M.ledgerset if known is None else [s for s in M.ledgerset if s['d0'] + dt.timedelta(days=60) <= known]
    Cr = [s for s in pool if s['a'] == a and s['tf'] == tf]
    ex = [s for s in Cr if s['lenses'] == lenses]
    sg = [s for s in Cr if s['grade'] == grade]
    ag = [s for s in pool if s['a'] == a and s['grade'] == grade]
    if not example:
        if len(ex) >= 15: return f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex
        if len(sg) >= 15: return (f'all {len(sg)} past {a} {tf} signals of {gp(grade)} (' + ('none' if not ex else f'only {len(ex)}')
                                  + ' had exactly the same confirmations, too few to use)'), sg
        return f'all {len(ag)} past signals of {gp(grade)} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag
    if len(ex) >= 15: return f'all {len(ex)} {a} {tf} signals with exactly the same confirmations whose 60 days had closed by then', ex
    if len(sg) >= 15: return (f'all {len(sg)} {a} {tf} signals of {gp(grade)} whose 60 days had closed by then (' + ('none' if not ex else f'only {len(ex)}')
                              + ' had exactly the same confirmations, too few to use)'), sg
    return f'all {len(ag)} signals of {gp(grade)} across all {a} charts whose 60 days had closed by then ({a} {tf} alone had only {len(sg)}, too few to use)', ag


def from6(x6, nd):
    return None if x6 is None else rha(Decimal(repr(x6)), nd)


def card_figs(M, G):
    n = len(G)
    m = lambda k: [s['m'][k] for s in G]
    sc = [s['sc'] for s in G if s['sc'] is not None]
    old = [s for s in G if s['d0'] < SPLIT]; new = [s for s in G if s['d0'] >= SPLIT]
    sv = lambda X: share(sum(s['m']['surv'] for s in X), len(X)) if X else None
    best6, dpk6, dd6 = r6(median(m('up'))), r6(median(m('ddpk'))), r6(median(m('dd')))
    lad = ladder([(s['m']['hl'], s['entry']) for s in G])
    t10 = [s['m']['t10'] for s in G if s['m']['t10'] is not None]
    t20 = [s['m']['t20'] for s in G if s['m']['t20'] is not None]
    mr = lambda xs: rha(float(median(xs)), 0) if xs else None
    f = dict(n=n, surv=share(sum(m('surv')), n), scaled=share(sum(sc), len(sc)) if sc else None,
             r20=share(sum(m('r20')), n), r10=share(sum(m('r10')), n),
             best=from6(best6, 1), dpk=from6(dpk6, 1), dd=from6(dd6, 1), t30=share(sum(m('t30')), n),
             best_full1=rha_bin(median(m('up')), 1), dpk_full1=rha_bin(median(m('ddpk')), 1), dd_full1=rha_bin(median(m('dd')), 1),
             best6=best6, dpk6=dpk6, dd6=dd6, nOld=len(old), sOld=sv(old), nNew=len(new), sNew=sv(new),
             lad={k: dict(n=v['n'], ok=share(v['ok'], v['n']), liq=share(v['liq'], v['n']), ex=share(v['ok'], v['n'], 6),
                          exf=(Fraction(100 * v['ok'], v['n']) if v['n'] else None)) for k, v in lad.items()},
             d10=mr(t10), d20=mr(t20), dhigh=mr(m('dpk')), dlow=mr(m('ddday')))
    return f


def check_card(M, loc, c, f, sample_txt):
    st = M.st
    A = lambda lab, shown, yours, cause='': R.add(st, loc, lab, shown, yours, cause or lab)
    A('sample', c['sample'], sample_txt, 'sample wording/rule')
    A('past_trades', c['past_trades'], f['n'], 'n')
    A('past_signals', c.get('past_signals'), f['n'], 'n')
    A('rose10_within60d_pct (big number)', c['rose10_within60d_pct'], f['r10'])
    A('rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], f['surv'])
    A('beat_normal_move_pct', c['beat_normal_move_pct'], f['scaled'])
    A('rose20_within60d_pct', c['rose20_within60d_pct'], f['r20'])
    A('fell30_within60d_pct', c['fell30_within60d_pct'], f['t30'])
    A('typical_biggest_rise_pct', c['typical_biggest_rise_pct'], f['best'], 'rounded once from the 6-place exact median')
    A('typical_dip_before_rise_pct', c['typical_dip_before_rise_pct'], f['dpk'], 'rounded once from the 6-place exact median')
    A('typical_deepest_dip_pct', c['typical_deepest_dip_pct'], f['dd'], 'rounded once from the 6-place exact median')
    A('typical_biggest_rise_exact_pct', c['typical_biggest_rise_exact_pct'], f['best6'], 'exact median')
    A('typical_dip_before_rise_exact_pct', c['typical_dip_before_rise_exact_pct'], f['dpk6'], 'exact median')
    A('typical_deepest_dip_exact_pct', c['typical_deepest_dip_exact_pct'], f['dd6'], 'exact median')
    A('before_2022.past_trades', c['before_2022']['past_trades'], f['nOld'])
    A('before_2022.surv10', c['before_2022']['rose10_never_fell25_within60d_pct'], f['sOld'])
    A('since_2022.past_trades', c['since_2022']['past_trades'], f['nNew'])
    A('since_2022.surv10', c['since_2022']['rose10_never_fell25_within60d_pct'], f['sNew'])
    A('typical_day_first_rose10', c['typical_day_first_rose10'], f['d10'])
    A('typical_day_first_rose20', c['typical_day_first_rose20'], f['d20'])
    A('typical_day_of_60d_high', c['typical_day_of_60d_high'], f['dhigh'])
    A('typical_day_of_deepest_dip', c['typical_day_of_deepest_dip'], f['dlow'])
    fe = c['from_entry']; l0 = f['lad'][0]
    A('from_entry.past_trades', fe['past_trades'], l0['n'])
    A('from_entry.still_rose10_pct', fe['still_rose10_pct'], l0['ok'])
    A('from_entry.went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], l0['liq'])
    A('from_entry.still_rose10_exact_pct', fe['still_rose10_exact_pct'], l0['ex'])
    for row in c['if_it_falls_first']:
        k = row['fell_pct']; l = f['lad'][k]
        A(f'falls {k}% first: past_trades', row['past_trades'], l['n'])
        A(f'falls {k}% first: still_rose10_pct', row['still_rose10_pct'], l['ok'])
        A(f'falls {k}% first: went_on_to_fall25_pct', row['went_on_to_fall25_pct'], l['liq'])
        A(f'falls {k}% first: still_rose10_exact_pct', row['still_rose10_exact_pct'], l['ex'])
    A('ladder rows', [r['fell_pct'] for r in c['if_it_falls_first']].__repr__(), '[5, 10, 15, 20]')
    # edge (the first level whose exact share is below 70)
    edge = 0 if l0['exf'] is not None and l0['exf'] < 70 else next((-k for k in (5, 10, 15, 20) if f['lad'][k]['exf'] is not None and f['lad'][k]['exf'] < 70), None)
    return edge


def forming_setups(M):
    """my own provisional lows on every chart: a CT pivot still waiting on its right-hand bars."""
    out = []
    for (a, tf), b in M.bars.items():
        pv, ct, K = M.piv[(a, tf)]
        n = len(ct)
        for back in (1, 2, 3):
            ti = n - 1 - back
            v = ct[ti]
            if v is None or any(x is None for x in ct[ti - 3:ti]): continue
            if not all(x > v for x in ct[ti - 3:ti]): continue
            if not all(ct[j] > v for j in range(ti + 1, n)): continue
            need = 3 - back
            # confirmation bar: index ti+3 (may be in the future)
            d = b['date'][-1]; k = n - 1
            while k < ti + 3:
                d = next_open(d, tf); k += 1
            conf_open = d
            nxt = next_open(conf_open, tf)
            d0f = nxt - dt.timedelta(days=1)
            ts, te = bar_span(b['date'], ti, tf)
            day = M.day[a]
            cand = [(day.b['l'][day.pos[x]], x) for x in (ts + dt.timedelta(days=i) for i in range((te - ts).days + 1)) if x in day.pos]
            lowday = min(cand)[1]
            kill = None
            if need in (0, 1):
                base = b['c'][:-1] if need == 0 else list(b['c'])
                au, ad = rsi_state(base)
                last = base[-1]
                RS = v / (100 - v)
                ad1 = ad * 13 / 14
                x = last + 14 * RS * ad1 - 13 * au
                if x < last:
                    au1 = au * 13 / 14
                    x = last - (14 * au1 / RS - 13 * ad)
                kill = x
            prime = K[ti] is not None and 20 <= K[ti] < 50
            out.append(dict(a=a, tf=tf, ti=ti, need=need, tdate=b['date'][ti], lowday=lowday, d0=d0f, kill=kill,
                            price=b['c'][-1], ct=v, k=K[ti]))
    return out


def main():
    res = {}
    for st, now in (('replay_0414', dt.datetime(2026, 11, 12, 4, 14, tzinfo=dt.timezone.utc)), ('current', None)):
        S = os.path.join(os.path.dirname(OUT), 'a13', st)
        feed = json.load(open(os.path.join(S, 'feed', 'ctzb_feed.json')))
        if now is None:
            now = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
        M = build(st, now)
        today = M.today
        mine = dict(cards={}, open={}, example=None)
        # ---------------- forming cards
        F = forming_setups(M)
        fc = {c['signal_id']: c for c in feed['cards']}
        mineids = {f"{x['a']}-{x['tf']}-{x['d0']}": x for x in F}
        for sid in sorted(set(fc) | set(mineids)):
            R.add(st, 'feed cards (forming setups)', f'{sid} has a card', yn(sid in fc), yn(sid in mineids), 'forming list')
        for sid, c in fc.items():
            x = mineids.get(sid)
            loc = f'feed cards {sid}'
            if x is None: continue
            A = lambda lab, shown, yours, cause='': R.add(st, loc, lab, shown, yours, cause or lab)
            A('chart', c['chart'], f"{x['a']} {x['tf']}"); A('asset', c['asset'], x['a']); A('timeframe', c['timeframe'], x['tf'])
            A('low_date', c['low_date'], str(x['tdate'])); A('low_day', c['low_day'], str(x['lowday']))
            A('confirms_on', c['confirms_on'], str(x['d0'])); A('bars_to_confirm', c['bars_to_confirm'], x['need'])
            A('must_close_above', c['must_close_above'], None if x['kill'] is None else rha_bin(x['kill'], 2), 'kill close')
            A('price_now', c['price_now'], rha_bin(M.day[x['a']].b['c'][-1], 2), 'latest price')
            A('price_now = chart last close', c['price_now'], rha_bin(x['price'], 2))
            A('entry_close (forming: empty)', c['entry_close'], None)
            A('label', c['label'], feed['label'])
            txt, G = sample_for(M, x['a'], x['tf'], c['grade'], lens_codes(c['confirmations']))
            f = card_figs(M, G)
            edge = check_card(M, loc, c, f, txt)
            mine['cards'][sid] = dict(f=f, edge=edge, x={k: (str(v) if isinstance(v, dt.date) else v) for k, v in x.items()}, sample=txt)
        # ---------------- open signals
        opens = []
        for (a, tf), lst in M.sig.items():
            if tf not in GRADED: continue
            for s in lst:
                if 0 <= (today - s['d0']).days <= 60:
                    opens.append(s)
        fo = {o['signal_id']: o for o in feed['open_signals']}
        mo = {f"{s['a']}-{s['tf']}-{s['d0']}": s for s in opens}
        for sid in sorted(set(fo) | set(mo)):
            R.add(st, 'feed open_signals', f'{sid} listed', yn(sid in fo), yn(sid in mo), 'open list')
        for sid, o in fo.items():
            s = mo.get(sid)
            if s is None: continue
            loc = f'feed open_signals {sid}'
            A = lambda lab, shown, yours, cause='': R.add(st, loc, lab, shown, yours, cause or lab)
            e = s['entry']; d0 = s['d0']; day = M.day[s['a']]
            A('chart', o['chart'], s['chart']); A('entry_date', o['entry_date'], str(d0))
            A('entry_close', o['entry_close'], rha_bin(e, 2)); A('tags', o['tags'], s['tags'])
            A('days_elapsed', o['days_elapsed'], (today - d0).days)
            ks = day.window(d0, 60, closed_before=today)
            mark = lambda k: next((rha_bin((day.b['c'][j] / e - 1) * 100, 1) for j in ks if (day.dates[j] - d0).days == k), None)
            A('day10_pct', o['day10_pct'], mark(10)); A('day30_pct', o['day30_pct'], mark(30)); A('day60_pct', o['day60_pct'], mark(60))
            A('best_so_far_pct', o['best_so_far_pct'], rha_bin((max(day.b['h'][j] for j in ks) / e - 1) * 100, 1) if ks else None)
            A('worst_so_far_pct', o['worst_so_far_pct'], rha_bin((min(day.b['l'][j] for j in ks) / e - 1) * 100, 1) if ks else None)
            A('label', o['label'], feed['label'])
            c = o['card']
            if c is None:
                A('card present', 'missing', 'present'); continue
            locc = f'feed open_signals {sid} card'
            B = lambda lab, shown, yours, cause='': R.add(st, locc, lab, shown, yours, cause or lab)
            B('signal_id', c['signal_id'], sid); B('low_date', c['low_date'], str(s['tdate']))
            ts, te = bar_span(M.bars[(s['a'], s['tf'])]['date'], s['ti'], s['tf'])
            cand = [(day.b['l'][day.pos[x]], x) for x in (ts + dt.timedelta(days=i) for i in range((te - ts).days + 1)) if x in day.pos]
            B('low_day', c['low_day'], str(min(cand)[1])); B('confirms_on', c['confirms_on'], str(d0))
            B('bars_to_confirm', c['bars_to_confirm'], None); B('must_close_above', c['must_close_above'], None)
            B('price_now', c['price_now'], rha_bin(day.b['c'][-1], 2), 'latest price'); B('entry_close', c['entry_close'], rha_bin(e, 2))
            B('grade = open signal grade', c['grade'], o['grade']); B('confirmations = open signal lenses', lens_codes(c['confirmations']).__repr__() if c['confirmations'] else '', (set() if o['confirmations'] == '-' else set(o['confirmations'].split(' + '))).__repr__())
            txt, G = sample_for(M, s['a'], s['tf'], c['grade'], lens_codes(c['confirmations']))
            f = card_figs(M, G)
            edge = check_card(M, locc, c, f, txt)
            # edge level and status (audit #9)
            if edge is None:
                lvl, status = None, 'intact'
            elif edge == 0:
                lvl, status = 0, 'lost'
            else:
                lvl, status = edge, 'intact'
                for j in ks:
                    if day.b['l'][j] <= e * (1 + edge / 100): status = 'lost'; break
                    if day.b['h'][j] >= e * 1.10: status = 'intact'; break
            A('edge_level_pct', o['edge_level_pct'], lvl); A('edge_status', o['edge_status'], status)
            mine['open'][sid] = dict(f=f, edge=edge, lvl=lvl, status=status, sample=txt, entry=e, d0=str(d0), tdate=str(s['tdate']),
                                     days=(today - d0).days, best=o['best_so_far_pct'], worst=o['worst_so_far_pct'])
        # ---------------- example card
        xc = feed['example_card']
        loc = 'feed example_card'
        s = next(s for s in M.ledgerset if s['chart'] == 'ETH 2D' and s['d0'] == dt.date(2024, 9, 22))
        A = lambda lab, shown, yours, cause='': R.add(st, loc, lab, shown, yours, cause or lab)
        A('signal_id', xc['signal_id'], 'ETH-2D-2024-09-22'); A('example', xc.get('example'), True)
        A('low_date', xc['low_date'], str(s['tdate']))
        ts, te = bar_span(M.bars[('ETH', '2D')]['date'], s['ti'], '2D'); day = M.day['ETH']
        cand = [(day.b['l'][day.pos[x]], x) for x in (ts + dt.timedelta(days=i) for i in range((te - ts).days + 1)) if x in day.pos]
        A('low_day', xc['low_day'], str(min(cand)[1])); A('confirms_on', xc['confirms_on'], '2024-09-22')
        A('price_now (example: none)', xc['price_now'], None); A('entry_close', xc['entry_close'], rha_bin(s['entry'], 2))
        A('bars_to_confirm', xc['bars_to_confirm'], None); A('must_close_above', xc['must_close_above'], None)
        A('grade = ledger grade', xc['grade'], s['grade'])
        A('confirmations = ledger lenses', repr(sorted(lens_codes(xc['confirmations']))), repr(sorted(s['lenses'])))
        txt, G = sample_for(M, 'ETH', '2D', xc['grade'], lens_codes(xc['confirmations']), known=dt.date(2024, 9, 22), example=True)
        f = card_figs(M, G)
        edge = check_card(M, loc, xc, f, txt)
        mine['example'] = dict(f=f, edge=edge, sample=txt, entry=s['entry'], tdate=str(s['tdate']), lowday=str(min(cand)[1]))
        # example's own 60 days (What happened)
        mine['example']['m'] = {k: v for k, v in s['m'].items() if k not in ('hl',)}
        res[st] = mine
    pickle.dump(res, open(os.path.join(OUT, 'part2.pkl'), 'wb'))
    R.write(os.path.join(OUT, 'part2_checks.csv'), os.path.join(OUT, 'part2_dis.csv'))
    bad = [r for r in R.ROWS if r['ok'] != 'yes']
    print(len(R.ROWS), 'checks', len(bad), 'disagreements')
    for r in bad[:80]:
        print(r)


if __name__ == '__main__':
    main()
