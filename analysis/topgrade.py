"""Top grade at 70%: does the card's own number pick the better signals? DECLARED 27 Nov 2026 14:05 ET, before running.

Jared, 27 Nov 2026: drop the letter grades on the client side. One label, "top grade" or "not top grade", at the
70% bar, with the card's own percentage beside it. Claude's pick (Jared to confirm after this check): the figure is
the card's from-entry share, "rose 10% before ever falling 25.3%" (low checked first within a day), the same figure
the edge-gone status already reads, so a card can never be top grade and have its edge gone from day one.

WALK-FORWARD. Each test signal gets the card it would have had on its confirmation date: its sample is built exactly
as stack_live.py builds a live card (exactly the same confirmations if 15+, else this chart at the same grade if
15+, else the same grade across the asset's 1D, 2D, 3D and 5D charts; ETH pools only signals with funding reads),
from signals of that asset whose 60 days had closed by that date (as the worked example). Nothing later is used.

DATA     every regime-gated signal in stack_live's rows (R.rsi_regime BTC 2D 8/13/60/41) on 1D, 2D, 3D, 5D, ETH and
         BTC, whose own 60 days have closed. Entry = the confirmation close.
TEST     signals confirmed 2019-01-01 or later (earlier ones only build samples). Split by year 2019 to 2026, by asset
         and by chart. ETH and BTC are one sample for anything date-anchored: the years are read pooled first.
OUTCOME  rose 10% before ever falling 25.3% within 60 calendar days of entry (the card's own definition), daily
         candles, low checked first. Also shown: reached +10% at any time; fell 25.3% first.

CANDIDATES (declared now; no others will be run)
  T1  card's from-entry share >= 70% (exact share)                          <- the pick
  T2  T1 and the card's sample has at least 15 signals
  T3  card's headline share (high reached +10% within 60 days) >= 70%
  T4  grade A+ (the current top grade: 4+ of the asset's lenses)

PASS RULE (set now, for T1)
  T1 becomes the top-grade rule if, over all test signals pooled:
    (a) its top-grade signals' outcome share is at least 70%, and
    (b) it beats the not-top-grade signals by at least 10 points, and
    (c) it beats them on each asset separately, and
    (d) it beats them in at least 5 of the test years in which it has 5 or more top-grade signals.
  T2 replaces T1 only if T1 fails and T2 passes. T3 and T4 are reported for comparison only.
  Collinearity: the overlap of T1 with A+ is reported (how much of T1 is just A+ again).

Entry quality only. Computed signals, not fills; no exit is in the data, so none of this is a strategy return.
  python3 -I analysis/topgrade.py      -> analysis/RESULTS_topgrade.md
"""
import os, sys, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
os.chdir(ROOT)
import stack_live as SL
import measures as MS

BAR, MINN, START = 70.0, 15, dt.date(2019, 1, 1)
TFS = ('1D', '2D', '3D', '5D')


def lenses():
    # the asset's lens list, built as stack_live.py builds it after its analysis hook (lines 535-541)
    import json
    j = lambda f: json.load(open(os.path.join(ROOT, 'analysis', f)))
    LENS = j('grade.json')['lenses']
    for k, v in j('grade2.json').items(): LENS[k] = LENS[k] + [x for x in v if x != 'DIVH']
    for k, v in j('grade3.json')['counted'].items(): LENS[k] = LENS[k] + v
    for k, v in j('grade6.json')['added'].items(): LENS[k] = LENS[k] + v
    return LENS


