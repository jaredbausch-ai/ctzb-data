"""Independent check of every card against the signal ledger (28 Oct 2026, "the odds on the cards must be
airtight"). Runs in the Action after stack_live.py.

datasets/cards.csv is built by stack_live.py. datasets/ledger.csv is built separately by
grade_live.py, one row per graded signal. This script re-derives each card's sample
from the ledger alone, using the rule written on the card (exactly the same
confirmations / this chart at the same grade / the same grade across the asset's
charts), recomputes every figure on the card and fails the run if any differs, exactly: n, the
big number (rose 10%), surv10, scaled20, +20%, -30%, the rounded and exact medians, the eras,
the timing medians, and the from-entry row and every falls-first ladder row (shown and exact
shares) from the 1D candles. There are no 8D cards since 12 Nov 2026 (audit #14: stack_live only
builds cards on graded charts); the 8D skip below is a guard, and it fails the run if one appears.
(Extended 12 Nov 2026, audit #8: it used to check 10 of these.)
  python3 -I verify_cards.py
"""
import csv, os, sys, statistics as st, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clock import now_utc  # noqa: E402
from rounding import rnd as round  # noqa: E402,A001 -- one rounding rule (audit 12 Nov 2026)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'datasets')
LIQ = -25.3
PLAIN = {'CT well above its Signal line': 'GAP', 'a higher low than the last signal': 'HIGH', 'other charts already confirmed': 'AGREE',
         'a BTC 3D signal in the 10 days before': 'BTC3', 'an ETH 2D signal in the 10 days before': 'BTCX',
         'funding at or above its 90-day median': 'FUND', 'funding not cooling': 'FCOOL', 'the 8D chart rising': 'UP8',
         'CT recovering fast from the low': 'FASTCT'}


_DAY = {}


def day_path(a, d0, entry, H=60):
    """Independent of stack_live: read the 1D csv directly and return (days to +10%, days to +20%,
    day of the 60-day high, day of the 60-day low) for one entry."""
    if a not in _DAY:
        rows = list(csv.DictReader(open(os.path.join(HERE, 'data', f'{a}_1D.csv'))))
        # the repo's documented flash-print rule (engine._declamp / refresh._declean, CONTEXT): a low
        # under half the bar's body, or a high over twice it, is pulled back to the body. Written out
        # here, not imported, so this check stays independent of the engine.
        def fix(r):
            o, h, l, c = (float(r[k]) for k in ('open', 'high', 'low', 'close'))
            lb, hb = min(o, c), max(o, c)
            return (l if not (lb > 0 and l < 0.5 * lb) else lb), (h if not (hb > 0 and h > hb / 0.5) else hb)
        _DAY[a] = [(dt.datetime.fromtimestamp(int(r['time']), dt.timezone.utc).date(),) + tuple(reversed(fix(r))) for r in rows]
    D = _DAY[a]; end = d0 + dt.timedelta(days=H)
    w = [x for x in D if d0 < x[0] <= end]
    if not w: return None
    first = lambda p: next(((x[0] - d0).days for x in w if x[1] >= entry * (1 + p / 100)), None)
    hi = max(w, key=lambda x: x[1]); lo = min(w, key=lambda x: x[2])
    return first(10), first(20), (hi[0] - d0).days, (lo[0] - d0).days


def window(a, d0, H=60):
    """(high, low) of each closed daily bar in the 60 calendar days after d0, flash prints clamped."""
    day_path(a, d0, 1.0)
    end = d0 + dt.timedelta(days=H)
    return [(x[1], x[2]) for x in _DAY[a] if d0 < x[0] <= end]


