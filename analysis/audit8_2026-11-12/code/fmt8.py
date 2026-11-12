import datetime as dt
from fractions import Fraction as F
from lib8 import rhaz
MINUS = '−'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']


def num(v, d=1):
    if v is None: return 'n/a'
    s = rhaz(F(v), d)
    if s == 0: return f'{0:.{d}f}'
    txt = f'{abs(s):.{d}f}'
    return (MINUS if s < 0 else '') + txt


def pct(v, d=1, sign=True):
    if v is None: return 'n/a'
    s = rhaz(F(v), d)
    return ('+' if sign and s > 0 else '') + num(v, d) + '%'


def money(v):
    if v is None: return 'n/a'
    s = rhaz(F(v), 2)
    return '$' + f'{s:,.2f}'


def dlong(d):
    if isinstance(d, str): d = dt.date.fromisoformat(d[:10])
    return f'{d.day} {MON[d.month - 1]} {d.year}'


def dshort(d):
    return f'{d.day:02d} {MON[d.month - 1]}'
