"""Build CT Zone Bounce v16 and CTZB Scanner v10 from the repo (29 Oct 2026).

Jared: "update both indicators to our most recent format so they parallel each
other." Both scripts are generated from ONE engine block (pine/engine_v10.pine.in)
and ONE data block written here, so they cannot drift apart, and the data block
comes from the same code path that writes datasets/cards.csv:

  * the regime: every flip of R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41),
    hard-coded up to the build date; after it the script runs the same state
    machine itself, starting from the built state
  * FASTCT cut points per BTC chart (2016-21, top third), as stack_live
  * the like-for-like card samples (docs/CARD_SPEC.md): for every chart, every
    set of confirmations that has occurred (its count, and its numbers when 15+),
    every chart x grade, every asset x grade

Before writing anything it re-derives every card in datasets/cards.csv from the
tables, the way the Pine lookup will, and refuses to build on any difference.

  python3 -I pine/build_v10.py
"""
import csv, json, os, sys, datetime as dt, statistics as st

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'analysis'))
os.chdir(HERE)
import engine as E
import regimes as R
import measures as MS
import stack_live as SL

PINE = os.path.join(HERE, 'pine')
TFS = ('1D', '2D', '3D', '5D', '8D')
GRADES = ('C', 'B', 'A', 'A+')


def lens_lists():
    L = json.load(open('analysis/grade.json'))['lenses']
    for k, v in json.load(open('analysis/grade2.json')).items(): L[k] = L[k] + [x for x in v if x != 'DIVH']
    for k, v in json.load(open('analysis/grade3.json'))['counted'].items(): L[k] = L[k] + v
    for k, v in json.load(open('analysis/grade6.json'))['added'].items(): L[k] = L[k] + v
    return L


def gof(c): return 'C' if c <= 1 else 'B' if c == 2 else 'A' if c == 3 else 'A+'


