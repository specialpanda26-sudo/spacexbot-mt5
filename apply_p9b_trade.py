"""Section 9B apply script: the chart pop-up for a closed trade.
Needs backend/tradeview.py to exist first (its own cat command). Edits 4 files, all or none:
  backend/app.py       import + GET /api/trade/<id>
  backend/pnlcard.py   every profit-curve point now carries its trade id
  static/index.html    Trades rows are tappable, the profit curve is tappable, the pop-up block (P9B), one CSS line (pointer cursor)
  docs/HANDOFF.md      9B marked DONE
Every old text must match exactly once. If anything does not fit, NOTHING is changed. Safe to run twice."""
import os, re, sys

BLOCK = r'''/*P9B-start*/
/* ---- Section 9B: the chart pop-up for one closed trade. Tap a trade in the Trades list, or a point on the profit curve (Home), and GET /api/trade/<id> says what the server really stored: the price levels, the lots, the times, the profit, and the candles it still holds. The exit PRICE is never drawn: the server does not store it, and the pop-up says so. Nothing on it is made up. ---- */
(function () {
  "use strict";
  var w = document.getElementById("sheet"), body = document.getElementById("sheetBody");
  if (!w || !body || !window.SXA) return;
  var TOK = 0;
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function num(n) { var x = Number(n); return n !== null && n !== "" && isFinite(x) ? x : null; }
  function money(n) { var x = Math.round(Number(n) * 100) / 100; if (!isFinite(x)) x = 0; return (x < 0 ? "-" : x > 0 ? "+" : "") + "$" + Math.abs(x).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function when(t) { var d = new Date(Number(t) * 1000); return t && isFinite(d) ? d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "-"; }
  function span(s) { s = Math.max(0, Math.round(Number(s) || 0)); var d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60); return d ? d + "d " + h + "h" : h ? h + "h " + m + "m" : m ? m + "m" : s + "s"; }
  function price(p, d) { return Number(p).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }); }

  function chart(d) {
    var W = 320, H = 230, L = 6, R = 78, T = 12, B = 26, lv = d.levels || {}, cn = d.candles || {}, c = cn.rows || [], dec = Number(d.dec) || 2;
    var defs = [["tp", "TP", "good"], ["entry", "Entry", "muted"], ["fill", "Fill", "muted"], ["sl", "SL", "bad"]];
    var items = defs.map(function (x) { var p = num(lv[x[0]]); return p > 0 ? { n: x[1], p: p, c: x[2] } : null; }).filter(Boolean);
    var vals = items.map(function (i) { return i.p; });
    c.forEach(function (r) { vals.push(Number(r[2]), Number(r[3])); });
    if (!vals.length) return "";
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals); if (hi === lo) { hi += 1; lo -= 1; }
    var pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    function Y(p) { return T + (H - T - B) * (hi - p) / (hi - lo); }
    var n = c.length, step = n ? (W - L - R) / n : 0, s = "";
    c.forEach(function (r, i) {
      var x = L + step * (i + 0.5), up = Number(r[4]) >= Number(r[1]), col = "var(" + (up ? "--good" : "--bad") + ")", bw = Math.max(1, step * 0.6);
      var y1 = Y(Math.max(Number(r[1]), Number(r[4]))), y2 = Y(Math.min(Number(r[1]), Number(r[4])));
      s += '<line x1="' + x.toFixed(1) + '" x2="' + x.toFixed(1) + '" y1="' + Y(Number(r[2])).toFixed(1) + '" y2="' + Y(Number(r[3])).toFixed(1) + '" stroke-width="1" style="stroke:' + col + '"/>' +
        '<rect x="' + (x - bw / 2).toFixed(1) + '" y="' + y1.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(1, y2 - y1).toFixed(1) + '" style="fill:' + col + '"/>';
    });
    var lab = items.map(function (i) { return { y: Y(i.p), i: i }; }).sort(function (a, b) { return a.y - b.y; }), prev = -99;
    lab.forEach(function (o) { o.ly = Math.max(o.y, prev + 12); prev = o.ly; });
    lab.forEach(function (o) {
      var col = "var(--" + o.i.c + ")";
      s += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + o.y.toFixed(1) + '" y2="' + o.y.toFixed(1) + '" stroke-width="1.5" stroke-dasharray="5 4" style="stroke:' + col + '"/>' +
        '<text x="' + (W - R + 5) + '" y="' + (o.ly + 3.5).toFixed(1) + '" font-size="10" font-weight="700" style="fill:' + col + '">' + o.i.n + " " + esc(price(o.i.p, dec)) + "</text>";
    });
    if (n && cn.secs) {
      var t0 = Number(c[0][0]);
      [[d.opened, "Opened", "end"], [d.closed, "Closed", "start"]].forEach(function (m) {
        var i = (Number(m[0]) - t0) / Number(cn.secs); if (!(i >= 0 && i <= n)) return;
        var x = L + step * i;
        s += '<line x1="' + x.toFixed(1) + '" x2="' + x.toFixed(1) + '" y1="' + T + '" y2="' + (H - B) + '" stroke-width="1.5" stroke-dasharray="2 3" style="stroke:var(--muted)"/>' +
          '<text x="' + (x + (m[2] === "end" ? -3 : 3)).toFixed(1) + '" y="' + (H - 10) + '" font-size="10" font-weight="700" text-anchor="' + m[2] + '" style="fill:var(--muted)">' + m[1] + "</text>";
      });
    }
    return '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Trade chart">' + s + "</svg>";
  }

  function render(d) {
    var buy = d.side === "buy", win = Number(d.pnl) > 0, lv = d.levels || {}, cn = d.candles || {}, dec = Number(d.dec) || 2, rows = [];
    [["tp", "Take profit"], ["entry", "Planned entry"], ["fill", "Filled at"], ["sl", "Stop loss"]].forEach(function (x) { var p = num(lv[x[0]]); if (p > 0) rows.push("<dt>" + x[1] + '</dt><dd class="num">' + esc(price(p, dec)) + "</dd>"); });
    if (num(d.lots) > 0) rows.push('<dt>Lots</dt><dd class="num">' + esc(String(d.lots)) + "</dd>");
    rows.push("<dt>Opened</dt><dd>" + esc(when(d.opened)) + "</dd><dt>Closed</dt><dd>" + esc(when(d.closed)) + "</dd><dt>Held for</dt><dd>" + esc(span(d.closed - d.opened)) + "</dd>");
    if (d.strategy_name) rows.push("<dt>Strategy</dt><dd>" + esc(d.strategy_name) + "</dd>");
    rows.push("<dt>Broker</dt><dd>" + esc(d.broker || "-") + "</dd>");
    var notes = [], ch = chart(d);
    notes.push((d.exit && d.exit.note) || "The exit price and the reason this trade closed are not recorded.");
    if (!(cn.rows && cn.rows.length)) notes.push("The server no longer holds the candles for this trade (they are kept in memory only), so only the price levels are drawn.");
    else if (!cn.covers_open || !cn.covers_close) notes.push("The server holds only some of the candles around this trade.");
    if (!(num(lv.fill) > 0)) notes.push("No fill price was recorded, so Entry is the planned price.");
    return '<div class="grab"></div><div class="card-head"><h2 id="shTitle" style="font-size:26px">' + esc(d.symbol) + '</h2><span class="chip ' + (buy ? "ok" : "stop") + '">' + (buy ? "Buy" : "Sell") + "</span></div>" +
      '<div class="pmeta"><b class="num ' + (win ? "good" : "bad") + '" style="font-size:30px">' + esc(money(d.pnl)) + '</b><span class="note">closed ' + esc(when(d.closed)) + "</span></div>" +
      (ch ? '<div class="chart" style="min-height:0">' + ch + "</div>" : "") + '<dl class="kv">' + rows.join("") + "</dl>" +
      notes.map(function (t) { return '<p class="note">' + esc(t) + "</p>"; }).join("") + '<button class="btn block" data-close="1">Close</button>';
  }

  function show(html) {
    body.innerHTML = html;
    try { lastFocus = document.activeElement; } catch (e) { }
    w.hidden = false;
    requestAnimationFrame(function () { requestAnimationFrame(function () { w.classList.add("open"); }); });
  }
  function open(id) {
    var me = ++TOK;
    show('<div class="grab"></div><div class="card-head"><h2 id="shTitle" style="font-size:26px">Trade</h2></div><p class="note">Loading this trade...</p><button class="btn block" data-close="1">Close</button>');
    SXA.api("/api/trade/" + encodeURIComponent(id), { method: "GET" }).then(function (d) {
      if (me === TOK) body.innerHTML = render(d);
    }, function (e) {
      if (me !== TOK) return;
      body.innerHTML = '<div class="grab"></div><div class="card-head"><h2 id="shTitle" style="font-size:26px">Trade</h2></div><p class="note">' + esc(e && e.status === 404 ? "This trade is not available any more." : "Cannot load this trade. Check your internet and try again.") + '</p><button class="btn block" data-close="1">Close</button>';
    });
  }
  window.SXT = { open: open };
  function target(e) { var t = e.target && e.target.closest ? e.target.closest("[data-tid]") : null, id = t ? parseInt(t.getAttribute("data-tid"), 10) : 0; return id > 0 ? id : 0; }
  document.addEventListener("click", function (e) { var id = target(e); if (id) open(id); });
  document.addEventListener("keydown", function (e) { if (e.key !== "Enter" && e.key !== " ") return; var id = target(e); if (id) { e.preventDefault(); open(id); } });
})();
/*P9B-end*/
'''

