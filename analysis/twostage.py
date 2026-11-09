"""Two-stage trade: enter on a confirmed 1D bucket-A signal, let the 2D pivot decide.

Declared by Jared, 9 Nov 2026, before running.

ENTRY   A confirmed bucket-A signal on the 1D (CT RSI < 40 at the trough),
        regime gate on, entry at the close of the confirmation bar (ei = ti+3).

THE WATCH  At that entry date, is a 2D pivot CANDIDATE pending -- a 2D bar whose
        CT is strictly below the 3 bars before it, with fewer than 3 bars to its
        right and not yet broken? If none is pending the signal is not part of
        this test and is reported separately.

EXIT / HOLD
        VANISH   a later 2D bar prints CT <= the candidate's CT before it gets
                 its 3 clean bars. Close at that 2D bar's close. A COMPLETE
                 TRADE: entry, exit, realised return.
        CONFIRM  the candidate gets 3 bars to the right and becomes a real
                 pivot. Jared stays in or adds, so there is no exit. Measured as
                 best upside from entry, worst drawdown from entry, and 30- and
                 60-day return from entry.

Entry quality only on the CONFIRM leg: there is no exit in that branch, so its
numbers are not a strategy return. The VANISH leg is a real round trip.
"""
import csv, datetime as dt, statistics as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R

PVL = PVR = 3
ZBEAR = 40.0


def series(path):
    b = E.load(path)
    ct = E.rsi(b['close'], 14)
    k = E.sma(E.stoch_of(ct, 14), 3)
    return b, ct, k


def pending_candidate(ct, d, asof_i):
    """The most recent un-confirmed, un-broken 2D pivot candidate at bar asof_i."""
    for i in range(asof_i, max(asof_i - PVR, PVL) - 1, -1):
        if i - PVL < 0 or ct[i] is None:
            continue
        if any(ct[j] is None for j in range(i - PVL, asof_i + 1)):
            continue
        if not all(ct[j] > ct[i] for j in range(i - PVL, i)):
            continue
        if not all(ct[j] > ct[i] for j in range(i + 1, asof_i + 1)):
            continue
        if asof_i - i >= PVR:          # already confirmed, not pending
            continue
        return i
    return None


def resolve(ct, cand, n):
    """CONFIRM at the bar that completes PVR clean bars, or VANISH at the breaker."""
    for j in range(cand + 1, min(cand + PVR + 1, n)):
        if ct[j] is None:
            return None, None
        if ct[j] <= ct[cand]:
            return 'VANISH', j
    if cand + PVR < n:
        return 'CONFIRM', cand + PVR
    return None, None


def run(asset):
    b1, ct1, k1 = series(f'data/{asset}_1D.csv')
    b2, ct2, k2 = series(f'data/{asset}_2D.csv')
    g = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    out, _ = E.signals(f'data/{asset}_1D.csv', regime=g, ungated=False)
    sigs = [s for s in out if s['bk'] == 'A']

    d2 = b2['date']; c2 = b2['close']
    c1 = b1['close']; h1 = b1['high']; l1 = b1['low']; d1 = b1['date']
    pos2 = {x: i for i, x in enumerate(d2)}
    n2 = len(d2); n1 = len(d1)

    rows = []
    no_cand = 0
    for s in sigs:
        ei = s['ei']
        if ei >= n1:
            continue
        ed = d1[ei]
        # the 2D bar holding the entry date (2D bar dated D covers D and D+1)
        i2 = None
        for cand_d in (ed, ed - dt.timedelta(days=1)):
            if cand_d in pos2:
                i2 = pos2[cand_d]; break
        if i2 is None:
            continue
        cand = pending_candidate(ct2, d2, i2)
        if cand is None:
            no_cand += 1
            continue
        verdict, j = resolve(ct2, cand, n2)
        if verdict is None:
            continue
        entry = c1[ei]
        row = dict(asset=asset, entry_date=ed, entry=entry, verdict=verdict,
                   cand_date=d2[cand], cand_ct=ct2[cand], cand_k=k2[cand],
                   cand_bk='A' if ct2[cand] < ZBEAR else 'B+',
                   cand_prime=(k2[cand] is not None and 20 <= k2[cand] < 50))
        if verdict == 'VANISH':
            row['exit_date'] = d2[j]
            row['exit'] = c2[j]
            row['ret'] = 100 * (c2[j] / entry - 1)
            # worst low between entry and that exit, on the 1D
            seg = [l1[x] for x in range(ei + 1, n1) if d1[x] <= d2[j] + dt.timedelta(days=1)]
            row['dd'] = 100 * (min(seg) / entry - 1) if seg else 0.0
        else:
            for H in (30, 60):
                end = ed + dt.timedelta(days=H)
                seg = [x for x in range(ei + 1, n1) if d1[x] <= end]
                if not seg:
                    row[f'r{H}'] = None; row[f'up{H}'] = None; row[f'dd{H}'] = None
                    continue
                row[f'r{H}'] = 100 * (c1[seg[-1]] / entry - 1)
                row[f'up{H}'] = 100 * (max(h1[x] for x in seg) / entry - 1)
                row[f'dd{H}'] = 100 * (min(l1[x] for x in seg) / entry - 1)
        rows.append(row)
    return rows, no_cand, len(sigs)


