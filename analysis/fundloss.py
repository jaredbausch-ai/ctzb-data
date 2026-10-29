"""What does the ETH grade lose without its two funding confirmations? (29 Oct 2026)

Jared, before rewriting the TradingView scripts: "What will we lose with the funding?
Will our odds be inaccurate?" TradingView cannot read the 12-exchange funding the
grade uses, so the scripts could grade ETH on its four price confirmations only.

DECLARED before running. Two versions of the ETH grade, same count rule
(0-1 = C, 2 = B, 3 = A, 4+ = A+):
  FULL   GAP, HIGH, AGREE, BTC3, FUND, FCOOL   (the live grade)
  PRICE  GAP, HIGH, AGREE, BTC3
Sample: every regime-gated ETH 1D/2D/3D/5D signal with funding data (2020 on), the
sample the live grade is measured on. Also PRICE on the full ETH history (2016 on),
which it can use because it needs no funding.
Measure: the card's headline, rose 10% and never fell 25.3% within 60 days (surv10);
also rose 20%.
Reported:
  1 each grade's rate and count, both versions
  2 how often the two versions give a different letter, and which way
  3 odds as quoted on the day (walk-forward, no hindsight: the grade's rate over
    signals whose 60 days had finished before this entry, 10+ needed): average
    quote vs actual by grade, Brier score, AUC; whole sample and since 2022
  4 split by chart and by year: does FULL beat PRICE (Brier) in each
Nothing is adopted from this run; it answers the question.
  python3 -I analysis/fundloss.py
"""
import os, sys, json, datetime as dt
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'analysis'))
os.chdir(HERE)
import measures as MS
import stack_live as SL

FULL = ['GAP', 'HIGH', 'AGREE', 'BTC3', 'FUND', 'FCOOL']
PRICE = ['GAP', 'HIGH', 'AGREE', 'BTC3']
ORDER = ['C', 'B', 'A', 'A+']
gof = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'


def auc(p, y):
    pos = [a for a, b in zip(p, y) if b]; neg = [a for a, b in zip(p, y) if not b]
    if not pos or not neg: return float('nan')
    s = sum((1 if a > b else 0.5 if a == b else 0) for a in pos for b in neg)
    return s / (len(pos) * len(neg))


