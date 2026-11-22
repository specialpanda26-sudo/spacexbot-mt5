/* Test Lab card in the Admin panel (owner only; the server answers only for an admin AND TEST_LAB=1). Each button shows a FAKE situation with the site's real screen.
   Nothing is saved, charged or traded. A "Test mode" bar stays on screen while a fake case is showing. */
(function () {
  function $(i) { return document.getElementById(i); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function banner(on) {
    var b = $("tlBan");
    if (!on) { if (b && b.parentNode) b.parentNode.removeChild(b); return; }
    if (b) return;
    b = document.createElement("div"); b.id = "tlBan"; b.setAttribute("role", "status");
    b.style.cssText = "position:fixed;left:0;right:0;top:0;z-index:99999;padding:calc(8px + env(safe-area-inset-top,0px)) 12px 8px;background:#ffb020;color:#1a1a1a;font-weight:700;font-size:13px;display:flex;gap:10px;align-items:center;justify-content:space-between";
    b.innerHTML = '<span>Test mode: this is fake. Nothing was charged, saved or traded.</span><button type="button" id="tlStop" style="min-width:44px;min-height:36px;border:0;border-radius:8px;background:#1a1a1a;color:#fff;font-weight:700">Stop</button>';
    document.body.appendChild(b);
    $("tlStop").onclick = function () { banner(false); try { window.sxLabHooks && window.sxLabHooks.stop(); } catch (e) {} };
  }
  function show(r) {
    if (!r || r.fake !== true) return false;
    banner(true);
    if (r.kind === "deriv") { if (window.sxDerivLogin && window.sxDerivLogin.say) window.sxDerivLogin.say(r.msg); return true; }
    if (r.kind === "pay" && window.sxLabHooks) { window.sxLabHooks.pay(r.what); return true; }
    return false;
  }
  function mount(el) {
    if (!el || el.getAttribute("data-tl")) return; el.setAttribute("data-tl", "1");
    if (!window.SXA || !window.SXA.api) return;
    window.SXA.api("/api/admin/testlab").then(function (j) {
      if (!j || !j.on) { el.innerHTML = '<h3 style="margin:8px 0 0">Test Lab</h3><p class="note">Off. Set TEST_LAB=1 on Render to show fake situations here.</p>'; return; }
      var g = {}, h = '<h3 style="margin:8px 0 0">Test Lab</h3><p class="note">Shows a fake situation with the real screen. Nothing is charged, saved or traded.</p>';
      (j.cases || []).forEach(function (c) { (g[c.group] = g[c.group] || []).push(c); });
      Object.keys(g).forEach(function (k) { h += '<p class="note"><b>' + esc(k) + '</b></p><div style="display:flex;flex-wrap:wrap;gap:8px">' + g[k].map(function (c) { return '<button type="button" class="btn" data-tl-case="' + esc(c.id) + '">' + esc(c.label) + "</button>"; }).join("") + "</div>"; });
      el.innerHTML = h + '<p class="err" id="tlErr"></p>';
      el.onclick = function (e) {
        var b = e.target.closest ? e.target.closest("[data-tl-case]") : null; if (!b) return;
        var er = $("tlErr"); if (er) er.textContent = "";
        window.SXA.api("/api/admin/testlab/run", { method: "POST", body: { case: b.getAttribute("data-tl-case") } }).then(function (r) {
          if (!show(r) && er) er.textContent = "This test case could not be shown.";
        }).catch(function (x) { if (er) er.textContent = (x && x.message) || "Could not run this test."; });
      };
    }).catch(function () { el.innerHTML = ""; });
  }
  function scan() { mount($("tlab")); }
  window.sxTestLab = { mount: mount, show: show, banner: banner };
  try { new MutationObserver(scan).observe(document.body || document.documentElement, { childList: true, subtree: true }); } catch (e) {}
})();
