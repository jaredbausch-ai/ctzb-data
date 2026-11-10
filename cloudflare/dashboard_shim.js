/* Stand-in for the Dashboard artifact type's `dash` runtime, so the ETH Setup Standard
 * page (docs/artifacts/eth-setup-standard.html) runs unchanged on Cloudflare.
 *
 * The page uses exactly three calls -- dash.data(name), dash.onData(fn), dash.calc(name,
 * {inputs, fn}) -- plus cells bound with data-source / data-field / data-where. Datasets
 * are the pipeline's CSVs, read same-origin from /data/datasets/<name>.csv, which the
 * Worker serves from the mirror. Values stay strings, as the CSVs are; the page already
 * coerces with + where it needs numbers.
 *
 * Reloads every 5 minutes and when the tab comes back into view. A failed fetch keeps
 * the last good copy; the page's own DATA DELAYED banner (from status.csv) covers age.
 */
(function () {
  "use strict";
  var SOURCES = ["status", "grades", "live", "forward", "dipdist", "cards", "liveread", "prints", "windows"];
  var store = {}, calcs = {}, subs = [], loading = false;
  SOURCES.forEach(function (n) { store[n] = { status: "loading", data: [] }; });

  function parseCSV(text) {
    var rows = [], row = [], f = "", q = false, i = 0, c;
    text = text.replace(/^﻿/, "");
    for (; i < text.length; i++) {
      c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; }
        else f += c;
      } else if (c === '"') q = true;
      else if (c === ",") { row.push(f); f = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(f); f = ""; rows.push(row); row = [];
      } else f += c;
    }
    if (f !== "" || row.length) { row.push(f); rows.push(row); }
    rows = rows.filter(function (r) { return !(r.length === 1 && r[0] === ""); });
    if (!rows.length) return [];
    var head = rows.shift();
    return rows.map(function (r) {
      var o = {}; head.forEach(function (h, j) { o[h] = r[j] === undefined ? "" : r[j]; }); return o;
    });
  }

  function bind() {
    var els = document.querySelectorAll("[data-source][data-field]");
    Array.prototype.forEach.call(els, function (el) {
      if (el.closest("table")) return;            // tables are filled by the page's own code
      var src = store[el.getAttribute("data-source")];
      if (!src || src.status !== "ok") return;
      var where = new URLSearchParams(el.getAttribute("data-where") || "");
      var row = src.data.find(function (r) {
        var ok = true; where.forEach(function (v, k) { if (String(r[k]) !== v) ok = false; }); return ok;
      });
      var v = row ? row[el.getAttribute("data-field")] : undefined;
      el.textContent = (v === undefined || v === "") ? "—" : String(v);
    });
  }

  function load() {
    if (loading) return; loading = true;
    Promise.all(SOURCES.map(function (n) {
      return fetch("/data/datasets/" + n + ".csv", { cache: "no-store", credentials: "same-origin" })
        .then(function (r) { if (!r.ok) throw new Error(n + " " + r.status); return r.text(); })
        .then(function (t) { store[n] = { status: "ok", data: parseCSV(t) }; })
        .catch(function (e) {
          if (store[n].status !== "ok") store[n] = { status: "error", data: [] };
          if (window.console) console.warn("dataset", e && e.message);
        });
    })).then(function () {
      Object.keys(calcs).forEach(function (n) {
        var c = calcs[n], ins = c.inputs.map(function (i) { return store[i]; });
        if (ins.every(function (x) { return x && x.status === "ok"; })) {
          try { store[n] = { status: "ok", data: c.fn.apply(null, ins.map(function (x) { return x.data; })) }; }
          catch (e) { store[n] = { status: "error", data: [] }; }
        }
      });
      bind();
      subs.forEach(function (f) { try { f(); } catch (e) { if (window.console) console.error(e); } });
    }).then(function () { loading = false; }, function () { loading = false; });
  }

  window.dash = {
    data: function (n) { return store[n] || { status: "error", data: [] }; },
    onData: function (f) { subs.push(f); },
    calc: function (n, c) { calcs[n] = c; store[n] = { status: "loading", data: [] }; }
  };
  document.addEventListener("DOMContentLoaded", load);
  setInterval(load, 5 * 60 * 1000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) load(); });
})();