def ladder(G):
    """From-entry and falls-first rows, written out independently of stack_live: within a day the
    low is checked before the high; rose 10% = high >= entry x 1.10; fell 25.3% = low <= entry x 0.747."""
    out = {}
    W = [(window(r['asset'], dt.date.fromisoformat(r['entry'])), float(r['entryPrice'])) for r in G]
    n = ok = liq = 0
    for w, e in W:
        n += 1
        for h, l in w:
            if l <= e * (1 + LIQ / 100): liq += 1; break
            if h >= e * 1.10: ok += 1; break
    out.update(l0ok=round(100 * ok / n) if n else '', l0liq=round(100 * liq / n) if n else '',
               l0okExact=round(100 * ok / n, 6) if n else '')
    for th in (5, 10, 15, 20):
        hit = ok = liq = 0
        for w, e in W:
            for j, (h, l) in enumerate(w):
                if l <= e * (1 - th / 100):
                    hit += 1
                    for hh, ll in w[j:]:
                        if ll <= e * (1 + LIQ / 100): liq += 1; break
                        if hh >= e * 1.10: ok += 1; break
                    break
                if h >= e * 1.10: break
        out[f'l{th}n'] = hit
        out[f'l{th}ok'] = round(100 * ok / hit) if hit else ''
        out[f'l{th}liq'] = round(100 * liq / hit) if hit else ''
        out[f'l{th}okExact'] = round(100 * ok / hit, 6) if hit else ''
    return out


