"""Compare a state's ledger and feed with the auditor's own values. Usage:
   python3 check.py <state dir> <state name> <out.csv[.gz]> [--clock ISO]"""
import sys, os, csv, json, gzip, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mine
from mine import rnd, px_at, tags_of, GRADED, TFS, EX_D0
from expect import Expect, lens_set_from_plain, lens_set_from_ledger, PLAIN, gof

FIELDS = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']


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
    return json.dumps(v, sort_keys=True)


class Ck:
    def __init__(self, state):
        self.state = state; self.rows = []

    def cmp(self, loc, label, shown, yours, cause=''):
        ok = norm(shown) == norm(yours)
        self.rows.append(dict(state=self.state, location=loc, label=label, shown='' if shown is None else shown,
                              yours='' if yours is None else yours, ok='yes' if ok else 'NO', cause='' if ok else cause))
        return ok

    def note(self, loc, label, shown, yours, ok, cause=''):
        self.rows.append(dict(state=self.state, location=loc, label=label, shown=shown, yours=yours, ok='yes' if ok else 'NO', cause='' if ok else cause))


def lsid(chart, d):
    return f"{chart.replace(' ', '-')}-{d}"


def card_check(ck, X, loc, card, exp_fig, extra):
    """compare one feed card with expected figures + identity fields"""
    for k, v in extra.items():
        ck.cmp(loc, k, card.get(k), v)
    for k in ('past_trades', 'past_signals', 'rose10_never_fell25_within60d_pct', 'beat_normal_move_pct', 'rose20_within60d_pct',
              'rose10_within60d_pct', 'fell30_within60d_pct', 'typical_biggest_rise_pct', 'typical_dip_before_rise_pct',
              'typical_deepest_dip_pct', 'typical_biggest_rise_exact_pct', 'typical_dip_before_rise_exact_pct',
              'typical_deepest_dip_exact_pct', 'typical_day_first_rose10', 'typical_day_first_rose20', 'typical_day_of_60d_high',
              'typical_day_of_deepest_dip'):
        ck.cmp(loc, k, card.get(k), exp_fig['past_trades'] if k == 'past_signals' else exp_fig.get(k))
    for fld in ('typical_biggest_rise', 'typical_dip_before_rise', 'typical_deepest_dip'):
        # the rounded field and the exact field rounded once must be the same figure
        ck.cmp(loc, fld + '_pct vs its exact field rounded once', card.get(fld + '_pct'), exp_fig[fld + '_shown'])
    for era in ('before_2022', 'since_2022'):
        e = card.get(era) or {}
        for k in ('past_trades', 'past_signals', 'rose10_never_fell25_within60d_pct'):
            ck.cmp(loc, f'{era}.{k}', e.get(k), exp_fig[era]['past_trades' if k == 'past_signals' else k])
    fe = card.get('from_entry') or {}
    for k in ('past_trades', 'past_signals', 'still_rose10_pct', 'went_on_to_fall25_pct', 'still_rose10_exact_pct'):
        ck.cmp(loc, f'from_entry.{k}', fe.get(k), exp_fig['from_entry']['past_trades' if k == 'past_signals' else k])
    lad = card.get('if_it_falls_first') or []
    ck.cmp(loc, 'ladder rows', len(lad), 4)
    for r, e in zip(lad, exp_fig['if_it_falls_first']):
        for k in ('fell_pct', 'past_trades', 'past_signals', 'still_rose10_pct', 'went_on_to_fall25_pct', 'still_rose10_exact_pct'):
            ck.cmp(loc, f'falls {e["fell_pct"]}%.{k}', r.get(k), e['past_trades' if k == 'past_signals' else k])
    ck.cmp(loc, 'label', card.get('label'), LABEL)


LABEL = ("Computed signal, not a fill. No trade was taken. Entry quality only: "
         "the data has no exits, so this is not a strategy return or a track record.")


