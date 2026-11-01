"""Jared's fib: last fractal high down to the signal low. Declared 31 Oct 2026.

Jared, 31 Oct: "I use the high from the last fractal before that, and then the low, and it
goes to fib numbers." fibtest / fibreclaim / fibdist all drew the PRIOR RISE (the low a run
started from up to its high) and asked where the pullback landed. Jared draws the DROP:
from the last fractal high before the low, down to the low. The levels then sit ABOVE the
low and are the resistance the bounce has to get through. Not tested before tonight.

UNIVERSE / OUTCOME as fibreclaim.py: regime-gated signals, 10 system charts, entry =
confirmation close ei = ti + 3, SURV10 / LIQ30 within 60 days.

THE FIB (knowable at entry):
  Fractal high: a Williams fractal, high[j] above the highs of the k bars each side.
    k = 2 (the standard 5-bar fractal) and k = 5 (a bigger one), as two scales.
  H = high of the last fractal high confirmed before the trough (j <= ti - k, j < ti).
  L = low[ti], the signal low.  Skipped if H <= L.
  Level f sits at L + f * (H - L): f in {0.236, 0.382, 0.5, 0.618, 0.786}, 1.0 = back to H.
  PLACEBO levels, not fib numbers: {0.30, 0.45, 0.55, 0.70, 0.85}.

LENSES at the entry close (each also run on the placebo levels):
  J1 ABOVE_236   entry close already above the 0.236
  J2 ABOVE_382   entry close already above the 0.382
  J3 ABOVE_500   entry close already above the 0.5
  J4 UNDER_LEVEL the next level above the entry is within 2% (resistance right overhead)

PASS RULES: A1-A7 as fibtest; A9 holds (>= 5, same direction) inside bounce-size terciles
(entry close / trough low), because being above a level is partly just bouncing further;
A10 beats its placebo cell by >= 5; A8 passes at both fractal sizes, same direction.

ALSO PRINTED, information only, not a lens (Jared's other use of the levels): the share of
signals whose price REACHED each level within 60 days of entry, and the median days to get
there, overall and by grade letter on the graded ledger. Exits stay discretionary.

Run from the repo root:  python3 -I analysis/fibjared.py
"""
import sys, os, csv, statistics, datetime as dt
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import stochdwell as S
import fibreclaim as FR
from tagstats import bucket_end

FIB = (0.236, 0.382, 0.5, 0.618, 0.786)
PLACEBO = (0.30, 0.45, 0.55, 0.70, 0.85)
KS = (2, 5)
LENSES = ('J1_ABOVE_236', 'J2_ABOVE_382', 'J3_ABOVE_500', 'J4_UNDER_LEVEL')
REACH = (0.236, 0.382, 0.5, 0.618, 0.786, 1.0)


def fractal_highs(hi, k):
    n = len(hi)
    return [k <= j < n - k and all(hi[j] > hi[x] for x in range(j - k, j))
            and all(hi[j] > hi[x] for x in range(j + 1, j + k + 1)) for j in range(n)]


def flags(H, L, cen, fs):
    lv = [L + f * (H - L) for f in fs]
    above = [cen > p for p in lv]
    nxt = [p for p in lv if p > cen]
    return {'J1_ABOVE_236': above[0], 'J2_ABOVE_382': above[1], 'J3_ABOVE_500': above[2],
            'J4_UNDER_LEVEL': bool(nxt) and (min(nxt) / cen - 1) <= 0.02}


def reach_days(ch, ei, H, L):
    """Days from entry until the daily high first reaches each level, within 60 days."""
    day, pos = S.day_series(ch.sym)
    de = bucket_end(ch.b['date'], ei)
    if de is None or de not in pos: return None
    i = pos[de]; end = de + dt.timedelta(days=60)
    out = {}
    for f in REACH:
        p = L + f * (H - L)
        if ch.b['close'][ei] >= p:
            out[f] = 0; continue
        out[f] = None
        for k in range(i + 1, len(day['date'])):
            if day['date'][k] > end: break
            if day['high'][k] >= p:
                out[f] = (day['date'][k] - de).days; break
    if day['date'][-1] < end: return None
    return out


