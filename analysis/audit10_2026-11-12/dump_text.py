import sys, json, datetime as dt
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]
src = open('page_audit.py').read().split('# ---------------------------------------------------------------- run')[0]
exec(compile(src, 'pa', 'exec'))
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(); page = br.new_page(viewport={'width': 1500, 'height': 1000})
    page.route('**/*', route)
    gen = dt.datetime.fromisoformat(FEED['generated_at'].replace('Z', '+00:00')); page.clock.install(time=gen + dt.timedelta(minutes=6))
    page.goto('http://site.test/'); page.wait_for_timeout(1200)
    print(page.evaluate('document.querySelector("#view-now").innerText'))
    page.click('#picker button[data-sel="BTC-2D-2026-09-21"]'); page.wait_for_timeout(300)
    print('=====OPEN'); print(page.evaluate('document.querySelector("#card").innerText'))
    page.click('#tab-chart'); page.wait_for_timeout(800)
    print('=====CHART'); print(page.evaluate('document.querySelector("#view-chart").innerText'))
    print([t for t in page.evaluate('Array.from(document.querySelectorAll("#chartSvg text")).map(e=>e.textContent)')])
    page.screenshot(path=f'shot_{LABEL}_chart_open.png')
    br.close()