def main():
    cards = list(csv.DictReader(open(os.path.join(OUT, 'cards.csv'))))
    # 12 Nov 2026: the member site's worked example is a card too, built only from signals
    # whose 60th day had closed by its confirmation date (2024-09-22)
    op_path = os.path.join(OUT, 'cards_open.csv')
    cards += list(csv.DictReader(open(op_path))) if os.path.exists(op_path) else []
    ex_path = os.path.join(OUT, 'cards_example.csv')
    for c in (list(csv.DictReader(open(ex_path))) if os.path.exists(ex_path) else []):
        c['_known_by'] = dt.date.fromisoformat(c['confirms'])
        cards.append(c)
    led = list(csv.DictReader(open(os.path.join(OUT, 'ledger.csv'))))
    bad, checked = [], 0
    for c in cards:
        if c['tf'] == '8D':
            bad.append(f"{c['chart']}: an 8D card exists; 8D is not graded and cannot be re-derived")
            continue
        lenses = set() if c['lenses'] == 'none' else {PLAIN[x] for x in c['lenses'].split('; ')}
        b = c['basis']
        L = led if '_known_by' not in c else [r for r in led if dt.date.fromisoformat(r['entry']) + dt.timedelta(days=60) <= c['_known_by']]
        if 'exactly the same confirmations' in b and not b.split(' signals ')[1].startswith(('graded', 'of ')):
            G = [r for r in L if r['chart'] == c['chart'] and set(x for x in r['lenses'].split(' + ') if x != '-') == lenses]
        elif f"{c['chart']} signals graded" in b or f"{c['chart']} signals of " in b:
            G = [r for r in L if r['chart'] == c['chart'] and r['grade'] == c['grade']]
        else:
            G = [r for r in L if r['asset'] == c['asset'] and r['grade'] == c['grade']]
        n = len(G)
        def pct(f): return round(100 * sum(1 for r in G if f(r)) / n) if n else ''
        mine = {'n': n,
                'surv10': pct(lambda r: r['surv10'] == 'yes'),   # the ledger's yes/no, decided on exact prices
                'reach20': pct(lambda r: r['reached20'] == 'yes'),
                'touched30': pct(lambda r: r['touched30'] == 'yes'),
                'bestMove': round(st.median(float(r['bestMove']) for r in G), 1) if n else '',
                'maxDip60': round(st.median(float(r['maxDrawdown']) for r in G), 1) if n else '',
                'reach10': pct(lambda r: r['reached10'] == 'yes'),
                'dipBeforeHigh': round(st.median(float(r['dipBeforeHigh']) for r in G), 1) if n else '',
                'bestMoveExact': round(st.median(float(r['bestMove']) for r in G), 6) if n else '',
                'dipBeforeHighExact': round(st.median(float(r['dipBeforeHigh']) for r in G), 6) if n else '',
                'maxDip60Exact': round(st.median(float(r['maxDrawdown']) for r in G), 6) if n else ''}
        sc = [r['scaled20'] == 'yes' for r in G if r['scaled20'] in ('yes', 'no')]
        mine['scaled20'] = round(100 * sum(sc) / len(sc)) if sc else ''
        old = [r for r in G if r['entry'] < '2022-01-01']; new = [r for r in G if r['entry'] >= '2022-01-01']
        sv = lambda X: round(100 * sum(r['surv10'] == 'yes' for r in X) / len(X)) if X else ''
        mine.update(nOld=len(old), surv10Old=sv(old), nNew=len(new), surv10New=sv(new))
        mine.update(ladder(G))
        paths = [p for p in (day_path(r['asset'], dt.date.fromisoformat(r['entry']), float(r['entryPrice'])) for r in G) if p]
        mm = lambda xs: round(st.median(xs)) if xs else ''
        timing = {'daysTo10': mm([p[0] for p in paths if p[0] is not None]), 'daysTo20': mm([p[1] for p in paths if p[1] is not None]),
                  'daysToHigh': mm([p[2] for p in paths]), 'daysToLow': mm([p[3] for p in paths])}
        for k, v in timing.items():
            cv = c.get(k, '')
            if (cv == '') != (v == '') or (cv != '' and abs(float(cv) - v) > 0):   # exact since 12 Nov 2026
                bad.append(f"{c['chart']} {k}: card {cv} vs 1D data {v}")
        for k, v in mine.items():
            cv = c.get(k, '')
            cv = float(cv) if cv != '' else ''
            # 12 Nov 2026: exact (0) for every shown figure. The three *Exact medians are the card's
            # full-precision medians to 6 places; the ledger stores each measure to 6 places, so from the
            # ledger they can only be confirmed to within one unit in the 6th place.
            tol = 1e-6 + 1e-12 if k.endswith('Exact') and k[:2] != 'l0' and not k.startswith(('l5', 'l10', 'l15', 'l20')) else 0
            if (cv == '') != (v == '') or (cv != '' and abs(cv - v) > tol):
                bad.append(f"{c['chart']} {k}: card {c[k]} vs ledger {v}")
        checked += 1
    # the ledger's surv10 column must agree with its own rounded figures except at the -25.3 line
    for r in led:
        exact = r['surv10'] == 'yes'; rounded = float(r['bestMove']) >= 10 and float(r['maxDrawdown']) > LIQ
        if exact != rounded and abs(float(r['maxDrawdown']) - LIQ) > 0.05 and abs(float(r['bestMove']) - 10) > 0.05:
            bad.append(f"ledger {r['chart']} {r['entry']}: surv10 column disagrees with its own figures")
    # every live (open) signal must have its own card: without it the feed would carry a live signal with no
    # card (12 Nov 2026 audit #19; that happened only if cards_open.csv was missing while open.csv existed)
    open_path = os.path.join(OUT, 'open.csv')
    have = {(c['chart'], c['confirms']) for c in cards}
    for o in (list(csv.DictReader(open(open_path))) if os.path.exists(open_path) else []):
        if (o['chart'], o['entry']) not in have:
            bad.append(f"{o['chart']} {o['entry']}: live signal has no card in cards_open.csv")
    status = os.path.join(OUT, 'stack_status.txt')
    if bad:
        open(status, 'a').write(f'{now_utc():%Y-%m-%d %H:%M} UTC FAILED card cross-check: ' + '; '.join(bad) + '\n')
        raise SystemExit('CARD CROSS-CHECK FAILURE:\n  ' + '\n  '.join(bad))
    open(status, 'a').write(f'{now_utc():%Y-%m-%d %H:%M} UTC OK card cross-check, {checked} cards match the ledger\n')
    print(f'verify_cards: {checked} cards match the ledger')


if __name__ == '__main__':
    import seal
    _OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datasets')
    seal.check(_OUT, 'cards')   # the steps before this one finished and their files are untouched (seal.py)
    main()
    seal.done(_OUT, 'cards')
