import sys, json, datetime as dt
sys.path.insert(0,'.')
import pagelib as PL
from playwright.sync_api import sync_playwright
root, sel = sys.argv[1], sys.argv[2]
feed=json.load(open(root+'/feed/ctzb_feed.json'))
at=(dt.datetime.fromisoformat(feed['generated_at'].replace('Z','+00:00'))+dt.timedelta(minutes=6)).isoformat()
with sync_playwright() as pw:
    br=pw.chromium.launch(); site=PL.Site(root); page=site.open(br, at)
    if sel!='default': page.click(f'#picker .pick[data-sel="{sel}"]'); page.wait_for_timeout(100)
    print(page.evaluate("document.querySelector('.app').innerText"))
    page.click('#tab-chart'); page.wait_for_timeout(300)
    print('=====CHART'); print(page.evaluate("document.querySelector('#view-chart').innerText")); print('SVG:', ' || '.join(page.evaluate("Array.from(document.querySelectorAll('#chartSvg text')).map(t=>t.textContent)")))
    br.close()
