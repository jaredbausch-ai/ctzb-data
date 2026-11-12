"""Check every number the page displays against my values. python3 compare_page.py <tag> <state_dir> <now>"""
import csv, datetime as dt, json, os, re, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import rnd, pct, Bars, closed_by, median
from check import Checks
from mine import State

OUT = os.path.dirname(os.path.abspath(__file__))
M = '−'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']   # en-GB short month (Chromium prints "Sept")


def dlong(iso):
    d = dt.date.fromisoformat(iso); return f'{d.day} {MON[d.month - 1]} {d.year}'


def dshort(d):
    return f'{d.day:02d} {MON[d.month - 1]}'


def P(v, d=1, sign=True):
    """My expected display of a percentage (v already rounded or exact Fraction)."""
    if v is None: return 'n/a'
    x = rnd(F(v), d)
    s = f'{abs(x):.{d}f}'
    neg = F(v) < 0 and float(x) != 0
    return ('+' if sign and x > 0 else '') + (M if (F(v) < 0 and x != 0) else '') + s + '%'


def money(v):
    x = rnd(F(v), 2)
    return '$' + f'{x:,.2f}'


def main(tag, sdir, now_s):
    now = dt.datetime.fromisoformat(now_s.replace('Z', '+00:00'))
    cap = json.load(open(os.path.join(OUT, f'page_{tag}.json')))
    mine = json.load(open(os.path.join(OUT, f'mine_{tag}.json')))
    S = State(sdir, now); feed = S.feed
    C = Checks(tag)
    cards = mine['cards']; opn = mine['open']; MI = mine['MI']; GS = mine['GS']; PP = mine['PP']
    # exact medians for prices
    import check as CK

    # ------------------------------------------------ header
    h = cap['header']
    C.add('page header', 'review: scored date + feed time', h['rvAsof'], f"{dlong(feed['scored_as_of'])} (feed {feed['generated_at'][11:16]} UTC)", 'header')
    C.add('page header', 'market filter', h['filterText'], 'Market filter: ' + ('on' if S.gate(now.date()) else 'off'), 'gate state today')
    C.add('page footer', 'data-through date', h['feedState'].split(' · ')[0], f'Data through {dlong(str(now.date()))}', 'scored date')

    # ------------------------------------------------ picker
    A_open = {k: v for k, v in opn.items() if next((o for o in feed['open_signals'] if o['signal_id'] == k), {}).get('grade') == 'A+'}
    live_btns = [b for b in cap['picker'] if 'top' in b['cls'] and 'Day' in b['text']]
    C.add('page picker Live', 'live buttons (A+ open signals)', '|'.join(sorted(b['sel'] for b in live_btns)), '|'.join(sorted(A_open)), 'live list')
    for b in live_btns:
        o = opn[b['sel']]; t = b['text'].replace('\n', ' ')
        exp = f"{o['chart']} Day {o['days_elapsed']} best {P(o['best_so_far_pct'])} · worst {P(o['worst_so_far_pct'])}"
        C.add(f"page picker Live {b['sel']}", 'button text', t, exp, 'live button')
    form_btns = [b for b in cap['picker'] if b['sel'] not in A_open and b['sel'] != 'example']
    for b in form_btns:
        c = cards[b['sel']]; fc = next(x for x in feed['cards'] if x['signal_id'] == b['sel'])
        t = b['text'].replace('\n', ' ')
        exp = f"{c['chart']} {c['reach10']}% {'top grade' if fc['grade'] == 'A+' else 'not top grade'} · confirms {dlong(c['confirms_on'])}"
        C.add(f"page picker Forming {b['sel']}", 'button text', t, exp, 'forming button')
    C.add('page picker', 'forming buttons', '|'.join(sorted(b['sel'] for b in form_btns)), '|'.join(sorted(k for k, v in cards.items() if v['kind'] == 'forming')), 'forming list')

    # ------------------------------------------------ cards
    for sel in cap['selections']:
        sid = sel['sel']; c = cards['example' if sid == 'example' else sid]
        kind = c['kind']; asset = 'ETH' if sid == 'example' else sid.split('-')[0]
        fc = feed['example_card'] if sid == 'example' else next((x for x in feed['cards'] if x['signal_id'] == sid), None) or next(o for o in feed['open_signals'] if o['signal_id'] == sid)['card']
        grade = fc['grade']; below = kind == 'forming' and grade != 'A+'
        loc = f'page card {sid}'
        lines = [x.strip() for x in sel['card'].split('\n') if x.strip()]
        txt = ' | '.join(lines)
        # entry used for prices on the chart side
        if kind == 'open': entry = F(str(c['entry_close']))
        elif kind == 'example': entry = F(str(feed['example_card']['entry_close']))
        else: entry = F(str(c['price_now']))
        # line under the state
        if kind == 'open':
            line = f"Confirmed {dlong(c['entry_date'])} · entry close {money(c['entry_close'])} · day {c['days_elapsed']} of 60 · best so far {P(c['best_so_far_pct'])} · worst {P(c['worst_so_far_pct'])}"
        elif kind == 'example':
            line = f"Example: confirmed {dlong('2024-09-22')} · entry close {money(entry)}"
        else:
            line = f"Low {dlong(c['low_date'])} · confirms {dlong(c['confirms_on'])}" + (f" if it closes above {money(c['kill'])}" if c.get('kill') is not None else '')
        C.add(loc, 'header line', lines[2], line, 'card header line')
        C.add(loc, 'state', lines[1], {'open': 'Live setup', 'example': 'Confirmed setup', 'forming': 'Setup forming'}[kind], 'state word')
        get = lambda lab, off=1: lines[lines.index(lab) + off] if lab in lines else None
        C.add(loc, 'big number (rose 10%)', get('rose 10% within 60 days', -1), f"{c['reach10']}%", 'big number')
        C.add(loc, 'surv line', get('rose 10% within 60 days'), f"{c['surv10']}% did it without ever falling 25.3%", 'surv10')
        C.add(loc, 'n line', get('rose 10% within 60 days', 2), f"from {c['n']} past signals like this one", 'n')
        C.add(loc, 'Typical high', get('Typical high'), P(F(c['best_exact'])), 'median best')
        C.add(loc, 'Typical drop from entry', get('Typical drop from entry'), P(F(c['dd_exact'])), 'median deepest dip')
        # edge
        if c['reach10'] < 70: edge = 0
        else:
            g = next((th for th, r in zip((5, 10, 15, 20), c['ladder']) if r['ok'] is not None and r['ok'] < 70), None)
            edge = -g if g else None
        etxt = 'Below the 70% bar from entry' if edge == 0 else (f'{P(edge, 0)} before it rises 10%' if edge is not None else 'Holds at every level')
        C.add(loc, 'Edge gone below', get('Edge gone below'), etxt, 'edge (own ladder)')
        # misses
        if kind == 'example':
            mk = c['misses_known']; mt = ('Every time' if mk['up_first'] == mk['misses'] else f"{mk['up_first']} of {mk['misses']}") + f" · median peak {P(mk['median_peak'])}"
            worst, d60 = mk['worst'], mk['day60']
        else:
            mm = MI[f'{asset} {grade}']; mt = ('Every time' if mm['up_first'] == mm['misses'] else f"{mm['up_first']} of {mm['misses']}") + f" · median peak {P(mm['median_peak_pct'])}"
            worst, d60 = mm['median_worst_drop_pct'], mm['median_day60_pct']
        C.add(loc, 'If it misses: up first', get('If it misses: up first'), mt, 'misses')
        if below:
            C.add(loc, 'misses pool line', get('If it misses: up first', 2), f"all {MI[f'{asset} {grade}']['signals']} {asset} signals of this grade", 'misses pool')
        C.add(loc, 'Dip before the high', get('Dip before the high, from entry'), P(F(c['dbh_exact'])), 'median dip before high')
        C.add(loc, 'High lands around', get('High lands around'), f"Day {c['dhigh']}", 'median day of high')
        C.add(loc, 'Reached +20%', get('Reached +20%'), f"{c['reach20']}%", 'reach20')
        C.add(loc, 'Touched -30%', get(f'Touched {M}30%'), f"{c['t30']}%", 'fell 30%')
        C.add(loc, 'Deepest dip lands around', get('Deepest dip lands around'), f"Day {c['dlow']}", 'median day of deepest dip')
        C.add(loc, 'Worst drop, misses', get('Worst drop, misses'), P(worst), 'misses worst')
        C.add(loc, 'Typical price on day 60, misses', get('Typical price on day 60, misses'), P(d60), 'misses day 60')
        # ladder
        C.add(loc, 'ladder From entry', f"{get('From entry n ' + str(fc['past_trades']), 0)} {get('From entry n ' + str(fc['past_trades']))}", f"From entry n {c['n']} {c['reach10']}%", 'ladder base')
        for th, r in zip((5, 10, 15, 20), c['ladder']):
            lab = next((x for x in lines if x.startswith(f'Falls {th}% first n ')), None)
            C.add(loc, f'ladder Falls {th}% first', f"{lab} {get(lab) if lab else ''}", f"Falls {th}% first n {r['n']} {'n/a' if r['ok'] is None else str(r['ok']) + '%'}", 'ladder')
        for era, n_, v in (('Before 2022', c['nOld'], c['sOld']), ('Since 2022', c['nNew'], c['sNew'])):
            lab = next((x for x in lines if x.startswith(era + ' n ')), None)
            C.add(loc, f'era {era}', f"{lab} {get(lab) if lab else ''}", f"{era} n {n_} {v}%", 'era')
        C.add(loc, 'lead trader', next((x for x in lines if x.startswith('Lead trader')), None), 'Lead trader: not in', 'no trades file')
        C.add(loc, 'ends with entry-quality disclaimer', 'yes' if 'Entry quality only: no exit, not a trade or a track record' in txt else 'no', 'yes', 'label')

        # ------------------------------------------------ chart tab
        bars_c = None
        for mode, ch in sel['chart'].items():
            cl = f'page chart {sid} {"At the alert" if mode == "bAlert" else "What happened"}'
            side = [x.strip() for x in ch['side'].split('\n') if x.strip()]
            g2 = lambda lab, off=1: side[side.index(lab) + off] if lab in side else None
            C.add(cl, 'side big number', g2('WHAT THE CARD SAYS', 2), f"{c['reach10']}%", 'big number')
            C.add(cl, 'side n/surv line', g2('WHAT THE CARD SAYS', 3), f"rose 10% within 60 days, from {c['n']} past signals; {c['surv10']}% without ever falling 25.3%", 'n/surv')
            samp = fc['sample']
            C.add(cl, 'side sample line', g2('WHAT THE CARD SAYS', 1), f"{fc['chart']} · " + (f'from {samp}' if kind != 'example' else 'example'), 'sample text')
            C.add(cl, 'side Typical high', g2('Typical high'), f"{P(F(c['best_exact']))} · {money(entry * (1 + F(c['best_exact']) / 100))}", 'typical high price from exact %')
            C.add(cl, 'side +10% target', g2('+10% target'), money(entry * F(11, 10)), 'entry x 1.10')
            C.add(cl, 'side Reached +20%', g2('Reached +20%'), f"{c['reach20']}%", 'reach20')
            C.add(cl, 'side Typical drop', g2('Typical drop'), f"{P(F(c['dd_exact']))} · {money(entry * (1 + F(c['dd_exact']) / 100))}", 'typical drop price from exact %')
            et = 'below the bar already' if edge == 0 else ('holds at every level' if edge is None else f"{money(entry * (1 + F(edge, 100)))} ({P(edge, 0)})")
            C.add(cl, 'side Edge gone below', g2('Edge gone below'), et, 'edge price')
            if kind == 'open':
                C.add(cl, 'side live box title', next((x for x in side if x.startswith('LIVE: DAY')), None), f"LIVE: DAY {c['days_elapsed']} OF 60", 'days elapsed')
                C.add(cl, 'side Best so far', g2('Best so far'), P(c['best_so_far_pct']), 'best so far')
                C.add(cl, 'side Worst so far', g2('Worst so far'), P(c['worst_so_far_pct']), 'worst so far')
                C.add(cl, 'side Day 10', g2('Day 10'), 'not yet' if c['day10_pct'] is None else P(c['day10_pct']), 'day 10')
            if 'Prices use today\'s close as a stand-in for the entry.' in side:
                C.add(cl, 'side note "Prices use today\'s close as a stand-in for the entry"', 'shown', 'shown' if kind == 'forming' else 'not applicable: prices use the entry close',
                      'label wrong for a live (confirmed) setup: its prices are built from the entry close' if kind == 'open' else '')
            # titles / subtitles
            if kind == 'open':
                C.add(cl, 'title', ch['title'], f"{fc['chart'].replace(' ', ' · ')} · LIVE SETUP, DAY {c['days_elapsed']} OF 60".upper(), 'title')
                C.add(cl, 'subtitle entry', ch['sub'].split('.')[0] + '.' + ch['sub'].split('.')[1].split(' ')[0] if False else ch['sub'][:ch['sub'].index('. ')], f"Confirmed {dlong(c['entry_date'])} · entry close {money(c['entry_close'])}", 'subtitle')
                pooled = 'Zones use the pooled top-grade figures' in ch['sub']
                own_is_pooled = fc['sample'].startswith(f"all {GS[f'{asset} A+']['n']} past grade A+ signals across all {asset} charts")
                C.add(cl, 'subtitle claim "Zones use the pooled top-grade figures"', 'claims pooled' if pooled else 'no claim',
                      'claims pooled' if own_is_pooled else 'own card sample', 'zones are drawn from the setup\'s own card, which here is not the pooled set')
            elif kind == 'forming':
                C.add(cl, 'subtitle', ch['sub'].split(' The shaded')[0],
                      f"Low {dlong(c['low_date'])} · confirms {dlong(c['confirms_on'])} · price levels drawn from today's price ({money(c['price_now'])}), since the entry price is the confirmation close; days count from the confirmation.", 'subtitle')
            else:
                C.add(cl, 'subtitle claim about the odds\' sample', 'Its odds use the full history, including signals after it.' if 'including signals after it' in ch['sub'] else 'no claim',
                      'odds use only signals whose 60 days had closed by 22 Sept 2024', 'stale label: the example card is built from signals closed by its date (no hindsight)')
            # svg texts
            texts = [t['text'] for t in ch['texts']]
            tx = lambda pre: next((t for t in ch['texts'] if t['text'].startswith(pre)), None)
            C.add(cl, 'svg Typical high label', (tx('Typical high') or {}).get('text'), f"Typical high {P(F(c['best_exact']))}", 'svg')
            C.add(cl, 'svg +10% label', (tx('+10% ·') or {}).get('text'), f"+10% · {c['reach10']}% of past signals got here", 'svg')
            C.add(cl, 'svg Typical drop label', (tx('Typical drop') or {}).get('text'), f"Typical drop {P(F(c['dd_exact']))}", 'svg')
            et2 = None if edge in (0, None) else f"Edge gone below {money(entry * (1 + F(edge, 100)))} ({P(edge, 0)}, before +10%)"
            C.add(cl, 'svg Edge label', (tx('Edge gone') or {}).get('text'), et2, 'svg edge')
            C.add(cl, 'svg High day label', (tx('High usually') or {}).get('text'), f"High usually ~day {c['dhigh']}", 'svg')
            zone = [t['text'] for t in ch['texts'] if re.fullmatch(r'\d+%|n/a', t['text'])]
            expz = [f"{c['reach10']}%"] + [('n/a' if r['ok'] is None else f"{r['ok']}%") for r in c['ladder'][:3]]
            C.add(cl, 'svg ladder zone labels', ' '.join(zone), ' '.join(expz), 'svg ladder')
            # price tags at right: typical high, +10%, entry, drop
            tags = [t['text'] for t in ch['texts'] if t['x'] == 1018]
            expt = sorted([money(entry * (1 + F(c['best_exact']) / 100)), money(entry * F(11, 10)), money(entry), money(entry * (1 + F(c['dd_exact']) / 100))])
            C.add(cl, 'svg price tags', ' '.join(sorted(tags)), ' '.join(expt), 'svg price tags')
            # geometry: which bar is the entry / today / confirmation / day 60 / high-day / low
            wicks = [l for l in ch['lines'] if l['x1'] == l['x2'] and not (l['y1'] == 24 and l['y2'] == 480)]
            if wicks:
                x0 = wicks[0]['x1']; slot = 2 * (x0 - 20)
                idx = lambda x: round((x - 20) / slot - 0.5, 3)
                if kind == 'example':
                    ex = json.load(open(f'{sdir}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')); bars = ex['bars']; tfd = 2
                else:
                    tfd = int(fc['timeframe'][:-1])
                    bars = [dict(t=int(r['time'])) for r in csv.DictReader(open(f"{sdir}/datasets/candles_{asset.lower()}_{fc['timeframe'].lower()}.csv"))]
                bdate = lambda i: dt.datetime.fromtimestamp(bars[0]['t'], dt.timezone.utc).date() + dt.timedelta(days=tfd * i) if i >= len(bars) else dt.datetime.fromtimestamp(bars[i]['t'], dt.timezone.utc).date()
                ent = tx('Entry') or tx('Today')
                ei = idx(ent['x'] - 6)
                if kind == 'forming':
                    exp_e = len(bars) - 1; conf_open = dt.date.fromisoformat(c['confirms_on']) - dt.timedelta(days=tfd - 1)
                    exp_c = (conf_open - bdate(0)).days / tfd
                    ct = tx('Confirms')
                    C.add(cl, 'svg "Confirms ... entry, day 0" text', ct['text'] if ct else None, f"Confirms {dlong(c['confirms_on'])} · entry, day 0", 'svg')
                    C.add(cl, 'geometry: confirmation line on the bar that closes on confirms_on', idx(ct['x'] - 6) if ct else None, exp_c, 'confirmation line placement')
                    anchor = exp_c
                    C.add(cl, 'geometry: "Today" line on the last bar', ei, exp_e, 'today line placement')
                    lowt = tx('Low ')
                    li = idx(lowt['x'] + 12)
                    lb = next(i for i, b in enumerate(bars) if dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date() == dt.date.fromisoformat(c['low_date']))
                    C.add(cl, 'geometry: low marker on the trough bar', li, lb, 'low marker placement')
                    raw = Bars(f"{sdir}/data/{asset}_{fc['timeframe']}.csv"); ti = raw.pos[dt.date.fromisoformat(c['low_date'])]
                    C.add(cl, 'svg low label', lowt['text'], f"Low {dlong(c['low_date'])} · {money(raw.l[ti])}", 'trough low price')
                else:
                    if kind == 'open':
                        exp_e = next(i for i, b in enumerate(bars) if dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date() == dt.date.fromisoformat(c['conf_open']))
                    else:
                        exp_e = next(i for i, b in enumerate(bars) if dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date() == dt.date(2024, 9, 21))
                    C.add(cl, 'geometry: "Entry" line on the confirmation bar (bar index)', ei, exp_e,
                          'entry bar looked up by open date == entry (close) date; on a 2D+ chart no bar opens then, so it falls back to the last bar (today)')
                    if ei != exp_e:
                        C.add(cl, 'geometry: date under the "Entry" line', str(bdate(int(round(ei)))), str(bdate(exp_e)), 'entry line drawn at the wrong date')
                    anchor = exp_e
                d60 = tx('Day 60'); x60i = idx(d60['x'] - 6)
                C.add(cl, 'geometry: "Day 60" line slot (bar index)', x60i, min(anchor + 60 / tfd, 10 ** 9), 'Day 60 placement (entry + 60 days)')
                C.add(cl, 'geometry: date of the "Day 60" line', str(bdate(int(round(x60i)))) if x60i == int(x60i) else f'slot {x60i}',
                      str(bdate(int(anchor + 60 / tfd))), 'Day 60 drawn at wrong date')
                hd = tx('High usually'); hi_i = idx(hd['x'] - 6)
                C.add(cl, 'geometry: "High usually ~day N" slot', hi_i, anchor + round(c['dhigh'] / tfd), 'high-day placement')
                # x-axis date labels = open dates of the bars in those slots
                for t in ch['texts']:
                    if t['y'] == 502:
                        i = idx(t['x'])
                        if i == int(i):
                            C.add(cl, f'x-axis label at slot {int(i)}', t['text'], dshort(bdate(int(i))), 'axis date')
            if mode == 'bHap':   # the example's real path, from daily candles
                day = S.day['ETH']; d0 = dt.date(2024, 9, 22); e = F(str(feed['example_card']['entry_close']))
                w = [(k, day.pos[d0 + dt.timedelta(days=k)]) for k in range(1, 61)]
                mh = max(day.h[j] for k, j in w); kh = next(k for k, j in w if day.h[j] == mh)
                ml = min(day.l[j] for k, j in w); kl = next(k for k, j in w if day.l[j] == ml)
                rng = lambda k: f"days {k - 1 + (k % 2)}–{k + (k % 2)}" if True else ''
                rng = lambda k: f"days {2 * ((k + 1) // 2) - 1}–{2 * ((k + 1) // 2)}"
                C.add(cl, 'what happened: reached +10% / +20%', g2('Reached +10% / +20%'), f"{'Yes' if mh >= e * F(11, 10) else 'No'} / {'Yes' if mh >= e * F(12, 10) else 'No'}", 'outcome')
                C.add(cl, 'what happened: best price', g2('Best price'), f"{P(pct(mh, e))}, {rng(kh)}", 'best (daily day ' + str(kh) + ')')
                C.add(cl, 'what happened: deepest drop', g2('Deepest drop'), f"{P(pct(ml, e))}, {rng(kl)}", 'deepest (daily day ' + str(kl) + ')')
                c10 = day.c[day.pos[d0 + dt.timedelta(days=10)]]
                C.add(cl, 'what happened: day 10 check', g2('Day 10 check'), f"{'Red' if c10 < e else 'Green'}, {P(pct(c10, e))}", 'day 10')
                C.add(cl, 'what happened: price on day 60', g2('Price on day 60'), P(pct(day.c[day.pos[d0 + dt.timedelta(days=60)]], e)), 'day 60')
                ths = [t['text'] for t in ch['texts'] if t['text'].startswith('This one')]
                C.add(cl, 'svg This one (high)', ths[0] if ths else None, f"This one: {money(mh)} · {P(pct(mh, e))} · {rng(kh)}", 'svg best')
                C.add(cl, 'svg This one (low)', ths[1] if len(ths) > 1 else None, f"This one: {money(ml)} · {P(pct(ml, e))} · {rng(kl)}", 'svg low')
                C.add(cl, '"At the alert" hides the outcome', 'yes' if not any(t['text'].startswith('This one') for t in sel['chart']['bAlert']['texts']) and 'WHAT THIS ONE DID' not in sel['chart']['bAlert']['side'] else 'no', 'yes', 'hindsight on alert view')
            # cloud
            pp = PP[asset]
            C.add(cl, 'cloud subtitle', ch['cloudSub'], f"Every past {asset} top-grade signal, n {pp['n']}", 'past paths n')
            d = pp['days'][60]
            C.add(cl, 'cloud day-60 note', re.search(r'Day 60: median \S+, middle half \S+ to \S+%', ch['cloudNote']).group(0),
                  f"Day 60: median {P(d['med'])}, middle half {P(d['q25'])} to {P(d['q75'])}", 'past paths day 60')

    # ------------------------------------------------ previous signals
    prev = [x.strip() for x in cap['prev_section'].split('\n') if x.strip()]
    ledA = sorted([r for r in mine['ledger'] if r['grade'] == 'A+'], key=lambda r: r['entry'], reverse=True)
    # stable order for equal dates: ledger file order
    order = {(r['chart'], r['entry']): i for i, r in enumerate(S.ledger)}
    ledA = sorted(ledA, key=lambda r: (r['entry'], -order[(r['chart'], r['entry'])]), reverse=True)
    for k, o in A_open.items():
        c = cards[k]
        if c['reach10'] < 70: ed = 0
        else:
            g = next((th for th, r in zip((5, 10, 15, 20), c['ladder']) if r['ok'] is not None and r['ok'] < 70), None); ed = -g if g else None
        lost = ed == 0 or (ed is not None and o['worst_so_far_pct'] <= ed)
        where = 'Edge lost or closed' if prev.index(o['chart'] + f"Day {o['days_elapsed']} of 60 · best {P(o['best_so_far_pct'])} · worst {P(o['worst_so_far_pct'])}") > prev.index('Edge lost or closed') else 'Edge intact'
        C.add('page previous signals ' + k, 'row text', next((x for x in prev if x.startswith(o['chart'] + 'Day')), None),
              o['chart'] + f"Day {o['days_elapsed']} of 60 · best {P(o['best_so_far_pct'])} · worst {P(o['worst_so_far_pct'])}", 'open row')
        C.add('page previous signals ' + k, 'group (own-ladder edge rule)', where, 'Edge lost or closed' if lost else 'Edge intact', 'edge grouping')
    if A_open:
        C.add('page previous signals', 'text under "Edge intact" when none is intact', prev[prev.index('Edge intact') + 1],
              'none intact (but 1 open top-grade setup exists)' if prev[prev.index('Edge intact') + 1] == 'No open top-grade setups.' else prev[prev.index('Edge intact') + 1],
              'says "No open top-grade setups." while an open top-grade setup is listed below it')
    rows5 = [x for x in prev if re.match(r'^(ETH|BTC) \dD\d', x)]
    for i, r in enumerate(ledA[:5]):
        shown = rows5[i] if i < len(rows5) else None
        exp = f"{r['chart']}{dlong(r['entry'])} · best {P(F(r['best_exact']))} · worst {P(F(r['dd_exact']))}"
        C.add(f'page previous signals recent #{i + 1}', 'row text', shown, exp, 'recent closed row')
        badge = prev[prev.index(shown) + 1] if shown in prev else None
        C.add(f'page previous signals recent #{i + 1}', 'badge', badge, 'Reached +20%' if r['r20'] else 'Rose 10%' if r['r10'] else 'Missed', 'badge')

    # ------------------------------------------------ record
    for a, rec in cap['record'].items():
        sub = [r for r in ledA if a == 'all' or r['asset'] == a]
        sub = sorted(sub, key=lambda r: r['entry'], reverse=True)
        C.add(f'page past signals {a}', 'count line', rec['count'], f"{len(sub)} signals · {sum(1 for r in sub if not r['r10'])} missed +10%", 'count')
        C.add(f'page past signals {a}', 'row count', len(rec['rows']), len(sub), 'rows')
        shown = {(r[0], r[1]): r for r in rec['rows']}
        for r in sub:
            k = (dlong(r['entry']), r['chart'])
            s = shown.get(k)
            exp = [dlong(r['entry']), r['chart'], money(F(r['entry_exact'])), 'Yes' if r['r10'] else 'No', 'Yes' if r['r20'] else 'No',
                   P(F(r['best_exact'])), P(F(r['dd_exact'])), P(F(r['ret_exact'])), str(r['dpk'])]
            names = ['Confirmed', 'Chart', 'Entry close', 'Rose 10%', 'Reached +20%', 'Best', 'Deepest drop', 'Day 60', 'High on day']
            for j, nm in enumerate(names[2:], 2):
                C.add(f"page past signals {a} {r['chart']} {r['entry']}", nm, s[j] if s else None, exp[j], 'record cell')
        sm = [x.strip() for x in rec['sum'].split('\n') if x.strip()]
        for asset in (('ETH', 'BTC') if a == 'all' else (a,)):
            i0 = sm.index(asset); blk = sm[i0:i0 + 12]
            gs = GS[f'{asset} A+']; mi = MI[f'{asset} A+']
            gb = lambda lab: blk[blk.index(lab) + 1] if lab in blk else None
            L = f'page past signals {a} summary {asset}'
            C.add(L, 'signals', blk[1], f"{gs['n']} signals", 'n')
            C.add(L, 'Rose 10% in 60 days', gb('Rose 10% in 60 days'), f"{gs['reach10']}%", 'reach10')
            C.add(L, 'Reached +20% in 60 days', gb('Reached +20% in 60 days'), f"{gs['reach20']}%", 'reach20')
            C.add(L, 'Rose 10%, never fell 25.3%', gb('Rose 10%, never fell 25.3%'), f"{gs['surv10']}%", 'surv10')
            C.add(L, 'Median deepest dip', gb('Median deepest dip'), P(gs['medDip']), 'median dip')
            C.add(L, 'Misses: median peak first', gb('Misses: median peak first'), P(mi['median_peak_pct']), 'misses median peak')
        C.add(f'page past signals {a}', 'entry-quality footnote', 'yes' if 'not a return or a track record' in rec['fine'] else 'no', 'yes', 'label')
    C.add('page', 'JavaScript errors', len(cap['errors']), 0, 'page errors')
    json.dump(C.rows, open(os.path.join(OUT, f'pagechecks_{tag}.json'), 'w'), indent=0)
    bad = [r for r in C.rows if r['ok'] != 'yes']
    print(tag, len(C.rows), 'page checks', len(bad), 'disagreements')
    for r in bad: print('  ', r['location'], '|', r['label'], '|', r['shown'], '|', r['yours'], '|', r['cause'])


if __name__ == '__main__':
    main(*sys.argv[1:4])
