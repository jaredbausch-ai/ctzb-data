"""How long do runs of consecutive losing signals last?

Jared's question, 9 Nov 2026, declared before running.

NOT a filter. CONTEXT already records that predicting which signals fail is an
open problem that killed Hurst, the FLD and the 160D window. This asks only:
given that a run is under way, how long do they go?

DEFINITION  Signals pooled across all graded charts in confirmation-date order,
            regime gate on -- the order Jared actually experiences them.
            A LOSER is a signal that did not reach +20% within 60 days (the
            repo's standard). The alternative read, negative at day 60, is
            reported alongside.
            A RUN is a maximal span of consecutive losers.

THE TAUTOLOGY GUARD. A run is DEFINED as ending at the first winner, so "the
signal after a run of N was a winner" is true by construction and is NOT
measured here. The honest question is the HAZARD RATE: having already reached
length N, how often did the run go on to N+1? That is not circular, because
both outcomes are possible at every N.

Only runs whose next signal has a settled 60-day window are counted, so an
unfinished run at the end of the data cannot be mistaken for a completed one.
"""
import csv, os, statistics as st, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LED = os.path.join(ROOT, 'datasets', 'ledger.csv')


def load(key):
    rows = list(csv.DictReader(open(LED)))
    rows.sort(key=lambda x: (x['entry'], x['chart']))
    out = []
    for x in rows:
        if key == 'reach20':
            if x['reached20'] not in ('yes', 'no'):
                continue
            out.append((x['entry'], x['chart'], x['reached20'] == 'yes'))
        else:
            try:
                out.append((x['entry'], x['chart'], float(x['return60d']) > 0))
            except (ValueError, TypeError):
                continue
    return out


def runs_of_losers(seq):
    """Maximal spans of consecutive losers. Only CLOSED runs (a winner after)."""
    out, cur = [], []
    for d, ch, win in seq:
        if win:
            if cur:
                out.append(cur); cur = []
        else:
            cur.append((d, ch))
    return out, cur  # closed runs, plus the unfinished tail


def report(key, label):
    seq = load(key)
    closed, tail = runs_of_losers(seq)
    L = [len(r) for r in closed]
    print(f'\n===== {label} =====')
    print(f'signals: {len(seq)}   closed runs of losers: {len(closed)}   '
          f'losers in all: {sum(L)}')
    if not L:
        return
    print(f'  run length: median {st.median(L):.0f}   mean {st.mean(L):.1f}   '
          f'max {max(L)}   p75 {sorted(L)[int(.75*len(L))]}   '
          f'p90 {sorted(L)[int(.90*len(L))]}')
    c = collections.Counter(L)
    print(f'\n  {"length":>7} {"runs":>5} {"share":>7} {"at least this long":>19}')
    tot = len(L)
    for n in sorted(c):
        atleast = sum(v for k, v in c.items() if k >= n)
        print(f'  {n:>7} {c[n]:>5} {100*c[n]/tot:>6.0f}% {100*atleast/tot:>18.0f}%')

    print(f'\n  HAZARD -- having reached length N, how often did it go on to N+1?')
    print(f'  (not the tautology: both outcomes are possible at every N)')
    print(f'  {"N":>4} {"runs that reached N":>20} {"went on":>9} {"rate":>7}')
    for n in range(1, max(L) + 1):
        reached = sum(1 for x in L if x >= n)
        went = sum(1 for x in L if x >= n + 1)
        if reached >= 5:
            print(f'  {n:>4} {reached:>20} {went:>9} {100*went/reached:>6.0f}%')

    if tail:
        print(f'\n  UNFINISHED run at the end of the settled data: {len(tail)} signals, '
              f'from {tail[0][0]} to {tail[-1][0]}')
        longer = sum(1 for x in L if x >= len(tail))
        print(f'    {longer} of {tot} historical runs ({100*longer/tot:.0f}%) reached this length or more')


if __name__ == '__main__':
    report('reach20', 'LOSER = did not reach +20% in 60 days (repo standard)')
    report('neg60', 'LOSER = negative at day 60')
