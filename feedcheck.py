"""Strict check of the member feed, the same rules the member page applies when it loads the feed
(13 Nov 2026). The schema is the JSON block between /*FEED_SCHEMA*/ and /*END_FEED_SCHEMA*/ in
docs/artifacts/member-site/index.html, so the page and the pipeline read one definition.

Types: pct (0..100), num (any finite number), n (whole number >= 0), day (whole number 0..60),
px (number > 0), date (YYYY-MM-DD), ts (ISO time), str (non-empty text), text (any text), bool,
"=a|b|c" (one of these words). A key ending in "?" may be null or missing. "@name" refers to defs.
A list spec is [item spec, min length, max length].

    python3 feedcheck.py feed/ctzb_feed.json     -> prints problems, exit 1 if any
"""
import datetime as dt, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, 'docs', 'artifacts', 'member-site', 'index.html')


def load_schema(page=PAGE):
    s = open(page, encoding='utf-8').read()
    m = re.search(r'/\*FEED_SCHEMA\*/(.*?)/\*END_FEED_SCHEMA\*/', s, re.S)
    return json.loads(m.group(1))


def _num(v): return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
def _int(v): return _num(v) and float(v) == int(v)
def _ymd(y, m, d):
    try: dt.date(int(y), int(m), int(d)); return True
    except ValueError: return False
def _date(v):
    m = re.fullmatch(r'(20\d{2})-(\d{2})-(\d{2})', v) if isinstance(v, str) else None
    return bool(m) and _ymd(*m.groups())
def _ts(v):
    m = re.fullmatch(r'(20\d{2})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z', v) if isinstance(v, str) else None
    return bool(m) and _ymd(*m.groups()[:3]) and int(m.group(4)) < 24 and int(m.group(5)) < 60 and int(m.group(6)) < 60

PRIM = {
    'pct': lambda v: _num(v) and 0 <= v <= 100,
    'num': _num,
    'n': lambda v: _int(v) and v >= 0,
    'day': lambda v: _int(v) and 0 <= v <= 60,
    'px': lambda v: _num(v) and v > 0,
    'date': _date, 'ts': _ts,
    'str': lambda v: isinstance(v, str) and v.strip() != '',
    'text': lambda v: isinstance(v, str),
    'bool': lambda v: isinstance(v, bool),
}


def check(v, spec, defs, path, out):
    if isinstance(spec, str):
        if spec.startswith('@'): return check(v, defs[spec[1:]], defs, path, out)
        if spec.startswith('='):
            if not (isinstance(v, str) and v in spec[1:].split('|')): out.append(f'{path}: not one of {spec[1:]}')
            return
        if not PRIM[spec](v): out.append(f'{path}: not {spec}')
        return
    if isinstance(spec, list):
        if not isinstance(v, list): out.append(f'{path}: not a list'); return
        if len(v) < spec[1] or (len(spec) > 2 and len(v) > spec[2]): out.append(f'{path}: {len(v)} items'); return
        for i, x in enumerate(v): check(x, spec[0], defs, f'{path}[{i}]', out)
        return
    if not isinstance(v, dict): out.append(f'{path}: not an object'); return
    for k, sp in spec.items():
        opt = k.endswith('?'); key = k[:-1] if opt else k
        x = v.get(key)
        if x is None:
            if not opt: out.append(f'{path}.{key}: missing')
            continue
        check(x, sp, defs, f'{path}.{key}', out)


