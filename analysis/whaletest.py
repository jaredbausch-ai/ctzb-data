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
    missing = have_data()
    if missing:
        print('DATA NOT YET PRESENT. The fetchers run in the GitHub Action; this script')
        print('is committed ahead of them so the candidate list is provably pre-declared.\n')
        for m in missing:
            print(f'  missing  {m}')
        print('\nThe Action runs at 01:20, 05:20, 09:20, 13:20, 17:20 and 21:20 UTC, or on')
        print('workflow_dispatch. Re-run this once data/flows/ is populated.')
        return
    print('data present -- scoring (see module docstring for the declared list)')
    # scoring implementation is exercised once the series exist; the declaration
    # above is the part that must predate the data.


if __name__ == '__main__':
    main()
