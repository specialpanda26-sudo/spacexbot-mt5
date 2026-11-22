/* C-AUTH 2: the "Log in with Deriv" button in the Deriv connect card + the message when Deriv sends the person back.
   Server side is backend/deriv_oauth.py (C-AUTH 1). This file never sees a token or a code: it only opens the address the server gives
   (it must be on auth.deriv.com) and shows the plain-words result the server saved. Pasting a token still works as before. */
(function () {
  var OK_HOST = "https://auth.deriv.com/";
  function $(id) { return document.getElementById(id); }
  function say(t) { var e = $("toast"); if (!e) return; e.textContent = t; e.hidden = false; clearTimeout(say.t); say.t = setTimeout(function () { e.hidden = true; }, 4500); }
  function logo() {
    var l = window.sxLogo && window.sxLogo("Deriv", 22);
    return l || '<span aria-hidden="true" style="display:inline-flex;width:22px;height:22px;border-radius:6px;background:#ff444f;color:#fff;font-weight:800;align-items:center;justify-content:center;font-size:13px">D</span>';
  }
  function html() {
    return '<div class="field"><button type="button" class="btn primary block" id="pL" style="display:flex;align-items:center;justify-content:center;gap:10px">' + logo() +
      '<span>Log in with Deriv</span></button><p class="muted" id="pLn">Deriv\'s own page opens. You never copy a token. We only ask to trade, never to withdraw.</p></div>' +
      '<p class="muted" style="text-align:center">or paste a token instead</p>';
  }
  function wire(btn, err) {
    if (!btn) return;
    var note = $("pLn");
    function msg(t) { if (err) err.textContent = t || ""; }
    if (window.SXA && window.SXA.api) window.SXA.api("/api/deriv/login-status").then(function (s) {
      if (!note || !s) return;
      if (s.seconds_left === null || s.seconds_left === undefined) return;
      note.textContent = s.seconds_left > 0 ? "Logged in with Deriv. It lasts about " + Math.max(1, s.days_left) + " more day(s), then tap again." : "Your Deriv login ended. Tap Log in with Deriv again.";
    }).catch(function () {});
    btn.onclick = function () {
      if (!window.SXA || !window.SXA.api) return msg("Sign in first.");
      btn.disabled = true; msg("Opening Deriv...");
      window.SXA.api("/api/deriv/login").then(function (j) {
        var u = j && j.url;
        if (typeof u !== "string" || u.indexOf(OK_HOST) !== 0) { btn.disabled = false; return msg("Could not open the Deriv login. Try again."); }
        window.location.href = u;
      }).catch(function (x) {
        btn.disabled = false;
        msg(x && x.status === 402 ? "A plan is needed to connect a broker." : x && x.status === 401 ? "Sign in first." : (x && x.message) || "Could not open the Deriv login. Try again.");
      });
    };
  }
  /* Deriv sends the person to /?deriv=ok#connect or /?deriv=fail#connect. Say what happened, then clean the address. */
  function back() {
    var r = (window.location.search || "").match(/[?&]deriv=(ok|fail)\b/); if (!r) return false;
    var good = r[1] === "ok";
    try { window.history.replaceState(null, "", window.location.pathname + (window.location.hash || "")); } catch (e) {}
    var n = 0;
    (function ask() {
      if (!window.SXA || !window.SXA.api) { if (n++ < 12) return setTimeout(ask, 700); return say(good ? "Deriv connected." : "Deriv login did not work. Try again."); }
      window.SXA.api("/api/deriv/login-status").then(function (s) {
        var m = s && s.last && s.last.msg;
        say(m || (good ? "Deriv connected." : "Deriv login did not work. Try again."));
      }).catch(function () { if (n++ < 12) setTimeout(ask, 700); else say(good ? "Deriv connected." : "Deriv login did not work. Try again."); });
    })();
    return true;
  }
  window.sxDerivLogin = { html: html, wire: wire, back: back, say: say };
  back();
})();
