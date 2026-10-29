"""Bar-for-bar Python replica of the v10 Pine ENGINE (pine/engine_v10.pine.in), run on
the repo's own candles and checked against datasets/cards.csv (29 Oct 2026).

The Pine cannot be run here, so this replays its rules exactly as written in Pine
(one-bar-late confirmations, the forming-low search, d0 arithmetic, the closed-form
kill close, the lens tests, the regime if-chain) and compares, for every chart:
forming or not, trough date, confirmation date, bars needed, kill close, and the
confirmations (BTC: all four; ETH: the four price ones, the console's minus funding)
and BTC's grade. Any difference is a bug in the Pine logic or in this replica.
  python3 -I pine/pine_mirror.py
"""
import csv, os, sys, datetime as dt
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'analysis'))
os.chdir(HERE)
import engine as E
import regimes as R

TFS = ('1D', '2D', '3D', '5D', '8D')
FCUT = {'BTC 1D': None, 'BTC 2D': None, 'BTC 3D': None, 'BTC 5D': None, 'BTC 8D': None}


def pine_fcut():
    src = open('pine/ctzb_scanner_v10.pine').read()
    for line in src.splitlines():
        line = line.strip()
        if line.startswith('r := ch == "BTC'):
            ch = line.split('"')[1]; FCUT[ch] = float(line.split('?')[1].split(':')[0])


def wilder(C):
    """ta.rma of gains and losses, ta.rsi"""
    n = len(C); ag = [None] * n; al = [None] * n; ct = [None] * n
    g = l = 0.0
    for i in range(1, 15):
        ch = C[i] - C[i - 1]; g += max(ch, 0); l += max(-ch, 0)
    ag[14], al[14] = g / 14, l / 14
    for i in range(15, n):
        ch = C[i] - C[i - 1]
        ag[i] = (ag[i - 1] * 13 + max(ch, 0)) / 14; al[i] = (al[i - 1] * 13 + max(-ch, 0)) / 14
    for i in range(14, n):
        ct[i] = 100.0 if al[i] == 0 else 100 - 100 / (1 + ag[i] / al[i])
    return ct, ag, al