def cross(f, out):
    """Rules across fields. Only reached when every field has the right type."""
    def card(c, p):
        if c['chart'] != f"{c['asset']} {c['timeframe']}": out.append(f'{p}: chart is not asset + timeframe')
        if c['signal_id'] != f"{c['asset']}-{c['timeframe']}-{c['confirms_on']}": out.append(f'{p}: signal_id does not match its chart and date')
        if c['before_2022']['past_trades'] + c['since_2022']['past_trades'] != c['past_trades']: out.append(f'{p}: the two eras do not add up to the sample')
        for e in ('before_2022', 'since_2022'):
            if (c[e]['past_trades'] == 0) != (c[e].get('rose10_never_fell25_within60d_pct') is None): out.append(f'{p}.{e}: count and share disagree')
        if [r['fell_pct'] for r in c['if_it_falls_first']] != [5, 10, 15, 20]: out.append(f'{p}: ladder rows are not 5, 10, 15, 20')
        for i, r in enumerate(c['if_it_falls_first']):
            nulls = [r.get(k) is None for k in ('still_rose10_pct', 'still_rose10_exact_pct', 'went_on_to_fall25_pct')]
            if any(x != (r['past_trades'] == 0) for x in nulls): out.append(f'{p}.if_it_falls_first[{i}]: count and shares disagree')
            if r['past_trades'] > c['past_trades']: out.append(f'{p}.if_it_falls_first[{i}]: more signals than the sample')
        if not (c['low_date'] <= c['low_day'] <= c['confirms_on']): out.append(f'{p}: low and confirmation dates out of order')
    if f['cards_withheld'] and (f['cards'] or f['open_signals'] or f.get('example_card') is not None):
        out.append('feed: cards are marked withheld but cards are present')
    if f['cards_withheld'] == f['checks']['all_passed']: out.append('feed: cards_withheld and checks.all_passed disagree')
    if not f['cards_withheld']:
        for k in ('market_regime', 'scored_as_of', 'posting_bar_pct'):
            if f.get(k) is None: out.append(f'feed.{k}: missing in a feed that is not withheld')
    day = f['generated_at'][:10]
    if f.get('scored_as_of') is not None and f['scored_as_of'] > day: out.append('feed.scored_as_of: after generated_at')
    for name in ('cards', 'open_signals'):
        ids = [x['signal_id'] for x in f[name]]
        if len(set(ids)) != len(ids): out.append(f'feed.{name}: a signal_id appears twice')
    for i, c in enumerate(f['cards']):
        card(c, f'feed.cards[{i}]')
        if c['confirms_on'] < day: out.append(f'feed.cards[{i}]: confirms before today')
    if f.get('example_card') is not None: card(f['example_card'], 'feed.example_card')
    for i, o in enumerate(f['open_signals']):
        p = f'feed.open_signals[{i}]'
        if o['signal_id'] != o['chart'].replace(' ', '-') + '-' + o['entry_date']: out.append(f'{p}: signal_id does not match its chart and date')
        if o['entry_date'] > day: out.append(f'{p}: entry after generated_at')
        if o.get('card') is not None:
            card(o['card'], p + '.card')
            if o['card']['chart'] != o['chart'] or o['card']['confirms_on'] != o['entry_date']: out.append(f'{p}: card belongs to another signal')
    for name in ('if_it_misses',):
        for i, m in enumerate(f[name]): _miss(m, f'feed.{name}[{i}]', out)
    if f.get('example_if_it_misses') is not None: _miss(f['example_if_it_misses'], 'feed.example_if_it_misses', out)
    for i, pp in enumerate(f['past_paths']): _path(pp, f'feed.past_paths[{i}]', out)
    if f.get('example_past_paths') is not None: _path(f['example_past_paths'], 'feed.example_past_paths', out)
    for k in ('grade_odds', 'if_it_misses'):
        keys = [(x['asset'], x['grade']) for x in f[k]]
        if len(set(keys)) != len(keys): out.append(f'feed.{k}: an asset and grade appear twice')
    assets = [x['asset'] for x in f['past_paths']]
    if len(set(assets)) != len(assets): out.append('feed.past_paths: an asset appears twice')


def _miss(m, p, out):
    if m['misses'] > m['signals'] or m['up_first'] > m['misses']: out.append(f'{p}: counts do not nest')
    for k in ('median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
        if (m.get(k) is None) != (m['misses'] == 0): out.append(f'{p}.{k}: count and median disagree')


def _path(pp, p, out):
    if [d['day'] for d in pp['days']] != list(range(61)): out.append(f'{p}: days are not 0 to 60 in order')
    if any(not (d['q25_pct'] <= d['median_pct'] <= d['q75_pct']) for d in pp['days']): out.append(f'{p}: quartiles out of order')


def problems(feed, schema=None):
    schema = schema or load_schema()
    out = []
    check(feed, schema['feed'], schema['defs'], 'feed', out)
    if not out: cross(feed, out)
    return out


def trades_problems(trades, schema=None):
    schema = schema or load_schema()
    out = []
    check(trades, schema['trades'], schema['defs'], 'trades', out)
    return out


if __name__ == '__main__':
    bad = problems(json.load(open(sys.argv[1])), load_schema(sys.argv[2]) if len(sys.argv) > 2 else None)
    for b in bad[:20]: print(b)
    print('feed ok' if not bad else f'{len(bad)} problem(s)')
    sys.exit(1 if bad else 0)
