"""Collect every check into all_checks.csv (frozen states + synthetic), all_checks_replays.csv.gz (replays) and
disagreements.csv; print the counts used in AUDIT16.md."""
import csv, glob, gzip, collections, json, re
from common import OUT
COLS = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
def rd(p):
    return list(csv.DictReader(open(p)))
frozen = []
for st in ('REPLAY', 'CURRENT'):
    frozen += rd(f'{OUT}/checks_raw_{st}.csv') + rd(f'{OUT}/replays/checks_{st}.csv') + rd(f'{OUT}/checks_labels_{st}.csv')
# the must-close figure is also printed on the page (Now card line), same figure
pg = json.load(open(f'{OUT}/page_REPLAY.json'))
line = pg['sel']['ETH-1D-2026-11-13']['card']['head'][2]
frozen.append(dict(state='REPLAY', group='9 must-close-above wording', location='Now card ETH-1D-2026-11-13', label="'confirms ... if it closes above $X': a close 1 cent above X confirms, a close at X does not",
                   shown=re.search(r'above (\$[\d,.]+)', line).group(1), yours='$2,047.20', ok='False', cause='the threshold is $2,047.2081; rounded up to $2,047.21, so a close at exactly $2,047.21 also confirms'))
synth = rd(f'{OUT}/checks_SYNTH.csv')
with open(f'{OUT}/all_checks.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(COLS + ['check'])
    for r in frozen + synth:
        w.writerow([r[c] for c in COLS] + [r['group']])
rep = []; nrep = 0
with gzip.open(f'{OUT}/all_checks_replays.csv.gz', 'wt', newline='') as f:
    w = csv.writer(f); w.writerow(COLS + ['check'])
    for p in sorted(glob.glob(f'{OUT}/replays/checks_R2*.csv')):
        nrep += 1
        for r in rd(p):
            w.writerow([r[c] for c in COLS] + [r['group']]); 
            rep.append((r['state'], r['group'], r['ok'])) if r['ok'] == 'True' else rep.append(r)
stale = rd(f'{OUT}/replays/checks_Rstale_clock.csv'); bad_st = [r for r in stale if r['ok'] == 'False']; print('STALE-CLOCK', len(stale), len(bad_st))
bad_f = [r for r in frozen if r['ok'] == 'False']; bad_s = [r for r in synth if r['ok'] == 'False']; bad_r = [r for r in rep if isinstance(r, dict)]
print('FROZEN', len(frozen), 'checks;', len(bad_f), 'not ok')
for st in ('REPLAY', 'CURRENT'):
    rows = [r for r in frozen if r['state'] == st]
    by = collections.Counter(); byb = collections.Counter()
    for r in rows:
        k = r['group'].split()[0]; by[k] += 1; byb[k] += r['ok'] == 'False'
    print(' ', st, len(rows), {k: (by[k], byb[k]) for k in sorted(by, key=int)})
print('SYNTH', len(synth), len(bad_s)); print('REPLAYS', nrep, len(rep), len(bad_r))
c = collections.Counter(r['group'] for r in bad_r); print(c)
print('must-close distinct figures', len({(r['location'], r['shown']) for r in bad_r if 'must' in r['group']}), 'in replays', len({r['state'] for r in bad_r if 'must' in r['group']}))
print('on-track distinct setups', len({r['location'] for r in bad_r if 'on-track' in r['group']}), 'in replays', len({r['state'] for r in bad_r if 'on-track' in r['group']}))
with open(f'{OUT}/disagreements.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['scope'] + COLS + ['check'])
    for scope, rows in (('frozen state', bad_f), ('replay (other date)', bad_r), ('other state (clock ahead of candles)', bad_st), ('synthetic page state', bad_s)):
        for r in rows: w.writerow([scope] + [r[c] for c in COLS] + [r['group']])
    extra = [
        ('replay (other date)', 'R2020-12-27, R2020-12-31, R2021-01-01, R2021-03-15, R2021-11-05', 'pipeline: extras_live.py', 'runs when an asset/grade has signals but no miss', 'crash: statistics.median of an empty list (analysis/carddesign.py misses())', 'a row with misses = 0', 'False', 'the zero-miss guard in extras_live.py is never reached; cannot recur on today\'s ledger (every group has a miss)', 'other'),
        ('replay (other date)', '167 top-grade card renderings (e.g. R2023-12-29 ETH-1D-2023-10-31)', 'Now card, "If it misses: went above entry" row', 'row names the pool it counts', '"6 of 6 · median best +6.5%" beside "88% ... from all 25 past ETH 1D signals"', 'pool named on the row (6 misses of all 55 ETH top-grade signals)', 'False', 'pool is named only in the detail tiles on top-grade cards; below-grade cards carry it on the row', '9 label'),
        ('other state (clock ahead of candles)', 'Rstale_clock (candles to 11 Nov, clock 12 Nov 00:05 UTC)', 'feed.open_signals[*].days_elapsed; page day counts', 'day in progress by the clock', '51 (BTC 2D live setup)', '52', 'False', 'stack_live.py takes today from the last ETH daily candle, refresh.py / tagstats.py from the clock; 23 signals + 6 page rows', '6'),
        ('test harness', 'tests/replay_at.sh, tests/test_gate_off.sh', 'replayed candles', '"candles cut at the end of <date>"', '5D bar opening 2026-06-10 closes 65,706.62 (the 14 June close)', '63,563.42 (the 11 June close)', 'False', 'the open 2D-8D bar is kept whole, so it holds days after the replay date', 'other'),
        ('docs vs code', '', 'CONTEXT "one rounding rule ... the page\'s toFixed does the same"', 'prices rounded like rounding.py', 'page money() uses toLocaleString: $2,872.305 -> $2,872.31; $3,191.905 -> $3,191.90', 'rounding.py gives 2872.30 and 3191.90; exact half-away rule gives .31 and .91', 'False', 'half-cent ties are rounded three different ways', 'docs'),
        ('docs vs code', '', 'FEED_SPEC "days_elapsed in calendar days since that close"', 'clock date', 'stack_live.py: today = last ETH daily candle date', 'clock date (as refresh.py, tagstats.py)', 'False', 'two notions of today in one run', 'docs'),
        ('docs vs code', '', 'tests/replay_at.sh header', 'candles cut at the end of <date>', 'open 2D-8D bar keeps later days', 'bar rebuilt from the cut daily candles', 'False', '', 'docs'),
        ('docs vs code', '', 'CARD_SPEC "Anything on a different sample shows its own n ... the misses (their count and the pool)"', 'pool on the miss row', 'top-grade cards: pool only in the detail tiles', 'pool beside the count', 'False', '', 'docs'),
        ('docs vs code', '', 'CARD_SPEC "Confirms ... if [asset] closes above X" (the close below which the low would not confirm)', 'X such that any close above it confirms and X itself does not', 'stack_live.py rounds the threshold to the nearest cent (2047.2081 -> 2047.21)', 'rounded down (2047.20)', 'False', 'rounds up about half the time (see the replay rows)', 'docs'),
        ('docs vs code', '', 'FEED_SPEC audit #9: the page\'s 70% bar comes from odds_fade.posting_bar_pct', 'odds_fade.posting_bar_pct', 'page reads top-level posting_bar_pct first (audit #14)', '', 'False', 'the #9 sentence is out of date', 'docs'),
        ('docs vs code', '', 'FEED_SPEC "It computes nothing of its own"', 'repackaging only', 'feed_live.py derives odds_fade.tier_fixed_on and the sample sentence from its own clock', 'from refresh.py\'s tier anchor', 'False', 'same value unless refresh ran with another --tier or across a year change', 'docs'),
    ]
    for e in extra: w.writerow(e)
