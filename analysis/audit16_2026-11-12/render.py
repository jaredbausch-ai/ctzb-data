"""Render the member page with Playwright and dump everything a member can read, per selectable setup and tab."""
import csv, json, os, sys, datetime as dt
from playwright.sync_api import sync_playwright

JS_CARD = r"""
() => {
  const T = (e) => e ? e.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const card = q('#card');
  const out = { text: T(card), frameColor: q('#cardFrame').style.getPropertyValue('--c') };
  out.head = qa('.card-head > *', card).map(T);
  out.stateAttr = (q('.card-head .state', card) || {}).dataset ? q('.card-head .state', card).dataset.state || null : null;
  out.stale = T(q('.stale-note', card));
  out.odds = qa('.odds > *', card).map(T);
  out.bigOpacity = q('.odds .big', card) ? q('.odds .big', card).style.opacity : null;
  out.stats = qa('.stats > *', card).map((e) => e.classList.contains('kv') ? Array.from(e.children).map(T) : [T(e)]);
  out.marker = T(q('.marker', card));
  out.tiles = qa('.tiles .tile', card).map((e) => [T(q('.t', e)), T(q('.v', e))]);
  out.boxLabels = qa('.boxes .lbl', card).map(T);
  out.ladder = qa('#ladder .bar', card).map((e) => ({ label: T(e.children[0]), width: q('.f', e).style.width, gone: q('.f', e).classList.contains('gone'), val: T(e.children[2]) }));
  out.ladderFine = T(q('#ladder .fine', card));
  out.eras = qa('#eras .bar', card).map((e) => ({ label: T(e.children[0]), width: q('.f', e).style.width, val: T(e.children[2]) }));
  out.erasFine = qa('.box.teal .fine', card).map(T);
  out.foot = T(q('.card-foot', card));
  out.empty = T(q('.empty-card', card));
  out.picker = qa('#picker button').map((b) => ({ sel: b.dataset.sel, cls: b.className, pressed: b.getAttribute('aria-pressed'), text: T(b) }));
  out.pickerText = T(q('#picker'));
  out.pnone = qa('#picker .pnone').map(T);
  return out;
}"""
JS_PAGE = r"""
() => {
  const T = (e) => e ? e.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  return { review: T(q('#review')), rvAsof: T(q('#rvAsof')), filter: T(q('#filterText')), filterOff: q('#filterPill').classList.contains('off'), feedState: T(q('#feedState')), foot: T(q('footer.foot')),
    lead: T(q('section.lead')), leadBody: T(q('#leadBody')),
    prevIntact: qa('#prevIntact > *').map((e) => ({ cls: e.className, name: T(q('.name', e)), sub: T(q('.sub', e)), badge: T(q('.badge', e)), badgeCls: q('.badge', e) ? q('.badge', e).className : null, text: T(e) })),
    prevClosed: qa('#prevClosed > *').map((e) => ({ cls: e.className, name: T(q('.name', e)), sub: T(q('.sub', e)), badge: T(q('.badge', e)), badgeCls: q('.badge', e) ? q('.badge', e).className : null, text: T(e) })),
    prevText: T(q('section.prev')), howBar: T(q('#howBar')), previewChecked: q('#previewSwitch').checked };
}"""
JS_CHART = r"""
() => {
  const T = (e) => e ? e.textContent.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  const dump = (svg) => Array.from(svg.children).map((e) => { const o = { tag: e.tagName, text: e.tagName === 'text' ? e.textContent : undefined };
    for (const a of e.attributes) o[a.name] = a.value; o.fill2 = e.style.getPropertyValue('fill'); o.stroke2 = e.style.getPropertyValue('stroke'); return o; });
  return { title: T(q('#chTitle')), sub: T(q('#chSub')), toggleHidden: q('.toggle').hidden, alertPressed: q('#bAlert').getAttribute('aria-pressed'), hapPressed: q('#bHap').getAttribute('aria-pressed'),
    svg: dump(q('#chartSvg')), cloud: dump(q('#cloudSvg')), cloudSub: T(q('#cloudSub')), cloudNote: T(q('#cloudNote')),
    side: qa('#chartSide > *').map((b) => ({ text: b.innerText.replace(/\s+/g, ' ').trim(), kv: qa('.kv', b).map((k) => Array.from(k.children).map((c) => c.innerText.replace(/\s+/g, ' ').trim())), fine: qa('.fine', b).map((c) => c.innerText.replace(/\s+/g, ' ').trim()),
       big: qa('div', b).filter((d) => d.style.fontSize === '42px').map((d) => d.innerText.trim()), small: qa('.small', b).map((c) => c.innerText.replace(/\s+/g, ' ').trim()) })),
    sideText: q('#chartSide').innerText.replace(/\s+/g, ' ').trim() };
}"""
JS_REC = r"""
() => {
  const T = (e) => e ? e.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = (s, r = document) => r.querySelector(s), qa = (s, r = document) => Array.from(r.querySelectorAll(s));
  return { count: T(q('#recCount')), head: qa('#view-record thead th').map(T), title: T(q('#view-record .sec-title')), fine: T(q('#view-record p.fine')),
    sum: qa('#recSum .sidebox').map((b) => qa('.kv', b).map((k) => Array.from(k.children).map(T))),
    rows: qa('#recBody tr').map((tr) => Array.from(tr.children).map((td) => td.innerText.trim())),
    badges: qa('#recBody tr').map((tr) => qa('.badge', tr).map((b) => b.className)), pressed: qa('.seg button').map((b) => [b.dataset.asset, b.getAttribute('aria-pressed')]) };
}"""


