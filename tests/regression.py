#!/usr/bin/env python3
"""Regression guard: a past signal's grade and outcome must never change silently.

Item 17(c). Every pipeline run re-derives the whole ledger from the candles. A
bug in a lens, a grade rule or the engine shows up as a PAST row changing value
-- which no diff of the CSV catches, because the same run also appends new rows
and recomputes cohort aggregates.

This compares each signal in datasets/ledger.csv against a committed baseline,
keyed by (asset, chart, entry), and fails on any change to a row that should be
frozen. New signals are expected and ignored.

Three classes of column:

  ALWAYS    derived from the signal itself and the grade rules. Frozen from the
            moment the signal confirms. A change here is a lens or grade bug.
  SETTLED   the 60-day outcome. Still filling in while the window is open, so
            only checked once entry + 60 days has passed.
  SKIP      cohort aggregates (gradeReach20 and friends). They legitimately move
            as new signals land in the same grade. Not checked.

Usage:
    python tests/regression.py              check, exit 1 on drift
    python tests/regression.py --approve    re-baseline after an INTENDED change
    python tests/regression.py --quiet      only print on failure

Re-baselining is deliberate and reviewable: the baseline is committed, so an
approved change shows up as a diff in the pull request.
"""
import argparse, csv, datetime as dt, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(ROOT, 'datasets', 'ledger.csv')
BASE = os.path.join(HERE, 'baseline', 'ledger.json')
WINDOW = 60

KEY = ('asset', 'chart', 'entry')
ALWAYS = ('low', 'entryPrice', 'tags', 'grade', 'lenses', 'year')
SETTLED = ('reached20', 'touched30', 'bestMove', 'maxDrawdown', 'dipBeforeHigh',
           'return60d', 'daysToHigh', 'reached10', 'reached15', 'surv10', 'scaled20',
           'dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN',
           'daySurv10', 'dayScaled20')
SKIP = ('gradeReach20', 'gradeTouched30', 'gradeMedDrawdown')


def read_ledger(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        out['|'.join(r[k] for k in KEY)] = r
    if len(out) != len(rows):
        sys.exit(f'FAIL  {len(rows) - len(out)} duplicate keys in ledger.csv; '
                 f'{KEY} is not unique')
    return out


def settled(entry, today):
    try:
        d = dt.date.fromisoformat(entry)
    except ValueError:
        return False
    return (today - d).days > WINDOW


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--approve', action='store_true',
                    help='re-baseline; only after an intended change')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    if not os.path.exists(LEDGER):
        sys.exit(f'FAIL  {LEDGER} missing -- did refresh.py run?')
    cur = read_ledger(LEDGER)

    if a.approve or not os.path.exists(BASE):
        os.makedirs(os.path.dirname(BASE), exist_ok=True)
        keep = ALWAYS + SETTLED
        snap = {k: {c: v[c] for c in keep if c in v} for k, v in cur.items()}
        with open(BASE, 'w') as f:
            json.dump({'window': WINDOW, 'n': len(snap), 'rows': snap}, f,
                      indent=0, sort_keys=True)
        print(f'baselined {len(snap)} signals -> {os.path.relpath(BASE, ROOT)}')
        return 0

    with open(BASE) as f:
        base = json.load(f)['rows']

    today = dt.date.today()
    drift, gone = [], []
    for k, old in base.items():
        new = cur.get(k)
        if new is None:
            gone.append(k)
            continue
        is_settled = settled(k.split('|')[2], today)
        for col, was in old.items():
            if col in SKIP:
                continue
            if col in SETTLED and not is_settled:
                continue
            now = new.get(col, '')
            if now != was:
                drift.append((k, col, was, now))

    added = len(cur) - len(base) + len(gone)
    if not drift and not gone:
        if not a.quiet:
            print(f'PASS  {len(base)} baselined signals unchanged, {added} new')
        return 0

    print(f'FAIL  regression in datasets/ledger.csv')
    if gone:
        print(f'\n  {len(gone)} baselined signal(s) VANISHED:')
        for k in gone[:20]:
            print(f'    {k}')
    if drift:
        print(f'\n  {len(drift)} value change(s) on frozen rows:')
        print(f'    {"signal":42} {"column":16} {"was":>12} {"now":>12}')
        for k, col, was, now in drift[:40]:
            print(f'    {k:42} {col:16} {was:>12} {now:>12}')
        if len(drift) > 40:
            print(f'    ... and {len(drift) - 40} more')
    print('\n  A past grade or outcome moved. Either a lens/grade/engine bug, or an')
    print('  intended change -- if intended, run with --approve and commit the')
    print('  baseline so the change is reviewable in the diff.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
