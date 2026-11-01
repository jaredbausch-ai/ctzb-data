"""Does the confirmation close RECLAIMING a fib level add to the grade? Declared 31 Oct 2026.

Jared's question, 31 Oct: if the bar that confirms the signal closes above a fib level
that was acting as resistance, can that count toward the grade? fibtest.py tested where
the LOW sits (not special); this tests what the ENTRY CLOSE did relative to the levels.

UNIVERSE / OUTCOME as fibtest.py: 1,172 regime-gated signals on the 10 system charts,
entry = confirmation close ei = ti + 3, SURV10 / LIQ30 within 60 days.

SWING (before the trough bar ti only): fibtest.swing() for W in {30, 60, 90} days, and the
last 90 bars of the chart (BARS-90, fibfractal's passing scale). Range = H - L0.
FIB LEVELS (retracements of that swing, price = H - f * range): f in {0.236, 0.382, 0.5,
0.618, 0.786}. PLACEBO LEVELS, same count, not fib numbers: f in {0.30, 0.45, 0.55, 0.70, 0.85}.

LENSES (each run on fib levels AND placebo levels):
  C1 RECLAIM    the trough bar CLOSED below a level and the entry close is above it
                (at least one level reclaimed during the confirmation)
  C2 RECLAIM_DEEP  same, but the level reclaimed is 0.618 or deeper (placebo: 0.70+)
  C3 JUST_ABOVE the entry close sits 0-2% ABOVE a level (support just under the entry)
  C4 JUST_BELOW the entry close sits 0-2% BELOW a level (resistance just over the entry)
  4 lenses x 4 swings = 16 fib cells, 16 placebo cells.

PASS RULES, fib cells (A1-A7 as stochdwell/fibtest), plus
  A8  passes A1-A7 at two of the four swings, same direction
  A9  lift >= 5 (same direction) stratified by bounce size (entry close / trough low,
      terciles) -- reclaiming a level is partly just "bounced further", and "rebound
      already paid" died in the 23 Oct sweep
  A10 beats its PLACEBO cell (same lens, same swing) by >= 5 points in its direction.
      If made-up levels do as well, the levels are not what is working.

Run from the repo root:  python3 -I analysis/fibreclaim.py
"""
import sys, os, statistics, datetime as dt
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import stochdwell as S
import fibtest as F

FIB = (0.236, 0.382, 0.5, 0.618, 0.786)
PLACEBO = (0.30, 0.45, 0.55, 0.70, 0.85)
SWINGS = ('30d', '60d', '90d', 'BARS-90')
LENSES = ('C1_RECLAIM', 'C2_RECLAIM_DEEP', 'C3_JUST_ABOVE', 'C4_JUST_BELOW')


def swing_of(ch, ti, sw):
    if sw.endswith('d'):
        return F.swing(ch, ti, int(sw[:-1]))
    hi, lo = ch.b['high'], ch.b['low']
    js = list(range(max(0, ti - 90), ti))
    if len(js) < 90: return None
    h = max(js, key=lambda j: hi[j]); L0 = min(lo[j] for j in js if j <= h)
    return (hi[h], L0) if hi[h] > L0 else None


def lens_flags(H, L0, ctr, cen, fs, deep):
    rng = H - L0
    lv = [(f, H - f * rng) for f in fs if H - f * rng > 0]
    rec = [f for f, p in lv if ctr < p <= cen]
    return {'C1_RECLAIM': bool(rec),
            'C2_RECLAIM_DEEP': any(f >= deep for f in rec),
            'C3_JUST_ABOVE': any(0 <= (cen / p - 1) <= 0.02 for f, p in lv),
            'C4_JUST_BELOW': any(0 < (p / cen - 1) <= 0.02 for f, p in lv)}