def candles_json(root, a, tf):
    p = f"{root}/datasets/candles_{a.lower()}_{tf.lower()}.csv"
    if not os.path.exists(p): return None
    return json.dumps({"chart": f"{a} {tf}", "bars": [{"t": float(r["time"]), "o": float(r["open"]), "h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"])} for r in csv.DictReader(open(p))]})


def render(root, feed="file", clock_offset_min=6, only_now=False, ledger="file", trades=None, example="file", width=1440, height=900, feed_status=503):
    page_src = open(f"{root}/docs/artifacts/member-site/index.html", encoding="utf-8").read()
    doc = "<!doctype html><html><head><meta charset=utf-8></head><body>" + page_src + "</body></html>"
    if feed == "file": feed = json.load(open(f"{root}/feed/ctzb_feed.json"))
    led = open(f"{root}/datasets/ledger.csv").read() if ledger == "file" else ledger
    ex = open(f"{root}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json").read() if example == "file" else example
    reqs = []
    out = {"errors": [], "console": []}
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": width, "height": height})
        pg.on("pageerror", lambda e: out["errors"].append(str(e)))
        pg.on("console", lambda m: out["console"].append(m.text) if m.type == "error" else None)
        def h(route):
            u = route.request.url; reqs.append(u)
            if u == "http://site.test/" or u.startswith("http://site.test/#"): return route.fulfill(body=doc, content_type="text/html")
            if "fonts" in u: return route.abort()
            if u.endswith("data/ctzb_feed.json"):
                return route.fulfill(body=json.dumps(feed), content_type="application/json") if feed is not None else route.fulfill(status=feed_status, body="x")
            if u.endswith("data/ledger.csv"): return route.fulfill(body=led, content_type="text/csv") if led is not None else route.fulfill(status=404, body="x")
            if u.endswith("data/trades.json") and trades is not None: return route.fulfill(body=json.dumps(trades), content_type="application/json")
            if "data/example_ETH-2D-2024-09-22.json" in u: return route.fulfill(body=ex, content_type="application/json") if ex is not None else route.fulfill(status=404, body="x")
            if "/data/candles/" in u:
                a, tf = u.rsplit("/", 1)[1][:-5].split("_"); c = candles_json(root, a, tf) if tf in ("1D", "2D", "3D", "5D", "8D") and a in ("ETH", "BTC") else None
                return route.fulfill(body=c, content_type="application/json") if c else route.fulfill(status=404, body="x")
            return route.fulfill(status=404, body="x")
        pg.route("**/*", h)
        if feed is not None and feed.get("generated_at"):
            t = dt.datetime.fromisoformat(feed["generated_at"].replace("Z", "+00:00")) + dt.timedelta(minutes=clock_offset_min)
            pg.clock.install(time=t)
        pg.goto("http://site.test/#now"); pg.wait_for_timeout(1200)
        out["page"] = pg.evaluate(JS_PAGE)
        out["initial"] = pg.evaluate(JS_CARD)
        out["bodyNow"] = pg.inner_text("body")
        sels = [x["sel"] for x in out["initial"]["picker"]]
        out["sel"] = {}
        for sel in sels:
            pg.evaluate("(v) => { location.hash = '#now'; }", "now"); pg.wait_for_timeout(150)
            pg.click(f'#picker button[data-sel="{sel}"]'); pg.wait_for_timeout(300)
            d = {"card": pg.evaluate(JS_CARD)}
            if not only_now:
                pg.click("#tab-chart"); pg.wait_for_timeout(700)
                d["chart"] = pg.evaluate(JS_CHART)
                if not d["chart"]["toggleHidden"]:
                    pg.click("#bHap"); pg.wait_for_timeout(500)
                    d["chart_happened"] = pg.evaluate(JS_CHART)
                    pg.click("#bAlert"); pg.wait_for_timeout(400)
                    d["chart_alert_again"] = pg.evaluate(JS_CHART)
                pg.click("#tab-now"); pg.wait_for_timeout(200)
            out["sel"][sel] = d
        pg.evaluate("() => { location.hash = '#now'; }"); pg.wait_for_timeout(200)
        if pg.is_checked("#previewSwitch"): pg.click("#previewSwitch"); pg.wait_for_timeout(300)
        out["switch_off"] = pg.evaluate(JS_CARD)
        if not only_now:
            pg.click("#tab-chart"); pg.wait_for_timeout(500)
            out["switch_off_chart"] = pg.evaluate(JS_CHART)
            pg.click("#tab-record"); pg.wait_for_timeout(500)
            out["record"] = {}
            for a in ("all", "ETH", "BTC"):
                pg.click(f'.seg button[data-asset="{a}"]'); pg.wait_for_timeout(300)
                out["record"][a] = pg.evaluate(JS_REC)
            pg.click("#tab-read"); pg.wait_for_timeout(300)
            out["read"] = pg.inner_text("#view-read")
            out["bodyRead"] = pg.inner_text("body")
        out["requests"] = sorted(set(reqs))
        b.close()
    return out


if __name__ == "__main__":
    root, dest = sys.argv[1], sys.argv[2]
    r = render(root)
    json.dump(r, open(dest, "w"))
    print(dest, "errors", r["errors"], "console", r["console"][:3], "selectable", list(r["sel"]))
