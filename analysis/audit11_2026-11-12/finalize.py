"""Merge every check into all_checks.csv and disagreements.csv, plus the label / wording rows."""
import csv, json, os, collections
OUT = os.path.dirname(os.path.abspath(__file__))
rows = []
for s in ('replay', 'current'):
    rows += json.load(open(os.path.join(OUT, f'_{s}_data.json')))
    rows += [r for r in json.load(open(os.path.join(OUT, f'_{s}_page_checks.json')))]

LABELS = [
    ('Big number "rose 10% within 60 days"', 'share whose daily high reached entry x 1.10 in days 1-60', True, ''),
    ('"N% did it without ever falling 25.3%"', 'rose 10% and no daily low at or below entry x 0.747 in the 60 days', True, ''),
    ('"Typical high"', 'median of each signal\'s best daily high in 60 days vs entry', True, ''),
    ('"Typical drop from entry"', 'median of each signal\'s lowest daily low in 60 days vs entry', True, ''),
    ('"Dip before the high, from entry"', 'median lowest low up to and including the day of the 60-day high, vs entry', True, ''),
    ('"High lands around Day N" / "Deepest dip lands around Day N"', 'median day of the 60-day high / deepest low, counted from entry', True, ''),
    ('"Reached +20% ... · n" / "Touched -30% ... · n"', 'shares on the card sample, n shown', True, ''),
    ('"If it misses: went above entry X of Y · median best"', 'misses = did not rise 10%; X = best price above entry; median best move', True, ''),
    ('"Typical worst drop, misses" / "Typical change by day 60, misses"', 'medians over the misses; pool and count named in the label', True, ''),
    ('Ladder "From entry" / "Falls k% first"', 'rose 10% before falling 25.3%, after first falling k% before any +10%; n per row', True, ''),
    ('"Edge gone below"', 'first ladder row whose exact share is under 70%', True, ''),
    ('"By era" note', 'rose 10% and never fell 25.3%, split at 1 Jan 2022, n per era', True, ''),
    ('Live card "day N of 60", "best/worst so far"', 'day in progress; closed daily bars only', True, ''),
    ('Past signals columns', 'Confirmed = confirmation close date; Day 60 = day-60 close; High on day = day of 60-day high', True, ''),
    ('Previous signals badges', 'Reached +20% / Rose 10% / Missed (= did not rise 10%); On track / Edge lost from edge_status', True, ''),
    ('Cloud "median path / middle half"', 'median and 25th-75th percentile of daily closes vs entry, top-grade signals', True, ''),
    ('Footer "Daily candles closed through"', 'last closed daily bar', True, ''),
    ('Entry-quality wording (card foot, Past signals note, footer, How to read)', 'nothing reads as a return, a trade taken or a track record', True, ''),
]
for s in ('replay', 'current'):
    for lab, meaning, ok, cause in LABELS:
        rows.append(dict(state=s, location='page labels', label=lab, shown='(wording)', yours=meaning, ok='yes', cause=''))
# the two wording findings
P = {s: json.load(open(os.path.join(OUT, f'_{s}_page.json'))) for s in ('replay', 'current')}
for s, p in P.items():
    for sel, v in p['views'].items():
        for mode in ('chart_alert', 'chart_happened', 'chart_alert_again'):
            if mode in v and 'None on this one.' in (v[mode]['side'] or ''):
                rows.append(dict(state=s, location=f'page chart {sel} ({mode.replace("chart_", "")}) side box', label='lead trader markers',
                                 shown='"The lead trader\'s real entries and exits show on the chart as markers. None on this one."',
                                 yours='unknown: the trades feed was unreadable (404); the same screen says "Lead trader: unavailable"', ok='no',
                                 cause='label: asserts no trades without the data'))
    for sel, v in p['views'].items():
        tiles = ' | '.join(t for t, _ in v['now']['card']['tiles'])
        if ' A+' in tiles or ' C' in tiles.split('misses of all')[-1]:
            rows.append(dict(state=s, location=f'page card {sel}', label='grade code in member-facing labels',
                             shown=tiles.split(' | ')[6], yours='CONTEXT (member card redesign): "the grade stays internal"', ok='no',
                             cause='docs vs code'))
with open(os.path.join(OUT, 'all_checks.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(rows)
bad = [r for r in rows if r['ok'] == 'no']
with open(os.path.join(OUT, 'disagreements.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(bad)
print('total', len(rows), 'bad', len(bad))
c = collections.Counter((r['state'], r['location'].split(' ')[0] + ' ' + (r['location'].split(' ')[1] if len(r['location'].split(' ')) > 1 else '')) for r in rows)
for k, v in sorted(c.items()): print(k, v)
print(collections.Counter((r['state'], r['cause']) for r in bad))
