"""Audit 15 -- extra page states: an old feed (stale note), on the CURRENT state. Usage: python3 page_extra.py <state dir> <name>"""
import sys, csv, json, datetime as dt
from harness import Site, norm_ws
from core import Checks
S, NAME = sys.argv[1], sys.argv[2]; C = Checks(NAME)
feed = json.load(open(f'{S}/feed/ctzb_feed.json'))
gen = dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
for mins, want in ((6, None), (5 * 60 - 1, None), (5 * 60 + 1, 5), (7 * 60 + 10, 7), (26 * 60 + 59, 26)):
    st = Site(S)
    st.page.clock.set_fixed_time(gen + dt.timedelta(minutes=mins)); st.page.reload()
    st.page.wait_for_function("document.querySelector('#feedState') && document.querySelector('#feedState').textContent.length > 0"); st.page.wait_for_timeout(300)
    t = st.text('#card .stale-note')
    C.add('page stale note', f'feed {mins} minutes old (a warning from 5 hours, whole hours rounded down)', norm_ws(t) if t else '(none)',
          f"This data is {want} hours old. The update pipeline has not refreshed it on schedule, so treat everything below as out of date until it does." if want else '(none)')
    st.close()
print([x[1:6] for x in C.rows])
csv.writer(open(f'checks_pagex_{NAME}.csv', 'w', newline='')).writerows(C.rows)
