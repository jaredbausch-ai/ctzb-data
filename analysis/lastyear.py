"""Replay the market-state rating (analysis/twoweek.py) over the last year and score it.

DECLARED BEFORE RUNNING (22 Oct 2026).

  window     forecasts made on every day from 2025-10-22 to 2026-10-21 whose
             H-day outcome is complete by the last closed daily bar
  horizons   14, 30, 60, 90 calendar days
  forecast   built on day D from data knowable on D only:
               pool    days d with (D - d) > H (outcome closed), the same gate
                       state as D, all 12 features present
               BASE    the pool's own rates and percentiles
               ANALOG  40 nearest pool days on the twoweek.py S12 features,
                       standardised on that pool, declustered at 10 days
  primary    days with the gate ON (the only days the rating is built for)
  variant    days with the gate OFF, rated against a gate-OFF pool. The CTZB
             work never trades gate-off, so this is "what the method would have
             said if asked", reported separately and never pooled with ON
  scores     direction   call = up when P(up) >= 50%; hit rate
             Brier       P(up), P(touch +10), P(touch -10), P(touch +20), P(touch -20)
             calibration mean forecast vs realised frequency for each event
             band        share of realised returns inside the forecast IQR
                         (target 50%), below its p25 (25%), above its p75 (25%)
             median err  realised return minus forecast median, median and mean abs
  checks     a gate-ON forecast on a day that twoweek.py's walk-forward also
             tested must equal it (same pool rule, same picker)

Neighbouring days share most of their outcome window, so a year of daily
forecasts is a handful of independent cases at 60/90 days. Every gate-ON day
scorable at 60/90 falls inside 22 Oct - 5 Dec 2025: one episode, not a sample.

Run from the repo root:  python3 -I analysis/lastyear.py
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import twoweek as T

START, END = dt.date(2025, 10, 22), dt.date(2026, 10, 21)
EVENTS = [('up', lambda o: o['ret'] > 0), ('+10', lambda o: o['mfe'] >= 10), ('-10', lambda o: o['mae'] <= -10),
          ('+20', lambda o: o['mfe'] >= 20), ('-20', lambda o: o['mae'] <= -20)]


def forecast(days, oc):
    r = np.array([oc[d]['ret'] for d in days])
    f = {k: float(np.mean([fn(oc[d]) for d in days])) for k, fn in EVENTS}
    f.update(med=float(np.median(r)), q25=float(np.percentile(r, 25)), q75=float(np.percentile(r, 75)))
    return f


def score(rows, which):
    n = len(rows)
    if not n:
        return None
    out = dict(n=n)
    fc = [r[which] for r in rows]; ac = [r['act'] for r in rows]
    out['hit'] = 100 * np.mean([(f['up'] >= 0.5) == (a['ret'] > 0) for f, a in zip(fc, ac)])
    out['callup'] = 100 * np.mean([f['up'] >= 0.5 for f in fc])
    for k, fn in EVENTS:
        p = np.array([f[k] for f in fc]); y = np.array([float(fn(a)) for a in ac])
        out[f'b{k}'] = float(np.mean((p - y) ** 2)); out[f'p{k}'] = 100 * p.mean(); out[f'y{k}'] = 100 * y.mean()
    out['inband'] = 100 * np.mean([f['q25'] <= a['ret'] <= f['q75'] for f, a in zip(fc, ac)])
    out['below'] = 100 * np.mean([a['ret'] < f['q25'] for f, a in zip(fc, ac)])
    out['above'] = 100 * np.mean([a['ret'] > f['q75'] for f, a in zip(fc, ac)])
    err = np.array([a['ret'] - f['med'] for f, a in zip(fc, ac)])
    out['emed'] = float(np.median(err)); out['eabs'] = float(np.mean(np.abs(err)))
    return out


def main():
    gate = T.gate_daily()
    feats = T.SUBSETS['S12']
    for sym in ('ETH', 'BTC'):
        day, state = T.live_state(sym)
        last_closed = day['date'][-2]          # the newest daily bar is still forming
        for H in T.HORIZONS:
            oc, _ = T.outcomes(day, H)
            oc = {d: o for d, o in oc.items() if d + dt.timedelta(days=H) <= last_closed}
            allf = [d for d in day['date'] if d in oc and T.vec(state[d], feats) is not None]
            rows = []
            for D in day['date']:
                if not (START <= D <= END) or D not in oc or T.vec(state[D], feats) is None:
                    continue
                g = gate(D)
                pool = [d for d in allf if (D - d).days > H and gate(d) == g]
                X = np.array([T.vec(state[d], feats) for d in pool])
                ch = T.pick(pool, X, np.array(T.vec(state[D], feats)), T.K_PRIMARY)
                rows.append(dict(d=D, g=g, base=forecast(pool, oc), ana=forecast(ch, oc), act=oc[D],
                                 npool=len(pool)))
            print(f'==================== {sym}  H={H}  forecasts {rows[0]["d"]} .. {rows[-1]["d"]}')
            for lab, sel in (('GATE ON  (primary)', [r for r in rows if r['g']]),
                             ('GATE OFF (variant)', [r for r in rows if not r['g']])):
                if not sel:
                    print(f'  {lab}: no scorable days'); continue
                print(f'  {lab}: {len(sel)} days {sel[0]["d"]} .. {sel[-1]["d"]}  '
                      f'realised up {100*np.mean([r["act"]["ret"]>0 for r in sel]):.0f}%  '
                      f'median realised {np.median([r["act"]["ret"] for r in sel]):+.1f}%')
                for which in ('base', 'ana'):
                    s = score(sel, which)
                    print(f'    {which.upper():<6} called up {s["callup"]:3.0f}%  direction hit {s["hit"]:3.0f}%  '
                          f'in IQR {s["inband"]:3.0f}% (below {s["below"]:3.0f}% / above {s["above"]:3.0f}%)  '
                          f'median err {s["emed"]:+6.1f}%  mean |err| {s["eabs"]:5.1f}%')
                    print('           ' + '  '.join(f'{k}: fc {s[f"p{k}"]:3.0f}% real {s[f"y{k}"]:3.0f}% B {s[f"b{k}"]:.3f}'
                                              for k, _ in EVENTS))
            # monthly view, gate ON and OFF together but labelled
            print('  by month (base fc up / analog fc up / realised up, mean over days)')
            months = sorted({(r['d'].year, r['d'].month) for r in rows})
            for y, m in months:
                sel = [r for r in rows if (r['d'].year, r['d'].month) == (y, m)]
                gs = 'ON' if all(r['g'] for r in sel) else 'OFF' if not any(r['g'] for r in sel) else 'mix'
                print(f'    {y}-{m:02d} gate {gs:<3} n={len(sel):>2}  base {100*np.mean([r["base"]["up"] for r in sel]):3.0f}%  '
                      f'analog {100*np.mean([r["ana"]["up"] for r in sel]):3.0f}%  '
                      f'realised {100*np.mean([r["act"]["ret"]>0 for r in sel]):3.0f}%  '
                      f'med ret {np.median([r["act"]["ret"] for r in sel]):+6.1f}%')
            print()


if __name__ == '__main__':
    main()
