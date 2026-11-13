"""Damage test for the member page (13 Nov 2026, after audit #21).

The page uses the feed only if it passes one strict check (the schema inside the page; feedcheck.py reads
the same block, and feed_live.py refuses to publish a feed that fails it). This test takes real feeds and
damages every field the page reads, in every way (missing, null, wrong type, out of range, unknown word,
bad date, list emptied / cut / doubled / reversed, sign flipped, ...), and checks:

  1. real feeds, a held feed and the fail-closed feed all pass the check;
  2. the page's verdict (window.__feedProblems) and the pipeline's (feedcheck.problems) agree on every
     damaged feed;
  3. every kind of damaged feed the page still ACCEPTS renders on every tab with no script error and no raw
     placeholder (NaN, undefined, null, [object, Infinity, ${, $-);
  4. REJECTED feeds show "Data unavailable", with no script error and no raw placeholder;
  5. every feed field the page reads is in the schema (recorded with a Proxy while every tab and button is used);
  6. the lead-trader file, the ledger and the chart files: damaged ones read "unavailable", never garbage.

    python3 tests/test_feed_damage.py [state dir ...]      # default: this repo + a replay of 2026-11-12
Env: RENDER_LIMIT (accepted kinds rendered per state, default all), REJECT_LIMIT (default 40).
Needs playwright + chromium. Entry quality only: computed signals, not fills.
"""
import copy, csv, datetime as dt, json, os, random, re, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

R0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R0)
import feedcheck  # noqa: E402

BAD = re.compile(r"\$\{|undefined|NaN|\bnull\b|n/a%|n/ax|\[object|Infinity|\$-")
VALUES = [None, "", "abc", 0, -1, 150, 1e12, 3.7, True, False, [], {}, [None], "NaN", "2099-01-01", "2026-02-30", "1999-01-01",
          "2026-11-12T25:00:00Z", "A+", "ETH", "BTC 2D", "Bullish", "lost", 5, "5", 61, -0.0001, 100.0001]
JS_APPLY = """(ops) => ops.map((op) => {
  const f = structuredClone(window.__base[op.base]);
  if (!op.path.length) return window[op.fn](op.value).length > 0;
  let cur = f; for (const k of op.path.slice(0, -1)) cur = cur[k];
  const key = op.path[op.path.length - 1];
  if (op.op === "del") { if (Array.isArray(cur)) cur.splice(key, 1); else delete cur[key]; }
  else if (op.op === "set") cur[key] = op.value;
  else if (op.op === "cut") cur[key] = cur[key].slice(0, -1);
  else if (op.op === "double") cur[key].push(structuredClone(cur[key][cur[key].length - 1]));
  else if (op.op === "reverse") cur[key].reverse();
  return window[op.fn](f).length > 0;
})"""
RECORDER = r"""
window.__paths = {};
(() => {
  const wrap = (v, path) => {
    if (v === null || typeof v !== 'object') return v;
    return new Proxy(v, { get(t, k, r) {
      if (typeof k === 'symbol') return Reflect.get(t, k, r);
      const val = Reflect.get(t, k, r);
      if (typeof val === 'function') return val;
      if (Array.isArray(t)) { if (k === 'length') return val; return wrap(val, path + '[]'); }
      const p = path + '.' + k; window.__paths[p] = 1;
      return wrap(val, p);
    } });
  };
  const oj = Response.prototype.json;
  Response.prototype.json = async function () { const j = await oj.call(this); const u = this.url;
    return u.includes('ctzb_feed') ? wrap(j, 'feed') : u.includes('trades.json') ? wrap(j, 'trades') : j; };
})();
"""
TRADES = {"label": "x", "updated_at": "2026-11-12T04:00:00Z", "trades": [
    {"id": "1:open", "mode": "live", "time": "2026-11-10T12:00:00.123Z", "asset": "BTC", "instrument": "perp", "direction": "long", "action": "open",
     "price": 101000.5, "leverage": 3.3, "size_pct": 10.0, "reduced_pct": None, "move_pct": None, "account_pct": None, "held_days": None},
    {"id": "2:close", "mode": "live", "time": "2026-10-20T12:00:00Z", "asset": "ETH", "instrument": "perp", "direction": "long", "action": "close",
     "price": 3300, "leverage": 3.3, "size_pct": 10.0, "reduced_pct": None, "move_pct": 10.0, "account_pct": 3.1, "held_days": 19.0}]}


