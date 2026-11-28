/* CH2: the composer's + menu, removable chips and the long-paste TXT chip (Section 2).
   Plugs into the shell from CH1 (static/chat.js) through window.sxChat. Nothing is uploaded here: every pick stays in the page until a later section sends it.
   What chat.js reads: window.sxChat.files = [{id, kind, name, size, file, text, url, truncated}] and window.sxChat.clearFiles().
   kind = pdf | image | photo | text | paste. The pure part (makeStore, wantsPasteChip, humanSize) also loads in node, for tests/test_ch2.py. */
(function (root) {
  "use strict";
  var LIM = { files: 5, imgBytes: 10 * 1048576, pdfBytes: 15 * 1048576, txtBytes: 2 * 1048576, pasteChars: 1500, pasteLines: 25, textChars: 300000 };
  var SHOWN = 20000;
  var SAY = {
    many: "You can attach up to " + LIM.files + " items. Remove one first.",
    wrong: "That file type is not supported. Use a PDF, an image or a text file.",
    big: "That file is too big. Limits: images 10 MB, PDFs 15 MB, text files 2 MB.",
    empty: "That file is empty."
  };

  function humanSize(n) {
    n = Number(n) || 0;
    if (n < 1024) return n + " B";
    if (n < 1048576) return Math.round(n / 1024) + " KB";
    return (Math.round(n / 104857.6) / 10) + " MB";
  }
  function wantsPasteChip(t, lim) {
    lim = lim || LIM; t = String(t || "");
    if (t.length >= lim.pasteChars) return true;
    var n = 1, i = -1;
    while ((i = t.indexOf("\n", i + 1)) !== -1) { n++; if (n >= lim.pasteLines) return true; }
    return false;
  }
  function verdict(kind, name, mime, size, lim) {
    var low = String(name || "").toLowerCase(), m = String(mime || "").toLowerCase();
    if (!(size > 0)) return "empty";
    if (kind === "pdf") return (m === "application/pdf" || /\.pdf$/.test(low)) ? (size > lim.pdfBytes ? "big" : "") : "wrong";
    if (kind === "image" || kind === "photo") return (m.indexOf("image/") === 0 || /\.(png|jpe?g|webp|gif|heic|heif)$/.test(low)) ? (size > lim.imgBytes ? "big" : "") : "wrong";
    if (kind === "text") return (m.indexOf("text/") === 0 || m === "application/json" || /\.(txt|md|csv|tsv|json|log)$/.test(low)) ? (size > lim.txtBytes ? "big" : "") : "wrong";
    return "wrong";
  }
  function makeStore(lim) {
    var items = [], seq = 0;
    function taken(n) { for (var i = 0; i < items.length; i++) if (items[i].name === n) return true; return false; }
    function pasteName() { var n = "transcript.txt", k = 2; while (taken(n)) { n = "transcript-" + k + ".txt"; k++; } return n; }
    return {
      items: function () { return items.slice(); },
      add: function (it) {
        if (items.length >= lim.files) return { ok: false, why: "many" };
        var t = it.text == null ? null : String(it.text), cut = false;
        if (it.kind === "paste") { if (!t || !t.trim()) return { ok: false, why: "empty" }; }
        else { var v = verdict(it.kind, it.name, it.file && it.file.type, it.size, lim); if (v) return { ok: false, why: v }; }
        if (t != null && t.length > lim.textChars) { t = t.slice(0, lim.textChars); cut = true; }
        var out = { id: "a" + (++seq), kind: it.kind, name: it.kind === "paste" ? pasteName() : String(it.name || "file"), size: it.size || 0, file: it.file || null, text: t, url: "", truncated: cut };
        items.push(out); return { ok: true, item: out };
      },
      remove: function (id) { for (var i = 0; i < items.length; i++) if (items[i].id === id) return items.splice(i, 1)[0]; return null; },
      clear: function () { var old = items; items = []; return old; }
    };
  }
  var API = { LIM: LIM, humanSize: humanSize, wantsPasteChip: wantsPasteChip, verdict: verdict, makeStore: makeStore };
  if (typeof module !== "undefined" && module.exports) module.exports = API;

  var doc = root.document;
  if (!doc || !root.sxChat) return;
  var input = doc.getElementById("cxIn"), tools = doc.getElementById("cxTools");
  if (!input || !tools || !input.parentNode) return;
  root.sxChatAttach = API;
  var api = root.sxChat, box = input.parentNode, store = makeStore(LIM);

  var ICON = {
    plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
    x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    pdf: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>',
    image: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="1.6"/><path d="M21 16l-5-5-8 8"/></svg>',
    photo: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.5"/></svg>',
    text: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14M5 11h14M5 16h9"/></svg>',
    screen: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>'
  };
  var CSS = [
    ".cxa-wrap{position:relative;flex:none}",
    ".cxa-i{display:inline-grid;place-items:center}",
    ".cxa-i svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}",
    ".cxa-plus{width:38px;height:38px;border-radius:50%;border:2px solid var(--line);background:var(--surface);color:var(--fg);display:grid;place-items:center;padding:0}",
    ".cxa-plus:active{background:var(--surface2)}",
    ".cxa-menu{position:absolute;left:0;bottom:calc(100% + 10px);min-width:220px;background:var(--surface);border:2px solid var(--line);border-radius:18px;box-shadow:var(--shadow);padding:6px;z-index:20}",
    ".cxa-menu[hidden]{display:none}",
    ".cxa-it{display:flex;align-items:center;gap:12px;width:100%;min-height:44px;border:0;background:none;color:var(--fg);font:inherit;font-weight:800;padding:8px 12px;border-radius:12px;text-align:left}",
    ".cxa-it:hover,.cxa-it:active{background:var(--surface2)}",
    ".cxa-att{display:grid;gap:6px;padding:2px 0 6px}",
    ".cxa-att[hidden]{display:none}",
    ".cxa-chips{display:flex;flex-wrap:wrap;gap:8px}",
    ".cxa-chip{display:inline-flex;align-items:center;max-width:100%;border:2px solid var(--line);background:var(--surface2);border-radius:999px;overflow:hidden}",
    ".cxa-open{display:flex;align-items:center;gap:8px;min-width:0;border:0;background:none;color:var(--fg);font:inherit;font-weight:800;font-size:13px;padding:6px 4px 6px 10px}",
    ".cxa-th{width:26px;height:26px;border-radius:8px;object-fit:cover;flex:none}",
    ".cxa-n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:150px}",
    ".cxa-s{color:var(--muted);font-weight:700;white-space:nowrap}",
    ".cxa-x{flex:none;width:34px;height:34px;border:0;background:none;color:var(--muted);display:grid;place-items:center;padding:0}",
    ".cxa-x svg{width:16px;height:16px}",
    ".cxa-note{font-size:13px;font-weight:700;color:var(--muted)}",
    ".cxa-note:empty{display:none}",
    ".cx-fl{font-size:13px;font-weight:700;color:var(--muted);margin-top:4px;white-space:pre-wrap}",
    ".cxa-sheet{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.5);display:grid;place-items:end center}",
    ".cxa-panel{width:min(560px,100%);max-height:80vh;max-height:80dvh;background:var(--surface);border:2px solid var(--line);border-radius:22px 22px 0 0;padding:16px;display:grid;gap:12px;grid-template-rows:auto minmax(0,1fr) auto}",
    ".cxa-h{display:flex;align-items:baseline;gap:10px;min-width:0}",
    ".cxa-h b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    ".cxa-body{overflow:auto;min-height:0}",
    ".cxa-pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;font-size:13px;font-weight:700;margin:0}",
    ".cxa-body img{max-width:100%;border-radius:12px;display:block;margin:0 auto}",
    ".cxa-f{display:flex;justify-content:flex-end;gap:10px}",
    ".cxa-btn{border:2px solid var(--line);background:var(--surface);color:var(--fg);border-radius:999px;padding:10px 18px;font:inherit;font-weight:800}",
    ".cxa-btn.main{border-color:var(--green);background:var(--green);color:var(--on-green)}"
  ].join("\n");
  var S = doc.createElement("style"); S.textContent = CSS; doc.head.appendChild(S);

  function el(tag, cls, text) { var e = doc.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function icon(name) { var s = el("span", "cxa-i"); s.innerHTML = ICON[name]; return s; }

  var att = el("div", "cxa-att"), chips = el("div", "cxa-chips"), note = el("div", "cxa-note"), noteTimer = 0;
  note.setAttribute("role", "status"); att.hidden = true; att.appendChild(chips); att.appendChild(note); box.insertBefore(att, input);

  function show() { att.hidden = !(store.items().length || note.textContent); }
  function say(msg) {
    note.textContent = msg; show();
    try { root.clearTimeout(noteTimer); noteTimer = root.setTimeout(function () { note.textContent = ""; show(); }, 6000); } catch (e) {}
  }
  function release(list) {
    list.forEach(function (it) { if (it.url && root.URL && root.URL.revokeObjectURL) { try { root.URL.revokeObjectURL(it.url); } catch (e) {} } });
  }
  function sync() { api.files = store.items(); render(); if (api.refresh) api.refresh(); }
  function drop(id) { var it = store.remove(id); if (it) release([it]); sync(); }

  function preview(it, opener) {
    var ov = el("div", "cxa-sheet"), p = el("div", "cxa-panel"), h = el("div", "cxa-h"), body = el("div", "cxa-body"), ft = el("div", "cxa-f");
    ov.setAttribute("role", "dialog"); ov.setAttribute("aria-modal", "true"); ov.setAttribute("aria-label", "Preview of " + it.name);
    h.appendChild(el("b", "", it.name)); h.appendChild(el("span", "cxa-s", humanSize(it.size)));
    if (it.text != null) {
      var pre = el("pre", "cxa-pre"); pre.textContent = it.text.slice(0, SHOWN); body.appendChild(pre);
      if (it.text.length > SHOWN) body.appendChild(el("p", "cxa-s", "Showing the first " + SHOWN + " characters. The whole text stays attached."));
    } else if (it.url) { var im = el("img"); im.src = it.url; im.alt = it.name; body.appendChild(im); }
    else body.appendChild(el("p", "", "No preview for PDFs here. It stays on this device until you send."));
    var rm = el("button", "cxa-btn", "Remove"), cl = el("button", "cxa-btn main", "Close");
    rm.type = "button"; cl.type = "button"; ft.appendChild(rm); ft.appendChild(cl);
    p.appendChild(h); p.appendChild(body); p.appendChild(ft); ov.appendChild(p);
    function onKey(e) { if (e.key === "Escape") close(); }
    function close() { ov.remove(); doc.removeEventListener("keydown", onKey); try { opener.focus(); } catch (e) {} }
    ov.addEventListener("click", function (e) { if (e.target === ov) close(); });
    cl.addEventListener("click", close);
    rm.addEventListener("click", function () { close(); drop(it.id); });
    doc.addEventListener("keydown", onKey);
    doc.body.appendChild(ov); try { cl.focus(); } catch (e) {}
  }

  function render() {
    while (chips.children.length) chips.removeChild(chips.children[0]);
    store.items().forEach(function (it) {
      var c = el("div", "cxa-chip"), o = el("button", "cxa-open"), x = el("button", "cxa-x");
      o.type = "button"; x.type = "button";
      o.setAttribute("aria-label", "Preview " + it.name); x.setAttribute("aria-label", "Remove " + it.name);
      if (it.url) { var th = el("img", "cxa-th"); th.src = it.url; th.alt = ""; o.appendChild(th); }
      else o.appendChild(icon(it.kind === "pdf" ? "pdf" : (it.kind === "image" || it.kind === "photo") ? "image" : "text"));
      o.appendChild(el("span", "cxa-n", it.name)); o.appendChild(el("span", "cxa-s", humanSize(it.size)));
      x.appendChild(icon("x"));
      o.addEventListener("click", function () { preview(it, o); });
      x.addEventListener("click", function () { drop(it.id); });
      c.appendChild(o); c.appendChild(x); chips.appendChild(c);
    });
    show();
  }

  function put(it) {
    var r = store.add(it);
    if (!r.ok) { say(SAY[r.why] || SAY.wrong); return; }
    if ((it.kind === "image" || it.kind === "photo") && root.URL && root.URL.createObjectURL) { try { r.item.url = root.URL.createObjectURL(it.file); } catch (e) {} }
    sync();
    if (r.item.truncated) say("Long text was cut to its first 300,000 characters.");
  }
  function readText(f, cb) {
    if (f.text) { f.text().then(cb, function () { say("Could not read that file."); }); return; }
    var r = new root.FileReader(); r.onload = function () { cb(String(r.result || "")); }; r.onerror = function () { say("Could not read that file."); }; r.readAsText(f);
  }
  function addFiles(kind, files) {
    Array.prototype.slice.call(files || []).forEach(function (f) {
      if (store.items().length >= LIM.files) { say(SAY.many); return; }
      var v = verdict(kind, f.name, f.type, f.size, LIM);
      if (v) { say(SAY[v]); return; }
      if (kind === "text") readText(f, function (txt) { put({ kind: kind, name: f.name, size: f.size, file: f, text: txt }); });
      else put({ kind: kind, name: f.name, size: f.size, file: f });
    });
  }

  var wrap = el("div", "cxa-wrap"), plus = el("button", "cxa-plus"), menu = el("div", "cxa-menu"), inputs = {};
  plus.type = "button"; plus.setAttribute("aria-label", "Add"); plus.setAttribute("aria-haspopup", "menu"); plus.setAttribute("aria-expanded", "false"); plus.appendChild(icon("plus"));
  menu.hidden = true; menu.setAttribute("role", "menu");
  function setMenu(open) { menu.hidden = !open; plus.setAttribute("aria-expanded", open ? "true" : "false"); }
  function shareScreen() {
    if (typeof api.shareScreen === "function") { try { api.shareScreen(); } catch (e) { say("Could not start Share screen."); } return; }
    say("Share screen is added in a later step.");
  }
  var MENU = [["pdf", "PDF"], ["image", "Image"], ["photo", "Take a photo"], ["text", "Text file"], ["screen", "Share screen"]];
  var ACCEPT = { pdf: "application/pdf,.pdf", image: "image/*", photo: "image/*", text: ".txt,.md,.csv,.tsv,.json,.log,text/plain" };
  MENU.forEach(function (m) {
    var kind = m[0], b = el("button", "cxa-it");
    b.type = "button"; b.setAttribute("role", "menuitem"); b.appendChild(icon(kind)); b.appendChild(el("span", "", m[1]));
    b.addEventListener("click", function () { setMenu(false); if (kind === "screen") shareScreen(); else inputs[kind].click(); });
    menu.appendChild(b);
    if (ACCEPT[kind]) {
      var f = el("input", "cxa-file"); f.type = "file"; f.accept = ACCEPT[kind]; f.hidden = true;
      if (kind === "photo") f.setAttribute("capture", "environment"); else f.multiple = true;
      f.addEventListener("change", function () { var picked = Array.prototype.slice.call(f.files || []); f.value = ""; addFiles(kind, picked); });
      inputs[kind] = f; wrap.appendChild(f);
    }
  });
  wrap.appendChild(plus); wrap.appendChild(menu); tools.insertBefore(wrap, tools.firstChild);
  plus.addEventListener("click", function (e) { if (e.stopPropagation) e.stopPropagation(); setMenu(menu.hidden); });
  doc.addEventListener("click", function (e) { if (!menu.hidden && !wrap.contains(e.target)) setMenu(false); });
  doc.addEventListener("keydown", function (e) { if (e.key === "Escape" && !menu.hidden) { setMenu(false); try { plus.focus(); } catch (x) {} } });

  input.addEventListener("paste", function (e) {
    var cd = e.clipboardData; if (!cd) return;
    var imgs = Array.prototype.slice.call(cd.files || []).filter(function (f) { return /^image\//.test(f.type || ""); });
    if (imgs.length) { e.preventDefault(); addFiles("image", imgs); return; }
    var t = cd.getData ? cd.getData("text") : "";
    if (!wantsPasteChip(t)) return;
    e.preventDefault();
    var bytes = root.TextEncoder ? new root.TextEncoder().encode(t).length : t.length;
    put({ kind: "paste", name: "transcript.txt", size: bytes, text: t });
  });

  api.files = [];
  api.clearFiles = function () { release(store.clear()); sync(); };
})(typeof window !== "undefined" ? window : this);