def main():
    SL._HOOK = lambda loc: loc
    L = SL.main()
    rows, feats, DAY, DPOS, today = L['rows'], L['feats'], L['DAY'], L['DPOS'], L['today']
    LENS = lenses()
    gof = lambda c: 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'

    def path(s):
        a = s['a']; i0 = DPOS[a].get(s['d0'])
        if i0 is None: return None
        D = DAY[a]['date']; H, Lo = [], []
        for k in range(i0 + 1, len(D)):
            if (D[k] - s['d0']).days > 60: break
            H.append(DAY[a]['high'][k]); Lo.append(DAY[a]['low'][k])
        return H, Lo

    OUT = {}
    def outcome(s):
        key = (s['a'], s['tf'], s['d0'])
        if key in OUT: return OUT[key]
        p = path(s)
        if p is None: OUT[key] = None; return None
        e = s['entry']; first = None
        for h, l in zip(*p):
            if l <= e * (1 + MS.LIQ / 100): first = 'fell'; break
            if h >= e * 1.10: first = 'rose'; break
        OUT[key] = {'rose_first': first == 'rose', 'fell_first': first == 'fell', 'reach10': max(p[0], default=0) >= e * 1.10}
        return OUT[key]

    done = [s for s in rows if s['tf'] in TFS and s['d0'] + dt.timedelta(days=60) < today and outcome(s) is not None]
    sets = {}
    def S(s):
        k = id(s)
        if k not in sets: sets[k] = frozenset(x for x in LENS[s['a']] if feats(s).get(x))
        return sets[k]

    tests = []
    for s in done:
        if s['d0'] < START: continue
        a, tf = s['a'], s['tf']
        known = [x for x in done if x['a'] == a and x['d0'] + dt.timedelta(days=60) <= s['d0']]
        have = S(s); g = gof(len(have))
        Cf = [x for x in known if x['tf'] == tf and (a != 'ETH' or (x.get('fund') is not None and x.get('fcool') is not None))]
        ex = [x for x in Cf if S(x) == have]
        sg = [x for x in Cf if gof(len(S(x))) == g]
        ag = [x for x in known if (a != 'ETH' or (x.get('fund') is not None and x.get('fcool') is not None)) and gof(len(S(x))) == g]
        G = ex if len(ex) >= 15 else sg if len(sg) >= 15 else ag
        if not G: continue
        o = [outcome(x) for x in G]
        pf = 100 * sum(x['rose_first'] for x in o) / len(o)
        ph = 100 * sum(x['reach10'] for x in o) / len(o)
        tests.append(dict(a=a, tf=tf, d0=s['d0'], y=s['d0'].year, g=g, n=len(G), pf=pf, ph=ph, **outcome(s)))

    cand = {'T1': lambda t: t['pf'] >= BAR, 'T2': lambda t: t['pf'] >= BAR and t['n'] >= MINN,
            'T3': lambda t: t['ph'] >= BAR, 'T4': lambda t: t['g'] == 'A+'}
    share = lambda xs, k='rose_first': (100 * sum(x[k] for x in xs) / len(xs)) if xs else None
    f = lambda v: '–' if v is None else f'{v:.0f}%'
    md = ['# Top grade at 70%: walk-forward check (27 Nov 2026)', '',
          'Declared before running: `analysis/topgrade.py` (candidates T1 to T4 and the pass rule are in its header).',
          'Each test signal is judged by the card it would have had on its confirmation date, built only from signals',
          'whose 60 days had closed by then. Outcome: rose 10% before ever falling 25.3% within 60 days of entry.', '',
          '**Entry quality only.** Computed signals, not fills. The data has no exits, so this is not a strategy return or a track record.', '',
          f'Test signals: {len(tests)} (ETH and BTC, 1D to 5D, confirmed 2019-01-01 to {max(t["d0"] for t in tests)}, 60 days closed).', '',
          '## All candidates, pooled', '',
          '| Rule | Top grade: signals | Rose 10% before falling 25.3% | Reached +10% | Fell 25.3% first | Not top grade: signals | Rose 10% before falling 25.3% | Gap (points) |',
          '|---|---|---|---|---|---|---|---|']
    names = {'T1': 'T1 from-entry share ≥ 70%', 'T2': 'T2 T1 with 15+ in the sample', 'T3': 'T3 headline share ≥ 70%', 'T4': 'T4 grade A+ (today)'}
    verdict = {}
    for c, fn in cand.items():
        top = [t for t in tests if fn(t)]; rest = [t for t in tests if not fn(t)]
        gap = (share(top) - share(rest)) if top and rest else None
        md.append(f'| {names[c]} | {len(top)} | {f(share(top))} | {f(share(top, "reach10"))} | {f(share(top, "fell_first"))} | {len(rest)} | {f(share(rest))} | {"–" if gap is None else f"{gap:+.0f}"} |')
        verdict[c] = (top, rest, gap)

    for c in ('T1', 'T2'):
        top, rest, gap = verdict[c]
        md += ['', f'## {names[c]}: split', '', '| Split | Top grade: signals | Rose 10% before falling 25.3% | Not top grade: signals | Rose 10% before falling 25.3% |', '|---|---|---|---|---|']
        for lab, key in (('Asset', 'a'), ('Chart', None), ('Year', 'y')):
            vals = sorted({(t['a'] + ' ' + t['tf']) if key is None else t[key] for t in tests})
            for v in vals:
                sel = (lambda t, v=v: t['a'] + ' ' + t['tf'] == v) if key is None else (lambda t, v=v, key=key: t[key] == v)
                tt = [t for t in top if sel(t)]; rr = [t for t in rest if sel(t)]
                md.append(f'| {lab} {v} | {len(tt)} | {f(share(tt))} | {len(rr)} | {f(share(rr))} |')

    def passes(c):
        top, rest, gap = verdict[c]
        if not top or not rest: return False, 'no split'
        a_ = share(top) >= BAR; b_ = gap >= 10
        c_ = all(share([t for t in top if t['a'] == x]) is not None and share([t for t in rest if t['a'] == x]) is not None
                 and share([t for t in top if t['a'] == x]) > share([t for t in rest if t['a'] == x]) for x in ('ETH', 'BTC'))
        yrs = [y for y in sorted({t['y'] for t in tests}) if len([t for t in top if t['y'] == y]) >= 5]
        wins = [y for y in yrs if [t for t in rest if t['y'] == y] and share([t for t in top if t['y'] == y]) > share([t for t in rest if t['y'] == y])]
        d_ = len(wins) >= 5
        return a_ and b_ and c_ and d_, f'(a) {f(share(top))} ≥ 70%: {a_}; (b) gap {gap:+.0f} ≥ 10: {b_}; (c) both assets: {c_}; (d) beats in {len(wins)} of {len(yrs)} years with 5+: {d_}'

    ov = [t for t in verdict['T1'][0] if t['g'] == 'A+']
    md += ['', '## Pass rule', '']
    for c in ('T1', 'T2'):
        ok, why = passes(c); md.append(f'- **{c}: {"PASSES" if ok else "fails"}.** {why}')
    md += [f'- Overlap: {len(ov)} of the {len(verdict["T1"][0])} T1 top-grade signals are also A+; '
           f'{len([t for t in tests if t["g"] == "A+"])} test signals are A+ in all.', '']
    open(os.path.join(HERE, 'RESULTS_topgrade.md'), 'w').write('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