def schema_paths(schema, root):
    out = set()
    def walk(spec, p):
        out.add(p)
        if isinstance(spec, str):
            if spec.startswith('@'): walk(schema['defs'][spec[1:]], p)
        elif isinstance(spec, list): walk(spec[0], p + '[]')
        else:
            for k, v in spec.items(): walk(v, p + '.' + k.rstrip('?'))
    walk(schema[root], root)
    return out


def nodes(v, path=(), gen='feed'):
    """Every node as (concrete path, generic path). Lists: first and last item only."""
    yield path, gen
    if isinstance(v, dict):
        for k in v: yield from nodes(v[k], path + (k,), gen + '.' + k)
    elif isinstance(v, list) and v:
        for i in sorted({0, len(v) - 1}): yield from nodes(v[i], path + (i,), gen + '[]')


def getp(obj, path):
    for k in path: obj = obj[k]
    return obj


def ops_for(base, root, known):
    """Every damage, as JSON-safe ops: (generic path, kind, op)."""
    for val, name in (([], 'a list'), ("x", 'text'), (None, 'null'), (5, 'a number'), ({}, 'an empty object'), (True, 'true')):
        yield root, 'whole file is ' + name, {'path': [], 'op': 'set', 'value': val}
    for path, gen in nodes(base, gen=root):
        if not path or gen not in known: continue
        old = getp(base, path); P = list(path)
        yield gen, 'missing', {'path': P, 'op': 'del'}
        for val in VALUES:
            if type(val) == type(old) and val == old: continue
            yield gen, json.dumps(val), {'path': P, 'op': 'set', 'value': val}
        if isinstance(old, list) and old:
            yield gen, 'cut by one', {'path': P, 'op': 'cut'}
            yield gen, 'last item doubled', {'path': P, 'op': 'double'}
            if len(old) > 1: yield gen, 'reversed', {'path': P, 'op': 'reverse'}
        if isinstance(old, (int, float)) and not isinstance(old, bool):
            for val, name in ((-old, 'sign flipped'), (old + 0.5, 'plus a half'), (old * 1000 + 1000, 'times 1000'), (str(old), 'as text'), (old + 1, 'plus one'), (old - 1, 'minus one')):
                if val != old: yield gen, name, {'path': P, 'op': 'set', 'value': val}
        if isinstance(old, str) and old:
            for val, name in ((old.lower(), 'lower case'), (old.upper(), 'upper case'), (old + ' ', 'trailing space'), (old[:-1], 'last character cut'), ('  ', 'blank')):
                if val != old: yield gen, name, {'path': P, 'op': 'set', 'value': val}
        if isinstance(old, bool):
            yield gen, 'flipped', {'path': P, 'op': 'set', 'value': not old}


def applied(base, op):
    """A damaged deep copy (for rendering)."""
    if not op['path']: return copy.deepcopy(op['value'])
    f = copy.deepcopy(base); cur = getp(f, op['path'][:-1]); key = op['path'][-1]
    if op['op'] == 'del':
        if isinstance(cur, list): del cur[key]
        else: cur.pop(key, None)
    elif op['op'] == 'set': cur[key] = copy.deepcopy(op['value'])
    elif op['op'] == 'cut': cur[key] = cur[key][:-1]
    elif op['op'] == 'double': cur[key].append(copy.deepcopy(cur[key][-1]))
    elif op['op'] == 'reverse': cur[key].reverse()
    return f


