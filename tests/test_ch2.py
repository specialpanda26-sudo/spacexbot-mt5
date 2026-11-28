"""CH2: composer + menu, removable chips, long paste becomes a TXT chip. Needs node. Run: python tests/test_ch2.py (ends N/N passed)"""
import os, re, sys, json, subprocess
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
def rd(*p): return open(os.path.join(R, *p), encoding='utf-8').read()
idx, att, chat = rd('static', 'index.html'), rd('static', 'chat_attach.js'), rd('static', 'chat.js')
res = []
def T(n, ok): res.append((n, bool(ok)))

T('chat_attach.js loads right after chat.js', '<script src="/static/chat.js"></script><script src="/static/chat_attach.js"></script>' in idx)
T('no hard-coded colours (site variables only)', not re.search(r'#[0-9a-fA-F]{6}\b', att))
T('nothing is uploaded in this section', not re.search(r'fetch\(|XMLHttpRequest|sendBeacon|WebSocket', att))
T('innerHTML is only ever given the fixed icon strings', all(m.startswith('ICON[') for m in re.findall(r'innerHTML\s*=\s*([^;]+);', att)) and 'innerHTML' in att)
T('file names are written with textContent', 'el("span", "cxa-n", it.name)' in att and 'el("b", "", it.name)' in att)
sub = chat[chat.index('function submit('):chat.index('function fit(')]
T('chat.js sends the files with the message and clears the chips when it sends', 'replyFn || placeholder)(text, fl)' in sub and 'window.sxChat.clearFiles()' in sub)
T('chat.js lets an attachment alone enable Send', 'input.value.trim() || files().length' in chat)
T('chat.js shows the attachment names in your bubble with textContent', 'fa.textContent = fl.map' in chat)
T('New chat clears the chips', 'function reset() { if (window.sxChat && window.sxChat.clearFiles)' in chat)
T('chat.js exposes refresh for the chips', 'refresh: refresh' in chat)

