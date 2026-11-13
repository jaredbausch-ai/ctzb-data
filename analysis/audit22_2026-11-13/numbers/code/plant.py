"""Plant errors in a copy of the replay_0414 state, one at a time, and see whether the checker catches each.
Usage: python3 plant.py <source state> <work dir> <out json>"""
import sys, os, json, csv, shutil, datetime as dt, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, page, pagecheck

SRC, WORK, OUT = sys.argv[1:4]


def fresh():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    for d in ('data', 'datasets', 'feed', os.path.join('docs', 'artifacts', 'member-site')):
        shutil.copytree(os.path.join(SRC, d), os.path.join(WORK, d), ignore=shutil.ignore_patterns('derivs', 'ext', 'flows', 'onchain', 'options', 'tradingview'))


def feed_edit(fn):
    p = os.path.join(WORK, 'feed', 'ctzb_feed.json'); f = json.load(open(p)); fn(f); json.dump(f, open(p, 'w'))


def ledger_edit(fn):
    p = os.path.join(WORK, 'datasets', 'ledger.csv'); rows = list(csv.DictReader(open(p))); h = list(rows[0].keys())
    rows = fn(rows)
    with open(p, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=h); w.writeheader(); w.writerows(rows)


def page_edit(old, new):
    p = os.path.join(WORK, 'docs', 'artifacts', 'member-site', 'index.html'); s = open(p).read()
    assert s.count(old) == 1, old
    open(p, 'w').write(s.replace(old, new))


def setk(path, v):
    def f(feed):
        o = feed
        for k in path[:-1]:
            o = o[k]
        o[path[-1]] = v(o[path[-1]]) if callable(v) else v
    return f


def bump(x, d):
    return round(x + d, 6)


def led_row(chart, entry, key, fn):
    def f(rows):
        for r in rows:
            if r['chart'] == chart and r['entry'] == entry:
                r[key] = fn(r[key])
        return rows
    return f


