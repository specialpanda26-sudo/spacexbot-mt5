/* CH1: the Chat tab shell (Section 1). Layout only: empty state, quick chips, message list, composer.
   Looks like the site (same colours, rounded cards, chunky green button) and works like a modern chat: bot text on the left, your bubble on the right,
   a composer pinned at the bottom with a slot for the + and mic buttons (Sections 2 and 4).
   The brain is NOT connected yet (Section 6): until then the tab is for the owner only (OPEN = false) and replies are a clear placeholder.
   Plug-in points for later sections: window.sxChat.setReply(fn) where fn(text) returns a Promise of the answer text; window.sxChat.tools = the empty slot in the composer. */
(function () {
  "use strict";
  var OPEN = false;                       /* false = owner only. Set true when the chat brain is ready for subscribers. */
  var vw = document.getElementById("view-chat"), nb = document.getElementById("navChat");
  if (!vw || !window.SXA) return;

  var CSS = [
    ".nav button[hidden]{display:none!important}",
    ".nav{grid-template-columns:none;grid-auto-flow:column;grid-auto-columns:1fr}",
    ".cx{display:flex;flex-direction:column;min-height:calc(100vh - 170px);min-height:calc(100dvh - 170px);min-width:0}",
    ".cx-top{display:flex;justify-content:flex-end;min-height:0}",
    ".cx-new{border:0;background:none;color:var(--muted);font-weight:800;font-size:13px;padding:6px 10px;border-radius:999px}",
    ".cx-new:active{background:var(--surface2)}",
    ".cx-empty{flex:1;display:grid;align-content:center;justify-items:center;gap:10px;text-align:center;padding:18px 6px}",
    ".cx-pet{width:112px;height:112px;animation:cxfloat 3.2s ease-in-out infinite}",
    "@keyframes cxfloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}",
    ".cx-empty h2{font-size:24px;letter-spacing:-.02em}",
    ".cx-empty p{max-width:34ch;color:var(--muted);font-weight:700}",
    ".cx-chips{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:6px;max-width:520px}",
    ".cx-chip{border:2px solid var(--line);background:var(--surface);color:var(--fg);border-radius:999px;padding:9px 14px;font-weight:800;font-size:14px;transition:transform .2s var(--spring),border-color .2s,background .2s}",
    ".cx-chip:hover{border-color:var(--sky);background:var(--sky-soft)}",
    ".cx-chip:active{transform:scale(.96)}",
    ".cx-list{flex:1;display:flex;flex-direction:column;gap:16px;padding:6px 0 18px;min-width:0}",
    ".cx-list[hidden],.cx-empty[hidden],.cx-top[hidden]{display:none}",
    ".cx-m{display:flex;gap:10px;min-width:0;animation:rise .45s var(--ease) both}",
    ".cx-m.me{justify-content:flex-end}",
    ".cx-m.me .cx-t{background:var(--surface2);border:2px solid var(--line);border-radius:20px 20px 6px 20px;padding:10px 14px;max-width:86%}",
    ".cx-m.bot .cx-t{padding:4px 0;max-width:calc(100% - 40px)}",
    ".cx-t{white-space:pre-wrap;word-wrap:break-word;overflow-wrap:anywhere;font-weight:700;min-width:0}",
    ".cx-av{flex:none;width:30px;height:30px;border-radius:50%;background:var(--green-soft);display:grid;place-items:center}",
    ".cx-dots{display:inline-flex;gap:5px;padding:8px 0}",
    ".cx-dots i{width:8px;height:8px;border-radius:50%;background:var(--muted);animation:cxdot 1.1s ease-in-out infinite}",
    ".cx-dots i:nth-child(2){animation-delay:.15s}.cx-dots i:nth-child(3){animation-delay:.3s}",
    "@keyframes cxdot{0%,80%,100%{opacity:.25;transform:scale(.8)}40%{opacity:1;transform:scale(1)}}",
    ".cx-bar{position:sticky;bottom:calc(76px + env(safe-area-inset-bottom,0px));z-index:5;padding:8px 0 4px;background:linear-gradient(to top,var(--bg) 70%,transparent)}",
    ".cx-box{display:grid;gap:6px;background:var(--surface);border:2px solid var(--line);border-radius:22px;padding:10px 10px 8px 14px;box-shadow:var(--shadow);transition:border-color .2s}",
    ".cx-box:focus-within{border-color:var(--sky)}",
    ".cx-in{width:100%;border:0;outline:0;resize:none;background:none;color:var(--fg);font:inherit;font-weight:700;font-size:16px;line-height:1.4;max-height:180px;min-height:26px;padding:2px 0}",
    ".cx-in::placeholder{color:var(--muted)}",
    ".cx-row{display:flex;align-items:center;justify-content:space-between;gap:10px}",
    ".cx-tools{display:flex;align-items:center;gap:8px;min-width:0;flex:1}",
    ".cx-hint{font-size:12px;color:var(--muted);font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    ".cx-send{flex:none;width:42px;height:42px;border-radius:50%;border:2px solid var(--green);background:var(--green);color:var(--on-green);display:grid;place-items:center;box-shadow:0 3px 0 var(--green-d);transition:transform .15s var(--spring),opacity .2s}",
    ".cx-send:active{transform:translateY(2px);box-shadow:0 0 0 var(--green-d)}",
    ".cx-send:disabled{opacity:.4;box-shadow:none}",
    ".cx-send svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}",
    "@media (min-width:900px){.cx{min-height:calc(100vh - 150px);min-height:calc(100dvh - 150px);max-width:820px;width:100%;margin:0 auto}.cx-bar{bottom:12px}.cx-hint{white-space:normal}}",
    "@media (prefers-reduced-motion:reduce){.cx-pet,.cx-dots i,.cx-m{animation:none}}"
  ].join("\n");
  var S = document.createElement("style"); S.textContent = CSS; document.head.appendChild(S);

  var CHIPS = ["Why did the bot not trade today?", "Explain my settings", "How is my risk set?", "What does Burst mode do?"];
  vw.innerHTML =
    '<div class="cx" id="cx">' +
      '<div class="cx-top" id="cxTop" hidden><button class="cx-new" id="cxNew" type="button">New chat</button></div>' +
      '<div class="cx-empty" id="cxEmpty">' +
        '<svg class="mk cx-pet" aria-hidden="true"><use href="#mk"/></svg>' +
        '<h2 id="cxHi">Ask me anything about your bot</h2>' +
        '<p>Settings, trades, why it waited, how a strategy works. Type below.</p>' +
        '<div class="cx-chips" id="cxChips"></div>' +
      '</div>' +
      '<div class="cx-list" id="cxList" role="log" aria-live="polite" aria-label="Conversation" hidden></div>' +
      '<div class="cx-bar"><div class="cx-box">' +
        '<textarea class="cx-in" id="cxIn" rows="1" placeholder="Ask about your bot" aria-label="Message" enterkeyhint="send"></textarea>' +
        '<div class="cx-row"><div class="cx-tools" id="cxTools"><span class="cx-hint" id="cxHint"></span></div>' +
        '<button class="cx-send" id="cxSend" type="button" aria-label="Send" disabled><svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button></div>' +
      '</div></div>' +
    '</div>';

  var $ = function (id) { return document.getElementById(id); };
  var list = $("cxList"), empty = $("cxEmpty"), top = $("cxTop"), input = $("cxIn"), send = $("cxSend"), tools = $("cxTools"), hint = $("cxHint");
  var BUSY = false, replyFn = null;
  var touch = window.matchMedia && window.matchMedia("(pointer:coarse)").matches;
  hint.textContent = touch ? "Not financial advice." : "Enter to send. Shift+Enter for a new line. Not financial advice.";

  CHIPS.forEach(function (c) {
    var b = document.createElement("button"); b.type = "button"; b.className = "cx-chip"; b.textContent = c;
    b.addEventListener("click", function () { submit(c); }); $("cxChips").appendChild(b);
  });

  function toBottom() { try { window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" }); } catch (e) { window.scrollTo(0, document.documentElement.scrollHeight); } }
  function showList() { list.hidden = false; empty.hidden = true; top.hidden = false; }
  function add(role, text, fl) {
    showList();
    var m = document.createElement("div"); m.className = "cx-m " + (role === "me" ? "me" : "bot");
    if (role !== "me") { var av = document.createElement("div"); av.className = "cx-av"; av.innerHTML = '<svg class="mk" width="20" height="20" aria-hidden="true"><use href="#mk"/></svg>'; m.appendChild(av); }
    var t = document.createElement("div"); t.className = "cx-t"; t.textContent = text || ""; if (fl && fl.length) { var fa = document.createElement("div"); fa.className = "cx-fl"; fa.textContent = fl.map(function (f) { return "Attached: " + f.name; }).join("\n"); t.appendChild(fa); } m.appendChild(t);
    list.appendChild(m); toBottom(); return m;
  }
  function thinking() {
    showList();
    var m = document.createElement("div"); m.className = "cx-m bot";
    m.innerHTML = '<div class="cx-av"><svg class="mk" width="20" height="20" aria-hidden="true"><use href="#mk"/></svg></div><div class="cx-t"><span class="cx-dots" aria-label="Thinking"><i></i><i></i><i></i></span></div>';
    list.appendChild(m); toBottom(); return m;
  }
  function placeholder(text, fl) {
    return Promise.resolve("The chat brain is not connected yet. This tab is the layout only, so you can check how it looks. Your message above is just shown back to you." + (fl && fl.length ? " Your " + fl.length + " attachment(s) stay on this device; nothing is uploaded yet." : ""));
  }
  function submit(text) {
    text = String(text == null ? input.value : text).trim();
    var fl = files().slice();          /* CH2: what is attached goes with the message */
    if ((!text && !fl.length) || BUSY) return;
    input.value = ""; fit();
    if (window.sxChat && window.sxChat.clearFiles) window.sxChat.clearFiles();          /* CH2: the chips leave the box when the message goes */
    refresh();
    add("me", text, fl); BUSY = true; refresh();
    var wait = thinking();
    Promise.resolve().then(function () { return (replyFn || placeholder)(text, fl); })
      .then(function (ans) { wait.remove(); add("bot", ans || "I have no answer for that yet."); },
            function (e) { wait.remove(); add("bot", (e && e.message) || "Something went wrong. Try again in a moment."); })
      .then(function () { BUSY = false; refresh(); });
  }
  function fit() { input.style.height = "auto"; input.style.height = Math.min(180, input.scrollHeight) + "px"; }
  function files() { return (window.sxChat && window.sxChat.files) || []; }          /* CH2 */
  function refresh() { send.disabled = BUSY || !(input.value.trim() || files().length); }
  function reset() { if (window.sxChat && window.sxChat.clearFiles) window.sxChat.clearFiles(); list.innerHTML = ""; list.hidden = true; empty.hidden = false; top.hidden = true; input.value = ""; fit(); refresh(); }

  input.addEventListener("input", function () { fit(); refresh(); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !touch && !e.isComposing) { e.preventDefault(); submit(); }
  });
  send.addEventListener("click", function () { submit(); });
  $("cxNew").addEventListener("click", reset);

  /* who may see the tab */
  function allowed() {
    var u; try { u = SXA.user(); } catch (e) { u = null; }
    if (!u || !u.verified) return false;
    return OPEN ? !!(u.admin || u.active) : !!u.admin;
  }
  function greet() {
    var u; try { u = SXA.user(); } catch (e) { u = null; }
    var n = u && u.name ? String(u.name).trim().split(/\s+/)[0] : "";
    $("cxHi").textContent = n ? "Hi " + n + ". Ask me anything about your bot" : "Ask me anything about your bot";
  }
  function gate() {
    var ok = allowed(); if (nb) nb.hidden = !ok;
    if (ok) greet();
    if (!ok && location.hash === "#chat") location.hash = SXA.resolved && SXA.resolved() ? "#home" : "#welcome";
  }
  gate(); setInterval(gate, 1500);
  window.addEventListener("hashchange", function () { if (location.hash === "#chat") { gate(); setTimeout(function () { try { input.focus({ preventScroll: true }); } catch (e) {} }, 400); } });

  window.sxChat = { add: add, send: submit, reset: reset, refresh: refresh, tools: tools, setReply: function (fn) { replyFn = typeof fn === "function" ? fn : null; } };
})();
