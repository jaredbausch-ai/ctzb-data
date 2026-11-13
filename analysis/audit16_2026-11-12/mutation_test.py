"""Does my page checker have teeth? Serve the page a feed/ledger with planted errors and count what it catches."""
import json, copy, re
import render as R, chk_page
from common import *
root = STATES['REPLAY'][0]
feed = json.load(open(root + '/feed/ctzb_feed.json')); led = open(root + '/datasets/ledger.csv').read()
f = copy.deepcopy(feed); planted = []
o = next(x for x in f['open_signals'] if x['signal_id'] == 'BTC-2D-2026-09-21')
o['card']['rose10_within60d_pct'] += 1; planted.append('open card big number')
o['best_so_far_pct'] += 0.1; planted.append('open best so far')
o['card']['typical_biggest_rise_exact_pct'] += 0.06; planted.append('open typical high exact')
o['card']['if_it_falls_first'][1]['past_trades'] += 1; planted.append('open ladder n')
o['card']['typical_day_of_60d_high'] += 2; planted.append('open high day')
o['entry_close'] += 1; planted.append('open entry close')
c = f['cards'][0]; c['confirms_on'] = '2026-11-14'; planted.append('forming confirms_on (id unchanged)')
f['cards'][1]['low_day'] = '2026-11-09'; planted.append('forming low_day')
f['cards'][2]['must_close_above'] += 0.01; planted.append('forming must close above')
f['example_card']['fell30_within60d_pct'] += 1; planted.append('example touched 30')
f['example_if_it_misses']['median_day60_pct'] += 0.1; planted.append('example miss d60')
f['past_paths'][1]['days'][60]['median_pct'] += 0.1; planted.append('BTC path day 60 median')
f['past_paths'][1]['days'][33]['q25_pct'] += 0.1; planted.append('BTC path day 33 q25')
f['grade_odds'][0]['rose10_never_fell25_within60d_pct'] += 1; planted.append('grade odds surv10 ETH A+')
f['if_it_misses'][4]['median_peak_pct'] += 0.1; planted.append('BTC A+ miss median peak')
led2 = led.replace('ETH,ETH 1D,2025-12-01,2025-12-04', 'ETH,ETH 1D,2025-12-01,2025-12-05', 1); planted.append('ledger entry date')
r = R.render(root, feed=f, ledger=led2)
json.dump(r, open(OUT + '/page_MUT.json', 'w'))
S, C, mine, pg = chk_page.run('REPLAY', dump=OUT + '/page_MUT.json')
print('planted', len(planted), 'flagged rows', len(C.bad()))
for b in C.bad()[:70]: print('  ', b['location'], '|', b['label'], '|', str(b['shown'])[:70], '|', str(b['yours'])[:70])
