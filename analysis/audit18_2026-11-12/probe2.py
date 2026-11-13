import json, sys
from playwright.sync_api import sync_playwright
import page_lib as P
root, sel = sys.argv[1], sys.argv[2]
with sync_playwright() as pw:
    s = P.Site(pw, root); s.open('now')
    if sel != '-': s.select(sel)
    d = s.dump(); print(d['card']['all']); print('PICKER', json.dumps(d['picker'], ensure_ascii=False)[:1500]); print('FILTER', d['filter'], '|', d['review'][:90])
    print('PREV', [x['text'] for x in d['prevIntact']], [x['text'] for x in d['prevClosed']])
    s.show('chart'); s.pg.wait_for_timeout(300); d = s.dump()
    print('CHART', d['chart']['title'], '|', d['chart']['sub']); print([t['text'] for t in d['chart']['svg'] if t['tag']=='text'])
    print([x['text'] for x in d['chart']['side']]); print(d['chart']['cloudSub'], '|', d['chart']['cloudNote'])
    print('errs', s.errs[:3]); s.close()