H = r"""
const vm = require("vm"), fs = require("fs"), path = process.argv[1], src = fs.readFileSync(path, "utf8");
const res = []; const T = (n, ok) => res.push([n, !!ok]);
const A = require(path), L = A.LIM, big = n => "x".repeat(n);
T("size words", A.humanSize(500) === "500 B" && A.humanSize(2048) === "2 KB" && A.humanSize(1572864) === "1.5 MB");
T("paste: 1499 chars stay in the box, 1500 become a chip", !A.wantsPasteChip(big(1499)) && A.wantsPasteChip(big(1500)));
T("paste: 24 lines stay, 25 lines become a chip", !A.wantsPasteChip(Array(24).fill("a").join("\n")) && A.wantsPasteChip(Array(25).fill("a").join("\n")));
T("paste: empty is not a chip", !A.wantsPasteChip("") && !A.wantsPasteChip(null));
let s = A.makeStore(L), a = s.add({ kind: "paste", text: "hello", size: 5 }), b = s.add({ kind: "paste", text: "again", size: 5 });
T("pasted chips are named transcript.txt then transcript-2.txt", a.item.name === "transcript.txt" && b.item.name === "transcript-2.txt");
s.remove(a.item.id); T("a freed name is reused", s.add({ kind: "paste", text: "third", size: 5 }).item.name === "transcript.txt");
s = A.makeStore(L); for (let i = 0; i < 5; i++) s.add({ kind: "paste", text: "t" + i, size: 2 });
T("the 6th item is refused: many", s.add({ kind: "paste", text: "t", size: 1 }).why === "many" && s.items().length === 5);
const v = (k, n, m, z) => A.verdict(k, n, m, z, L);
T("pdf: right type passes, an image posing as pdf does not", v("pdf", "a.pdf", "", 10) === "" && v("pdf", "a.png", "image/png", 10) === "wrong");
T("image: gif and heic pass, a pdf does not", v("image", "a.heic", "", 10) === "" && v("image", "a.pdf", "application/pdf", 10) === "wrong");
T("text: .txt and .md pass, .exe does not", v("text", "a.txt", "", 10) === "" && v("text", "n.md", "", 10) === "" && v("text", "a.exe", "application/octet-stream", 10) === "wrong");
T("sizes: over the limit is big, zero is empty", v("image", "a.png", "image/png", L.imgBytes + 1) === "big" && v("pdf", "a.pdf", "", L.pdfBytes + 1) === "big" && v("text", "a.txt", "", L.txtBytes + 1) === "big" && v("text", "a.txt", "", 0) === "empty");
let t = A.makeStore(L).add({ kind: "paste", text: big(L.textChars + 50), size: 1 });
T("very long text is cut and flagged", t.item.text.length === L.textChars && t.item.truncated === true);
T("an unknown kind is refused", A.makeStore(L).add({ kind: "zip", name: "a.zip", size: 5, file: { type: "" } }).why === "wrong");

/* ---- a small fake page ---- */
const out = { refresh: 0, revoked: [], focus: null };
function N(tag) { this.tag = tag; this.children = []; this.parentNode = null; this.ls = {}; this.attrs = {}; this.className = ""; this.hidden = false; this.value = ""; this._t = ""; this._h = ""; this.style = {}; }
N.prototype.appendChild = function (c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.children.push(c); return c; };
N.prototype.insertBefore = function (c, r) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; const i = r ? this.children.indexOf(r) : -1; if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; };
N.prototype.removeChild = function (c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parentNode = null; return c; };
N.prototype.remove = function () { if (this.parentNode) this.parentNode.removeChild(this); };
Object.defineProperty(N.prototype, "firstChild", { get() { return this.children[0] || null; } });
Object.defineProperty(N.prototype, "textContent", { get() { return this._t + this.children.map(c => c.textContent).join(""); }, set(x) { this._t = String(x); this.children = []; } });
Object.defineProperty(N.prototype, "innerHTML", { get() { return this._h; }, set(x) { this._h = String(x); } });
N.prototype.addEventListener = function (e, f) { (this.ls[e] = this.ls[e] || []).push(f); };
N.prototype.removeEventListener = function (e, f) { this.ls[e] = (this.ls[e] || []).filter(x => x !== f); };
N.prototype.setAttribute = function (k, x) { this.attrs[k] = String(x); };
N.prototype.getAttribute = function (k) { return k in this.attrs ? this.attrs[k] : null; };
N.prototype.contains = function (n) { for (; n; n = n.parentNode) if (n === this) return true; return false; };
N.prototype.focus = function () { out.focus = this; };
N.prototype.click = function () { if (this.tag === "input") { this.clicked = (this.clicked || 0) + 1; return; } this.fire("click"); };
N.prototype.fire = function (e, ev) { ev = ev || {}; ev.target = ev.target || this; ev.prevented = false; ev.stopped = false; ev.preventDefault = () => { ev.prevented = true; }; ev.stopPropagation = () => { ev.stopped = true; }; for (let n = this; n && !ev.stopped; n = n.parentNode) (n.ls[e] || []).slice().forEach(f => f(ev)); return ev; };
const doc = new N("doc"); doc.body = new N("body"); doc.head = new N("head"); doc.appendChild(doc.head); doc.appendChild(doc.body);
doc.createElement = tag => new N(tag);
const box = new N("div"), input = new N("textarea"), row = new N("div"), tools = new N("div"), hint = new N("span");
box.appendChild(input); box.appendChild(row); row.appendChild(tools); tools.appendChild(hint); doc.body.appendChild(box);
doc.getElementById = id => ({ cxIn: input, cxTools: tools })[id] || null;
const sxChat = { refresh() { out.refresh++; } };
const sb = { document: doc, sxChat, URL: { createObjectURL: f => "blob:" + f.name, revokeObjectURL: u => out.revoked.push(u) }, setTimeout: () => 1, clearTimeout() {}, TextEncoder };
sb.window = sb; vm.runInNewContext(src, sb);

const all = (n, r = []) => { r.push(n); n.children.forEach(c => all(c, r)); return r; };
const by = (n, c) => all(n).filter(x => (" " + x.className + " ").includes(" " + c + " "));
const F = (name, type, size, text) => ({ name, type, size, text: () => Promise.resolve(text == null ? "hello" : text) });
const settle = async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); };
const wrap = tools.children[0], plus = by(tools, "cxa-plus")[0], menu = by(tools, "cxa-menu")[0], att = box.children[0], ins = by(wrap, "cxa-file");
const chips = () => by(att, "cxa-chip"), pick = (i, files) => { ins[i].files = files; ins[i].fire("change"); };
(async () => {
  T("the + sits first in the composer tools, the chips area above the text box", wrap.className === "cxa-wrap" && plus && att.className === "cxa-att" && box.children[1] === input);
  T("the chips area is hidden while empty", att.hidden === true);
  T("the menu starts closed", menu.hidden === true && plus.getAttribute("aria-expanded") === "false");
  plus.fire("click"); T("tap + opens the menu", menu.hidden === false && plus.getAttribute("aria-expanded") === "true");
  T("menu offers PDF, Image, Take a photo, Text file, Share screen", JSON.stringify(by(menu, "cxa-it").map(x => x.textContent)) === JSON.stringify(["PDF", "Image", "Take a photo", "Text file", "Share screen"]));
  doc.body.fire("click"); T("tap outside closes it", menu.hidden === true);
  plus.fire("click"); doc.fire("keydown", { key: "Escape" }); T("Escape closes it and puts focus back on +", menu.hidden === true && out.focus === plus);
  plus.fire("click"); by(menu, "cxa-it")[0].fire("click");
  T("picking PDF opens the file picker and closes the menu", ins[0].clicked === 1 && menu.hidden === true && ins[0].accept.includes("pdf"));
  T("photo asks for the camera, the others take many files", ins[2].getAttribute("capture") === "environment" && !ins[2].multiple && ins[0].multiple && ins[1].multiple && ins[3].multiple);
  pick(0, [F("plan.pdf", "application/pdf", 1000)]);
  T("a picked PDF shows as one chip, and chat.js can see it", chips().length === 1 && sxChat.files.length === 1 && sxChat.files[0].kind === "pdf" && out.refresh > 0 && att.hidden === false);
  pick(1, [F("chart.png", "image/png", 5000)]);
  T("an image chip has a thumbnail", chips().length === 2 && by(att, "cxa-th")[0].src === "blob:chart.png");
  pick(3, [F("notes.txt", "text/plain", 11, "hello world")]); await settle();
  T("a text file is read into the chip", chips().length === 3 && sxChat.files[2].text === "hello world");
  const long = big(2000), ev = input.fire("paste", { clipboardData: { files: [], getData: () => long } });
  T("a long paste becomes transcript.txt and the box stays empty", ev.prevented && chips().length === 4 && sxChat.files[3].name === "transcript.txt" && input.value === "" && sxChat.files[3].text === long);
  const ev2 = input.fire("paste", { clipboardData: { files: [], getData: () => long } });
  T("a second long paste is transcript-2.txt", ev2.prevented && sxChat.files[4].name === "transcript-2.txt" && chips().length === 5);
  const ev3 = input.fire("paste", { clipboardData: { files: [], getData: () => "hi" } });
  T("a short paste is left alone", ev3.prevented === false);
  pick(1, [F("b.png", "image/png", 5)]);
  T("the 6th item is refused with a plain note", chips().length === 5 && by(att, "cxa-note")[0].textContent.includes("up to 5"));
  const ev4 = input.fire("paste", { clipboardData: { files: [F("shot.png", "image/png", 9)], getData: () => "" } });
  T("a pasted picture is not added past the limit either", ev4.prevented && chips().length === 5);
  by(att, "cxa-x")[1].fire("click");
  T("the x removes a chip and frees its picture", chips().length === 4 && out.revoked.includes("blob:chart.png") && sxChat.files.length === 4);
  const op = by(att, "cxa-open").find(x => x.getAttribute("aria-label") === "Preview transcript.txt"); op.fire("click");
  const sheet = by(doc.body, "cxa-sheet")[0];
  T("tapping a chip opens a preview with the text", sheet && sheet.getAttribute("role") === "dialog" && by(sheet, "cxa-pre")[0].textContent.length === 2000);
  doc.fire("keydown", { key: "Escape" }); T("Escape closes the preview and returns focus to the chip", by(doc.body, "cxa-sheet").length === 0 && out.focus === op);
  by(att, "cxa-open").find(x => x.getAttribute("aria-label") === "Preview transcript.txt").fire("click");
  by(by(doc.body, "cxa-sheet")[0], "cxa-btn").find(x => x.textContent === "Remove").fire("click");
  T("Remove inside the preview removes the chip", by(doc.body, "cxa-sheet").length === 0 && chips().length === 3 && !sxChat.files.some(f => f.name === "transcript.txt"));
  pick(0, [F("a.png", "image/png", 100)]);
  T("a wrong file type is refused with a plain note", chips().length === 3 && by(att, "cxa-note")[0].textContent.includes("not supported"));
  const evil = '<img src=x onerror=alert(1)>.txt';
  pick(3, [F(evil, "text/plain", 5, "x")]); await settle();
  T("a hostile file name stays plain text", by(att, "cxa-n").some(x => x.textContent === evil) && !all(doc.body).some(n => /onerror/.test(n._h)));
  plus.fire("click"); by(menu, "cxa-it")[4].fire("click");
  T("Share screen says it is coming while nothing is plugged in", by(att, "cxa-note")[0].textContent.includes("later step"));
  sxChat.shareScreen = () => { out.shared = 1; }; plus.fire("click"); by(menu, "cxa-it")[4].fire("click");
  T("Share screen calls the hook once CH12 plugs it in", out.shared === 1);
  pick(1, [F("z.png", "image/png", 5)]); sxChat.clearFiles();
  T("clearFiles empties the chips and frees the pictures", chips().length === 0 && sxChat.files.length === 0 && out.revoked.includes("blob:z.png"));
  console.log(JSON.stringify(res));
})().catch(e => { console.log(JSON.stringify([["node run crashed: " + (e && e.stack || e), false]])); });
"""
p = subprocess.run(['node', '-e', H, os.path.join(R, 'static', 'chat_attach.js')], capture_output=True, text=True)
try: rows = json.loads(p.stdout.strip().splitlines()[-1])
except Exception: rows = [['node did not run: ' + (p.stderr or p.stdout)[:300], False]]
for n, ok in rows: T(n, ok)

bad = [n for n, ok in res if not ok]
for n, ok in res: print(('PASS ' if ok else 'FAIL ') + n)
print('%d/%d passed' % (len(res) - len(bad), len(res))); sys.exit(1 if bad else 0)