TAP = r'''  function tapCurve(e) {     /* a tap on the curve opens the nearest trade (the curve is drawn 300 wide with 8 padding; point 0 is the start, 1..n are the trades) */
    try {
      var sv = e.target && e.target.closest ? e.target.closest("svg") : null;
      if (!sv || !sv.getBoundingClientRect || !D || !D.curve || !D.curve.length || !window.SXT) return;
      var r = sv.getBoundingClientRect(), n = D.curve.length; if (!r.width) return;
      var i = Math.max(1, Math.min(n, Math.round(((e.clientX - r.left) / r.width * 300 - 8) / 284 * n))), p = D.curve[i - 1];
      if (p && p.id > 0) window.SXT.open(p.id);
    } catch (err) { }
  }
  C.addEventListener("click", function (e) {
    var b = e.target && e.target.closest ? e.target.closest("[data-pb]") : null;
    if (!b) { tapCurve(e); return; }
    WANT = b.getAttribute("data-pb") || ""; poll();
  });'''

ROUTE = r'''

@app.get('/api/trade/<int:tid>')
@need(verified=True)
def trade_api(u, tid):
    """Section 9B: one of the person's own closed trades with the prices the server really stored and the candles it still holds (the pop-up chart)."""
    d = tradeview.detail(u['uid'], bool(u['admin']), tid)
    return (jsonify(d), 200) if d else (jsonify(error='trade not found'), 404)'''

