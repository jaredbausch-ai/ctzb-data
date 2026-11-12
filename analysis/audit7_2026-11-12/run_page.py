import datetime as dt, json, re, statistics as st, pickle
import audit as A
import page_check as P
from build import State
from lib import *

CK = A.CK


def my_paths(S, G):
    Ps = [p for p in (A.path_of(S, s) for s in G) if p is not None]
    return {d: (q_lin([p[d] for p in Ps], .25), q_lin([p[d] for p in Ps], .5), q_lin([p[d] for p in Ps], .75)) for d in range(61)}, len(Ps)


def run(name, clk):
    S = State(name, clk); F = S.feed()
    A.check_ledger(S); A.check_misses(S, F); A.check_cards(S, F)
    n0 = len(CK.rows)
    pg = json.load(open(f'page_{name}.json'))
    ex_json = json.load(open(f'{S.dir}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
    st_ = name
    sigs = {f"{s['a']}-{s['tf']}-{s['d0']}": s for v in S.sig.values() for s in v}
    for sid, mc in S.mycards.items():
        mc['confirms_label'] = None
        if mc['kind'] == 'open': mc['entry_close_exact'] = sigs[sid]['entry']
        if mc['kind'] == 'forming':
            mc['price_now_exact'] = S.day[mc['asset']].C[-1]
            d = dt.date.fromisoformat(mc['confirms_on'])
            mc['confirms_label'] = f"{d.day} {d.strftime('%b') if d.month != 9 else 'Sept'} {d.year}"
    # ---------------- header, banner, footer
    v0 = pg['views'][0]
    gen = dt.datetime.fromisoformat(F['generated_at'].replace('Z', '+00:00'))
    CK.add(st_, 'page banner', 'scored date', P.pdate(re.search(r'scored (\d+ \w+ \d{4})', v0['review']).group(1)).isoformat(), str(S.today), 'value')
    CK.add(st_, 'page banner', 'feed time', re.search(r'feed (\d\d:\d\d) UTC', v0['review']).group(1), gen.strftime('%H:%M'), 'value')
    CK.add(st_, 'page header', 'market filter', re.search(r'Market filter: (\w+)', v0['header']).group(1), 'on' if S.gate(S.today) else 'off', 'value')
    last_closed = max(d for d in S.day['ETH'].D if d < S.today)
    last_closed_b = max(d for d in S.day['BTC'].D if d < S.today)
    CK.add(st_, 'page footer', 'daily candles closed through', P.pdate(re.search(r'closed through (\d+ \w+ \d{4})', v0['footer']).group(1)).isoformat(), str(min(last_closed, last_closed_b)), 'value')
    CK.add(st_, 'page footer', 'updated', re.search(r'updated (\d\d:\d\d) UTC', v0['footer']).group(1), gen.strftime('%H:%M'), 'value')
    CK.add(st_, 'page footer', 'checks', 'passed' in v0['footer'], True, 'value')
    # ---------------- picker
    opens_ap = [sid for sid, mc in S.mycards.items() if mc['kind'] == 'open' and mc['grade'] == 'A+']
    form = sorted([sid for sid, mc in S.mycards.items() if mc['kind'] == 'forming'], key=lambda k: -S.mycards[k]['figs']['reach10'])
    pk = v0['picker']
    exp_sel = [s for s in sorted(opens_ap, key=lambda k: [o['signal_id'] for o in F['open_signals']].index(k))] + [s for s in form if S.mycards[s]['grade'] == 'A+'] + [s for s in form if S.mycards[s]['grade'] != 'A+'] + ['example']
    shown_sel = [b['sel'] for b in pk]
    CK.add(st_, 'page picker', 'buttons (set)', ','.join(sorted(shown_sel)), ','.join(sorted(exp_sel)), 'membership')
    fo = [s for s in shown_sel if s in S.mycards and S.mycards[s]['kind'] == 'forming']
    r10 = [S.mycards[s]['figs']['reach10'] for s in fo]
    CK.add(st_, 'page picker', 'forming buttons ranked by rose-10% odds (ties in any order)', ' '.join(map(str, r10)), ' '.join(map(str, sorted(r10, reverse=True))), 'value')
    CK.add(st_, 'page picker', 'live buttons first, example last', ','.join(shown_sel[:len(opens_ap)]) + '|' + shown_sel[-1], ','.join(sorted(opens_ap)) + '|example', 'value')
    for b in pk:
        loc = f"page picker {b['sel']}"
        if b['sel'] == 'example':
            CK.add(st_, loc, 'text', b['text'], 'Example: ETH 2D, Sep 2024', 'label'); continue
        mc = S.mycards[b['sel']]
        if mc['kind'] == 'open':
            o = mc['open']
            CK.add(st_, loc, 'Day N', P.find_num(r'Day (\d+)', b['text']), o['days_elapsed'], 'value')
            CK.add(st_, loc, 'best', P.find_num(r'best ([+−\-]?[\d\.]+)%', b['text']), o['best_so_far_pct'], 'value')
            CK.add(st_, loc, 'worst', P.find_num(r'worst ([+−\-]?[\d\.]+)%', b['text']), o['worst_so_far_pct'], 'value')
        else:
            CK.add(st_, loc, 'odds shown (rose 10%)', P.find_num(r'(\d+)%', b['text']), mc['figs']['reach10'], 'value')
            CK.add(st_, loc, 'grade wording', 'not top grade' in b['text'], mc['grade'] != 'A+', 'value')
            CK.add(st_, loc, 'confirms', P.pdate(re.search(r'confirms (\d+ \w+ \d{4})', b['text']).group(1)).isoformat(), mc['confirms_on'], 'value')
            CK.add(st_, loc, 'unlabelled percentage in the button', b['text'].replace('\n', ' '), 'a percentage with its meaning (rose 10% within 60 days)',
                   'label: the picker shows a bare "NN%" with no words saying what it measures', ok=False)
    # initial selection
    exp_init = (form[0] if form else (opens_ap[0] if opens_ap else 'example'))
    if [s for s in form if S.mycards[s]['grade'] == 'A+']: exp_init = [s for s in form if S.mycards[s]['grade'] == 'A+'][0]
    CK.add(st_, 'page picker', 'selected on load', ','.join(v0['selected_initial']), exp_init if form else (opens_ap[0] if opens_ap else 'example'), 'value')
    # ---------------- previous signals column
    def ostatus(sid):
        mc = S.mycards[sid]; o = mc['open']
        if o['best_so_far_pct'] is not None and o['best_so_far_pct'] >= 10: return 'intact'
        eg = P.setup_edge(mc['figs'])
        if eg == 0: return 'fading'
        return 'fading' if eg is not None and o['worst_so_far_pct'] is not None and o['worst_so_far_pct'] <= eg else 'intact'
    minis = v0['prev_minis']
    ledAp = [s for s in S.led if s['grade'] == 'A+']
    recent = sorted(ledAp, key=lambda s: s['d0'], reverse=True)[:5]
    exp_minis = [('intact', sid) for sid in opens_ap if ostatus(sid) == 'intact'] + [('fading', sid) for sid in opens_ap if ostatus(sid) == 'fading'] + [('closed', s) for s in recent]
    CK.add(st_, 'page previous signals', 'entries', len(minis), len(exp_minis), 'membership')
    for m, (kind, x) in zip(minis, exp_minis):
        if kind != 'closed':
            mc = S.mycards[x]; o = mc['open']; loc = f'page previous signals {x}'
            CK.add(st_, loc, 'chart', m['name'], mc['chart'], 'value')
            CK.add(st_, loc, 'Day N of 60', P.find_num(r'Day (\d+) of 60', m['sub']), o['days_elapsed'], 'value')
            CK.add(st_, loc, 'best', P.find_num(r'best ([+−\-]?[\d\.]+)%', m['sub']), o['best_so_far_pct'], 'value')
            CK.add(st_, loc, 'worst', P.find_num(r'worst ([+−\-]?[\d\.]+)%', m['sub']), o['worst_so_far_pct'], 'value')
            CK.add(st_, loc, 'badge (edge by its own ladder)', m['badge'], 'On track' if kind == 'intact' else 'Edge lost', 'value')
        else:
            s = x; loc = f"page previous signals {s['chart']} {s['d0']}"
            CK.add(st_, loc, 'chart', m['name'], s['chart'], 'value')
            CK.add(st_, loc, 'date', P.pdate(m['sub']).isoformat(), str(s['d0']), 'value')
            CK.add(st_, loc, 'best (60-day high vs entry)', P.find_num(r'best ([+−\-]?[\d\.]+)%', m['sub']), rnd(s['m']['up'], 1), 'value')
            CK.add(st_, loc, 'worst (60-day low vs entry)', P.find_num(r'worst ([+−\-]?[\d\.]+)%', m['sub']), rnd(s['m']['dd'], 1), 'value')
            CK.add(st_, loc, 'badge', m['badge'], 'Reached +20%' if s['m']['r20'] else 'Rose 10%' if s['m']['r10'] else 'Missed', 'value')
    # ---------------- each selected card + chart
    for v in pg['views'][1:]:
        sel = v['tag'].split(' ', 1)[1]
        mc = S.mycards[sel]; loc = f'page card {sel}'
        known = dt.date(2024, 9, 22) if mc['kind'] == 'example' else None
        mi = P.misses_for(S, mc['asset'], mc['grade'], known)
        P.check_card_view(S, st_, loc, v, mc, mi, F)
        for mode in ('alert', 'happened'):
            cv = v.get('chart_' + mode)
            if not cv: continue
            cl = f'page chart {sel} {mode}'
            if mc['kind'] != 'example':
                CK.add(st_, cl, 'toggle hidden for a live/forming setup', cv['toggle_hidden'], True, 'value')
            geo = P.check_chart(S, st_, cl, cv, mc, mode, F, ex_json)
            P.check_side(S, st_, cl, cv, mc, geo, mc['kind'])
            if mc['kind'] == 'example':
                G = [s for s in S.led if s['a'] == 'ETH' and s['grade'] == 'A+' and s['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)]
                sub = 'ETH top-grade signals whose 60 days had closed by 22 Sept 2024'
            else:
                G = [s for s in S.led if s['a'] == mc['asset'] and s['grade'] == 'A+']
                sub = f"Every past {mc['asset']} top-grade signal"
            Pq, n = my_paths(S, G)
            P.check_cloud(S, st_, cl, cv, mc, (Pq, n, sub))
            # chart title / subtitle numbers
            if mc['kind'] == 'open':
                CK.add(st_, cl, 'title day N of 60', P.find_num(r'DAY (\d+) OF 60', cv['title'].upper()), mc['open']['days_elapsed'], 'value')
                CK.add(st_, cl, 'subtitle entry close', P.find_num(r'entry close (\$[\d,]+\.\d\d)', cv['sub']), mc['entry_close'], 'value')
                CK.add(st_, cl, 'subtitle confirmed', P.pdate(re.search(r'Confirmed (\d+ \w+ \d{4})', cv['sub']).group(1)).isoformat(), mc['confirms_on'], 'value')
                CK.add(st_, cl, 'subtitle sample', re.search(r'own card \((.*)\)\.', cv['sub']).group(1), mc['sample'], 'value')
            elif mc['kind'] == 'forming':
                CK.add(st_, cl, 'subtitle low day', P.pdate(re.search(r'Low (\d+ \w+ \d{4})', cv['sub']).group(1)).isoformat(), mc['low_day'], 'value')
                CK.add(st_, cl, 'subtitle confirms', P.pdate(re.search(r'confirms (\d+ \w+ \d{4})', cv['sub']).group(1)).isoformat(), mc['confirms_on'], 'value')
                CK.add(st_, cl, "subtitle today's price", P.find_num(r"today's price \((\$[\d,]+\.\d\d)\)", cv['sub']), mc['price_now'], 'value')
            else:
                CK.add(st_, cl, 'subtitle entry close', P.find_num(r'entry close (\$[\d,]+\.\d\d)', cv['sub']), mc['entry_close'], 'value')
    # ---------------- past signals tab
    for a_, rec in pg['record'].items():
        rows = sorted([s for s in ledAp if a_ == 'all' or s['a'] == a_], key=lambda s: s['d0'], reverse=True)
        loc = f'page past signals {a_}'
        CK.add(st_, loc, 'count', P.find_num(r'(\d+) signals', rec['count']), len(rows), 'value')
        CK.add(st_, loc, 'missed +10%', P.find_num(r'(\d+) missed', rec['count']), sum(not s['m']['r10'] for s in rows), 'value')
        CK.add(st_, loc, 'table rows', len(rec['rows']), len(rows), 'membership')
        bad = []
        byk = {(P.pdate(r[0]).isoformat(), r[1]): r for r in rec['rows']}
        CK.add(st_, loc, 'rows in date order (newest first)', 'yes' if [P.pdate(r[0]) for r in rec['rows']] == sorted([P.pdate(r[0]) for r in rec['rows']], reverse=True) else 'no', 'yes', 'value')
        for s in rows:
            r = byk.get((str(s['d0']), s['chart']))
            if r is None:
                CK.add(st_, loc, f"row {s['chart']} {s['d0']}", 'absent', 'present', 'membership'); continue
            exp = [str(s['d0']), s['chart'], rnd(s['entry'], 2), 'Yes' if s['m']['r10'] else 'No', 'Yes' if s['m']['r20'] else 'No',
                   rnd(s['m']['up'], 1), rnd(s['m']['dd'], 1), rnd(s['m']['ret'], 1), s['m']['dpk']]
            got = [P.pdate(r[0]).isoformat(), r[1], P.num(r[2]), r[3], r[4], P.num(r[5]), P.num(r[6]), P.num(r[7]), int(r[8])]
            for h, g_, e_ in zip(rec['head'], got, exp):
                CK.add(st_, f"{loc} {s['chart']} {s['d0']}", h, g_, e_, 'value')
        for g in ('ETH', 'BTC'):
            if a_ not in ('all', g): continue
            G = [s for s in ledAp if s['a'] == g]; n = len(G)
            blk = re.search(rf'{g}\n(\d+) signals\n(.*?)(?=\n(?:ETH|BTC)\n|\Z)', rec['sum'], re.S)
            l2 = f'{loc} summary {g}'
            CK.add(st_, l2, 'signals', int(blk.group(1)), n, 'value')
            b = blk.group(2)
            CK.add(st_, l2, 'Rose 10% in 60 days', P.find_num(r'Rose 10% in 60 days\n(\d+)%', b), pctr(sum(s['m']['r10'] for s in G), n), 'value')
            CK.add(st_, l2, 'Reached +20% in 60 days', P.find_num(r'Reached \+20% in 60 days\n(\d+)%', b), pctr(sum(s['m']['r20'] for s in G), n), 'value')
            CK.add(st_, l2, 'Rose 10%, never fell 25.3%', P.find_num(r'never fell 25.3%\n(\d+)%', b), pctr(sum(s['m']['r10'] and not s['m']['fell25'] for s in G), n), 'value')
            CK.add(st_, l2, 'Median deepest dip', P.find_num(r'Median deepest dip\n([+−\-][\d\.]+)%', b), medr([s['m']['dd'] for s in G], 1), 'value')
            mi = P.misses_for(S, g, 'A+')
            CK.add(st_, l2, 'Misses: median best price', P.find_num(r'median best price\n([+−\-][\d\.]+)%', b), rnd(mi['median_peak_exact'], 1), 'value')
        CK.add(st_, loc, 'title', rec['title'], 'Every top-grade signal whose 60 days have closed', 'label: "Every top-grade signal" omits the open one(s) still inside their 60 days',
               ok=not any(mc['kind'] == 'open' and mc['grade'] == 'A+' and (a_ == 'all' or mc['asset'] == a_) for mc in S.mycards.values()))
    print(name, 'page checks', len(CK.rows) - n0, 'failed', sum(r['ok'] == 'no' for r in CK.rows[n0:]))
    return S


for name, clk in (('replay_0414', dt.datetime(2026,11,12,4,14,tzinfo=dt.timezone.utc)), ('current', dt.datetime(2026,11,12,17,7,11,tzinfo=dt.timezone.utc))):
    run(name, clk)
rows = [r for r in CK.rows if r['location'].startswith('page')]
pickle.dump(rows, open('page_checks.pkl', 'wb'))
import collections
bad = [r for r in rows if r['ok'] == 'no']
print(collections.Counter((r['state'], r['label']) for r in bad).most_common(80))
