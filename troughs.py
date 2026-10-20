#!/usr/bin/env python3
"""Every trough, one row each: how much upside was in it and what it cost to hold.

Gate: mechanical RSI regime, same as odds.py.
Columns per row (see KEYS):
  ch   chart            e.g. "ETH 2D"
  d    entry date       close of the confirmation bar, 3 bars after the RSI low
  px   entry price
  bk   bucket           A/B/C/D by RSI level at the trough
  tg   tags             "dia" / "hollow" / "dot"  (filled diamond = dia without hollow)
  d60  days from entry to that 60-day high. Compared against `dead` it says
       whether the high landed before or after the position was wiped out.
  u60  best upside within 60 days
  u90  best upside within 90 days
  umx  best upside within 365 days, stopping if price first falls -30% from entry.
       Bounded at a year on purpose: unbounded, a 2016 trough reports +21,435%,
       which measures how long BTC has existed rather than what the trough did.
  dmx  days to that umx peak
  h60  deepest the price went BELOW entry before the 60-day peak
  hmx  deepest the price went BELOW entry before the umx peak
  dead days until price fell -30% from entry WITHOUT having first gained +5%
       i.e. the trough killed the position before it ever gave anything back.
       null when the trough paid at least +5% before any such drop (or never dropped).
  cf   how many OTHER timeframes of the same asset had ALREADY printed within
       AGREE_DAYS BEFORE this entry. Knowable at the moment you would trade.
  cfs  the same count with a symmetric +/-AGREE_DAYS window, which is what
       refresh.py/ds_confluence uses. It credits charts that print up to ten
       days AFTER entry, so it is not knowable at entry: 627 of 979 rows score
       higher under it. Kept so the sheet reconciles with the dashboard, but
       cf is the one to trade from.
       Original note: Same rule refresh.py/ds_confluence uses, so the
       sheet and the dashboard agree: reference set is 1D/2D/3D/5D/8D, giving
       0-4. Not every reference chart is emitted as rows here; 8D is reference
       only.
  liqd days until price first fell -30% from entry at all, even long after the
       high; informational only -- held long enough almost everything prints one.
"""
import sys, json, datetime as dt
sys.path.insert(0, '/home/claude/ctzb-data')
import engine as E_, regimes as R

CHARTS = [("ETH","1D"),("ETH","2D"),("ETH","3D"),("ETH","5D"),("BTC","1D"),("BTC","2D")]
REF_TFS = ["1D","2D","3D","5D","8D"]   # agreement is scored against all of these
AGREE_DAYS = 10                        # matches refresh.py
LIQ = 0.30
KEYS = ["ch","d","px","bk","tg","u60","u90","umx","dmx","h60","hmx","dead","d60","cf","cfs","liqd"]

def r1(x): return None if x is None else round(x*100, 1)

def main():
    reg = R.rsi_regime('data/BTC_2D.csv', 8, 13, 60, 41)
    # entry dates on every reference chart, for the agreement count
    ref = {}
    for sym in sorted({s for s, _ in CHARTS}):
        for tf in REF_TFS:
            try:
                sg, bb = E_.signals(f'data/{sym}_{tf}.csv', regime=reg)
            except SystemExit:
                continue
            except FileNotFoundError:
                continue
            ref[(sym, tf)] = sorted(bb['date'][s['ei']] for s in sg)
    def agree(sym, tf, d0):
        """(backward-only, symmetric). Backward is what you could know."""
        back = sym_ = 0
        for t in REF_TFS:
            if t == tf: continue
            ds = ref.get((sym, t)) or []
            if any(-AGREE_DAYS <= (x - d0).days <= 0 for x in ds): back += 1
            if any(abs((x - d0).days) <= AGREE_DAYS for x in ds):   sym_ += 1
        return back, sym_
    rows = []
    for sym, tf in CHARTS:
        name = f"{sym} {tf}"
        path = f"data/{sym}_{tf}.csv"
        sigs, b = E_.signals(path, regime=reg)
        c, hi, lo, dates = b['close'], b['high'], b['low'], b['date']
        n, last = len(c), b['date'][-1]
        for s in sigs:
            ei, e, d0 = s['ei'], c[s['ei']], dates[s['ei']]
            # bounded horizons
            def horizon(days):
                w = [j for j in range(ei+1, n) if dates[j] <= d0+dt.timedelta(days=days)]
                if not w or last < d0+dt.timedelta(days=days): return None, None, None
                pk = max(w, key=lambda j: hi[j])
                heat = min(lo[j] for j in range(ei+1, pk+1))/e - 1 if pk > ei else 0.0
                return hi[pk]/e - 1, heat, (dates[pk]-d0).days
            u60, h60, d60 = horizon(60)
            u90, _, _     = horizon(90)
            # unbounded, but dead the moment it touches the wipeout distance
            umx, dmx, hmx, liqd, run = 0.0, 0, 0.0, None, 0.0
            for j in range(ei+1, n):
                if (dates[j]-d0).days > 365: break
                if lo[j]/e - 1 <= -LIQ:
                    liqd = (dates[j]-d0).days
                    break
                run = min(run, lo[j]/e - 1)
                if hi[j]/e - 1 > umx:
                    umx, dmx, hmx = hi[j]/e - 1, (dates[j]-d0).days, run
            # did it kill the position before giving back even +5%?
            dead, seen5 = None, False
            for j in range(ei+1, n):
                if hi[j]/e - 1 >= 0.05: seen5 = True; break
                if lo[j]/e - 1 <= -LIQ: dead = (dates[j]-d0).days; break
            tags = []
            if s['dis']:
                tags.append("dia")
                if not s['strong']: tags.append("hollow")
            if s['prime']: tags.append("dot")
            rows.append([name, str(d0), round(e, 2), s['bk'], " ".join(tags),
                         r1(u60), r1(u90), r1(umx), dmx, r1(h60), r1(hmx), dead, d60,
                         *agree(sym, tf, d0), liqd])
    rows.sort(key=lambda r: r[1])
    json.dump({"keys": KEYS, "rows": rows, "liq": LIQ,
               "gate": "rsi_regime(BTC_2D,8,13,60,41)", "built": str(dt.date.today())},
              sys.stdout, separators=(",", ":"))

if __name__ == "__main__":
    main()