def build():
    rows = []
    for ch in S.load_charts(S.SYS_TF):
        sig, _ = E.signals(f'data/{ch.sym}_{ch.tf}.csv', regime=S.GATE)
        c, lo = ch.b['close'], ch.b['low']
        for s in sig:
            ti, ei = s['ti'], s['ei']; o = ch.outcome(ei)
            if o is None: continue
            r = dict(chart=ch.name, asset=ch.sym, date=ch.b['date'][ei], bk=s['bk'], prime=s['prime'],
                     bounce=c[ei] / lo[ti] - 1, **o)
            for sw in SWINGS:
                g = swing_of(ch, ti, sw)
                for tag, fs, deep in (('F', FIB, 0.618), ('P', PLACEBO, 0.70)):
                    fl = lens_flags(*g, c[ti], c[ei], fs, deep) if g else {L: None for L in LENSES}
                    for L in LENSES: r[f'{tag}:{L}@{sw}'] = fl[L]
            rows.append(r)
    b = sorted(r['bounce'] for r in rows)
    t1, t2 = b[len(b) // 3], b[2 * len(b) // 3]
    for r in rows: r['btert'] = 0 if r['bounce'] < t1 else 1 if r['bounce'] < t2 else 2
    return rows


def cell(rows, key):
    pct = lambda v: 100 * statistics.mean(v) if v else float('nan')
    v = [r for r in rows if r[key] is not None]
    for r in v: r['_k'] = r[key]
    w = [r for r in v if r['_k']]; wo = [r for r in v if not r['_k']]
    if not w or not wo: return None
    sw, so = pct([r['surv'] for r in w]), pct([r['surv'] for r in wo])
    lw, lo = pct([r['liq'] for r in w]), pct([r['liq'] for r in wo])
    lift = sw - so; sgn = 1 if lift > 0 else -1
    def split(kf, minn):
        g = defaultdict(lambda: ([], []))
        for r in v: g[kf(r)][0 if r['_k'] else 1].append(r['surv'])
        return {x: (pct(a) - pct(b), min(len(a), len(b))) for x, (a, b) in g.items()
                if len(a) >= minn and len(b) >= minn}
    per = split(lambda r: 'old' if r['date'] < S.CUT else 'new', 10)
    cs, cn = S.same_sign_share(split(lambda r: r['chart'], 8), sgn, 0)
    ys, yn = S.same_sign_share(split(lambda r: r['date'].year, 5), sgn, 0)
    bka = S.strat_lift(v, '_k', lambda r: r['bk']); pra = S.strat_lift(v, '_k', lambda r: r['prime'])
    bta = S.strat_lift(v, '_k', lambda r: r['btert'])
    checks = [len(w) >= 40 and len(wo) >= 40, abs(lift) >= 8, (lw <= lo) if sgn > 0 else (lw >= lo),
              'old' in per and 'new' in per and per['old'][0] * sgn > 0 and per['new'][0] * sgn > 0,
              cs is not None and cs >= 2 / 3, ys is not None and ys >= 0.6,
              bka is not None and pra is not None and bka * sgn >= 5 and pra * sgn >= 5]
    failed = [f'A{j + 1}' for j, ok in enumerate(checks) if not ok]
    if bta is None or bta * sgn < 5: failed.append('A9')
    return dict(nw=len(w), nwo=len(wo), sw=sw, so=so, lw=lw, lo=lo, lift=lift, sgn=sgn, per=per,
                cs=(cs, cn), ys=(ys, yn), bka=bka, pra=pra, bta=bta, failed=failed)


def main():
    print(__doc__.split('Run from')[0])
    rows = build()
    fx = lambda x: f'{x:+.0f}' if x is not None else '-'
    print(f'  {"lens@swing":<24}{"n with":>7}{"SURV":>6}{"LIQ":>5}{"n w/o":>7}{"SURV":>6}{"LIQ":>5}{"lift":>6}'
          f'{"<2022":>7}{"2022+":>7}{"charts":>8}{"years":>7}{"bk-adj":>7}{"pr-adj":>7}{"bounce-adj":>11}'
          f'{"placebo":>8}  verdict')
    ok = defaultdict(list)
    for L in LENSES:
        for sw in SWINGS:
            e = cell(rows, f'F:{L}@{sw}'); p = cell(rows, f'P:{L}@{sw}')
            if e is None: print(f'  {L}@{sw}  (empty)'); continue
            failed = list(e['failed'])
            if p is None or (e['lift'] - p['lift']) * e['sgn'] < 5: failed.append('A10')
            if not failed: ok[L].append((sw, e['sgn']))
            fp = lambda k: f'{e["per"][k][0]:+.0f}' if k in e['per'] else '-'
            cs = f'{e["cs"][0]*100:.0f}%/{e["cs"][1]}' if e['cs'][0] is not None else '-'
            ys = f'{e["ys"][0]*100:.0f}%/{e["ys"][1]}' if e['ys'][0] is not None else '-'
            print(f'  {L + "@" + sw:<24}{e["nw"]:>7}{e["sw"]:>6.0f}{e["lw"]:>5.0f}{e["nwo"]:>7}{e["so"]:>6.0f}'
                  f'{e["lo"]:>5.0f}{e["lift"]:>+6.0f}{fp("old"):>7}{fp("new"):>7}{cs:>8}{ys:>7}{fx(e["bka"]):>7}'
                  f'{fx(e["pra"]):>7}{fx(e["bta"]):>11}{(fx(p["lift"]) if p else "-"):>8}  '
                  f'{"PASS A1-A7,A9,A10" if not failed else "fail " + ",".join(failed)}')
        print()
    print('A8 (two of the four swings, same direction):')
    for L in LENSES:
        hits = ok.get(L, [])
        same = len(hits) >= 2 and len({s for _, s in hits}) == 1
        print(f'  {L:<18}' + (('PASS at ' + ', '.join(w for w, _ in hits)) if same else
                              ('one swing only: ' + hits[0][0]) if len(hits) == 1 else 'none'))
    print('\nEntry quality only. No exit in the data; not a strategy return or a track record.')


if __name__ == '__main__':
    main()
