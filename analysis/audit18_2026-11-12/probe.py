import json, sys
from playwright.sync_api import sync_playwright
import page_lib as P
root = sys.argv[1]
with sync_playwright() as pw:
    s = P.Site(pw, root); s.open('now')
    d = s.dump()
    json.dump(d, open(sys.argv[2], 'w'), indent=1)
    print('errs', s.errs, 'clock', s.clock)
    print(set(u for u in s.requests if 'site.test' not in u))
    s.close()
