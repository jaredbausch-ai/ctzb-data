"""Sensitivity test of my own checks: change one figure the page is served (or one figure in the feed/ledger) and
confirm the checks flag it. Nothing here counts toward the audit's comparisons."""
import copy, csv, json, os, sys, shutil, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pagelib as PL, page_check as PC, audit_data as AD
RP = os.path.abspath('../a19/replay_0414'); CLK = '2026-11-12T04:14:00Z'
feed = json.load(open(RP + '/feed/ctzb_feed.json')); led = open(RP + '/datasets/ledger.csv').read()
def mfeed(fn):
    f = copy.deepcopy(feed); fn(f); return {'data/ctzb_feed.json': f}
def o(f, sid='BTC-2D-2026-09-21'): return next(x for x in f['open_signals'] if x['signal_id'] == sid)
def c(f, sid='ETH-1D-2026-11-13'): return next(x for x in f['cards'] if x['signal_id'] == sid)
def ledmut():
    rows = list(csv.reader(io.StringIO(led))); h = rows[0]; i = max(k for k, r in enumerate(rows) if k and r[h.index('grade')] == 'A+' and r[0] == 'ETH')
    rows[i][h.index('bestMove')] = str(round(float(rows[i][h.index('bestMove')]) + 0.06, 6)); s = io.StringIO(); csv.writer(s, lineterminator='\n').writerows(rows); return {'data/ledger.csv': s.getvalue()}
cj = PL.candles_json(RP, 'BTC_2D'); cj2 = copy.deepcopy(cj); cj2['bars'][-20]['h'] *= 1.2
muts = {
 'live card big number 85 -> 86': mfeed(lambda f: o(f)['card'].update(rose10_within60d_pct=86)),
 'forming card must-close-above + 1 cent': mfeed(lambda f: c(f).update(must_close_above=c(f)['must_close_above'] + 0.01)),
 'forming card ladder n + 1': mfeed(lambda f: c(f)['if_it_falls_first'][1].update(past_trades=c(f)['if_it_falls_first'][1]['past_trades'] + 1)),
 'live best so far + 0.1': mfeed(lambda f: o(f).update(best_so_far_pct=o(f)['best_so_far_pct'] + 0.1)),
 'live days elapsed + 1': mfeed(lambda f: o(f).update(days_elapsed=o(f)['days_elapsed'] + 1)),
 'ledger best move + 0.06': ledmut(),
 'past path BTC day-60 median + 0.1': mfeed(lambda f: f['past_paths'][1]['days'][60].update(median_pct=f['past_paths'][1]['days'][60]['median_pct'] + 0.1)),
 'a candle high x 1.2': {'data/candles/BTC_2D.json': cj2},
 'example typical drop exact + 0.05': mfeed(lambda f: f['example_card'].update(typical_deepest_dip_exact_pct=f['example_card']['typical_deepest_dip_exact_pct'] + 0.05)),
 'grade odds BTC top grade surv10 + 1': mfeed(lambda f: next(g for g in f['grade_odds'] if g['asset'] == 'BTC' and g['grade'] == 'A+').update(rose10_never_fell25_within60d_pct=77)),
 'forming confirms_on + 1 day': mfeed(lambda f: c(f).update(confirms_on='2026-11-14')),
 'live edge level -5 -> -10': mfeed(lambda f: o(f).update(edge_level_pct=-10)),
 'forming low_day - 1 day': mfeed(lambda f: c(f).update(low_day='2026-11-09')),
 'live entry close + 1 cent': mfeed(lambda f: o(f).update(entry_close=o(f)['entry_close'] + 0.01)),
 'misses median best + 0.1': mfeed(lambda f: next(m for m in f['if_it_misses'] if m['asset'] == 'BTC' and m['grade'] == 'A+').update(median_peak_pct=6.3)),
 'example exact share 77.3 -> 69.9 (edge)': mfeed(lambda f: f['example_card']['from_entry'].update(still_rose10_exact_pct=69.9)),
}
res = []
for name, ov in muts.items():
    PL.OVERRIDES = ov
    R, _ = PC.run(RP, CLK, 'MUT', '/dev/null'); res.append((name, len(R.bad())))
PL.OVERRIDES = {}
# data-level: a light copy of the state (candles symlinked), one figure changed in the feed or ledger
tmp = os.path.abspath('mut_tmp'); os.makedirs(tmp, exist_ok=True)
for d in ('data', 'docs', 'engine.py', 'regimes.py'):
    if not os.path.lexists(f'{tmp}/{d}'): os.symlink(f'{RP}/{d}', f'{tmp}/{d}')
def data_mut(name, fn_feed=None, fn_led=None):
    shutil.copytree(RP + '/datasets', tmp + '/datasets', dirs_exist_ok=True); os.makedirs(tmp + '/feed', exist_ok=True)
    f = copy.deepcopy(feed)
    if fn_feed: fn_feed(f)
    json.dump(f, open(tmp + '/feed/ctzb_feed.json', 'w'))
    if fn_led:
        rows = list(csv.reader(io.StringIO(led))); fn_led(rows, rows[0]); csv.writer(open(tmp + '/datasets/ledger.csv', 'w', newline='')).writerows(rows)
    R, _ = AD.run(tmp, CLK, 'MUT'); res.append(('DATA ' + name, len(R.bad())))
data_mut('ledger dipBeforeHigh + 0.000001', fn_led=lambda rows, h: rows[500].__setitem__(h.index('dipBeforeHigh'), str(round(float(rows[500][h.index('dipBeforeHigh')]) + 0.000001, 6))))
data_mut('ledger dayReach10 + 1', fn_led=lambda rows, h: rows[700].__setitem__(h.index('dayReach10'), str(int(rows[700][h.index('dayReach10')]) + 1)))
data_mut('ledger row removed', fn_led=lambda rows, h: rows.pop(300))
data_mut('odds_fade share + 1', lambda f: f['odds_fade']['early_dip'][2].update(rose10_after_day10_pct=90))
data_mut('odds_fade edge flipped', lambda f: f['odds_fade']['day10'][1].update(edge='intact'))
data_mut('open day10 + 0.1', lambda f: o(f).update(day10_pct=-1.9))
data_mut('card exact median 6th place', lambda f: c(f).update(typical_biggest_rise_exact_pct=c(f)['typical_biggest_rise_exact_pct'] + 0.000001))
data_mut('past_paths q25 + 0.1', lambda f: f['past_paths'][0]['days'][33].update(q25_pct=f['past_paths'][0]['days'][33]['q25_pct'] + 0.1))
data_mut('print tag changed', lambda f: f['prints'][0].update(tags='B'))
data_mut('if_it_misses up_first - 1', lambda f: f['if_it_misses'][0].update(up_first=f['if_it_misses'][0]['up_first'] - 1))
data_mut('trades_a_year 17 -> 18', lambda f: f.update(trades_a_year='18 on average'))
data_mut('must_close_above 1 cent up', lambda f: c(f).update(must_close_above=c(f)['must_close_above'] + 0.01))
for n, k in res: print(f'{k:4d} flagged | {n}')
print('mutations', len(res), 'caught', sum(k > 0 for n, k in res))
