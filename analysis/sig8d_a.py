"""8D bucket A (CT < 40 at the trough) and A + diamond: +20% / +10% / -30% within 60 days of the
confirmation close (ei = ti + 3), gated and ungated. Descriptive; 8D is not graded. (Jared, 23 Nov 2026)
ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.
  python3 -I analysis/sig8d_a.py -> analysis/RESULTS_sig8d_a.txt
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine as E, regimes as R
from tagstats import bucket_end
G = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41); out = []
for a in ('ETH', 'BTC'):
    day = E.load(f'data/{a}_1D.csv'); pos = {d: i for i, d in enumerate(day['date'])}
    for gname, reg in (('gated', G), ('ungated', lambda d: True)):
        sig, b = E.signals(f'data/{a}_8D.csv', regime=reg); ct = E.rsi(b['close'], 14)
        for lab, f in (('A any', lambda s: ct[s['ti']] < 40), ('A + diamond', lambda s: ct[s['ti']] < 40 and s['dis'])):
            rows = []
            for s in sig:
                if not f(s): continue
                d0 = bucket_end(b['date'], s['ei']); i = pos.get(d0)
                if i is None or i + 60 >= len(day['date']): continue
                c0 = day['close'][i]; hi = max(day['high'][i + 1:i + 61]) / c0 - 1; lo = min(day['low'][i + 1:i + 61]) / c0 - 1
                rows.append((d0, hi, lo))
            n = len(rows)
            if not n: continue
            out.append(f'{a} 8D {gname} {lab}: n {n}, +20% {100*sum(h >= .2 for _, h, _ in rows)/n:.0f}%, +10% {100*sum(h >= .1 for _, h, _ in rows)/n:.0f}%, '
                       f'-30% {100*sum(l <= -.3 for _, _, l in rows)/n:.0f}% | ' + ', '.join(f'{d} {100*h:+.0f}/{100*l:+.0f}' for d, h, l in rows))
out.append('ENTRY QUALITY ONLY. No exit in the data. Computed signals, never fills.')
open(os.path.join(HERE, 'RESULTS_sig8d_a.txt'), 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
