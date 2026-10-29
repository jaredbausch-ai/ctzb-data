"""Independent check of every trade card (28 Oct 2026, "the odds on the cards must be
airtight"). Runs in the Action after stack_live.py.

datasets/cards.csv is built by stack_live.py. datasets/ledger.csv is built separately by
grade_live.py, one row per graded signal. This script re-derives each card's sample
from the ledger alone, using the rule written on the card (exactly the same
confirmations / this chart at the same grade / the same grade across the asset's
charts), recomputes every percentage and median, and fails the run if any figure
differs. 8D cards are skipped: 8D signals are not in the graded ledger.
  python3 -I verify_cards.py
"""
import csv, os, sys, statistics as st, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'datasets')
LIQ = -25.3
PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}


def main():
    cards = list(csv.DictReader(open(os.path.join(OUT, 'cards.csv'))))
    led = list(csv.DictReader(open(os.path.join(OUT, 'ledger.csv'))))
    bad, checked = [], 0
    for c in cards:
        if c['tf'] == '8D':
            continue
        lenses = set() if c['lenses'] == 'none' else {PLAIN[x] for x in c['lenses'].split('; ')}
        b = c['basis']
        if 'exactly the same confirmations' in b and not b.split(' trades ')[1].startswith('graded'):
            G = [r for r in led if r['chart'] == c['chart'] and set(x for x in r['lenses'].split(' + ') if x != '-') == lenses]
        elif f"{c['chart']} trades graded" in b:
            G = [r for r in led if r['chart'] == c['chart'] and r['grade'] == c['grade']]
        else:
            G = [r for r in led if r['asset'] == c['asset'] and r['grade'] == c['grade']]
        n = len(G)
        def pct(f): return round(100 * sum(1 for r in G if f(r)) / n) if n else ''
        mine = {'n': n,
                'surv10': pct(lambda r: r['surv10'] == 'yes'),   # exact values; the ledger's dips are rounded to 0.1
                'reach20': pct(lambda r: r['reached20'] == 'yes'),
                'touched30': pct(lambda r: r['touched30'] == 'yes'),
                'bestMove': round(st.median(float(r['bestMove']) for r in G), 1) if n else '',
                'maxDip60': round(st.median(float(r['maxDrawdown']) for r in G), 1) if n else ''}
        for k, v in mine.items():
            cv = c[k]
            cv = int(cv) if k in ('n', 'surv10', 'reach20', 'touched30') and cv != '' else (float(cv) if cv != '' else '')
            tol = 1 if k in ('surv10', 'reach20', 'touched30') else 0.15 if k in ('bestMove', 'maxDip60') else 0
            if cv == '' or v == '' or abs(cv - v) > tol:
                bad.append(f"{c['chart']} {k}: card {c[k]} vs ledger {v}")
        checked += 1
    # the ledger's surv10 column must agree with its own rounded figures except at the -25.3 line
    for r in led:
        exact = r['surv10'] == 'yes'; rounded = float(r['bestMove']) >= 10 and float(r['maxDrawdown']) > LIQ
        if exact != rounded and abs(float(r['maxDrawdown']) - LIQ) > 0.05 and abs(float(r['bestMove']) - 10) > 0.05:
            bad.append(f"ledger {r['chart']} {r['entry']}: surv10 column disagrees with its own figures")
    status = os.path.join(OUT, 'stack_status.txt')
    if bad:
        open(status, 'a').write(f'{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC FAILED card cross-check: ' + '; '.join(bad) + '\n')
        raise SystemExit('CARD CROSS-CHECK FAILURE:\n  ' + '\n  '.join(bad))
    open(status, 'a').write(f'{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC OK card cross-check, {checked} cards match the ledger\n')
    print(f'verify_cards: {checked} cards match the ledger')


if __name__ == '__main__':
    main()
