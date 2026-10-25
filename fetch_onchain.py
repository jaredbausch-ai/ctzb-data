"""Free flow proxies with HISTORY: stablecoin supply and spot-ETF net flows.

Runs in the GitHub Action after fetch.py. NO API KEY for either source. The
container cannot reach them (agent proxy returns 403), which is why this lives
in the Action like the rest of the pipeline.

WHY THESE TWO, stated plainly. A true whale signal -- identifiable large holders
accumulating -- is NOT buildable from free data. It needs labelled on-chain
addresses, which is the product Glassnode and CryptoQuant sell. These are
proxies for "is large money entering", not "are whales buying". They are kept
because they are FLOW measures on a different axis from price, and per
CONTEXT.md the only two filters that ever survived here were different-axis
measures rather than transforms of the same closes.

  Stablecoin supply (DefiLlama, https://stablecoins.llama.fi, free, no key)
      Total circulating stablecoin market cap, daily, back to 2018-ish. Supply
      expands when fiat is converted to on-chain dollars -- dry powder entering
      the system, which is what a large buyer does before deploying. Contraction
      is money leaving. Slow-moving and macro: the real risk is that it sorts
      REGIMES rather than individual signals, and a regime gate already exists.
      vetotest/whaletest checks that collinearity explicitly.

  Spot ETF net flows (Farside, free, HTML table -- scraped)
      Daily net creations/redemptions in US$m for US spot BTC and ETH ETFs. The
      most literal institutional flow available for this cycle, since post-ETF
      the marginal large buyer buys shares rather than coins. SHORT HISTORY:
      BTC from Jan 2024, ETH from Jul 2024, so roughly two years against a
      signal record that starts in 2016. Too thin to carry a finding on its own.
      Scraping an HTML table is fragile by nature; the parse is defensive and
      logs rather than raising, so a layout change cannot break the candle run.

Writes, under data/flows/:
  stablecoin_supply_daily.csv   date, total_usd, d7_pct, d30_pct
  {SYM}_etf_flow_daily.csv      date, net_flow_usd_m
  fetch_log.txt                 appended, so failures are visible in the repo
"""
import csv, datetime as dt, json, os, re, time, urllib.request, urllib.error

OUT = 'data/flows'
SC = 'https://stablecoins.llama.fi/stablecoincharts/all'
ETF = {'BTC': 'https://farside.co.uk/btc/', 'ETH': 'https://farside.co.uk/ethereum-etf-flow/'}
LOG = []


def log(m):
    print(m); LOG.append(f'{dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M:%S} {m}')


def get(url, as_json=True, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; ctzb-pipeline/1.0)'})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            return json.loads(raw) if as_json else raw.decode('utf-8', 'replace')
        except Exception as e:
            log(f'  {type(e).__name__} on {url[:70]}')
            if i == tries - 1:
                return None
            time.sleep(2 ** i)
    return None


def stablecoins():
    d = get(SC)
    if not d:
        log('stablecoins: no data'); return
    ser = {}
    for row in d:
        try:
            day = dt.datetime.fromtimestamp(int(row['date']), dt.UTC).date()
            pegged = row.get('totalCirculatingUSD') or {}
            if isinstance(pegged, dict):
                # dollar-pegged only: this is a proxy for fiat converted to
                # on-chain DOLLARS. EUR/other pegs are a rounding error but
                # including them would make the series mean something else.
                v = float(pegged.get('peggedUSD', 0)) or sum(float(x) for x in pegged.values())
            else:
                v = float(pegged)
            if v > 0:
                ser[day] = v
        except Exception:
            continue
    if not ser:
        log('stablecoins: parsed 0 rows -- shape may have changed'); return
    days = sorted(ser)
    with open(f'{OUT}/stablecoin_supply_daily.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'total_usd', 'd7_pct', 'd30_pct'])
        for day in days:
            a = ser.get(day - dt.timedelta(days=7)); b = ser.get(day - dt.timedelta(days=30))
            w.writerow([day.isoformat(), f'{ser[day]:.0f}',
                        f'{(ser[day]/a-1)*100:.4f}' if a else '',
                        f'{(ser[day]/b-1)*100:.4f}' if b else ''])
    log(f'stablecoins: {len(days)} days, {days[0]} -> {days[-1]}, '
        f'latest ${ser[days[-1]]/1e9:.1f}B')


MONTHS = {m: i for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}


def etf(sym, url):
    html = get(url, as_json=False)
    if not html:
        log(f'{sym} ETF: no page'); return
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S | re.I)
    out = {}
    for tr in rows:
        cells = [re.sub(r'<[^>]+>', '', c) for c in
                 re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S | re.I)]
        cells = [c.replace('&nbsp;', ' ').strip() for c in cells]
        if len(cells) < 3:
            continue
        m = re.match(r'^(\d{1,2})\s+(\w{3})\s+(\d{4})$', cells[0])
        if not m:
            continue
        try:
            day = dt.date(int(m.group(3)), MONTHS[m.group(2)[:3].title()], int(m.group(1)))
        except (KeyError, ValueError):
            continue
        tot = None
        for c in reversed(cells[1:]):
            c2 = c.replace(',', '').replace('$', '').strip()
            neg = c2.startswith('(') and c2.endswith(')')
            c2 = c2.strip('()')
            if re.fullmatch(r'-?\d+(\.\d+)?', c2):
                tot = -float(c2) if neg else float(c2)
                break
        if tot is not None:
            out[day] = tot
    if not out:
        log(f'{sym} ETF: parsed 0 rows -- table layout may have changed'); return
    days = sorted(out)
    with open(f'{OUT}/{sym}_etf_flow_daily.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'net_flow_usd_m'])
        for day in days:
            w.writerow([day.isoformat(), f'{out[day]:.1f}'])
    log(f'{sym} ETF: {len(days)} days, {days[0]} -> {days[-1]}')


def main():
    os.makedirs(OUT, exist_ok=True)
    stablecoins()
    for sym, url in ETF.items():
        etf(sym, url); time.sleep(1.5)
    mode = 'a' if os.path.exists(f'{OUT}/fetch_log.txt') else 'w'
    with open(f'{OUT}/fetch_log.txt', mode) as f:
        f.write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
