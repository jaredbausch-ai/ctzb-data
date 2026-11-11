#!/usr/bin/env python3
"""Build cloudflare/ctzb-site-worker.js from the member site page and the template.

The page source is docs/artifacts/member-site/index.html, the same file published for
review as a claude.ai artifact (whose skeleton adds the document head; this script adds
an equivalent one). The chart view's worked example is embedded too. Both go in as JSON
string literals. Run after editing the page or cloudflare/site_worker_template.js.
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs/artifacts/member-site")
page = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
example = open(os.path.join(SITE, "data/example_ETH-2D-2024-09-22.json"), encoding="utf-8").read()
tpl = open(os.path.join(ROOT, "cloudflare/site_worker_template.js"), encoding="utf-8").read()

doc = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
       "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
       "<meta name=\"robots\" content=\"noindex,nofollow\">"
       "<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>"
       "</head><body>" + page + "</body></html>")
json.loads(example)  # must be valid JSON
for ph in ("__PAGE__", "__EXAMPLE__"):
    assert tpl.count(ph) == 1, ph
out = tpl.replace("__PAGE__", json.dumps(doc, ensure_ascii=False)).replace("__EXAMPLE__", json.dumps(example))
dst = os.path.join(ROOT, "cloudflare/ctzb-site-worker.js")
open(dst, "w", encoding="utf-8").write(out)
print(f"wrote {os.path.relpath(dst, ROOT)}: {len(out.encode('utf-8')):,} bytes (page {len(page):,})")
