"""Short-liquidation cluster model for ETH perps — the upside mirror of liqmap.py.

Same method, inverted: each day's POSITIVE change in aggregate OI is new notional
opened at that day's typical price, split long/short by the account ratio. The SHORT
side is spread over the leverage distribution; each slice gets an upside liquidation
price q = px * (1 + 1/lev - MMR). A slice survives only if price has NOT traded
ABOVE it since it was opened. Surviving short notional is normalised to today's
short-side OI and bucketed.

This is a MODEL. The leverage distribution is an assumption, not measured data.
"""
import csv, sys, datetime as dt

LEV = [(5,.15),(10,.25),(20,.25),(25,.15),(50,.12),(100,.08)]
MMR = 0.005
LOOKBACK = 120
BIN = 25.0

def rows(p):
    with open(p) as f: return list(csv.DictReader(f))

ohlc = rows('data/ETH_1D.csv')
for r in ohlc:
    r['d'] = dt.datetime.utcfromtimestamp(int(r['time'])).strftime('%Y-%m-%d')
    for k in ('open','high','low','close'): r[k] = float(r[k])

spot = float(sys.argv[1]) if len(sys.argv) > 1 else ohlc[-1]['close']
# patch the stale final bar with today's live extremes
if len(sys.argv) > 4:
    ohlc[-1]['high'] = max(ohlc[-1]['high'], float(sys.argv[2]))
    ohlc[-1]['low']  = min(ohlc[-1]['low'],  float(sys.argv[3]))
    ohlc[-1]['close'] = float(sys.argv[4])

byday = {r['d']: r for r in ohlc}
days_sorted = [r['d'] for r in ohlc]

oi = {r['date']: float(r['oi_usd_total']) for r in rows('data/derivs/ETH_oi_daily.csv')}
lsr = {}
for r in rows('data/derivs/ETH_lsratio_daily.csv'):
    k = list(r.keys())[1]
    try: lsr[r['date']] = float(r[k])
    except (TypeError, ValueError): pass

oidays = sorted(oi)
recent = oidays[-LOOKBACK:]

slices = []
for i in range(1, len(recent)):
    d, pd_ = recent[i], recent[i-1]
    if d not in byday: continue
    dOI = oi[d] - oi[pd_]
    if dOI <= 0: continue
    b = byday[d]
    px = (b['high'] + b['low'] + b['close']) / 3.0
    r = lsr.get(d, 2.0)
    short_notional = dOI * (1.0 / (1.0 + r))
    j = days_sorted.index(d)
    high_since = max([byday[x]['high'] for x in days_sorted[j+1:]] or [b['high']])
    for lev, w in LEV:
        q = px * (1.0 + 1.0/lev - MMR)
        if q <= spot: continue          # already liquidated / below market
        if q <= high_since: continue    # price already traded through it
        slices.append((q, short_notional * w))

tot = sum(n for _, n in slices)
rl = lsr.get(oidays[-1], 2.0)
short_oi_now = oi[oidays[-1]] * (1.0 / (1.0 + rl))
scale = (short_oi_now / tot) if tot else 0.0

bins = {}
for q, n in slices:
    bins[int(q // BIN) * BIN] = bins.get(int(q // BIN) * BIN, 0.0) + n * scale

print(f"spot {spot:.2f}   aggregate perp OI ${oi[oidays[-1]]/1e9:.2f}B   "
      f"L/S {rl:.2f}   modelled short OI ${short_oi_now/1e9:.2f}B")
print(f"\nbin_low  liq_notional_$M  cum_from_spot_$M  pct_of_short_OI")
cum = 0.0
for k in sorted(bins):
    cum += bins[k]
    print(f"{k:8.0f}  {bins[k]/1e6:14.1f}  {cum/1e6:16.1f}  {100*cum/short_oi_now:13.1f}%")
