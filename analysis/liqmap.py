"""Long-liquidation cluster model for ETH perps.

Inputs: data/ETH_1D.csv (OHLC), data/derivs/ETH_oi_daily.csv (aggregate perp OI, USD),
        data/derivs/ETH_lsratio_daily.csv (long/short account ratio).

Method: each day's POSITIVE change in aggregate OI is treated as new notional opened at
that day's typical price, split long/short by the account ratio. Longs are spread over a
leverage distribution; each slice gets a liquidation price. A slice survives only if price
has not already traded through it since it was opened. Surviving long notional is then
normalised to today's long-side OI and bucketed by liquidation price.

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
spot = float(sys.argv[1]) if len(sys.argv) > 1 else ohlc[-1]['close']

# lowest low seen from each day forward to now
fwd_min = {}
run = float('inf')
for d in reversed(days_sorted):
    if d in byday: run = min(run, byday[d]['low'])
    fwd_min[d] = run

slices = []   # (liq_price, notional)
for i in range(1, len(recent)):
    d, pd_ = recent[i], recent[i-1]
    if d not in byday: continue
    dOI = oi[d] - oi[pd_]
    if dOI <= 0: continue
    b = byday[d]
    px = (b['high'] + b['low'] + b['close']) / 3.0
    r = lsr.get(d, 2.0)
    long_notional = dOI * (r / (1.0 + r))
    j = days_sorted.index(d)
    low_since = min([byday[x]['low'] for x in days_sorted[j+1:]] or [b['low']])
    for lev, w in LEV:
        q = px * (1.0 - 1.0/lev + MMR)
        if q >= spot: continue          # already liquidated / above market
        if q >= low_since: continue     # price already traded through it
        slices.append((q, long_notional * w))

tot = sum(n for _, n in slices)
long_oi_now = oi[oidays[-1]] * (lsr.get(oidays[-1], 2.0) / (1 + lsr.get(oidays[-1], 2.0)))
scale = (long_oi_now / tot) if tot else 0.0

bins = {}
for q, n in slices:
    bins[int(q // BIN) * BIN] = bins.get(int(q // BIN) * BIN, 0.0) + n * scale

print(f"spot {spot:.2f}   aggregate perp OI ${oi[oidays[-1]]/1e9:.2f}B   "
      f"L/S {lsr.get(oidays[-1]):.2f}   modelled long OI ${long_oi_now/1e9:.2f}B")
print(f"\nbin_low  liq_notional_$M  cum_from_spot_$M  pct_of_long_OI")
cum = 0.0
for k in sorted(bins, reverse=True):
    cum += bins[k]
    print(f"{k:8.0f}  {bins[k]/1e6:14.1f}  {cum/1e6:16.1f}  {100*cum/long_oi_now:13.1f}%")