def main():
    cap = {}
    SL._HOOK = lambda L: cap.update(L) or L
    SL.main()
    rows, feats, DAY, DPOS, FCUT = cap['rows'], cap['feats'], cap['DAY'], cap['DPOS'], cap['FCUT']
    SPLIT = SL.SPLIT
    LENS = lens_lists()

    # ---- stats, the same formulas as stack_live.card() ----
    def ladder(G):
        res = []
        for th in (5, 10, 15, 20):
            hit = ok = liq = 0
            for s0 in G:
                a0 = s0['a']; i0 = DPOS[a0].get(s0['d0']); e0 = s0['entry']
                if i0 is None: continue
                Hs = DAY[a0]['high'][i0 + 1:i0 + 61]; Ls = DAY[a0]['low'][i0 + 1:i0 + 61]
                for j, (h, l) in enumerate(zip(Hs, Ls)):
                    if h >= e0 * 1.10: break
                    if l <= e0 * (1 - th / 100):
                        hit += 1
                        for hh, ll in zip(Hs[j:], Ls[j:]):
                            if ll <= e0 * (1 + MS.LIQ / 100): liq += 1; break
                            if hh >= e0 * 1.10: ok += 1; break
                        break
            res += [hit, round(100 * ok / hit) if hit else '', round(100 * liq / hit) if hit else '']
        return res

    def stats(G):
        n = len(G); pct = lambda k: round(100 * k / n) if n else ''
        sc = [x for x in (MS.scaled20(s0['a'], s0['d0'], s0['m']) for s0 in G) if x is not None]
        old = [s0 for s0 in G if s0['d0'] < SPLIT]; new = [s0 for s0 in G if s0['d0'] >= SPLIT]
        sv = lambda X: round(100 * sum(MS.surv10(s0['m']) for s0 in X) / len(X)) if X else ''
        return [n, pct(sum(MS.surv10(s0['m']) for s0 in G)), round(100 * sum(sc) / len(sc)) if sc else '',
                pct(sum(s0['m']['up'] >= 20 for s0 in G)), pct(sum(s0['m']['up'] >= 10 for s0 in G)),
                round(st.median(s0['m']['up'] for s0 in G), 1) if n else '', round(st.median(s0['m']['ddpk'] for s0 in G), 1) if n else '',
                round(st.median(s0['m']['dd'] for s0 in G), 1) if n else '', pct(sum(s0['m']['dd'] <= -30 for s0 in G)),
                len(old), sv(old), len(new), sv(new)] + ladder(G)
    SHDR = ['n', 'surv10', 'scaled20', 'reach20', 'reach10', 'bestMove', 'dipBeforeHigh', 'maxDip60', 'touched30',
            'nOld', 'surv10Old', 'nNew', 'surv10New'] + [f'l{t}{k}' for t in (5, 10, 15, 20) for k in ('n', 'ok', 'liq')]

    def mask(a, s):
        f = feats(s); return sum(1 << i for i, k in enumerate(LENS[a]) if f.get(k))

    T = {}          # key -> stats (or count only)
    for a in ('ETH', 'BTC'):
        okrow = (lambda s: s.get('fund') is not None and s.get('fcool') is not None) if a == 'ETH' else (lambda s: True)
        Aall = [s for s in rows if s['a'] == a and s['tf'] in ('1D', '2D', '3D', '5D') and okrow(s)]
        for g in GRADES:
            T[f'{a}|G|{g}'] = stats([s for s in Aall if gof(bin(mask(a, s)).count('1')) == g])
        for tf in TFS:
            Cf = [s for s in rows if s['a'] == a and s['tf'] == tf and okrow(s)]
            for g in GRADES:
                T[f'{a} {tf}|G|{g}'] = stats([s for s in Cf if gof(bin(mask(a, s)).count('1')) == g])
            by = {}
            for s in Cf: by.setdefault(mask(a, s), []).append(s)
            for m, G in by.items():
                T[f'{a} {tf}|X|{m}'] = stats(G) if len(G) >= 15 else [len(G)]

    # ---- re-derive every card from the tables, the way the Pine lookup does ----
    PLAINR = {v: k for k, v in {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
              'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
              'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}.items()}
    bad = []; cards = list(csv.DictReader(open('datasets/cards.csv')))
    for c in cards:
        a, tf, g = c['asset'], c['tf'], c['grade']
        have = set() if c['lenses'] == 'none' else {PLAINR[x] for x in c['lenses'].split('; ')}
        m = sum(1 << i for i, k in enumerate(LENS[a]) if k in have)
        ex = T.get(f'{a} {tf}|X|{m}', [0]); sg = T[f'{a} {tf}|G|{g}']; ag = T[f'{a}|G|{g}']
        S = ex if ex[0] >= 15 else sg if sg[0] >= 15 else ag
        for k, v in zip(SHDR, S):
            cv = c[k]
            if str(v) != cv and not (cv != '' and v != '' and float(cv) == float(v)):
                bad.append(f"{c['chart']} {k}: card {cv} vs table {v}")
    if bad:
        raise SystemExit('TABLES DO NOT REPRODUCE THE CARDS:\n  ' + '\n  '.join(bad))
    print(f'tables reproduce all {len(cards)} cards in datasets/cards.csv')

    # ---- regime flips ----
    ok, days = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41, ret_series=True)
    flips = []; prev = None
    for d in days:
        if ok[d] != prev: flips.append((d, ok[d])); prev = ok[d]
    last2d = days[-2]                       # the last CLOSED BTC 2D bar (the data's last bar is still open)
    built = max(DAY['ETH']['date'])

    # ---- write the data block ----
    ts = lambda d: int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000)
    na = lambda v: 'na' if v == '' else str(v)
    L = ['// ===== DATA BLOCK - generated by pine/build_v10.py; do not edit by hand =====',
         f'// Built {built} from the repo. The card numbers below are datasets/cards.csv\'s',
         '// like-for-like samples as of that date; the dashboard keeps updating, these do not',
         '// until the script is rebuilt and re-pasted.',
         f'string BUILT = "{built:%d %b %Y}"',
         f'int BUILT_2D = {ts(last2d)}   // last closed BTC 2D bar in the build',
         f'bool BUILT_STATE = {"true" if ok[last2d] else "false"}',
         'var array<int> RZ_T = array.from(' + ', '.join(str(ts(d)) for d, _ in flips) + ')',
         'var array<bool> RZ_S = array.from(' + ', '.join('true' if s else 'false' for _, s in flips) + ')',
         '// FASTCT cut points (CT at confirmation minus CT at the trough, top third, 2016-21)',
         'fcutFor(string ch) =>',
         '    float r = na']
    for tf in TFS:
        v = FCUT.get(('BTC', tf))
        if v is not None:
            L.append(f'    r := ch == "BTC {tf}" ? {v!r} : r')
    L += ['    r', '',
          '// Like-for-like samples. Key: "<chart>|X|<mask>" exact confirmations (count only when under 15),',
          '// "<chart>|G|<grade>" this chart at a grade, "<asset>|G|<grade>" a grade across the asset\'s 1D-5D charts.',
          '// Value: ' + ','.join(SHDR) + '  (na = no trades reached that row)',
          'var map<string, string> STATS = map.new<string, string>()',
          'if barstate.isfirst']
    for k in sorted(T):
        L.append(f'    STATS.put("{k}", "{",".join(na(v) for v in T[k])}")')
    L.append('// ===== END DATA BLOCK =====')
    data = '\n'.join(L) + '\n'

    eng = open(os.path.join(PINE, 'engine_v10.pine.in')).read()
    for name, tpl in (('ct_zone_bounce_v16.pine', 'indicator_v16.pine.in'), ('ctzb_scanner_v10.pine', 'scanner_v10.pine.in')):
        src = open(os.path.join(PINE, tpl)).read().replace('//@@DATA@@\n', data).replace('//@@ENGINE@@\n', eng)
        open(os.path.join(PINE, name), 'w').write(src)
        print(f'wrote pine/{name} ({src.count(chr(10))} lines)')
    print(f'regime flips: {len(flips)}, built state {"BULL" if ok[last2d] else "BEAR"} at {last2d}; FASTCT cuts '
          + ', '.join(f'BTC {tf} {FCUT[("BTC", tf)]:.2f}' for tf in TFS if FCUT.get(('BTC', tf)) is not None))


if __name__ == '__main__':
    main()