def main():
    pine_fcut()
    ok, days = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41, ret_series=True)
    flips = []; prev = None
    for d in days:
        if ok[d] != prev: flips.append((d, ok[d])); prev = ok[d]
    def regAt(d):
        s = False
        for fd, fs in flips:
            if d >= fd: s = fs
        return s
    ch = {}
    for a in ('ETH', 'BTC'):
        for tf in TFS:
            b = E.load(f'data/{a}_{tf}.csv'); C, D = b['close'], b['date']; n = len(C)
            ct, ag, al = wilder(C); em = E.ema(ct, 14); kL = E.sma(E.stoch_of(ct, 14), 3)
            lastD0 = lastEntry = None; pCt = pK = None
            # Pine reads a confirmation on the bar AFTER it closes: at bar k, trough k-4, confirmation k-1
            for k in range(7, n):
                v = ct[k - 4]
                w = [ct[k - j] for j in range(1, 8)]
                if v is None or any(x is None for x in w) or kL[k - 4] is None: continue
                if all(ct[k - j] > v for j in (1, 2, 3, 5, 6, 7)):
                    if regAt(D[k - 4]):
                        lastD0 = D[k] - dt.timedelta(days=1); lastEntry = C[k - 1]
                    pCt, pK = v, kL[k - 4]
            i = n - 1; fb = 0
            for bb in (1, 2, 3):
                if fb: break
                vv = ct[i - bb]
                if vv is None or ct[i - bb - 3] is None: continue
                if all(ct[i - bb - j] > vv for j in (1, 2, 3)) and all(ct[i - j] >= vv for j in range(0, bb)):
                    fb = bb
            tfd = int(tf[:-1])
            r = dict(a=a, tf=tf, fb=fb, lastD0=lastD0, lastEntry=lastEntry, ct=ct[i], em=em[i], c1=ct[i - 1], c2=ct[i - 2], cl=C[i])
            if fb:
                need = 3 - fb; fCt = ct[i - fb]
                r.update(need=need, trough=D[i - fb], d0=D[i] + dt.timedelta(days=need * tfd + tfd - 1), fCt=fCt)
                def kill(pc, pag, pal, T):
                    rs = T / (100 - T); x = rs * pal * 13 - pag * 13
                    return pc + x if x >= 0 else pc + pal * 13 - pag * 13 / rs
                r['kill'] = kill(C[i - 1], ag[i - 1], al[i - 1], fCt) if fb == 3 else kill(C[i], ag[i], al[i], fCt) if fb == 2 else None
            ch[(a, tf)] = r
    near = lambda d0, x: x is not None and 0 <= (d0 - x).days <= 10
    cards = {c['chart']: c for c in csv.DictReader(open('datasets/cards.csv'))}
    PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
             'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'UP8': 'the 8D chart rising',
             'FASTCT': 'CT recovering fast from the low', 'FUND': 'funding at or above its 90-day median', 'FCOOL': 'funding not cooling'}
    bad = []; rep = []
    for (a, tf), r in ch.items():
        name = f'{a} {tf}'; c = cards.get(name)
        if not r['fb']:
            if c: bad.append(f'{name}: card exists, mirror sees nothing forming')
            rep.append(f'{name}: nothing forming (no card: {c is None})'); continue
        if not c:
            bad.append(f'{name}: mirror sees a low forming, no card'); continue
        d0 = r['d0']
        oth = [ch[(a, t)]['lastD0'] for t in TFS if t != tf]
        agree = sum(near(d0, x) for x in oth)
        L = []
        if r['ct'] - r['em'] > 5: L.append('GAP')
        if a == 'ETH':
            if r['lastEntry'] is not None and r['cl'] > r['lastEntry']: L.append('HIGH')
            if agree >= 2: L.append('AGREE')
            if tf in ('1D', '2D') and near(d0, ch[('BTC', '3D')]['lastD0']): L.append('BTC3')
        else:
            e8 = ch[('BTC', '8D')]
            if e8['c1'] > e8['c2']: L.append('UP8')
            if tf in ('1D', '2D') and near(d0, ch[('ETH', '2D')]['lastD0']): L.append('BTCX')
            fc = FCUT.get(name)
            if fc is not None and r['ct'] - r['fCt'] >= fc: L.append('FASTCT')
        cl = set() if c['lenses'] == 'none' else {k for k, v in PLAIN.items() if v in c['lenses'].split('; ')}
        want = cl - {'FUND', 'FCOOL'}
        chk = [('trough', str(r['trough']), c['trough']), ('confirms', str(d0), c['confirms']), ('barsNeeded', str(r['need']), c['barsNeeded']),
               ('lenses', ' '.join(sorted(L)), ' '.join(sorted(want)))]
        kc = '' if r['kill'] is None else f"{r['kill']:.2f}"
        chk.append(('killClose', kc, c['killClose'] if c['killClose'] == '' else f"{float(c['killClose']):.2f}"))
        if a == 'BTC':
            g = 'C' if len(L) <= 1 else 'B' if len(L) == 2 else 'A' if len(L) == 3 else 'A+'
            chk.append(('grade', g, c['grade']))
        for k, x, y in chk:
            if x != y and not (k == 'killClose' and x and y and abs(float(x) - float(y)) <= 0.011):
                bad.append(f'{name} {k}: Pine logic {x} vs card {y}')
        rep.append(f"{name}: trough {r['trough']}, confirms {d0}, need {r['need']}, kill {kc or '-'}, confirmations {' '.join(L) or 'none'}")
    print('\n'.join(rep))
    if bad:
        raise SystemExit('PINE LOGIC DIFFERS FROM THE CARDS:\n  ' + '\n  '.join(bad))
    print(f'Pine engine logic matches all {len(cards)} cards (BTC fully; ETH on its price confirmations)')


if __name__ == '__main__':
    main()
