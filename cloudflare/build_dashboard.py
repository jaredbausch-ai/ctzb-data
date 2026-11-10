#!/usr/bin/env python3
"""Build cloudflare/ctzb-dashboard-worker.js from the page and the runtime shim.

The page source stays docs/artifacts/eth-setup-standard.html (byte-identical to the
claude.ai artifact's files/index.html, v38, on 10 Nov 2026). This wraps it in a full
document, puts the `dash` shim ahead of the page's own script, and embeds the result
in the Worker as a JSON string literal (which escapes everything a template literal
would not). Run after editing the page, the shim or the template.
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
page = open(os.path.join(ROOT, "docs/artifacts/eth-setup-standard.html"), encoding="utf-8").read()
shim = open(os.path.join(ROOT, "cloudflare/dashboard_shim.js"), encoding="utf-8").read()
tpl = open(os.path.join(ROOT, "cloudflare/dashboard_worker_template.js"), encoding="utf-8").read()

doc = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
       "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
       "<meta name=\"robots\" content=\"noindex,nofollow\">"
       "<title>ETH Setup Standard</title>"
       "<style>html,body{margin:0;background:#07090C}</style>"
       "<script>" + shim + "</script></head><body>" + page + "</body></html>")
assert tpl.count("__PAGE__") == 1
out = tpl.replace("__PAGE__", json.dumps(doc, ensure_ascii=False))
dst = os.path.join(ROOT, "cloudflare/ctzb-dashboard-worker.js")
open(dst, "w", encoding="utf-8").write(out)
print(f"wrote {os.path.relpath(dst, ROOT)}: {len(out):,} bytes (page {len(page):,}, shim {len(shim):,})")
