"""Five hand-forged feeds whose fields are each valid but contradict each other (audit round 48's hardening list).

Each takes a copy of a real feed and returns it forged. Shared by tests/test_feed_contradictions.py (the pipeline's
feedcheck.py) and tests/test_page_states.py (the member page's own strict check): both must reject all five.
"""
import copy


def _card(f):
    return next(c for c in f["cards"] + [o["card"] for o in f["open_signals"] if o.get("card")] if c["past_trades"] > 9)


def sample_digits(f):
    c = _card(f); c["sample"] = c["sample"].replace(str(c["past_trades"]), "1" + str(c["past_trades"]), 1); return f


def rose10_vs_median(f):
    c = _card(f); c["rose10_within60d_pct"] = 100; c["typical_biggest_rise_exact_pct"] = 3.0; return f


def two_prices(f):
    cs = f["cards"] + [o["card"] for o in f["open_signals"] if o.get("card")]
    a = next(x["asset"] for x in cs if sum(y["asset"] == x["asset"] and y.get("price_now") is not None for y in cs) > 1)
    c = [x for x in cs if x["asset"] == a and x.get("price_now") is not None][1]
    c["price_now"] = round(c["price_now"] * 1.01, 2); return f


def up_first_zero(f):
    m = next(m for m in f["if_it_misses"] if m["misses"] > 0 and (m.get("median_peak_pct") or 0) > 0)
    m["up_first"] = 0; return f


def eras_vs_share(f):
    c = next(c for c in f["cards"] + [o["card"] for o in f["open_signals"] if o.get("card")]
             if c["before_2022"]["past_trades"] > 0 and c["since_2022"]["past_trades"] > 0)
    c["before_2022"]["rose10_never_fell25_within60d_pct"] = 100; c["since_2022"]["rose10_never_fell25_within60d_pct"] = 100
    c["rose10_never_fell25_within60d_pct"] = 0; return f


FORGED = {"sample names a different count that contains n's digits": sample_digits,
          "rose 10% at 100% with a 3% median best move": rose10_vs_median,
          "two prices now for one asset": two_prices,
          "no miss went above entry, median peak above it": up_first_zero,
          "both eras at 100%, the card's share at 0%": eras_vs_share}


def forge(feed, name):
    return FORGED[name](copy.deepcopy(feed))