A1 = lambda f: next(i for i, o in enumerate(f['open_signals']) if o['grade'] == 'A+')
PL = [
    ('ledger bestMove +0.000001', 'ledger', led_row('ETH 2D', '2024-09-22', 'bestMove', lambda v: repr(round(float(v) + 1e-6, 6))), 'ledger ETH 2D 2024-09-22'),
    ('ledger tags gain a prime dot', 'ledger', led_row('ETH 1D', '2025-12-04', 'tags', lambda v: v + ' + prime dot'), 'ledger ETH 1D 2025-12-04'),
    ('ledger entryPrice +0.01', 'ledger', led_row('BTC 1D', '2025-12-04', 'entryPrice', lambda v: repr(round(float(v) + 0.01, 2))), 'ledger BTC 1D 2025-12-04'),
    ('ledger dayReach10 +1', 'ledger', led_row('ETH 3D', '2025-10-06', 'dayReach10', lambda v: str(int(v) + 1)), 'ledger ETH 3D 2025-10-06'),
    ('ledger dayScaled20 -1', 'ledger', led_row('BTC 2D', '2024-01-28', 'dayScaled20', lambda v: str(int(v) - 1) if v else '50'), 'ledger BTC 2D 2024-01-28'),
    ('ledger daysToHigh +1', 'ledger', led_row('ETH 5D', '2025-07-09', 'daysToHigh', lambda v: str(int(v) + 1)), 'ledger ETH 5D 2025-07-09'),
    ('ledger row deleted', 'ledger', lambda rows: [r for r in rows if not (r['chart'] == 'ETH 3D' and r['entry'] == '2025-08-10')], 'ledger membership'),
    ('grade_odds ETH A+ rose10 +1', 'feed', setk(['grade_odds', 0, 'rose10_within60d_pct'], lambda v: v + 1), 'grade_odds ETH A+'),
    ('if_it_misses ETH A+ median peak +0.1', 'feed', setk(['if_it_misses', 0, 'median_peak_pct'], lambda v: bump(v, 0.1)), 'if_it_misses ETH A+'),
    ('if_it_misses BTC A+ up_first -1', 'feed', lambda f: [m.update(up_first=m['up_first'] - 1) for m in f['if_it_misses'] if m['asset'] == 'BTC' and m['grade'] == 'A+'], 'if_it_misses BTC A+'),
    ('odds_fade early dip row 3 rose10 +1', 'feed', setk(['odds_fade', 'early_dip', 2, 'rose10_after_day10_pct'], lambda v: v + 1), 'odds_fade early_dip -5% to -10%'),
    ('odds_fade edge mark flipped', 'feed', setk(['odds_fade', 'day10', 1, 'edge'], 'intact'), 'odds_fade day10 red on day 10'),
    ('example card exact high 1e-6', 'feed', setk(['example_card', 'typical_biggest_rise_exact_pct'], lambda v: bump(v, 1e-6)), 'example_card'),
    ('forming card must_close_above +0.01', 'feed', lambda f: [c.update(must_close_above=round(c['must_close_above'] + 0.01, 2)) for c in f['cards'] if c['must_close_above']][:1], 'cards '),
    ('forming card low_day -1', 'feed', lambda f: f['cards'][0].update(low_day=str(dt.date.fromisoformat(f['cards'][0]['low_day']) - dt.timedelta(days=1))), 'cards '),
    ('forming card ladder exact share', 'feed', lambda f: f['cards'][1]['if_it_falls_first'][1].update(still_rose10_exact_pct=bump(f['cards'][1]['if_it_falls_first'][1]['still_rose10_exact_pct'], 0.5)), 'cards '),
    ('forming card sample text n', 'feed', lambda f: f['cards'][0].update(sample=f['cards'][0]['sample'].replace('all 17', 'all 18')), 'cards '),
    ('forming card eras swapped by one', 'feed', lambda f: (f['cards'][0]['before_2022'].update(past_trades=f['cards'][0]['before_2022']['past_trades'] + 1, past_signals=f['cards'][0]['before_2022']['past_trades'] + 1), f['cards'][0]['since_2022'].update(past_trades=f['cards'][0]['since_2022']['past_trades'] - 1, past_signals=f['cards'][0]['since_2022']['past_trades'] - 1)), 'cards '),
    ('forming card price_now +0.01', 'feed', lambda f: f['cards'][0].update(price_now=round(f['cards'][0]['price_now'] + 0.01, 2)), 'cards '),
    ('open signal days_elapsed +1', 'feed', lambda f: f['open_signals'][A1(f)].update(days_elapsed=f['open_signals'][A1(f)]['days_elapsed'] + 1), 'open_signals '),
    ('open signal edge_status lost->intact', 'feed', lambda f: f['open_signals'][A1(f)].update(edge_status='intact'), 'open_signals '),
    ('open signal best so far +0.1', 'feed', lambda f: f['open_signals'][A1(f)].update(best_so_far_pct=bump(f['open_signals'][A1(f)]['best_so_far_pct'], 0.1)), 'open_signals '),
    ('open card from-entry share +1', 'feed', lambda f: f['open_signals'][A1(f)]['card']['from_entry'].update(still_rose10_pct=f['open_signals'][A1(f)]['card']['from_entry']['still_rose10_pct'] + 1), 'open_signals '),
    ('past paths ETH day 30 median +0.1', 'feed', lambda f: f['past_paths'][0]['days'][30].update(median_pct=bump(f['past_paths'][0]['days'][30]['median_pct'], 0.1)), 'past_paths ETH'),
    ('example paths day 60 q75 +0.1', 'feed', lambda f: f['example_past_paths']['days'][60].update(q75_pct=bump(f['example_past_paths']['days'][60]['q75_pct'], 0.1)), 'example_past_paths'),
    ('print entry close +0.01', 'feed', lambda f: f['prints'][0].update(entry_close=round(f['prints'][0]['entry_close'] + 0.01, 2)), 'prints '),
    ('forming print note regime off', 'feed', lambda f: [p.update(note=p['note'].replace('regime on', 'regime off')) for p in f['prints'] if p['state'] == 'forming'][:1], 'prints '),
    ('trades a year 17 -> 16', 'feed', setk(['trades_a_year'], '16 on average'), 'top level'),
    # page plants: the code that turns the feed into what a member reads
    ('page: live line day N+1', 'page', ('· day ${o.days_elapsed} of 60 · best so far', '· day ${o.days_elapsed + 1} of 60 · best so far'), 'page card'),
    ('page: +10% level built at 11%', 'page', ('<div class="kv num"><span class="small">+10% level</span><b>${money(pxAt(m.entry, 10))}</b></div>', '<div class="kv num"><span class="small">+10% level</span><b>${money(pxAt(m.entry, 11))}</b></div>'), 'page chart'),
    ('page: Day 60 line one day early', 'page', ('x60 = X(Math.min(nSlots - 1, dayX(60)))', 'x60 = X(Math.min(nSlots - 1, dayX(58)))'), 'page chart'),
    ('page: footer shows the scored date', 'page', ('Date.parse(f.scored_as_of + "T00:00:00Z") - 86400000', 'Date.parse(f.scored_as_of + "T00:00:00Z") - 0'), 'page footer'),
    ('page: record Deepest drop shows best', 'page', ('<td class="lo">${pct(+r.maxDrawdown)}</td>', '<td class="lo">${pct(+r.bestMove)}</td>'), 'page Past signals'),
    ('page: alert axis uses the whole path', 'page', ('const shown = !forming && !happened ? bars.slice(0, E + 1) : bars;', 'const shown = bars;'), 'page chart example at the alert'),
    ('page: ladder rows show the card n', 'page', ('r.x !== "" && r.x != null && r.x < sf.bar, `n ${r.n}`)', 'r.x !== "" && r.x != null && r.x < sf.bar, `n ${m.n}`)'), 'page card'),
    ('page: At the alert draws the outcome candles', 'page', ('const upto = forming ? bars.length : (happened ? bars.length : E + 1);', 'const upto = bars.length;'), 'page chart example at the alert'),
    ('page: typical drop shows the rounded field rounded again', 'page', ('drop: c.typical_deepest_dip_exact_pct ?? c.typical_deepest_dip_pct', 'drop: Math.trunc(c.typical_deepest_dip_exact_pct)'), 'page card'),
]