def build():
    rows = []
    for ch in S.load_charts(S.SYS_TF):
        sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=S.GATE)
        c, lo, hi = ch.b['close'], ch.b['low'], ch.b['high']
        fh = {k: fractal_highs(hi, k) for k in KS}
        for s in sig:
            ti, ei = s['ti'], s['ei']; o = ch.outcome(ei)
            if o is None: continue
            r = dict(chart=ch.name, asset=ch.sym, date=ch.b['date'][ei], end=bucket_end(ch.b['date'], ei),
                     bk=s['bk'], prime=s['prime'], bounce=c[ei] / lo[ti] - 1, **o)
            for k in KS:
                j = next((x for x in range(ti - k, -1, -1) if fh[k][x]), None)
                H = hi[j] if j is not None else None; L = lo[ti]
                ok = H is not None and H > L
                for tag, fs in (('F', FIB), ('P', PLACEBO)):
                    fl = flags(H, L, c[ei], fs) if ok else {x: None for x in LENSES}
                    for x in LENSES: r[f'{tag}:{x}@k{k}'] = fl[x]
                r[f'reach@k{k}'] = reach_days(ch, ei, H, L) if ok else None
                r[f'leg@k{k}'] = (H / L - 1) * 100 if ok else None
            rows.append(r)
    b = sorted(r['bounce'] for r in rows)
    t1, t2 = b[len(b) // 3], b[2 * len(b) // 3]
    for r in rows: r['btert'] = 0 if r['bounce'] < t1 else 1 if r['bounce'] < t2 else 2
    return rows


def main():
    print(__doc__.split('Run from')[0])
    rows = build()
    fx = lambda x: f'{x:+.0f}' if x is not None else '-'
    print(f'  {"lens@fractal":<22}{"n with":>7}{"SURV":>6}{"LIQ":>5}{"n w/o":>7}{"SURV":>6}{"LIQ":>5}{"lift":>6}'
          f'{"<2022":>7}{"2022+":>7}{"charts":>8}{"years":>7}{"bk-adj":>7}{"pr-adj":>7}{"bounce-adj":>11}'
          f'{"placebo":>8}  verdict')
    ok = defaultdict(list)
    for L in LENSES:
        for k in KS:
            e = FR.cell(rows, f'F:{L}@k{k}'); p = FR.cell(rows, f'P:{L}@k{k}')
            if e is None: print(f'  {L}@k{k} (empty)'); continue
            failed = list(e['failed'])
            if p is None or (e['lift'] - p['lift']) * e['sgn'] < 5: failed.append('A10')
            if not failed: ok[L].append(e['sgn'])
            fp = lambda q: f'{e["per"][q][0]:+.0f}' if q in e['per'] else '-'
            cs = f'{e["cs"][0]*100:.0f}%/{e["cs"][1]}' if e['cs'][0] is not None else '-'
            ys = f'{e["ys"][0]*100:.0f}%/{e["ys"][1]}' if e['ys'][0] is not None else '-'
            print(f'  {L + "@k" + str(k):<22}{e["nw"]:>7}{e["sw"]:>6.0f}{e["lw"]:>5.0f}{e["nwo"]:>7}{e["so"]:>6.0f}'
                  f'{e["lo"]:>5.0f}{e["lift"]:>+6.0f}{fp("old"):>7}{fp("new"):>7}{cs:>8}{ys:>7}{fx(e["bka"]):>7}'
                  f'{fx(e["pra"]):>7}{fx(e["bta"]):>11}{(fx(p["lift"]) if p else "-"):>8}  '
                  f'{"PASS A1-A7,A9,A10" if not failed else "fail " + ",".join(failed)}')
    print('\nA8 (both fractal sizes, same direction):')
    for L in LENSES:
        h = ok.get(L, [])
        print(f'  {L:<16}' + ('PASS' if len(h) == 2 and len(set(h)) == 1 else f'{len(h)} of 2'))

    # information: did price reach each level within 60 days
    led = {(r['chart'], r['entry']): r['grade'] for r in csv.DictReader(open('datasets/ledger.csv'))}
    for k in KS:
        v = [r for r in rows if r[f'reach@k{k}']]
        legs = sorted(r[f'leg@k{k}'] for r in v)
        print(f'\nREACHED EACH LEVEL OF THE DROP WITHIN 60 DAYS  (fractal k={k}, {len(v)} signals, '
              f'median drop from fractal high to the low {legs[len(legs)//2]:.1f}%)')
        print(f'  {"group":<10}{"n":>5}' + ''.join(f'{f:>11}' for f in REACH))
        groups = [('all', v)] + [(g, [r for r in v if led.get((r['chart'], r['end'].isoformat() if r['end'] else '')) == g])
                                 for g in ('A+', 'A', 'B', 'C')]
        for name, gr in groups:
            if not gr: continue
            cells = []
            for f in REACH:
                got = [r[f'reach@k{k}'][f] for r in gr]
                hit = [x for x in got if x is not None]
                med = sorted(hit)[len(hit) // 2] if hit else None
                cells.append(f'{100 * len(hit) / len(got):>5.0f}% {("d" + str(med)) if med is not None else "":>4}')
            print(f'  {name:<10}{len(gr):>5}' + ''.join(f'{c:>11}' for c in cells))
    print('\n  (% that reached the level, median days to reach it; 0 = already above at entry)')
    print('\nEntry quality only. No exit in the data; not a strategy return or a track record.')


if __name__ == '__main__':
    main()