def run(sdir, name, clock=None):
    feed = json.load(open(os.path.join(sdir, 'feed', 'ctzb_feed.json')))
    now = dt.datetime.fromisoformat((clock or feed['generated_at']).replace('Z', '+00:00')).astimezone(dt.timezone.utc)
    S = mine.State(sdir, now)
    ledger = mine.read_csv(os.path.join(sdir, 'datasets', 'ledger.csv'))
    X = Expect(S, ledger)
    ck = Ck(name)
    today = S.today
    X.items = {}
    # ---------------- candle files are their daily candles bucketed (context, (aa))
    ck.note('data/*.csv', '2D-8D files equal bucketed daily candles', len(S.file_mismatch), 0, not S.file_mismatch, 'candle file')
    # ---------------- ledger membership
    for s in X.missing:
        early = s['a'] == 'ETH' and X.eth_start and s['d0'] < X.eth_start
        ck.note('ledger membership', f"{s['a']} {s['tf']} {s['d0']}", 'absent', 'gated signal, 60 days closed',
                bool(early), 'missing from ledger')
    if X.missing:
        ck.note('ledger membership', 'ETH signals before the first ETH ledger row (funding data start) left out', sum(1 for s in X.missing if s['a'] == 'ETH' and s['d0'] < X.eth_start), 'definition', True)
    for r in X.extra:
        ck.note('ledger membership', f"{r['chart']} {r['entry']}", 'present', 'not a gated signal with 60 days closed', False, 'extra ledger row')
    ck.cmp('ledger membership', 'first ETH ledger row', str(X.eth_start), '2020-03-21')
    # ---------------- ledger rows
    for s in X.rows:
        r = X.lkey[(f"{s['a']} {s['tf']}", str(s['d0']))]
        loc = f"ledger {r['chart']} {r['entry']}"
        e = X.ledger_row(s)
        for k, v in e.items():
            ck.cmp(loc, k, r.get(k), v)
        if s['m']['pct_space_differs']:
            ck.note(loc, 'percent-space vs price-space threshold', 'differs', 'same', False, 'float boundary')
        if s['near_eps']:
            ck.note(loc, 'diamond test within 1e-12 of EPS', 'near', '', False, 'EPS boundary')
        go = X.grade_record(s['a'], s['grade'])
        ck.cmp(loc, 'gradeReach20', r.get('gradeReach20'), go['reach20'])
        ck.cmp(loc, 'gradeTouched30', r.get('gradeTouched30'), go['touched30'])
        ck.cmp(loc, 'gradeMedDrawdown', r.get('gradeMedDrawdown'), go['medDip'])
        for k, v in X.day_odds(s).items():
            ck.cmp(loc, k, r.get(k), v)
    # ---------------- grade_odds
    for g in feed.get('grade_odds', []):
        loc = f"grade_odds {g['asset']} {g['grade']}"
        if g['grade'] in ('A+', 'A', 'B', 'C'):
            e = X.grade_record(g['asset'], g['grade'])
        elif g['grade'] in ('diamond or prime dot', 'no diamond or prime dot'):
            e = X.marker_record(g['grade'] == 'diamond or prime dot')
        else:
            ck.note(loc, 'HTF divergence row', 'lens logic', 'out of scope', True); continue
        ck.cmp(loc, 'past_trades', g.get('past_trades'), e['n']); ck.cmp(loc, 'past_signals', g.get('past_signals'), e['n'])
        ck.cmp(loc, 'rose10_within60d_pct', g.get('rose10_within60d_pct'), e['reach10'])
        ck.cmp(loc, 'rose10_never_fell25_within60d_pct', g.get('rose10_never_fell25_within60d_pct'), e['surv10'])
        ck.cmp(loc, 'rose20_within60d_pct', g.get('rose20_within60d_pct'), e['reach20'])
        ck.cmp(loc, 'median_deepest_dip_pct', g.get('median_deepest_dip_pct'), e['medDip'])
        ck.cmp(loc, 'sample', g.get('sample'), e['sample'])
        ck.cmp(loc, 'label', g.get('label'), LABEL)
    have = {(g['asset'], g['grade']) for g in feed.get('grade_odds', [])}
    for a in ('ETH', 'BTC'):
        for gr in ('A+', 'A', 'B', 'C'):
            if X.grade_record(a, gr) and (a, gr) not in have:
                ck.note('grade_odds', f'{a} {gr}', 'absent', 'present', False, 'missing row')
    # ---------------- if_it_misses
    seen = set()
    for m in feed.get('if_it_misses', []):
        loc = f"if_it_misses {m['asset']} {m['grade']}"; seen.add((m['asset'], m['grade']))
        G = [s for s in X.rows if s['a'] == m['asset'] and s['grade'] == m['grade']]
        e = X.misses(G)
        for k, v in e.items():
            ck.cmp(loc, k, m.get(k), v)
        ck.cmp(loc, 'miss_rule', m.get('miss_rule'), 'did not rise 10% within 60 days')
    for a in ('ETH', 'BTC'):
        for gr in ('A+', 'A', 'B', 'C'):
            if any(s['a'] == a and s['grade'] == gr for s in X.rows) and (a, gr) not in seen and any(s['grade'] == 'A+' and s['a'] == a for s in X.rows):
                ck.note('if_it_misses', f'{a} {gr}', 'absent', 'present', False, 'missing row')
    known_ex = [s for s in X.rows if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= EX_D0]
    exm = feed.get('example_if_it_misses')
    if today >= dt.date(2024, 11, 22):
        e = X.misses(known_ex)
        if exm is None:
            ck.note('example_if_it_misses', 'present', 'absent', 'present', False, 'missing')
        else:
            for k, v in e.items():
                if k in exm:
                    ck.cmp('example_if_it_misses', k, exm.get(k), v)
            ck.cmp('example_if_it_misses', 'miss_rule', exm.get('miss_rule'), 'did not rise 10% within 60 days')
            ck.cmp('example_if_it_misses', 'label', exm.get('label'), LABEL)
    # ---------------- past paths
    for p in feed.get('past_paths', []):
        loc = f"past_paths {p['asset']}"
        G = [s for s in X.rows if s['a'] == p['asset'] and s['grade'] == 'A+']
        e = X.paths(G)
        ck.cmp(loc, 'signals', p.get('signals'), e['signals'])
        for dd, ee in zip(p.get('days', []), e['days']):
            for k in ('day', 'q25_pct', 'median_pct', 'q75_pct'):
                ck.cmp(loc, f"day {ee['day']} {k}", dd.get(k), ee[k])
    exp = feed.get('example_past_paths')
    if today >= dt.date(2024, 11, 22):
        e = X.paths(known_ex)
        if exp is None:
            ck.note('example_past_paths', 'present', 'absent', 'present', False, 'missing')
        else:
            ck.cmp('example_past_paths', 'signals', exp.get('signals'), e['signals'])
            for dd, ee in zip(exp.get('days', []), e['days']):
                for k in ('day', 'q25_pct', 'median_pct', 'q75_pct'):
                    ck.cmp('example_past_paths', f"day {ee['day']} {k}", dd.get(k), ee[k])
    # ---------------- odds fade
    of = feed.get('odds_fade')
    if of:
        e = X.odds_fade()
        ck.cmp('odds_fade', 'tier_fixed_on', of.get('tier_fixed_on'), e['tier_fixed_on'])
        ck.cmp('odds_fade', 'posting_bar_pct', of.get('posting_bar_pct'), 70)
        ck.cmp('odds_fade', 'edge_measured_on', of.get('edge_measured_on'), 'rose 10% after day 10 (days 11 to 60)')
        ck.cmp('odds_fade', 'early_dip rows', len(of.get('early_dip', [])), len(e['early_dip']))
        ck.cmp('odds_fade', 'day10 rows', len(of.get('day10', [])), len(e['day10']))
        for kind, key in (('early_dip', 'band'), ('day10', 'check')):
            for r, ee in zip(of.get(kind, []), e[kind]):
                loc = f"odds_fade {kind} {ee[key]}"
                ck.cmp(loc, key, r.get(key), ee[key])
                for k in ('past_trades', 'past_signals', 'rose10_after_day10_pct', 'rose20_after_day10_pct'):
                    ck.cmp(loc, k, r.get(k), ee['past_trades' if k == 'past_signals' else k])
                ck.cmp(loc, 'rose10_within60d_pct (alias)', r.get('rose10_within60d_pct'), ee['rose10_after_day10_pct'])
                ck.cmp(loc, 'rose20_within60d_pct (alias)', r.get('rose20_within60d_pct'), ee['rose20_after_day10_pct'])
                ck.cmp(loc, 'edge (exact share vs 70%)', r.get('edge'), ee['edge'])
        ck.cmp('top level', 'trades_a_year', feed.get('trades_a_year'), e['trades_a_year'])
        ck.cmp('top level', 'signals_a_year', feed.get('signals_a_year'), e['trades_a_year'])
        if str(e['tier_fixed_on']) not in (of.get('sample') or '') and dt.date.fromisoformat(e['tier_fixed_on']).strftime('%-d %b %Y') not in (of.get('sample') or ''):
            ck.note('odds_fade', 'sample names the tier date', of.get('sample', '')[:90], e['tier_fixed_on'], False, 'wording')
    # ---------------- top level
    ck.cmp('top level', 'schema_version', feed.get('schema_version'), 6)
    ck.cmp('top level', 'posting_bar_pct', feed.get('posting_bar_pct'), 70)
    ck.cmp('top level', 'scored_as_of', feed.get('scored_as_of'), str(today))
    ck.cmp('top level', 'market_regime', feed.get('market_regime'), 'Bullish' if S.gate(today) else 'Bearish')
    # ---------------- prints
    exp_prints = []
    for a in ('ETH', 'BTC'):
        for tf in TFS:
            for s in S.sig[(a, tf)][-3:]:
                exp_prints.append(dict(signal_id=lsid(f'{a} {tf}', s['d0']), chart=f'{a} {tf}', state='confirmed', provisional=False,
                                       low_date=str(s['tdate']), confirms_on=str(s['d0']), entry_close=rnd(s['entry'], 2), tags=tags_of(s),
                                       note='regime on' if S.gate(s['tdate']) else 'regime off'))
            p = S.prov[(a, tf)]
            if p:
                exp_prints.append(dict(signal_id=lsid(f'{a} {tf}', p['d0']), chart=f'{a} {tf}', state='forming', provisional=True,
                                       low_date=str(p['tdate']), confirms_on=str(p['d0']), entry_close=rnd(p['price'], 2), tags=tags_of(p),
                                       note=('regime on' if p['gated'] else 'regime off') + f"; {p['need']} bar(s) to confirm"))
    fp = {(x['chart'], x['state'], x['confirms_on']): x for x in feed.get('prints', [])}
    ep = {(x['chart'], x['state'], x['confirms_on']): x for x in exp_prints}
    for k in sorted(set(fp) | set(ep)):
        loc = f"prints {k[0]} {k[1]} {k[2]}"
        if k not in fp:
            ck.note(loc, 'present', 'absent', 'present', False, 'missing print'); continue
        if k not in ep:
            ck.note(loc, 'present', 'present', 'absent', False, 'extra print'); continue
        for kk, v in ep[k].items():
            ck.cmp(loc, kk, fp[k].get(kk), v)
        ck.cmp(loc, 'label', fp[k].get('label'), LABEL)
    # ---------------- forming cards
    fc = {c['chart']: c for c in feed.get('cards', [])}
    for a in ('ETH', 'BTC'):
        for tf in TFS:
            p = S.prov[(a, tf)]; ch = f'{a} {tf}'
            c = fc.get(ch)
            want_card = bool(p) and tf in GRADED and p['gated']
            if c is None:
                if want_card:
                    # sample size cannot be known without the grade; a card is due if any same-grade sample exists
                    ck.note(f'cards {ch}', 'forming card exists', 'absent', 'a graded, gate-on forming low', False, 'missing card')
                continue
            loc = f"cards {ch} {c.get('confirms_on')}"
            if not want_card:
                ck.note(loc, 'forming card allowed', 'present', 'no gate-on graded forming low', False, 'card should not exist'); continue
            grade = c.get('grade'); lens = lens_set_from_plain(c.get('confirmations'))
            ck.cmp(loc, 'grade matches its confirmations count', grade, gof(len(lens)))
            text, G, rule = X.sample(a, tf, grade, lens, X.rows)
            fig = X.card_figures(G)
            extra = dict(signal_id=lsid(ch, p['d0']), asset=a, timeframe=tf, low_date=str(p['tdate']), low_day=str(S.low_day(a, tf, p['tdate'])),
                         confirms_on=str(p['d0']), bars_to_confirm=p['need'], must_close_above=mine.floor_cent(p['kill']) if p['kill'] is not None else None,
                         price_now=rnd(p['price'], 2), entry_close=None, sample=text)
            card_check(ck, X, loc, c, fig, extra)
            X.items[extra['signal_id']] = dict(kind='forming', fig=fig, extra=extra, grade=grade, asset=a, tf=tf, p=p)
            ck.note(loc, 'sample non-empty', fig['past_trades'], '>0', fig['past_trades'] > 0, 'empty sample')
            if p['kill'] is not None:
                fr = (p['kill'] * 100) % 1
                if fr < 1e-6 or fr > 1 - 1e-6:
                    ck.note(loc, 'must_close_above within 1e-8 of a cent', p['kill'], '', False, 'cent boundary')
    # ---------------- example card
    xc = feed.get('example_card')
    exr = next((s for s in X.rows if s['a'] == 'ETH' and s['tf'] == '2D' and s['d0'] == EX_D0), None)
    if today >= dt.date(2024, 11, 22) and exr is not None:
        if xc is None:
            ck.note('example_card', 'present', 'absent', 'present', False, 'missing example')
        else:
            known = [s for s in X.rows if s['d0'] + dt.timedelta(days=60) <= EX_D0]
            text, G, rule = X.sample('ETH', '2D', exr['grade'], exr['lens'], known, example=True)
            fig = X.card_figures(G)
            extra = dict(signal_id='ETH-2D-2024-09-22', chart='ETH 2D', asset='ETH', timeframe='2D', low_date=str(exr['tdate']),
                         low_day=str(S.low_day('ETH', '2D', exr['tdate'])), confirms_on='2024-09-22', bars_to_confirm=None,
                         must_close_above=None, price_now=None, entry_close=rnd(exr['c0'], 2), sample=text, grade=exr['grade'], example=True)
            card_check(ck, X, 'example_card', xc, fig, extra)
            X.items['example'] = dict(kind='example', fig=fig, extra=extra, grade=exr['grade'], asset='ETH', tf='2D', s=exr, known=known)
            ck.cmp('example_card', 'confirmations', lens_set_from_plain(xc.get('confirmations')) == exr['lens'], True)
            ck.note('example_card', 'only signals whose 60th day had closed by 2024-09-22', max((s['d0'] for s in G)), '<= 2024-07-24',
                    max(s['d0'] for s in G) <= dt.date(2024, 7, 24), 'look-ahead')
    elif xc is not None and today < dt.date(2024, 11, 22):
        ck.note('example_card', 'absent before 22 Nov 2024', 'present', 'absent', False, 'example too early')
    # ---------------- open signals
    eo = []
    for a in ('ETH', 'BTC'):
        for tf in GRADED:
            for s in S.sig[(a, tf)]:
                if 0 <= (today - s['d0']).days <= 60:
                    eo.append(s)
    fo = {o['signal_id']: o for o in feed.get('open_signals', [])}
    eom = {lsid(f"{s['a']} {s['tf']}", s['d0']): s for s in eo}
    for sid_ in sorted(set(fo) | set(eom)):
        loc = f'open_signals {sid_}'
        if sid_ not in fo:
            ck.note(loc, 'present', 'absent', 'present', False, 'missing open signal'); continue
        if sid_ not in eom:
            ck.note(loc, 'present', 'present', 'absent', False, 'extra open signal'); continue
        o = fo[sid_]; s = eom[sid_]; a = s['a']; d = S.daily[a]
        e0 = S.daily_close(a, s['d0'])
        win = [(k, off) for k, off in S.window(a, s['d0'])[1] if d['date'][k] < today]
        mark = lambda m_: next((rnd((d['c'][k] / e0 - 1) * 100, 1) for k, off in win if off == m_), None)
        ck.cmp(loc, 'chart', o.get('chart'), f"{a} {s['tf']}")
        ck.cmp(loc, 'entry_date', o.get('entry_date'), str(s['d0']))
        ck.cmp(loc, 'entry_close', o.get('entry_close'), rnd(e0, 2))
        ck.cmp(loc, 'entry close = chart bar close', e0, s['entry'])
        ck.cmp(loc, 'tags', o.get('tags'), tags_of(s))
        ck.cmp(loc, 'days_elapsed', o.get('days_elapsed'), (today - s['d0']).days)
        for m_ in (10, 30, 60):
            ck.cmp(loc, f'day{m_}_pct', o.get(f'day{m_}_pct'), mark(m_))
        ck.cmp(loc, 'best_so_far_pct', o.get('best_so_far_pct'), rnd((max(d['h'][k] for k, _ in win) / e0 - 1) * 100, 1) if win else None)
        ck.cmp(loc, 'worst_so_far_pct', o.get('worst_so_far_pct'), rnd((min(d['l'][k] for k, _ in win) / e0 - 1) * 100, 1) if win else None)
        ck.cmp(loc, 'label', o.get('label'), LABEL)
        c = o.get('card')
        if not c:
            ck.note(loc, 'card', 'absent', 'present', False, 'live signal without a card'); continue
        lens = lens_set_from_plain(c.get('confirmations'))
        ck.cmp(loc, 'card grade = signal grade', c.get('grade'), o.get('grade'))
        ck.cmp(loc, 'grade matches its confirmations count', c.get('grade'), gof(len(lens)))
        lens_o = lens_set_from_ledger(o.get('confirmations') or '-')
        ck.cmp(loc, 'card confirmations = signal confirmations', sorted(lens), sorted(lens_o))
        text, G, rule = X.sample(a, s['tf'], c.get('grade'), lens, X.rows)
        fig = X.card_figures(G)
        extra = dict(signal_id=sid_, chart=f"{a} {s['tf']}", asset=a, timeframe=s['tf'], low_date=str(s['tdate']),
                     low_day=str(S.low_day(a, s['tf'], s['tdate'])), confirms_on=str(s['d0']), bars_to_confirm=None, must_close_above=None,
                     price_now=rnd(d['c'][-1], 2), entry_close=rnd(e0, 2), sample=text)
        card_check(ck, X, loc + ' card', c, fig, extra)
        X.items[sid_] = dict(kind='open', fig=fig, extra=extra, grade=c.get('grade'), asset=a, tf=s['tf'], s=s, e0=e0, win=win)
        lvl = fig['_edge']
        ck.cmp(loc, 'edge_level_pct', o.get('edge_level_pct'), lvl)
        if lvl == 0:
            stat = 'lost'
        else:
            stat = 'intact'
            for k, off in win:
                if lvl is not None and d['l'][k] <= e0 * (1 + lvl / 100):
                    stat = 'lost'; break
                if d['h'][k] >= e0 * 1.10:
                    stat = 'rose10'; break
        ck.cmp(loc, 'edge_status', o.get('edge_status'), stat)
        X.items[sid_].update(status=stat, edge=lvl, days=(today - s['d0']).days,
                             best=rnd((max(d['h'][k] for k, _ in win) / e0 - 1) * 100, 1) if win else None,
                             worst=rnd((min(d['l'][k] for k, _ in win) / e0 - 1) * 100, 1) if win else None, day10=mark(10))
    return ck, S, X, feed


def write(rows, path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'wt', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


if __name__ == '__main__':
    sdir, name, out = sys.argv[1:4]
    clock = sys.argv[sys.argv.index('--clock') + 1] if '--clock' in sys.argv else None
    ck, S, X, feed = run(sdir, name, clock)
    write(ck.rows, out)
    bad = [r for r in ck.rows if r['ok'] != 'yes']
    print(f'{name}: {len(ck.rows)} comparisons, {len(bad)} disagreements')
    for r in bad[:40]:
        print('  ', r['location'], '|', r['label'], '| shown', r['shown'], '| mine', r['yours'])