CLICK_OLD = """  C.addEventListener("click", function (e) {
    var b = e.target && e.target.closest ? e.target.closest("[data-pb]") : null; if (!b) return;
    WANT = b.getAttribute("data-pb") || ""; poll();
  });"""

# (file, old text, new text, marker that is only there once applied)
EDITS = [
    ('backend/app.py', ', bridge, pnlcard\n', ', bridge, pnlcard, tradeview\n', 'pnlcard, tradeview'),
    ('backend/app.py', "    return jsonify(pnlcard.snapshot(u['uid'], bool(u['admin']), request.args.get('broker', '')))",
     "    return jsonify(pnlcard.snapshot(u['uid'], bool(u['admin']), request.args.get('broker', '')))" + ROUTE, '/api/trade/<int:tid>'),
    ('backend/pnlcard.py', "pts.append({'t': r['t'], 'v': round(run, 2)})", "pts.append({'t': r['t'], 'v': round(run, 2), 'id': r['id']})", "'id': r['id']})"),
    ('static/index.html', '.grab{width:44px;height:5px;border-radius:99px;background:var(--line);justify-self:center}\n',
     '.grab{width:44px;height:5px;border-radius:99px;background:var(--line);justify-self:center}\n#tList .row[data-tid]{cursor:pointer}#tList .row[data-tid]:focus-visible{outline:2px solid var(--line);outline-offset:2px}#pnlc .chart svg{cursor:pointer}\n', '#tList .row[data-tid]{cursor:pointer}'),
    ('static/index.html', """return '<li class="row"><span class="ic '+(up?"up":"dn")+'">'+(up?ICON_UP:ICON_DN)""",
     """return '<li class="row" data-tid="'+(Number(t.id)||0)+'" role="button" tabindex="0"><span class="ic '+(up?"up":"dn")+'">'+(up?ICON_UP:ICON_DN)""", 'data-tid="\'+(Number(t.id)||0)'),
    ('static/index.html', '. This is profit only, not your account balance.</p>', '. This is profit only, not your account balance. Tap a point on the curve to see that trade.</p>', 'Tap a point on the curve'),
    ('static/index.html', CLICK_OLD, TAP, 'function tapCurve(e)'),
    ('static/index.html', '/*P9A-end*/\n', '/*P9A-end*/\n' + BLOCK, '/*P9B-start*/'),
]


