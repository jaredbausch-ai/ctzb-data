"""Coin Metrics community API -> data/onchain/{BTC,ETH}_cm_daily.csv

Free, no key, current. Replaces the GitHub CSV dump, which stopped being
updated on 2026-05-24.
"""
import json, urllib.request, csv, sys, os

BASE = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
METRICS = ["PriceUSD","CapMrktCurUSD","CapMVRVCur","AdrActCnt",
           "SplyCur","SplyExNtv","FlowInExNtv","FlowOutExNtv"]

def fetch(asset):
    rows, token = [], None
    while True:
        q = (f"{BASE}?assets={asset}&metrics={','.join(METRICS)}"
             f"&frequency=1d&page_size=10000&start_time=2010-01-01")
        if token: q += f"&next_page_token={token}"
        with urllib.request.urlopen(q, timeout=120) as r:
            j = json.load(r)
        rows += j.get("data", [])
        token = j.get("next_page_token")
        if not token: break
    return rows

for a in ("btc","eth"):
    rows = fetch(a)
    out = f"data/onchain/{a.upper()}_cm_daily.csv"
    with open(out,"w",newline="") as f:
        w = csv.writer(f); w.writerow(["date"]+METRICS)
        for r in rows:
            w.writerow([r["time"][:10]] + [r.get(m,"") for m in METRICS])
    have = [r for r in rows if r.get("CapMVRVCur")]
    print(f"{out}  {len(rows)} rows  {rows[0]['time'][:10]} -> {rows[-1]['time'][:10]}"
          f"   MVRV populated to {have[-1]['time'][:10]}")
