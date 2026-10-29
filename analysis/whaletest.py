"""Do capital-flow proxies sort CTZB signals? Declared 25 Oct 2026.

THE CANDIDATE LIST BELOW WAS WRITTEN BEFORE THE DATA EXISTED. fetch_flows.py and
fetch_onchain.py were committed in the same session and populate on the next
Action run, so nothing here could have been chosen by looking at results. That is
the strongest version of the guard in CONTEXT.md and it will not be available
again once the series are on disk.

WHAT THIS IS NOT. None of these measure whales. A true whale signal needs
labelled on-chain addresses (Glassnode, CryptoQuant -- paid). These are proxies
for "is large money entering the system":

  stablecoin supply   fiat converted to on-chain dollars = dry powder
  Coinbase Premium    US spot bid against offshore = institutional lean
  spot ETF net flow   the literal institutional bid, but only ~2 years of it

DECLARED FEATURES, evaluated at the entry bar (d0), all from data up to and
including d0. Tercile cut points from the DISCOVERY period only.

  stablecoin supply            Coinbase Premium              spot ETF flow
  W1  7d growth > 0            W5  premium > 0               W9  5d net flow > 0
  W2  7d growth top third      W6  7d mean prem top third    W10 5d net top third
  W3  30d growth top third     W7  premium rising 14d        W11 20d net flow > 0
  W4  growth accelerating      W8  prem > 90d median         W12 flow > 0 on d0

EACH is scored BOTH ways -- as a selector (take only when true) and as a veto
(skip when true) -- and in both polarities, because the 23 Oct run proved that
a selector bar can hide an exclusion effect.

BARS. Selector: >= 70% win in both periods, n >= 15 each. Veto: kept win rate
above baseline AND kept -30% below baseline AND more losers than winners removed,
both periods, n >= 15 excluded. Any survivor then faces:
  per-chart split      the guard that killed four findings
  regime-age strata    THE ONE THAT MATTERS. Capital flow is slow and macro and
                       may simply be restating the regime gate. Every signal in
                       the record is already gated, so the test is whether the
                       edge survives stratifying by how long the regime has been
                       on -- the same check that exposed the higher-low filter as
                       late-regime-only.
  gap>5 overlap        does it add anything to the stack that already exists

HISTORY IS UNEQUAL AND THAT IS NOT COSMETIC. Stablecoins ~2018, premium 2017,
ETF 2024. The ETF features cover roughly two years against a signal record
starting 2016, which is too thin to carry a finding alone and is reported
separately rather than pooled.

Run from the repo root:  python3 -I analysis/whaletest.py
"""
import sys, os, csv, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E, regimes as R
from tagstats import bucket_end, measure
from derivtest import CHARTS

FLOW = 'data/flows'
REGIME_ON = dt.date(2026, 9, 2)
SC = f'{FLOW}/stablecoin_supply_daily.csv'
PREM = {s: f'{FLOW}/{s}_premium_daily.csv' for s in ('BTC', 'ETH')}
ETFF = {s: f'{FLOW}/{s}_etf_flow_daily.csv' for s in ('BTC', 'ETH')}

SC_FEATS = ['W1', 'W2', 'W3', 'W4']
PR_FEATS = ['W5', 'W6', 'W7', 'W8']
ET_FEATS = ['W9', 'W10', 'W11', 'W12']
NAMES = {'W1': 'stablecoin 7d growth > 0', 'W2': 'stablecoin 7d growth top third',
         'W3': 'stablecoin 30d growth top third', 'W4': 'stablecoin growth accelerating',
         'W5': 'Coinbase premium > 0', 'W6': 'premium 7d mean top third',
         'W7': 'premium rising 14d', 'W8': 'premium above 90d median',
         'W9': 'ETF 5d net flow > 0', 'W10': 'ETF 5d net top third',
         'W11': 'ETF 20d net flow > 0', 'W12': 'ETF flow > 0 on entry day'}


def read(path, key, val):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for r in csv.DictReader(f):
            v = r.get(val, '')
            if v not in ('', None):
                try:
                    out[dt.date.fromisoformat(r[key])] = float(v)
                except ValueError:
                    continue
    return out


