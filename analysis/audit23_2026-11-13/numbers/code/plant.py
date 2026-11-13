"""Test my own checker: plant errors in a copy of a frozen state and count how many are caught."""
import json, csv, os, sys, shutil, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SRC = os.path.join(OUT, '..', 'a23', 'replay_0414')
NOW = '2026-11-12T04:14:00Z'


def copy(dst):
    shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst)
    for sub in ('data', 'datasets', 'feed', 'docs/artifacts/member-site'):
        shutil.copytree(os.path.join(SRC, sub), os.path.join(dst, sub))
    for f in ('engine.py', 'regimes.py'):
        shutil.copy(os.path.join(SRC, f), dst)


def data_plants(d):
    F = os.path.join(d, 'feed', 'ctzb_feed.json'); f = json.load(open(F))
    L = os.path.join(d, 'datasets', 'ledger.csv'); rows = list(csv.DictReader(open(L))); hdr = list(rows[0].keys())
    P = []

    def led(i, k, v, what):
        P.append((f"ledger {rows[i]['chart']} {rows[i]['entry']}", k, what)); rows[i][k] = v
    led(10, 'bestMove', f"{float(rows[10]['bestMove']) + 0.000001:.6f}", '+1e-6 on a 6-place measure')
    led(20, 'entryPrice', f"{float(rows[20]['entryPrice']) + 0.01:.2f}", 'entry price +1 cent')
    led(30, 'dayReach10', str(int(rows[30]['dayReach10'] or 0) + 1) if rows[30]['dayReach10'] else '50', 'odds-on-the-day +1')
    led(40, 'tags', rows[40]['tags'] + ' + prime dot' if 'prime' not in rows[40]['tags'] else rows[40]['tags'].replace(' + prime dot', ''), 'tag flipped')
    k = next(i for i, r in enumerate(rows) if r['dayScaled20'] not in ('', None))
    led(k, 'dayScaled20', '', 'dayScaled20 blanked')
    led(50, 'daysToHigh', str(int(rows[50]['daysToHigh']) + 1), 'day of high +1')
    led(60, 'surv10', 'no' if rows[60]['surv10'] == 'yes' else 'yes', 'surv10 flipped')
    gone = next(i for i, r in enumerate(rows) if r['grade'] == 'A+' and r['asset'] == 'BTC')
    P.append((f"ledger {rows[gone]['chart']} {rows[gone]['entry']}", 'membership', 'a top-grade row deleted')); del rows[gone]
    w = csv.DictWriter(open(L, 'w', newline=''), fieldnames=hdr); w.writeheader(); w.writerows(rows)

    def fe(path, k, what, fn):
        P.append((path, k, what))
        return fn
    c = f['cards']
    c[0]['rose10_within60d_pct'] += 1; P.append((f"cards {c[0]['signal_id']}", 'rose10_within60d_pct', '+1 point'))
    c[0]['typical_biggest_rise_exact_pct'] = round(c[0]['typical_biggest_rise_exact_pct'] + 1e-6, 6); P.append((f"cards {c[0]['signal_id']}", 'typical_biggest_rise_exact_pct', '+1e-6'))
    c[1]['if_it_falls_first'][2]['still_rose10_exact_pct'] = round(c[1]['if_it_falls_first'][2]['still_rose10_exact_pct'] + 0.000001, 6); P.append((f"cards {c[1]['signal_id']} falls 15%", 'still_rose10_exact_pct', '+1e-6'))
    km = next(x for x in c if x['must_close_above'])
    km['must_close_above'] = round(km['must_close_above'] + 0.01, 2); P.append((f"cards {km['signal_id']}", 'must_close_above', '+1 cent'))
    c[3]['low_day'] = str(dt.date.fromisoformat(c[3]['low_day']) - dt.timedelta(days=1)); P.append((f"cards {c[3]['signal_id']}", 'low_day', '-1 day'))
    c[2]['before_2022']['past_trades'] += 1; P.append((f"cards {c[2]['signal_id']}", 'before_2022.past_trades', '+1'))
    o = f['open_signals']
    o[0]['days_elapsed'] += 1; P.append((f"open_signals {o[0]['signal_id']}", 'days_elapsed', '+1'))
    bt = next(x for x in o if x['signal_id'] == 'BTC-2D-2026-09-21')
    bt['edge_status'] = 'intact'; P.append(('open_signals BTC-2D-2026-09-21', 'edge_status', 'lost -> intact'))
    o[3]['best_so_far_pct'] = round(o[3]['best_so_far_pct'] + 0.1, 1); P.append((f"open_signals {o[3]['signal_id']}", 'best_so_far_pct', '+0.1'))
    o[5]['card']['from_entry']['went_on_to_fall25_pct'] += 1; P.append((f"open_signals {o[5]['signal_id']} card", 'from_entry.went_on_to_fall25_pct', '+1'))
    o[6]['day10_pct'] = None if o[6]['day10_pct'] is not None else 1.0; P.append((f"open_signals {o[6]['signal_id']}", 'day10_pct', 'blanked'))
    x = f['example_card']; x['sample'] = x['sample'].replace('75', '76'); P.append(('example_card', 'sample', 'n in text'))
    x['typical_day_of_deepest_dip'] += 1; P.append(('example_card', 'typical_day_of_deepest_dip', '+1'))
    f['grade_odds'][0]['median_deepest_dip_pct'] = round(f['grade_odds'][0]['median_deepest_dip_pct'] - 0.1, 1); P.append(('grade_odds ETH A+', 'median_deepest_dip_pct', '-0.1'))
    f['grade_odds'][5]['sample'] = '2020-04-18 to 2025-12-05'; P.append((f"grade_odds {f['grade_odds'][5]['asset']} {f['grade_odds'][5]['grade']}", 'sample', 'last date'))
    f['if_it_misses'][0]['median_peak_pct'] = round(f['if_it_misses'][0]['median_peak_pct'] + 0.1, 1); P.append(('if_it_misses ETH A+', 'median_peak_pct', '+0.1'))
    f['if_it_misses'][5]['up_first'] -= 1; P.append((f"if_it_misses {f['if_it_misses'][5]['asset']} {f['if_it_misses'][5]['grade']}", 'up_first', '-1'))
    f['past_paths'][0]['days'][30]['median_pct'] = round(f['past_paths'][0]['days'][30]['median_pct'] + 0.1, 1); P.append(('past_paths ETH day 30', 'median_pct', '+0.1'))
    f['example_past_paths']['days'][60]['q75_pct'] = round(f['example_past_paths']['days'][60]['q75_pct'] + 0.1, 1); P.append(('example_past_paths day 60', 'q75_pct', '+0.1'))
    ed = f['odds_fade']['early_dip'][1]; ed['edge'] = 'gone' if ed['edge'] == 'intact' else 'intact'; P.append((f"odds_fade early_dip {ed['band']}", 'edge', 'flipped'))
    f['odds_fade']['day10'][1]['rose10_after_day10_pct'] += 1; P.append((f"odds_fade day10 {f['odds_fade']['day10'][1]['check']}", 'rose10_after_day10_pct', '+1'))
    f['trades_a_year'] = '18 on average'; P.append(('feed', 'trades_a_year', '17 -> 18'))
    f['prints'][0]['entry_close'] = round(f['prints'][0]['entry_close'] + 0.01, 2); P.append((f"prints {f['prints'][0]['signal_id']} confirmed", 'entry_close', '+1 cent'))
    f['market_regime'] = 'Bearish'; P.append(('feed', 'market_regime (gate on today)', 'Bullish -> Bearish'))
    json.dump(f, open(F, 'w'), indent=1)
    return P


