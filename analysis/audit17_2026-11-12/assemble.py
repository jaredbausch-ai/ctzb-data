"""Audit 17: collect every comparison into all_checks.csv (the two frozen states and the synthetic page states in
full), disagreements.csv (every disagreement, replays included) and counts by check number."""
import csv, glob, gzip, os, collections, json, sys
A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HDR = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
csv.field_size_limit(10**9)


def check_no(loc):
    if loc.startswith(('data ', 'datasets ', 'example json', 'gate')): return '0 data files'
    if loc.startswith('ledger'): return '1 ledger'
    if loc.startswith('grade_odds'): return '2 grade_odds'
    if loc.startswith(('if_it_misses', 'example_if_it_misses')): return '3 if_it_misses'
    if loc.startswith('odds_fade'): return '4 odds_fade'
    if loc.startswith(('card ', 'cards')) or (loc.startswith('open ') and loc.endswith(' card')): return '5 cards'
    if loc.startswith(('open', 'print', 'top level')): return '6 open signals, prints, top level'
    if loc.startswith(('past_paths', 'example_past_paths')): return '7 past paths'
    if loc.startswith('page'): return '8 page'
    if loc.startswith('labels'): return '10 labels on feed records'
    return 'other'


def read(p):
    op = gzip.open if p.endswith('.gz') else open
    with op(p, 'rt', newline='') as f:
        r = csv.reader(f); next(r)
        return [x for x in r]

frozen = []
for st in ('replay', 'current'):
    frozen += read(f'{A}/out/data_{st}.csv') + read(f'{A}/out/all_{st}.csv')
synth = read(f'{A}/out/synth.csv') + read(f'{A}/out/synth_tz.csv') + read(f'{A}/out/synth_trades.csv')
with open(f'{A}/all_checks.csv', 'w', newline='') as f:
    csv.writer(f).writerows([HDR] + frozen + synth)
counts = collections.OrderedDict()
for r in frozen:
    k = (r[0], check_no(r[1])); c = counts.setdefault(k, [0, 0]); c[0] += 1; c[1] += r[5] != 'ok'
dis = [r for r in frozen + synth if r[5] != 'ok']
rep = {}
files = sorted(glob.glob(f'{A}/out/rp/*.csv.gz')) + sorted(glob.glob(f'{A}/out/rp2/*.csv.gz'))
for p in files:
    rows = read(p)
    if not rows: continue
    name = rows[0][0]
    rep[name] = (len(rows), sum(1 for r in rows if r[5] != 'ok'), [r for r in rows if r[5] != 'ok'])
dis += [r for v in rep.values() for r in v[2]]
# findings that are not row-by-row comparisons: pipeline failures in replays, and docs vs code
EXTRA = [
 ['R_2026-03-15', 'pipeline stack_live.py -> feed, page card', 'quiet market (no low forming on any chart, no signal in the last 60 days): the run passes and the page shows the quiet card',
  'COVERAGE FAILURE (every registry id "never evaluated"); stack_status FAILED; feed withheld; page: "Setups held back / A data check failed on the latest run", footer "checks FAILED, cards held back"',
  'run passes; page: "No setup right now / Waiting for the next one / The market filter is off ..."', 'DISAGREE', 'check_coverage() fails when there is no subject to evaluate'],
 ['R_2026-02-16', 'pipeline stack_live.py -> feed, page card', 'quiet market: the run passes', 'COVERAGE FAILURE, feed withheld', 'run passes, quiet card', 'DISAGREE', 'same as R_2026-03-15'],
 ['R_2026-07-24', 'pipeline stack_live.py -> feed, page card', 'quiet market: the run passes', 'COVERAGE FAILURE, feed withheld', 'run passes, quiet card', 'DISAGREE', 'same as R_2026-03-15'],
 ['DOCS', 'docs/FEED_SPEC.md "Fail-closed feed"', '"Readers need no special case: it is a withheld feed"', 'the member page reads that feed as "Market filter: off" with an empty scored date', 'needs a special case (no market_regime / scored_as_of in that feed)', 'DISAGREE', 'docs vs code'],
 ['DOCS', 'docs/FEED_SPEC.md "Audit #16 corrections" (and SITE_CHANGES 6c)', '"a missing chart file ... read as unavailable, not as ... the previous setup\'s figures"', 'example chart file missing: the previous setup\'s cloud and caption stay on screen', 'cleared', 'DISAGREE', 'docs vs code'],
 ['DOCS', 'docs/CARD_SPEC.md "The member site\'s card" (and CONTEXT 31 Oct note)', 'the live card "says \'Edge lost\' or \'On track\'"', 'the page has a third status, "Rose 10%" (only FEED_SPEC audit #16 mentions it)', 'three statuses defined in CARD_SPEC', 'DISAGREE', 'docs vs code'],
 ['EARLY-HISTORY (not counted)', 'pipeline refresh.py', 'replay 2018-12-10 runs', 'ZeroDivisionError', 'n/a', 'not counted', 'before any walk-forward baseline exists; not reachable going forward'],
 ['EARLY-HISTORY (not counted)', 'pipeline extras_live.py', 'replays 2019-12-30, 2019-12-31, 2020-01-01, 2020-01-02, 2020-01-03, 2020-06-07 run', 'IndexError (paths of an empty example sample)', 'n/a', 'not counted', 'before any ETH top-grade signal is known; not reachable going forward'],
]
dis += EXTRA
with open(f'{A}/disagreements.csv', 'w', newline='') as f:
    csv.writer(f).writerows([HDR] + dis)
with open(f'{A}/replay_summary.csv', 'w', newline='') as f:
    csv.writer(f).writerows([['replay', 'comparisons', 'disagreements']] + [[k, v[0], v[1]] for k, v in sorted(rep.items())])
print('frozen comparisons', len(frozen), 'disagreements', sum(1 for r in frozen if r[5] != 'ok'))
for (st, k), c in sorted(counts.items(), key=lambda x: (x[0][1], x[0][0])): print(f'  {k:40s} {st:8s} {c[0]:6d}  {c[1]}')
print('synthetic', len(synth), 'disagreement rows', sum(1 for r in synth if r[5] != 'ok'), 'states', len(set(r[1] for r in synth)))
print('replays', len(rep), 'comparisons', sum(v[0] for v in rep.values()), 'disagreement rows', sum(v[1] for v in rep.values()), 'replays with any', sum(1 for v in rep.values() if v[1]))
for k, v in sorted(rep.items()):
    if v[1]: print('   ', k, v[:2], sorted(set(r[2].split(' [')[0][:60] for r in v[2]))[:8])