def have_data():
    missing = [p for p in [SC] + list(PREM.values()) + list(ETFF.values()) if not os.path.exists(p)]
    return missing


def main():
    """Scoring added 28 Oct 2026 (the declaration above is unchanged). The premium
    fetch has never worked: Binance answers GitHub's US runners with HTTP 451, so
    W5-W8 have no data. The ETF source returns only ~14 days, far short of the
    15-per-period minimum, so W9-W12 cannot be scored. W1-W4 (stablecoin supply,
    2017 on) are scored against the declared bars; discovery = to 2021."""
    import grokpack as GP
    sc = read(SC, 'date', 'total_usd')
    print('FLOWS TEST (whaletest.py, declared 25 Oct 2026), run', dt.date.today(), '| entry quality only, computed signals, not fills')
    print('  W5-W8 Coinbase premium: NO DATA (Binance blocks the US GitHub runners, HTTP 451)')
    etf = read(ETFF['BTC'], 'date', 'net_flow_usd_m')
    print(f'  W9-W12 spot ETF flow: {len(etf)} days of history -- too short to score')
    rows, _ = GP.build()
    rows = [r for r in rows if r['tf'] in ('1D', '2D', '3D', '5D')]
    def g(d, k):
        a, b = sc.get(d), sc.get(d - dt.timedelta(days=k))
        return None if not a or not b else 100 * (a / b - 1)
    for r in rows:
        d = r['d0']; r['g7'] = g(d, 7); r['g30'] = g(d, 30); p7 = g(d - dt.timedelta(days=7), 7)
        r['acc'] = None if r['g7'] is None or p7 is None else r['g7'] > p7
    disc = [r for r in rows if r['d0'] < dt.date(2022, 1, 1)]
    cut7 = sorted(r['g7'] for r in disc if r['g7'] is not None); cut30 = sorted(r['g30'] for r in disc if r['g30'] is not None)
    c7 = cut7[int(2 * len(cut7) / 3)]; c30 = cut30[int(2 * len(cut30) / 3)]
    F = {'W1': lambda r: None if r['g7'] is None else r['g7'] > 0, 'W2': lambda r: None if r['g7'] is None else r['g7'] >= c7,
         'W3': lambda r: None if r['g30'] is None else r['g30'] >= c30, 'W4': lambda r: r['acc']}
    def st_(G):
        n = len(G)
        return None if not n else dict(n=n, win=100 * sum(r['win'] for r in G) / n, l30=100 * sum(r['t30'] for r in G) / n,
                                       losers=sum(not r['win'] for r in G), winners=sum(r['win'] for r in G))
    for a in ('ETH', 'BTC'):
        print(f'\n{a}')
        for k in SC_FEATS:
            for pol in (True, False):
                lab = f'{k} {NAMES[k]}' + ('' if pol else ' -- FALSE')
                sel_ok = True; veto_ok = True; parts = []
                for pl, per in (('to 2021', lambda r: r['d0'] < dt.date(2022, 1, 1)), ('2022 on', lambda r: r['d0'] >= dt.date(2022, 1, 1))):
                    U = [r for r in rows if r['a'] == a and per(r) and F[k](r) is not None]
                    W = [r for r in U if F[k](r) == pol]; O = [r for r in U if F[k](r) != pol]
                    b, w, o = st_(U), st_(W), st_(O)
                    if not b or not w or not o: sel_ok = veto_ok = False; parts.append(f'{pl} -'); continue
                    parts.append(f'{pl} base {b["win"]:3.0f}% | true n={w["n"]} {w["win"]:3.0f}% -30% {w["l30"]:3.0f}% | rest {o["win"]:3.0f}% -30% {o["l30"]:3.0f}%')
                    if not (w['n'] >= 15 and w['win'] >= 70): sel_ok = False
                    if not (w['n'] >= 15 and o['win'] > b['win'] and o['l30'] < b['l30'] and w['losers'] > w['winners']): veto_ok = False
                print(f'  {lab}')
                for x in parts: print('     ', x)
                print(f'      selector: {"PASS" if sel_ok else "fail"} | veto: {"PASS" if veto_ok else "fail"}')
    print('\n  Context only unless something passes; survivors would then face the per-chart, regime-age and gap>5 guards.')


if __name__ == '__main__':
    main()
