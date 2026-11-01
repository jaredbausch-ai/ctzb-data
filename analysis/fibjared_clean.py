"""fibjared reach table, clean version. 31 Oct 2026. Information only, not a lens.

The fibjared reach table counted a level as reached on day 0 when the entry close was
already above it, which inflates the higher grades (strong bounces are already past the
lower levels at entry). This keeps ONLY signals still BELOW each level at entry, so the
figure is the chance price goes on to reach that level within 60 days, from entry.
Also printed: the share already above at entry, and the median drop size by grade.

Run from the repo root:  python3 -I analysis/fibjared_clean.py
"""
import sys, os, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fibjared as J

rows = J.build()
led = {(r['chart'], r['entry']): r['grade'] for r in csv.DictReader(open('datasets/ledger.csv'))}
for k in J.KS:
    v = [r for r in rows if r[f'reach@k{k}']]
    print(f'\nFRACTAL k={k}: of signals still BELOW the level at entry, % that reached it within 60 days '
          f'(n below / % already above at entry)')
    print(f'  {"group":<6}{"n":>5}{"drop":>7}' + ''.join(f'{f:>16}' for f in J.REACH))
    for name in ('all', 'A+', 'A', 'B', 'C'):
        gr = v if name == 'all' else [r for r in v if led.get((r['chart'], r['end'].isoformat() if r['end'] else '')) == name]
        if not gr: continue
        drops = sorted(r[f'leg@k{k}'] for r in gr)
        cells = []
        for f in J.REACH:
            d = [r[f'reach@k{k}'][f] for r in gr]
            below = [x for x in d if x != 0]
            hit = [x for x in below if x is not None]
            above = 100 * (len(d) - len(below)) / len(d)
            cells.append(f'{(100 * len(hit) / len(below)) if below else float("nan"):>4.0f}% n{len(below):<4}({above:.0f}%)')
        print(f'  {name:<6}{len(gr):>5}{drops[len(drops)//2]:>6.1f}%' + ''.join(f'{c:>16}' for c in cells))
print('\nEntry quality only. Exits stay discretionary; this is information, not a target rule.')
