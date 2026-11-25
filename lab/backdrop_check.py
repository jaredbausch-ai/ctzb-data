"""Check the TradingView strip (lab/pine/ctzb_backdrop.pine) against the lab's own reads.

  python3 -I lab/backdrop_check.py <TradingView CSV export of an ETH 1D chart with the strip on>

For every closed daily bar in the export, the strip's "Band window on" / "Turn window on"
must equal lab/backdrop.py's BAND / TURN for an entry at that day's close. Prints the
agreement and every disagreement.
"""
import sys, os, csv, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'analysis')); sys.path.insert(0, ROOT); os.chdir(ROOT)
import backdrop as BD


def main(path, asset='ETH'):
    at = BD.backdrop_reader(asset)[0]
    rows = list(csv.DictReader(open(path)))
    n = ok = 0; bad = []
    for r in rows[:-1]:  # the last bar is still forming
        if not r.get('Band window on'): continue
        d = dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date()
        if d < dt.date(2017, 1, 1): continue
        e = at(d); tv = (r['Band window on'] == '1', r['Turn window on'] == '1')
        n += 1
        if tv == (e['BAND'], e['TURN']): ok += 1
        else: bad.append((d, tv, (e['BAND'], e['TURN'])))
    print(f'{asset} daily bars checked: {n}; strip agrees with the lab on {ok}')
    for d, tv, ex in bad[:50]:
        print(f'  {d}  strip band/turn {tv}  lab {ex}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'ETH')
