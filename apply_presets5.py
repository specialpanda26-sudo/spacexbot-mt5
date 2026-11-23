"""Presets S5: the Bot-tab card in static/prefs_ui.js ("Small account settings").
 - three buttons ($10, $20, $30). A tap only PICKS a size and shows what will change; nothing is saved yet.
 - before the Confirm button it shows the most one trade may lose in dollars (balance x risk %), from the server's own numbers
   (GET /api/presets -> minlot[tier].risk_usd and balance). No balance known = no dollar amount is shown, never a guess.
 - Confirm posts {tier}; "Back to my old settings" posts {undo: true}. Uses the existing /api/presets routes (S4).
 - owner: no card. Real mode: buttons off and the card says to use Demo first (the server refuses it too).
 - after a save the Strategies card reloads (window.sxPrefsReload).
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
import sys
P = 'static/prefs_ui.js'
s = open(P, encoding='utf-8').read()
if 'A2. Small account settings' in s: print(P, ': already ok'); sys.exit(0)

HOOK_OLD = "    paint();\n  })();\n\n  /* ---------- B. Open trades"
HOOK_NEW = "    window.sxPrefsReload = function () { DIRTY = false; return load(true); };          /* S5: the preset card asks this card to show the new values */\n    paint();\n  })();\n\n  /* ---------- B. Open trades"
if s.count(HOOK_OLD) != 1: sys.exit('STOP: cannot find the end of the Strategies card exactly once')

CARD = r'''  /* ---------- A2. Small account settings (Bot tab). GET/POST /api/presets. A tap on $10 / $20 / $30 only picks; Confirm saves; Back puts the old values back. ---------- */
  if (vb) (function () {
    var C = document.createElement("div"); C.className = "card"; C.id = "presetc"; C.hidden = true;
    var pc = document.getElementById("prefc"), after = document.getElementById("posc") || document.getElementById("botstatec");
    if (pc) vb.insertBefore(C, pc); else vb.insertBefore(C, after ? after.nextSibling : vb.firstChild);
    var S = null, SEL = 0, BUSY = false, ERR = "", SIG = "", LH = "", TK = 0, SIZES = [10, 20, 30];
    function usd(n) { return "$" + (Math.round(Number(n) * 100) / 100).toFixed(2); }
    function pct(n) { return String(+Number(n).toFixed(2)); }
    function on() { return ready() && (S ? !S.owner : !!ERR); }          /* hidden while loading and for the owner; a failed first load shows its message */
    function confirmBox(k) {
      var v = S.tiers[String(k)] || {}, m = (S.minlot || {})[String(k)] || {}, bal = Number(m.balance) || 0, blocked = !!m.blocked;
      var h = '<div style="border:2px solid var(--line);border-radius:16px;padding:10px 14px;margin:10px 0"><p class="note" style="font-weight:800;color:var(--fg)">The $' + k + " settings will set:</p>";
      h += '<p class="note">' + esc((v.strategies || []).length) + " strategies that may trade alone, " + esc(v.entries) + " entry per setup, " + esc(v.max_open) + " open trade at a time, stop after " + esc(v.streak) + " losses in a row.</p>";
      h += '<p class="note">Risk per trade: ' + esc(pct(v.risk_pct)) + "% of your balance. Burst and every-minute scans: off.</p>";
      if (bal > 0) {
        h += '<p class="note" style="font-weight:800;color:var(--fg)">Most one trade may lose: about ' + esc(usd(m.risk_usd)) + " (" + esc(pct(m.risk_pct)) + "% of your " + esc(usd(bal)) + " balance).</p>";
        h += '<p class="note">If a setup has 2 or more entries, the whole group stops at a loss of ' + esc(usd(bal * Number(v.loss_pct) / 100)) + " (" + esc(pct(v.loss_pct)) + "%).</p>";
      } else h += '<p class="note">Your balance is not known yet, so no dollar amount can be shown.</p>';
      if (m.message) h += '<p class="note" style="color:var(--bad);font-weight:800">' + esc(m.message) + "</p>";
      h += '<p class="note">Not set by this: ' + esc((S.not_included || []).join("; ").toLowerCase()) + ".</p>";
      h += '<div class="jrow"><button type="button" class="btn primary" data-ok="1"' + (BUSY || blocked ? " disabled" : "") + ">" + (BUSY ? "Saving..." : "Confirm $" + k + " settings") + '</button><button type="button" class="btn" data-no="1"' + (BUSY ? " disabled" : "") + ">Cancel</button></div></div>";
      return h;
    }
    function html() {
      var h = '<div class="card-head"><h2>Small account settings</h2>' + (S && S.active ? '<span class="chip info">$' + esc(S.active) + " on</span>" : "") + "</div>";
      if (!S) return h + '<p class="note">' + esc(ERR || "Loading...") + "</p>";
      h += '<p class="note">One tap picks smaller, fewer trades for a small account. It only changes your own settings, and you can go back. It does not make money or keep an account safe.</p>';
      h += '<div class="seg" role="group" aria-label="Account size" style="justify-self:start;max-width:100%">' + SIZES.map(function (k) {
        return '<button type="button" data-p="' + k + '" aria-pressed="' + ((SEL || S.active) === k) + '"' + (!S.demo || BUSY ? " disabled" : "") + ">$" + k + "</button>"; }).join("") + "</div>";
      if (!S.demo) h += '<p class="note">Try these on a Demo account first. Switch to Demo above, then pick a size.</p>';
      if (SEL && S.demo) h += confirmBox(SEL);
      if (ERR) h += '<p class="note" style="color:var(--bad)">' + esc(ERR) + "</p>";
      if (S.can_undo) h += '<div class="jrow"><button type="button" class="btn" data-undo="1"' + (BUSY ? " disabled" : "") + ">Back to my old settings</button></div>";
      return h;
    }
    function paint() {
      var show = on(); C.hidden = !show; C.style.display = show ? "" : "none";
      if (!show) { if (LH) { C.innerHTML = ""; LH = ""; } return; }
      var h = html(); if (h !== LH) C.innerHTML = LH = h;
    }
    function load() {
      if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
      return SXA.api("/api/presets").then(function (j) { S = j; ERR = ""; }, function () { if (!S) ERR = "Cannot reach the server."; }).then(function () { BUSY = false; paint(); });
    }
    function send(body, done) {
      BUSY = true; ERR = ""; paint();
      SXA.api("/api/presets", { method: "POST", body: body }).then(function (j) { S = j; SEL = 0; BUSY = false; toast(done); if (window.sxPrefsReload) window.sxPrefsReload(); paint(); },
        function (x) { ERR = (x && x.message) || "Not saved."; BUSY = false; paint(); });
    }
    C.addEventListener("click", function (e) {
      if (!S || BUSY) return; var t = e.target.closest ? e.target : null; if (!t) return;
      var p = t.closest("[data-p]"), ok = t.closest("[data-ok]"), no = t.closest("[data-no]"), un = t.closest("[data-undo]");
      if (ok) { var ml = (S.minlot || {})[String(SEL)] || {}; if (SEL && S.demo && !ml.blocked) send({ tier: SEL }, "Smaller-risk settings are on"); return; }          /* a size no market can trade at is never sent */
      if (un) { send({ undo: true }, "Your old settings are back"); return; }
      if (no) { SEL = 0; ERR = ""; paint(); return; }
      if (p && S.demo) { SEL = parseInt(p.getAttribute("data-p"), 10) || 0; ERR = ""; paint(); }
    });
    setInterval(function () {
      var u = me(), sg = u ? [u.uid, !!u.verified].join("|") : ""; TK++;
      if (sg !== SIG) { SIG = sg; S = null; SEL = 0; ERR = ""; paint(); if (u) load(); return; }
      if (ready() && vb.classList.contains("on") && !document.hidden && !SEL && TK % 30 === 0) load();
    }, 1000);
    new MutationObserver(function () { if (ready() && vb.classList.contains("on") && !BUSY && !SEL) load(); }).observe(vb, { attributes: true, attributeFilter: ["class"] });
    paint();
  })();

'''
s = s.replace(HOOK_OLD, HOOK_NEW)
MARK = "  /* ---------- B. Open trades"
s = s.replace(MARK, CARD + MARK, 1)
open(P, 'w', encoding='utf-8').write(s); print(P, ': edited')