def rd(p):
    with open(p, encoding='utf-8', newline='') as f: return f.read()


def main():
    for f in ('backend/app.py', 'backend/pnlcard.py', 'static/index.html', 'docs/HANDOFF.md'):
        if not os.path.exists(f): sys.exit('Run this from the project folder (the one that has backend/ and static/). Missing: ' + f)
    if not os.path.exists('backend/tradeview.py'): sys.exit('STOPPED. backend/tradeview.py is missing: run its cat command first. Nothing was changed.')
    text = {f: rd(f) for f in {e[0] for e in EDITS} | {'docs/HANDOFF.md'}}
    done = 0
    for f, old, new, mark in EDITS:
        if mark in text[f]: continue
        n = text[f].count(old)
        if n != 1: sys.exit('STOPPED. Expected one match in %s, found %d for: %r\nNothing was changed.' % (f, n, old[:90]))
        text[f] = text[f].replace(old, new); done += 1
    h = text['docs/HANDOFF.md']
    if '- 9B DONE' not in h:
        h2, k = re.subn(r'(?m)^- 9B TODO.*$', '- 9B DONE (Nov 19: backend/tradeview.py + GET /api/trade/<id> + the P9B block in static/index.html + tests/test_trade9b.py + tests/test_trade9bui.py)  Chart pop-ups: tap a closed trade (Trades list) or a point on the profit curve (Home). Shows what the server stored: planned entry, fill, stop loss, take profit, lots, opened and closed times, profit, and the M15 candles it still holds (kept in memory only, so old trades may have none). There is NO exit price and NO close reason: the EA and the Deriv loop store only the profit and the close time, so the pop-up marks the close TIME and says the exit is not recorded.', h)
        if k != 1: sys.exit('STOPPED. The 9B TODO line in docs/HANDOFF.md was not found exactly once. Nothing was changed.')
        text['docs/HANDOFF.md'] = h2; done += 1
    if not done: print('Already applied. Nothing to do.'); return
    for f, t in text.items():
        with open(f, 'w', encoding='utf-8', newline='') as o: o.write(t)
    print('Done: %d edits applied.' % done)


if __name__ == '__main__':
    main()