PAGE_PLANTS = [
    ('`+10% level`', 'money(pxAt(m.entry, 10))}</b>', 'money(pxAt(m.entry, 10.1))}</b>', 'side box'),
    ('recCount counts +20% misses', 'rows.filter((r) => r.reached10 !== "yes").length} missed', 'rows.filter((r) => r.reached20 !== "yes").length} missed', 'count line'),
    ('Day 60 line one bar late', 'x60 = X(Math.min(nSlots - 1, dayX(60)))', 'x60 = X(Math.min(nSlots - 1, dayX(62)))', 'Day 60 line'),
    ('cloud median shifted', '`${X(d.day)},${Y(d.median_pct)}`', '`${X(d.day)},${Y(d.median_pct + 0.5)}`', 'cloud median path'),
    ('ladder gone mark at 60% instead of 70%', 'r.x !== "" && r.x != null && r.x < sf.bar, `n ${r.n}`', 'r.x !== "" && r.x != null && r.x < sf.bar - 10, `n ${r.n}`', 'ladder'),
    ('footer closed-through date = scored_as_of', 'Date.parse(f.scored_as_of + "T00:00:00Z") - 86400000', 'Date.parse(f.scored_as_of + "T00:00:00Z") - 0', 'closed through'),
    ('typical drop shows the deepest dip before the high', 'drop: c.typical_deepest_dip_exact_pct ?? c.typical_deepest_dip_pct', 'drop: c.typical_dip_before_rise_exact_pct ?? c.typical_deepest_dip_pct', 'Typical drop'),
    ('misses pool count', '${mi.misses} misses of ${m.kind', '${mi.misses + 1} misses of ${m.kind', 'misses'),
    ('live best so far rounded to whole', 'best ${pct(o.best_so_far_pct)} · worst ${pct(o.worst_so_far_pct)}</span></button>', 'best ${pct(o.best_so_far_pct, 0)} · worst ${pct(o.worst_so_far_pct)}</span></button>', 'live button'),
    ('axis floor at -15% instead of -20%', 'lv.drop, entry * 0.8) * 0.95', 'lv.drop, entry * 0.85) * 0.95', 'line height'),
]


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import checkdata
    from pagecheck import check_page
    import pagerun
    now = dt.datetime.fromisoformat(NOW.replace('Z', '+00:00'))
    res = []
    d = os.path.join(OUT, 'work', 'plant_data'); copy(d)
    plants = data_plants(d)
    K, S, extra = checkdata.check_state(d, now, 'plant')
    bad = [r for r in K.rows if r['ok'] != 'yes']
    for loc, lab, what in plants:
        hit = any(r['location'] == loc and r['label'] == lab for r in bad) or any(r['location'].startswith(loc) and lab in r['label'] for r in bad) \
            or (lab == 'membership' and any(r['label'] == 'membership ' + loc[len('ledger '):] for r in bad))
        res.append(dict(kind='data', where=f'{loc} / {lab}', planted=what, caught=hit))
    print('data plants', sum(x['caught'] for x in res), 'of', len(res), 'caught; disagreements raised', len(bad))
    # page plants: the feed is untouched, one page edit at a time
    dp = os.path.join(OUT, 'work', 'plant_page'); copy(dp)
    page = os.path.join(dp, 'docs', 'artifacts', 'member-site', 'index.html'); orig = open(page).read(); S = None
    for name, a, b, key in PAGE_PLANTS:
        if a not in orig:
            res.append(dict(kind='page', where=name, planted='(edit point not found)', caught=False)); continue
        open(page, 'w').write(orig.replace(a, b))
        hv = os.path.join(dp, 'h.json')
        pagerun.run(dp, hv)
        K, S, extra = checkdata.check_state(dp, now, 'plantpage', S=S)
        n0 = len(K.rows)
        check_page(K, S, dp, json.load(open(hv)), extra)
        badp = [r for r in K.rows[n0:] if r['ok'] != 'yes']
        res.append(dict(kind='page', where=name, planted=f'{a[:40]} -> {b[:40]}', caught=bool(badp), flagged=len(badp),
                        sample='; '.join(f"{r['location']}|{r['label']}" for r in badp[:3])))
        print(name, bool(badp), len(badp))
    open(page, 'w').write(orig)
    json.dump(res, open(os.path.join(OUT, 'plant_results.json'), 'w'), indent=1)
    print('caught', sum(x['caught'] for x in res), 'of', len(res))
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(dp, ignore_errors=True)
