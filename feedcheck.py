"""Strict check of the member feed, the same rules the member page applies when it loads the feed
(13 Nov 2026). The schema is the JSON block between /*FEED_SCHEMA*/ and /*END_FEED_SCHEMA*/ in
docs/artifacts/member-site/index.html, so the page and the pipeline read one definition.

Types (the page's comment beside FEED_SCHEMA lists the same): pct 0..100, pcti a whole number 0..100, num a
finite number under a million either way, n a whole number 0 or more, day a whole number 0..60, px a price above
0 and under 10^9, dip -100..0, rise 0..100,000, chg above -100 and up to 100,000, share above 0 up to 100, lev
above 0 up to 100, date (YYYY-MM-DD), ts (ISO time, UTC), str (non-empty text), text (any text), bool,
"=a|b|c" (one of these words). Text is trimmed and digits matched as JavaScript does (ASCII digits only;
JavaScript's whitespace set, which includes the byte-order mark), so both sides give the same verdict. A key ending in "?" may be null or missing. "@name" refers to defs.
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
# JavaScript's String.prototype.trim whitespace set (ECMAScript WhiteSpace + LineTerminator)
_JS_WS = '\t\n\x0b\x0c\r \xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'


def _js_trim(v):
    return v.strip(_JS_WS)


def _ymd(y, m, d):
    try: dt.date(int(y), int(m), int(d)); return True
    except ValueError: return False
def _date(v):
    m = re.fullmatch(r'(20\d{2})-(\d{2})-(\d{2})', v, re.ASCII) if isinstance(v, str) else None
    return bool(m) and _ymd(*m.groups())
def _ts(v):
    m = re.fullmatch(r'(20\d{2})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z', v, re.ASCII) if isinstance(v, str) else None
    return bool(m) and _ymd(*m.groups()[:3]) and int(m.group(4)) < 24 and int(m.group(5)) < 60 and int(m.group(6)) < 60

PRIM = {
    'pct': lambda v: _num(v) and 0 <= v <= 100,
    'pcti': lambda v: _int(v) and 0 <= v <= 100,
    'num': lambda v: _num(v) and abs(v) < 1e6,
    'n': lambda v: _int(v) and 0 <= v < 1e6,
    'day': lambda v: _int(v) and 0 <= v <= 60,
    'px': lambda v: _num(v) and 0 < v < 1e9,
    'dip': lambda v: _num(v) and -100 <= v <= 0,
    'rise': lambda v: _num(v) and 0 <= v <= 1e5,
    'chg': lambda v: _num(v) and -100 < v <= 1e5,
    'share': lambda v: _num(v) and 0 < v <= 100,
    'lev': lambda v: _num(v) and 0 < v <= 100,
    'date': _date, 'ts': _ts,
    'str': lambda v: isinstance(v, str) and _js_trim(v) != '',
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
        whole = all(c.get(k) is not None for k in CARD_FIGS) and c['from_entry'].get('still_rose10_pct') is not None and c['from_entry'].get('still_rose10_exact_pct') is not None
        if c['past_trades'] > 0 and whole:
            if c['rose10_never_fell25_within60d_pct'] > c['rose10_within60d_pct'] or c['rose20_within60d_pct'] > c['rose10_within60d_pct']:
                out.append(f'{p}: a share is above the rose-10% share it is part of')
            if not c['typical_deepest_dip_exact_pct'] <= c['typical_dip_before_rise_exact_pct']:
                out.append(f'{p}: the dip before the high is deeper than the deepest dip')
            fe = c['from_entry']
            if abs(fe['still_rose10_pct'] - fe['still_rose10_exact_pct']) > 0.5: out.append(f'{p}.from_entry: rounded and exact shares disagree')
            if fe['still_rose10_exact_pct'] > c['rose10_within60d_pct'] + 0.5 or c['rose10_never_fell25_within60d_pct'] > fe['still_rose10_exact_pct'] + 0.5:
                out.append(f'{p}.from_entry: out of line with the shares it sits between')
        for i, r in enumerate(c['if_it_falls_first']):
            if i and r['past_trades'] > c['if_it_falls_first'][i - 1]['past_trades']:
                out.append(f'{p}.if_it_falls_first[{i}]: more signals than the shallower row')
            if r['past_trades'] > 0 and None not in (r.get('still_rose10_pct'), r.get('still_rose10_exact_pct'), r.get('went_on_to_fall25_pct')) and (
                    abs(r['still_rose10_pct'] - r['still_rose10_exact_pct']) > 0.5 or r['still_rose10_pct'] + r['went_on_to_fall25_pct'] > 101):
                out.append(f'{p}.if_it_falls_first[{i}]: shares disagree')
        figs = [c.get(k) for k in CARD_FIGS] + [c['from_entry'].get('still_rose10_pct'), c['from_entry'].get('still_rose10_exact_pct')]
        if any((x is None) != (c['past_trades'] == 0) for x in figs): out.append(f'{p}: figures and sample size disagree')
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
            if (o['card']['chart'] != o['chart'] or o['card']['confirms_on'] != o['entry_date'] or o['card']['grade'] != o['grade']
                    or o['card'].get('entry_close') != o['entry_close']):
                out.append(f'{p}: card belongs to another signal')
        el = (dt.date.fromisoformat(day) - dt.date.fromisoformat(o['entry_date'])).days
        if o['days_elapsed'] != el: out.append(f'{p}.days_elapsed: not the days since entry')
        for k, dd in (('day10_pct', 10), ('day30_pct', 30), ('day60_pct', 60)):
            if (o.get(k) is None) != (o['days_elapsed'] <= dd): out.append(f'{p}.{k}: present before its day closed, or missing after')
        mv = [o.get(k) for k in ('day10_pct', 'day30_pct', 'day60_pct') if o.get(k) is not None]
        b, w = o.get('best_so_far_pct'), o.get('worst_so_far_pct')
        if b is not None and w is not None and any(x > b or x < w for x in mv + [w]):
            out.append(f'{p}: a figure is outside the best and worst so far')
        if o['edge_status'] == 'rose10' and not (b is not None and b >= 9.95): out.append(f'{p}: marked rose 10% but best so far is under 10%')
        if o['edge_status'] == 'intact' and b is not None and b > 10.05: out.append(f'{p}: marked on track but best so far is over 10%')
        lv = o.get('edge_level_pct')
        if lv is not None and w is not None:
            if o['edge_status'] == 'lost' and w > lv + 0.05: out.append(f'{p}: marked lost but never fell to its edge level')
            if o['edge_status'] == 'intact' and w < lv - 0.05: out.append(f'{p}: marked on track but fell past its edge level')
    for name in ('if_it_misses',):
        for i, m in enumerate(f[name]): _miss(m, f'feed.{name}[{i}]', out)
    if f.get('example_if_it_misses') is not None: _miss(f['example_if_it_misses'], 'feed.example_if_it_misses', out)
    for i, pp in enumerate(f['past_paths']): _path(pp, f'feed.past_paths[{i}]', out)
    if f.get('example_past_paths') is not None: _path(f['example_past_paths'], 'feed.example_past_paths', out)
    of = f.get('odds_fade')
    if of is not None:
        filled = bool(of['early_dip'] or of['day10'])
        in_order = lambda got, fixed: all(x in fixed and (i == 0 or fixed.index(x) > fixed.index(got[i - 1])) for i, x in enumerate(got))
        if not in_order([b['band'] for b in of['early_dip']], ODDS_BANDS) or not in_order([b['check'] for b in of['day10']], ODDS_CHECKS):
            out.append('feed.odds_fade: rows are not the fixed bands and checks in order')
        if filled and of.get('tier_fixed_on') is None: out.append('feed.odds_fade.tier_fixed_on: missing')
        # the mark is decided on the exact share, the share shown is rounded: they can differ only at the bar itself
        if any((b['rose10_after_day10_pct'] < of['posting_bar_pct'] - 0.5) if b['edge'] == 'intact' else (b['rose10_after_day10_pct'] > of['posting_bar_pct'] + 0.5)
               for b in of['early_dip'] + of['day10']):
            out.append('feed.odds_fade: an edge mark disagrees with its share')
    for i, g in enumerate(f['grade_odds']):
        if any((g.get(k) is None) != (g['past_trades'] == 0) for k in GRADE_FIGS): out.append(f'feed.grade_odds[{i}]: figures and sample size disagree')
        if g['past_trades'] > 0 and None not in (g.get('rose10_never_fell25_within60d_pct'), g.get('rose20_within60d_pct'), g.get('rose10_within60d_pct')) and (
                g['rose10_never_fell25_within60d_pct'] > g['rose10_within60d_pct'] or g['rose20_within60d_pct'] > g['rose10_within60d_pct']):
            out.append(f'feed.grade_odds[{i}]: a share is above the rose-10% share it is part of')
    go = {(x['asset'], x['grade']): x for x in f['grade_odds']}
    for i, mm in enumerate(f['if_it_misses']):
        g = go.get((mm['asset'], mm['grade']))
        if not g or g['past_trades'] != mm['signals'] or (mm['signals'] > 0 and g.get('rose10_within60d_pct') is not None and abs(100 * (mm['signals'] - mm['misses']) / mm['signals'] - g['rose10_within60d_pct']) > 0.5):
            out.append(f'feed.if_it_misses[{i}]: does not match grade_odds')
    for i, pp in enumerate(f['past_paths']):
        g = go.get((pp['asset'], 'A+'))
        if not g or g['past_trades'] != pp['signals']: out.append(f'feed.past_paths[{i}]: does not match grade_odds')
    ex = f.get('example_card')
    if ex is not None:
        if ex['signal_id'] != EXAMPLE_ID: out.append('feed.example_card: not the worked example')
        if f.get('example_past_paths') is not None and f['example_past_paths']['signals'] != ex['past_trades']: out.append("feed.example_past_paths: not the example's sample")
        if f.get('example_if_it_misses') is not None and f['example_if_it_misses']['signals'] != ex['past_trades']: out.append("feed.example_if_it_misses: not the example's sample")
    for k in ('grade_odds', 'if_it_misses'):
        keys = [(x['asset'], x['grade']) for x in f[k]]
        if len(set(keys)) != len(keys): out.append(f'feed.{k}: an asset and grade appear twice')
    assets = [x['asset'] for x in f['past_paths']]
    if len(set(assets)) != len(assets): out.append('feed.past_paths: an asset appears twice')


EXAMPLE_ID = 'ETH-2D-2024-09-22'
GRADE_FIGS = ["rose10_within60d_pct", "rose10_never_fell25_within60d_pct", "rose20_within60d_pct", "median_deepest_dip_pct"]
CARD_FIGS = ["rose10_within60d_pct", "rose10_never_fell25_within60d_pct", "rose20_within60d_pct", "fell30_within60d_pct", "typical_biggest_rise_exact_pct", "typical_dip_before_rise_exact_pct", "typical_deepest_dip_exact_pct", "typical_day_of_60d_high", "typical_day_of_deepest_dip"]
ODDS_BANDS = ['shallower than -2%', '-2% to -5%', '-5% to -10%', '-10% to -20%', 'worse than -20%']
ODDS_CHECKS = ['green on day 10', 'red on day 10']


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
    if out:
        return out
    t = lambda x: dt.datetime.strptime(x[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=dt.timezone.utc)
    now = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)
    for i, x in enumerate(trades['trades']):
        if i and t(x['time']) > t(trades['trades'][i - 1]['time']): out.append(f'trades[{i}]: not newest first')
        if t(x['time']) > now: out.append(f'trades[{i}]: in the future')
    return out


if __name__ == '__main__':
    bad = problems(json.load(open(sys.argv[1])), load_schema(sys.argv[2]) if len(sys.argv) > 2 else None)
    for b in bad[:20]: print(b)
    print('feed ok' if not bad else f'{len(bad)} problem(s)')
    sys.exit(1 if bad else 0)
