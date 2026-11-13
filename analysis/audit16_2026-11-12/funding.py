"""My own reading of the funding availability rule that decides ETH ledger membership (docs: 'ETH samples start
once funding data and its 90-day median exist')."""
import csv, datetime as dt, os


def load(root, a):
    wt, mean = {}, {}
    for r in csv.DictReader(open(os.path.join(root, 'data', 'derivs', f'{a}_funding_daily.csv'))):
        d = dt.date.fromisoformat(r['date'])
        v = r.get('funding_oi_weighted') or r.get('funding_mean')
        if v not in ('', None): wt[d] = float(v)
        if r.get('funding_mean') not in ('', None): mean[d] = float(r['funding_mean'])
    return wt, mean


def has_median(wt, d):
    if d not in wt: return False
    return sum(1 for k in range(1, 91) if d - dt.timedelta(days=k) in wt) >= 60


def has_cooling(mean, d):
    a = sum(1 for k in range(7) if d - dt.timedelta(days=k) in mean)
    b = sum(1 for k in range(7) if d - dt.timedelta(days=14 + k) in mean)
    return a >= 5 and b >= 5