def verdict(base, op, fn):
    """The pipeline's verdict on one damage, applied in place and undone (no full copy)."""
    if not op['path']: return bool(fn(op['value']))
    cur = getp(base, op['path'][:-1]); key = op['path'][-1]; saved = copy.copy(cur)
    try:
        if op['op'] == 'del':
            if isinstance(cur, list): del cur[key]
            else: cur.pop(key, None)
        elif op['op'] == 'set': cur[key] = copy.deepcopy(op['value'])
        elif op['op'] == 'cut': cur[key] = cur[key][:-1]
        elif op['op'] == 'double': cur[key] = cur[key] + [copy.deepcopy(cur[key][-1])]
        elif op['op'] == 'reverse': cur[key] = cur[key][::-1]
        return bool(fn(base))
    finally:
        if isinstance(cur, list): cur[:] = saved
        else: cur.clear(); cur.update(saved)


class Site:
    """The page served from a state folder, with any file replaceable."""
    def __init__(self, browser, R, record=False):
        self.R = R; self.page_html = open(f'{R0}/docs/artifacts/member-site/index.html', encoding='utf-8').read()
        self.feed = json.load(open(f'{R}/feed/ctzb_feed.json')); self.base = copy.deepcopy(self.feed)
        self.ledger = open(f'{R}/datasets/ledger.csv').read(); self.trades = None; self.candle_edit = None
        self.ex = open(f'{R0}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json').read()
        self._c = {}; self.errs = []
        self.pg = browser.new_page(viewport={'width': 1440, 'height': 900})
        self.pg.on('pageerror', lambda e: self.errs.append(str(e)))
        self.pg.on('console', lambda m: self.errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        self.pg.route('**/*', self._route)
        if record: self.pg.add_init_script(RECORDER)
        self.pg.clock.install(time=self.base['generated_at'])

    def _candles(self, a, tf):
        if (a, tf) not in self._c:
            p = f'{self.R}/datasets/candles_{a.lower()}_{tf.lower()}.csv'
            self._c[(a, tf)] = {'chart': f'{a} {tf}', 'bars': [{'t': float(r['time']), 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']), 'c': float(r['close'])} for r in csv.DictReader(open(p))]} if os.path.exists(p) else None
        return self._c[(a, tf)]

    def _route(self, route):
        u = route.request.url
        if u.endswith('/'): return route.fulfill(body='<!doctype html><html><head><meta charset=utf-8></head><body>' + self.page_html + '</body></html>', content_type='text/html')
        if u.endswith('ctzb_feed.json'): return route.fulfill(body=json.dumps(self.feed), content_type='application/json')
        if u.endswith('trades.json'): return route.fulfill(body=json.dumps(self.trades), content_type='application/json') if self.trades is not None else route.fulfill(status=404, body='x')
        if u.endswith('ledger.csv'): return route.fulfill(body=self.ledger)
        if 'example_' in u: return route.fulfill(body=self.ex, content_type='application/json')
        if '/candles/' in u:
            a, tf = u.rsplit('/', 1)[1][:-5].split('_'); c = self._candles(a, tf)
            if c and self.candle_edit: c = self.candle_edit(copy.deepcopy(c))
            return route.fulfill(body=json.dumps(c), content_type='application/json') if c else route.fulfill(status=404, body='x')
        if 'fonts' in u: return route.abort()
        return route.fulfill(status=404, body='x')

    def text(self):
        # what a member can read: the page text plus the labels drawn inside charts
        return self.pg.inner_text('body') + '\n' + self.pg.evaluate("Array.from(document.querySelectorAll('svg text')).filter((t) => t.getClientRects().length).map((t) => t.textContent).join('\\n')")

    def render(self, full=False):
        """Text of every tab (and, with full, after every picker button on Now and Chart)."""
        self.pg.goto('about:blank')   # a change of #tab alone does not reload the page, so the files would not be read again
        del self.errs[:]; seen = {}
        for v in ('now', 'chart', 'record', 'read'):
            self.pg.goto('http://site.test/#' + v); self.pg.wait_for_timeout(700 if v == 'chart' else 300)
            seen[v] = self.text()
            if not full or v in ('record', 'read'): continue
            sel = "button, input[type=checkbox], [data-id], [data-asset]"
            for i in range(self.pg.evaluate("(s) => document.querySelectorAll(s).length", sel)):
                self.pg.evaluate("([s, i]) => { const e = document.querySelectorAll(s)[i]; if (e && e.offsetParent !== null && !/^(tab|nav)/.test(e.id || '') && !e.closest('nav')) e.click(); }", [sel, i])
                self.pg.wait_for_timeout(300 if v == 'chart' else 120)
                seen[v] += '\n' + self.text()
        return seen

    def clean(self, seen):
        txt = '\n'.join(seen.values()); g = BAD.search(txt)
        return (not self.errs and not g), (self.errs[:1], (g.group(0) + ' in: ' + txt[max(0, g.start() - 60):g.end() + 20].replace('\n', ' ')) if g else '')


def has(text, phrase):
    return phrase.lower() in text.lower()   # headings are upper-cased by the stylesheet


def main():
    results = []
    def ok(label, cond, detail=''):
        results.append(bool(cond)); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f'  -- {detail}' if not cond else ''), flush=True)
    schema = feedcheck.load_schema(); FP = schema_paths(schema, 'feed'); TP = schema_paths(schema, 'trades')
    dirs = [a for a in sys.argv[1:] if not a.startswith('--')]
    tmp = None
    if not dirs:
        tmp = tempfile.mkdtemp(prefix='ctzb_damage_')
        r = subprocess.run(['bash', f'{R0}/tests/replay_at.sh', '2026-11-12', f'{tmp}/replay_1112'], capture_output=True, text=True)
        ok('replay of 12 Nov 2026 built (a state with forming cards)', r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])
        dirs = [R0, f'{tmp}/replay_1112']
    rl = int(os.environ.get('RENDER_LIMIT', '100000')); jl = int(os.environ.get('REJECT_LIMIT', '40'))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for R in dirs:
            name = os.path.basename(R.rstrip('/'))
            S = Site(b, R); base = S.base
            print(f'--- {name}: feed {base["generated_at"]}, {len(base["cards"])} forming cards, {len(base["open_signals"])} live signals ---')
            ok(f'{name}: the real feed passes the strict check', not feedcheck.problems(base, schema), str(feedcheck.problems(base, schema)[:3]))
            held = copy.deepcopy(base); held.update(cards_withheld=True, cards=[], open_signals=[], example_card=None); held['checks']['all_passed'] = False
            ok(f'{name}: a held feed passes the strict check', not feedcheck.problems(held, schema), str(feedcheck.problems(held, schema)[:3]))
            # 2. verdicts agree
            OPS = list(ops_for(base, 'feed', FP))
            py = [verdict(base, op, lambda f: feedcheck.problems(f, schema)) for _, _, op in OPS]
            assert base == S.feed, 'the in-place damage was not undone'
            S.pg.goto('http://site.test/'); S.pg.wait_for_timeout(400)
            S.pg.evaluate("(f) => { window.__base = { feed: f }; }", base)
            js = []
            for i in range(0, len(OPS), 500):
                js += S.pg.evaluate(JS_APPLY, [dict(op, base='feed', fn='__feedProblems') for _, _, op in OPS[i:i + 500]])
            diff = [(OPS[i][0], OPS[i][1]) for i in range(len(OPS)) if py[i] != js[i]]
            ok(f'{name}: page and pipeline give the same verdict on all {len(OPS)} damaged feeds ({sum(py)} rejected, {len(OPS) - sum(py)} accepted)', not diff, str(diff[:6]))
            # 3. accepted kinds render clean
            seen, todo = set(), []
            for i, (gen, kind, op) in enumerate(OPS):
                if py[i] or (gen, kind) in seen: continue
                seen.add((gen, kind)); todo.append((gen, kind, op))
            random.Random(7).shuffle(todo); bad = []
            for gen, kind, op in todo[:rl]:
                S.feed = applied(base, op); good, why = S.clean(S.render())
                if not good: bad.append((gen, kind, why))
            ok(f'{name}: {min(rl, len(todo))} of {len(todo)} accepted kinds of damage render on every tab with no script error and no raw placeholder', not bad, f'{len(bad)} bad, e.g. {bad[:3]}')
            for x in bad[:60]: print('       ', str(x)[:400])
            # 4. rejected ones read "Data unavailable"
            rej = [OPS[i] for i in range(len(OPS)) if py[i]]; random.Random(11).shuffle(rej); bad = []
            for gen, kind, op in rej[:jl]:
                S.feed = applied(base, op); seen_ = S.render(); good, why = S.clean(seen_)
                if not good or not has(seen_['now'], 'Data unavailable'): bad.append((gen, kind, why, has(seen_['now'], 'Data unavailable')))
            ok(f'{name}: {min(jl, len(rej))} rejected feeds read "Data unavailable", no script error, no raw placeholder', not bad, str(bad[:3]))
            # the undamaged feed, the held feed and the fail-closed feed, every button
            S.feed = base; good, why = S.clean(S.render(full=True)); ok(f'{name}: the real feed renders clean on every tab and button', good, str(why))
            S.feed = held; seen_ = S.render(full=True); good, why = S.clean(seen_)
            ok(f'{name}: the held feed reads "Setups held back" and renders clean', good and has(seen_['now'], 'Setups held back'), str(why))
            sys.argv_backup = sys.argv; fc_path = os.path.join(tempfile.mkdtemp(prefix='ctzb_fc_'), 'f.json')
            import feed_live
            os.environ['CTZB_NOW'] = base['generated_at']; feed_live.fail_closed(fc_path, RuntimeError('x')); os.environ.pop('CTZB_NOW')
            fc = json.load(open(fc_path))
            ok(f'{name}: the fail-closed feed passes the strict check', not feedcheck.problems(fc, schema), str(feedcheck.problems(fc, schema)[:3]))
            S.feed = fc; seen_ = S.render(full=True); good, why = S.clean(seen_)
            ok(f'{name}: the fail-closed feed reads "Setups held back", "Market filter: unavailable", no candle date', good and has(seen_['now'], 'Setups held back') and has(seen_['now'], 'Market filter: unavailable') and not has(seen_['now'], 'closed through'), str(why))
            # 5. every field the page reads is in the schema
            # the lead-trader fixture, dated just before this state's feed (the page's clock is the feed's time)
            g0 = dt.datetime.strptime(base['generated_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
            TR = copy.deepcopy(TRADES)
            for k, x in enumerate(TR['trades']): x['time'] = (g0 - dt.timedelta(days=2 + 20 * k)).strftime('%Y-%m-%dT%H:%M:%SZ')
            S.pg.close(); S = Site(b, R, record=True); S.trades = TR; S.render(full=True)
            read = set(S.pg.evaluate('window.__paths'))
            extra = sorted(p for p in read if p not in FP and p not in TP and not p.endswith(('.then', '._open')))
            ok(f'{name}: every feed and lead-trader field the page reads ({len(read)}) is in the schema', not extra, str(extra[:8]))
            # 6a. lead-trader file
            ok(f'{name}: a well-formed lead-trader file passes', not feedcheck.trades_problems(TR, schema, now=g0))
            TOPS = list(ops_for(TR, 'trades', TP)); tb = copy.deepcopy(TR)
            py = [verdict(tb, op, lambda t: feedcheck.trades_problems(t, schema, now=g0)) for _, _, op in TOPS]
            S.pg.evaluate("(t) => { window.__base = { trades: t }; }", TR)
            js = S.pg.evaluate(JS_APPLY, [dict(op, base='trades', fn='__tradesProblems') for _, _, op in TOPS])
            diff = [(TOPS[i][0], TOPS[i][1]) for i in range(len(TOPS)) if py[i] != js[i]]
            ok(f'{name}: page and pipeline agree on all {len(TOPS)} damaged lead-trader files ({sum(py)} rejected)', not diff, str(diff[:6]))
            bad = []; seen = set()
            for i, (gen, kind, op) in enumerate(TOPS):
                if (gen, kind, py[i]) in seen: continue
                seen.add((gen, kind, py[i]))
                if py[i] and len([1 for g, k, p in seen if p]) > 60: continue
                S.trades = applied(TR, op); seen_ = S.render(); good, why = S.clean({'now': seen_['now']})
                if not good or (py[i] and not has(seen_['now'], 'feed is unavailable')): bad.append((gen, kind, py[i], why))
            ok(f'{name}: damaged lead-trader files render clean; rejected ones read "unavailable"', not bad, f'{len(bad)} bad, e.g. {bad[:3]}')
            S.trades = None
            # 6b. ledger
            lines = S.ledger.rstrip('\n').split('\n'); hdr = lines[0].split(','); top = [i for i, l in enumerate(lines) if ',A+,' in l]
            def cell(i, col, val):
                c = lines[i].split(','); c[hdr.index(col)] = val; return '\n'.join(lines[:i] + [','.join(c)] + lines[i + 1:]) + '\n'
            cases = {'a top-grade row twice': '\n'.join(lines + [lines[top[0]]]) + '\n', 'a row with a cell missing': '\n'.join(lines[:5] + [lines[5].rsplit(',', 1)[0]] + lines[6:]) + '\n',
                     'text in a top-grade price': cell(top[0], 'entryPrice', 'abc'), 'a top-grade date that is not a date': cell(top[0], 'entry', '2026-02-30'),
                     'a top-grade best move of NaN': cell(top[1], 'bestMove', 'NaN'), 'reached20 yes with reached10 no': cell(top[0], 'reached10', 'no') if 'yes' in lines[top[0]] else cell(top[0], 'reached20', 'maybe'),
                     'an unknown chart': cell(top[0], 'chart', 'ETH 9D'), 'a blank day count': cell(top[0], 'daysToHigh', ''), 'one top-grade row dropped': '\n'.join(lines[:top[0]] + lines[top[0] + 1:]) + '\n',
                     'header only': lines[0] + '\n', 'empty file': ''}
            bad = []
            for label, text in cases.items():
                S.feed = base; S.ledger = text; seen_ = S.render(); good, why = S.clean(seen_)
                if not good or not has(seen_['record'], 'Past signals unavailable'): bad.append((label, why, has(seen_['record'], 'Past signals unavailable')))
            ok(f'{name}: {len(cases)} damaged ledgers read "Past signals unavailable"', not bad, str(bad[:3]))
            S.ledger = open(f'{R}/datasets/ledger.csv').read()
            # 6c. chart files (only when a chart is drawn from one: a live or forming setup)
            if base['cards'] or any(o['grade'] == 'A+' for o in base['open_signals']):
                def hi_low(c): c['bars'][-3]['h'] = c['bars'][-3]['c'] * 0.5; return c
                def twice(c): c['bars'].insert(5, dict(c['bars'][5])); return c
                def rev(c): c['bars'].reverse(); return c
                def nullbar(c): c['bars'][7] = None; return c
                def zero(c): c['bars'][9]['l'] = 0; return c
                def text(c): c['bars'][9]['c'] = '100'; return c
                def nine(c): c['bars'] = c['bars'][:9]; return c
                def notlist(c): c['bars'] = {'0': c['bars'][0]}; return c
                edits = {'a high below its close': hi_low, 'a bar twice': twice, 'bars reversed': rev, 'a null bar': nullbar, 'a zero low': zero, 'a price as text': text, 'nine bars': nine, 'bars not a list': notlist,
                         'the file is a list': lambda c: c['bars'], 'the file is null': lambda c: None}
                bad = []
                for label, fn in edits.items():
                    S.candle_edit = fn; seen_ = S.render(); good, why = S.clean(seen_)
                    if not good or not has(seen_['chart'], 'Chart data unavailable'): bad.append((label, why))
                S.candle_edit = None
                ok(f'{name}: {len(edits)} damaged chart files read "unavailable" on the Chart tab', not bad, str(bad[:3]))
            S.pg.close()
        b.close()
    print(f'\n{sum(results)}/{len(results)} passed'); sys.exit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