def main():
    cap = {}
    SL._HOOK = lambda L: cap.update(L) or L
    SL.main()
    rows, feats = cap['rows'], cap['feats']
    S = [r for r in rows if r['a'] == 'ETH' and r['tf'] in ('1D', '2D', '3D', '5D')]
    for r in S:
        f = feats(r)
        r['_full'] = gof(sum(bool(f.get(k)) for k in FULL)) if r.get('fund') is not None and r.get('fcool') is not None else None
        r['_price'] = gof(sum(bool(f.get(k)) for k in PRICE))
        r['_y'] = MS.surv10(r['m']); r['_y20'] = r['m']['up'] >= 20
    F = sorted([r for r in S if r['_full']], key=lambda r: r['d0'])
    P16 = sorted(S, key=lambda r: r['d0'])
    out = []
    pr = lambda *a: out.append(' '.join(str(x) for x in a))

    pr('# What the ETH grade loses without funding (analysis/fundloss.py, run', dt.date.today(), ')')
    pr('Sample: regime-gated ETH 1D/2D/3D/5D signals with a finished 60 days.',
       f'With funding data (2020 on): {len(F)}. Full history (2016 on): {len(P16)}.')
    pr('Measure: rose 10% and never fell 25.3% within 60 days (the card headline); rose 20% alongside.\n')

    def table(G, key, title):
        pr(f'## {title}\n')
        pr('| Grade | n | Rose 10%, never fell 25% | Rose 20% |'); pr('|---|---|---|---|')
        for g in ORDER:
            X = [r for r in G if r[key] == g]
            if X: pr(f'| {g} | {len(X)} | {round(100 * sum(r["_y"] for r in X) / len(X))}% | {round(100 * sum(r["_y20"] for r in X) / len(X))}% |')
        pr(f'| all | {len(G)} | {round(100 * sum(r["_y"] for r in G) / len(G))}% | {round(100 * sum(r["_y20"] for r in G) / len(G))}% |\n')
    table(F, '_full', '1. FULL grade (live), 2020 on')
    table(F, '_price', '1. PRICE-only grade, same signals (2020 on)')
    table(P16, '_price', '1. PRICE-only grade, full history (2016 on)')

    pr('## 2. Same signal, different letter (2020 on)\n')
    same = sum(r['_full'] == r['_price'] for r in F)
    up = sum(ORDER.index(r['_full']) > ORDER.index(r['_price']) for r in F)
    pr(f'Same letter {same} of {len(F)} ({round(100 * same / len(F))}%). FULL higher {up}, FULL lower {len(F) - same - up}.\n')
    pr('| PRICE grade | FULL C | FULL B | FULL A | FULL A+ |'); pr('|---|---|---|---|---|')
    for g in ORDER:
        pr(f'| {g} | ' + ' | '.join(str(sum(1 for r in F if r['_price'] == g and r['_full'] == h)) for h in ORDER) + ' |')
    pr('')

    def walk(G, key):
        q = []
        for r in G:
            past = [s for s in G if s[key] == r[key] and s['d0'] + dt.timedelta(days=61) <= r['d0']]
            q.append(100 * sum(s['_y'] for s in past) / len(past) if len(past) >= 10 else None)
        return q

    pr('## 3. Odds quoted on the day vs what happened (walk-forward, no hindsight)\n')
    res = {}
    for name, G, key in (('FULL, 2020 on', F, '_full'), ('PRICE, same signals', F, '_price'), ('PRICE, 2016 on', P16, '_price')):
        q = walk(G, key)
        Z = [(qq, r) for qq, r in zip(q, G) if qq is not None]
        res[name] = Z
    pr('| Version | Signals quoted | Avg quote | Actual | Brier (lower is better) | AUC (higher is better) |'); pr('|---|---|---|---|---|---|')
    for name, Z in res.items():
        for lab, ZZ in (('all', Z), ('since 2022', [z for z in Z if z[1]['d0'] >= dt.date(2022, 1, 1)])):
            if not ZZ: continue
            p = [z[0] / 100 for z in ZZ]; y = [1 if z[1]['_y'] else 0 for z in ZZ]
            br = sum((a - b) ** 2 for a, b in zip(p, y)) / len(p)
            pr(f'| {name}, {lab} | {len(ZZ)} | {round(100 * sum(p) / len(p))}% | {round(100 * sum(y) / len(y))}% | {br:.3f} | {auc(p, y):.2f} |')
    pr('')
    pr('Quoted vs actual by grade, on the signals both versions quoted (2020 on):\n')
    both = {id(r): qq for qq, r in res['FULL, 2020 on']}
    bothp = {id(r): qq for qq, r in res['PRICE, same signals']}
    common = [r for r in F if id(r) in both and id(r) in bothp]
    pr('| Grade | FULL n | FULL quote | FULL actual | PRICE n | PRICE quote | PRICE actual |'); pr('|---|---|---|---|---|---|---|')
    for g in ORDER:
        a = [r for r in common if r['_full'] == g]; b = [r for r in common if r['_price'] == g]
        fa = lambda X, D: (f'{round(sum(D[id(r)] for r in X) / len(X))}%', f'{round(100 * sum(r["_y"] for r in X) / len(X))}%') if X else ('-', '-')
        x1, y1 = fa(a, both); x2, y2 = fa(b, bothp)
        pr(f'| {g} | {len(a)} | {x1} | {y1} | {len(b)} | {x2} | {y2} |')
    pr('')

    pr('## 4. Split by chart and by year: Brier on the signals both versions quoted (lower is better)\n')
    def br(X, D):
        return sum((D[id(r)] / 100 - (1 if r['_y'] else 0)) ** 2 for r in X) / len(X)
    pr('| Split | n | FULL | PRICE | Better |'); pr('|---|---|---|---|---|')
    wins = [0, 0]
    for lab, X in [(f'ETH {tf}', [r for r in common if r['tf'] == tf]) for tf in ('1D', '2D', '3D', '5D')] + \
                  [(str(y), [r for r in common if r['d0'].year == y]) for y in sorted({r['d0'].year for r in common})]:
        if len(X) < 5: continue
        a, b = br(X, both), br(X, bothp)
        w = 'FULL' if a < b - 0.0005 else 'PRICE' if b < a - 0.0005 else 'tie'
        if w == 'FULL': wins[0] += 1
        if w == 'PRICE': wins[1] += 1
        pr(f'| {lab} | {len(X)} | {a:.3f} | {b:.3f} | {w} |')
    pr(f'\nFULL better in {wins[0]} splits, PRICE better in {wins[1]}.')
    pr('\nEntry quality only: computed signals, never fills; no exit in the data.')
    txt = '\n'.join(out) + '\n'
    open(os.path.join(HERE, 'analysis', 'RESULTS_fundloss.md'), 'w').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
