"""Audit 15 -- page test: a live setup whose confirmation bar is a year's short last bar (2D bar of 31 Dec 2023 alone).
Replay state 2024-01-01; the ETH 2D signal confirmed 2023-12-31 is graded A there, so it is only shown if marked top grade:
the grade is changed in a COPY of the feed to see how the chart places its entry (page logic only)."""
import json, copy, csv
from harness import Site, norm_ws
from core import Checks
S = 'states/d2024-01-01'; C = Checks('replay 2024-01-01 (synthetic: ETH 2D 2023-12-31 shown as top grade)')
feed = json.load(open(f'{S}/feed/ctzb_feed.json'))
o = next(x for x in feed['open_signals'] if x['signal_id'] == 'ETH-2D-2023-12-31'); print(o['grade'], o['entry_date'], o['days_elapsed']); o['grade'] = 'A+'
st = Site(S, feed_override=feed); st.click('#picker button[data-sel="ETH-2D-2023-12-31"]'); st.click('#tab-chart'); st.page.wait_for_timeout(400)
txt = [e['text'] for e in st.svg('#chartSvg') if e['tag'] == 'text']
C.add('page chart, live setup confirmed on the short year-end bar', 'chart draws the setup (an Entry line on the 31 Dec 2023 bar)', ' | '.join(txt)[:200], 'Entry line on the bar of 31 Dec 2023',
      'the page finds the entry bar by bar open + (bar length - 1) days; the 2D bar of 31 Dec is one day long, so no bar matches')
print(C.rows); st.close()
csv.writer(open('checks_pagey.csv', 'w', newline='')).writerows(C.rows)