def main():
    res = []
    only = os.environ.get('ONLY')
    for name, kind, fn, where in PL:
        if only and name not in only.split('|'):
            continue
        fresh()
        try:
            if kind == 'feed':
                feed_edit(fn)
            elif kind == 'ledger':
                ledger_edit(fn)
            else:
                page_edit(*fn)
        except Exception as e:  # noqa
            res.append(dict(name=name, planted=False, error=repr(e))); continue
        ck, S, X, feed = check.run(WORK, 'plant', '2026-11-12T04:14:00Z')
        if kind in ('page', 'feed', 'ledger'):
            dump = page.dump(WORK, os.path.join(WORK, 'p.json'))
            pagecheck.run(ck, WORK, dump, S, X, feed)
        bad = [r for r in ck.rows if r['ok'] != 'yes']
        hit = [r for r in bad if r['location'].startswith(where) or where in r['location']]
        res.append(dict(name=name, kind=kind, caught=bool(bad), at_place=bool(hit), n_bad=len(bad),
                        first=[f"{r['location']} | {r['label']} | {str(r['shown'])[:60]} | {str(r['yours'])[:60]}" for r in (hit or bad)[:3]]))
        print(name, '->', 'CAUGHT' if bad else 'MISSED', len(bad), (hit or bad)[:1] and ((hit or bad)[0]['location'], (hit or bad)[0]['label']))
    json.dump(res, open(OUT, 'w'), indent=1)
    print(sum(r.get('caught', False) for r in res), 'of', len(res), 'caught')


if __name__ == '__main__':
    main()