def agg(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return dict(n=len(vals), mean=st.mean(vals), med=st.median(vals),
                worst=min(vals), best=max(vals))


if __name__ == '__main__':
    for asset in ('ETH', 'BTC'):
        rows, no_cand, nsig = run(asset)
        V = [r for r in rows if r['verdict'] == 'VANISH']
        C = [r for r in rows if r['verdict'] == 'CONFIRM']
        print(f'\n===== {asset} =====')
        print(f'1D bucket-A signals, gate on: {nsig}')
        print(f'  with a 2D pivot candidate pending at entry: {len(rows)}')
        print(f'  no candidate pending (not part of this test): {no_cand}')
        print(f'  -> CONFIRM {len(C)}   VANISH {len(V)}'
              + (f'   ({100*len(C)/len(rows):.0f}% confirm)' if rows else ''))

        if V:
            a = agg([r['ret'] for r in V]); d = agg([r['dd'] for r in V])
            w = sum(1 for r in V if r['ret'] > 0)
            print(f'\n  VANISH leg -- complete trades, entry to the breaking 2D close:')
            print(f'    n={a["n"]}  profitable {w}/{a["n"]} ({100*w/a["n"]:.0f}%)')
            print(f'    return   mean {a["mean"]:+.2f}%   median {a["med"]:+.2f}%   '
                  f'worst {a["worst"]:+.2f}%   best {a["best"]:+.2f}%')
            print(f'    drawdown mean {d["mean"]:+.2f}%   median {d["med"]:+.2f}%   worst {d["worst"]:+.2f}%')
            hold = [(r['exit_date'] - r['entry_date']).days for r in V]
            print(f'    days held: median {st.median(hold):.0f}')

        if C:
            print(f'\n  CONFIRM leg -- entry quality only, no exit (n={len(C)}):')
            for H in (30, 60):
                r = agg([x[f'r{H}'] for x in C]); u = agg([x[f'up{H}'] for x in C]); dd = agg([x[f'dd{H}'] for x in C])
                if not r: continue
                w = sum(1 for x in C if x[f'r{H}'] is not None and x[f'r{H}'] > 0)
                print(f'    {H}d  n={r["n"]}  up {w}/{r["n"]} ({100*w/r["n"]:.0f}%)'
                      f'   return mean {r["mean"]:+.2f}% median {r["med"]:+.2f}%'
                      f'   best upside mean {u["mean"]:+.2f}% median {u["med"]:+.2f}%'
                      f'   worst DD mean {dd["mean"]:+.2f}% median {dd["med"]:+.2f}%')

        strict = [r for r in rows if r['cand_bk'] == 'A' and r['cand_prime']]
        print(f'\n  Subset where the 2D candidate is A AND prime (today\'s setup): n={len(strict)}')
        if strict:
            sc = sum(1 for r in strict if r['verdict'] == 'CONFIRM')
            print(f'    CONFIRM {sc}/{len(strict)}')
