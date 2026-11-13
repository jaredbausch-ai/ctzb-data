"""Audit 18: full page check of one state (check 8). usage: run_page.py <state> <root> <today> <out csv> [dump dir]"""
import csv, datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import core as K, stage_data as SD, page_lib as P, page_expect as PE

BAD = re.compile(r"\$\{|undefined|NaN|null|\[object|Infinity|n/a%")
READ_NUMS = ['60', '10%', '60', '25.3%', '3.3', '5%', '60', '60', '5%', '10%', '15%', '20%', '10%', '25.3%', '70%', '10%', '60', '60', '60']


def run(state, root, today, dump_dir=None, site_kw=None, ctx=None, C=None):
    if ctx is None:
        C, ctx = SD.run(state, root, today)
    ex_json = json.load(open(os.path.join(root, 'docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json')))
    pc = PE.PageCheck(C, ctx, root, ex_json)
    M = pc.models()
    # the example chart file against the raw ETH 2D candles
    c2 = ctx['ch'][('ETH', '2D')]
    if today >= K.D(2024, 11, 24):      # (a replay of an earlier date has no candles for the example)
        bad = 0
        for b in ex_json['bars']:
            i = c2.pos.get(K.utcdate(b['t']))
            if i is None or (b['o'], b['h'], b['l'], b['c']) != (c2.o[i], c2.h[i], c2.l[i], c2.c[i]): bad += 1
        C.add('page example file', f"{len(ex_json['bars'])} bars = raw ETH 2D candles (o/h/l/c)", bad, 0)
        eb = ex_json['bars'][ex_json['entry_index']]
        C.add('page example file', 'entry_index is the bar closing 2024-09-22', str(K.bar_close_date(K.utcdate(eb['t']), 2)), '2024-09-22')
        C.add('page example file', 'entry_close', ex_json['entry_close'], float(c2.xc[c2.pos[K.utcdate(eb['t'])]]))
        C.add('page example file', 'bars run consecutively through day 60', 'yes' if K.utcdate(ex_json['bars'][ex_json['entry_index'] + 30]['t']) == K.D(2024, 11, 20) else 'no', 'yes')
    # candle files the chart reads = the last 70 raw bars
    for (a, tf), c in ctx['ch'].items():
        p = os.path.join(root, 'datasets', f'candles_{a.lower()}_{tf.lower()}.csv')
        rows = list(csv.DictReader(open(p))) if os.path.exists(p) else []
        tail = c.raw[-70:]
        bad = sum(1 for r, t in zip(rows, tail) if (int(r['time']), r['open'], r['high'], r['low'], r['close']) != t) + abs(len(rows) - len(tail))
        C.add(f'page candles {a} {tf}', 'chart file = the last 70 raw bars', bad, 0)
    dumps = {}
    with sync_playwright() as pw:
        s = P.Site(pw, root, **(site_kw or {}))
        s.open('now')
        d = s.dump(); dumps['initial'] = d
        init = M['best'].x['signal_id'] if M['best'] else (M['opens'][0].x['signal_id'] if M['opens'] else None)
        loc = 'page Now (as opened)'
        pc.chrome(loc, d, M, init)
        C.add(loc, 'opens on the example only when nothing is live or forming', d['preview'], init is None)
        C.add(loc, 'no raw placeholder in the page text', len(BAD.findall(d['body'])), 0)
        sel = [(m.x['signal_id'], m) for m in M['opens']] + [(m.x['signal_id'], m) for m in M['forming']]
        if not sel:
            # the quiet card: nothing top-grade live, nothing forming. The page opens on the example; switch it off.
            if d['preview']:
                s.pg.click('#previewSwitch'); s.pg.wait_for_timeout(300)
            q = s.dump(); dumps['quiet'] = q; loc = 'page Now quiet card'
            gate_on = ctx['gate'](today)
            y1 = today.year - 1
            nA = sum(1 for r in ctx['L'] if r['grade'] == 'A+' and 2020 <= int(r['entry'][:4]) <= y1)
            per = (f"Top-grade setups come about {K.rnd(K.Fr(nA, y1 - 2020 + 1))} times a year (2020 to {y1} average; bear years, when the market filter is off, are included)."
                   if nA and y1 >= 2020 else '')
            body = (f"The market filter is on. Nothing at the top grade is forming or confirmed today. {per}".strip() if gate_on
                    else "The market filter is off, so the system is quiet. It stays quiet in downtrends, sometimes for a year.")
            C.add(loc, 'state', q['card']['state'], 'No setup right now')
            C.add(loc, 'text (filter state, signals a year)', q['card']['empty'], f"Waiting for the next one {body} You'll get a push alert the moment one confirms.")
            C.add(loc, 'no raw placeholder', len(BAD.findall(q['body'])), 0)
        best_id = M['best'].x['signal_id'] if M['best'] else None
        for sid, m in sel:
            s.show('now'); s.select(sid); d = s.dump(); dumps[sid + ' now'] = d
            loc = f"page Now {'Live' if m.kind == 'open' else 'Forming'} {sid}"
            pc.card(loc, d, m, best_id)
            C.add(loc, 'picker button pressed', [b['sel'] for r in d['picker'] for b in r['btns'] if b['pressed'] == 'true'], [sid])
            C.add(loc, 'no raw placeholder', len(BAD.findall(d['body'])), 0)
            s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump(); dumps[sid + ' chart'] = d
            pc.chart(f"page Chart {'Live' if m.kind == 'open' else 'Forming'} {sid}", d, m)
            C.add(f"page Chart {sid}", 'no raw placeholder', len(BAD.findall(d['body'])), 0)
        # the example
        if M['example']:
            m = M['example']
            s.show('now'); s.select('example'); d = s.dump(); dumps['example now'] = d
            pc.card('page Now Example', d, m)
            s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump(); dumps['example chart alert'] = d
            pc.chart('page Chart Example (At the alert)', d, m, happened=False)
            C.add('page Chart Example (At the alert)', 'outcome texts absent', len([t for t in d['chart']['svg'] if t['tag'] == 'text' and t['text'].startswith('This one')]), 0)
            s.pg.click('#bHap'); s.pg.wait_for_timeout(300); d = s.dump(); dumps['example chart happened'] = d
            pc.chart('page Chart Example (What happened)', d, m, happened=True)
            C.add('page Chart Example', 'no raw placeholder', len(BAD.findall(d['body'])), 0)
        else:
            s.show('now'); s.select('example'); d = s.dump(); dumps['example now'] = d
            C.add('page Now Example', 'no example card in the feed -> says unavailable', d['card']['state'], 'Example unavailable')
        # past signals
        s.show('record')
        for a in ('all', 'ETH', 'BTC'):
            s.pg.click(f'.seg button[data-asset="{a}"]'); s.pg.wait_for_timeout(250); d = s.dump(); dumps['record ' + a] = d
            pc.record(f'page Past signals ({a})', d, a)
        C.add('page Past signals', 'heading', d['record']['head'].upper(), 'EVERY TOP-GRADE SIGNAL WHOSE 60 DAYS HAVE CLOSED · COMPUTED, NEVER TRADED')
        C.add('page Past signals', 'no raw placeholder', len(BAD.findall(d['body'])), 0)
        s.show('read'); d = s.dump(); dumps['read'] = d
        nums = re.findall(r'\d+(?:\.\d+)?%?', d['read'])
        C.add('page How to read', 'every number in the text', ' '.join(nums), ' '.join(READ_NUMS))
        C.add('page How to read', 'posting bar from the feed', d['howBar'], '70% bar')
        C.add('page', 'no script error on any view', len(s.errs), 0, cause='; '.join(s.errs[:2]))
        s.close()
    if dump_dir:
        os.makedirs(dump_dir, exist_ok=True)
        json.dump(dumps, open(os.path.join(dump_dir, f'dump_{state}.json'), 'w'), ensure_ascii=False)
    return C, ctx, dumps


if __name__ == '__main__':
    state, root, today, out = sys.argv[1:5]
    C, ctx, _ = run(state, root, dt.date.fromisoformat(today), dump_dir=sys.argv[5] if len(sys.argv) > 5 else None)
    with open(out, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writerows(C.rows)
    n, b = C.summary()
    print(state, 'comparisons', n, 'disagreements', b)
    for r in C.rows:
        if r[5] != 'ok': print('  ', r[1], '|', r[2], '| shown:', str(r[3])[:160], '| mine:', str(r[4])[:160], '|', r[6])
