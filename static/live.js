/* spaceXBot web client. Supabase handles sign-in (Google, or email + 6-digit code); the server decides who you are and what you may do. */
(function () {
  "use strict";
  var cfg = (window.SXB && window.SXB.sb) || {}, ok = !!(cfg.url && cfg.key && window.supabase), S = null, ME = null, sink = null, done = false, first = true, PEND = null, lastUid = null;

  function norm(j) {
    return { uid: j.uid, name: j.name || (j.email || "").split("@")[0], email: j.email || "", verified: !!j.verified, admin: !!j.admin, active: !!j.active,
      plan_until: j.plan_until || 0, created: j.created || 0, dob: j.dob || null, age: j.age || null, gender: j.gender || null, prof: j.prof || {}, raw: j };
  }
  function tok() { return S ? S.auth.getSession().then(function (r) { return r.data && r.data.session ? r.data.session.access_token : null; }) : Promise.resolve(null); }
  function api(path, o) {
    o = o || {};
    return tok().then(function (t) {
      var h = { "Content-Type": "application/json" }; if (t) h.Authorization = "Bearer " + t;
      return fetch(path, { method: o.method || "GET", headers: h, body: o.body ? JSON.stringify(o.body) : undefined }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) { var e = new Error(j.error || "Request failed (" + r.status + ")"); e.status = r.status; throw e; }
          return j;
        });
      });
    });
  }
  function load() { return api("/api/me").then(function (j) { ME = norm(j); lastUid = ME.uid; return ME; }); }
  function fire() { if (sink) sink(ME, first); }
  function need() { if (!ok) return Promise.reject(Object.assign(new Error("Sign-in is not set up on this server yet."), { code: "sxb/config" })); return null; }
  function chk(r) { if (r.error) throw r.error; return r.data; }

  var ready = new Promise(function (res) {
    if (!ok) { done = true; res(); return; }
    S = window.supabase.createClient(cfg.url, cfg.key, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } });
    S.auth.onAuthStateChange(function (ev, ses) {
      if (ev === "TOKEN_REFRESHED" || ev === "USER_UPDATED") return;
      if (ev === "SIGNED_IN" && ses && ses.user && ses.user.id === lastUid) return;
      setTimeout(function () {   /* never call Supabase inside its own callback */
        var p = ses ? load().catch(function () { ME = null; if (window.sxToast) window.sxToast("Cannot reach the server. Try again shortly."); }) : (ME = null, lastUid = null, Promise.resolve());
        p.then(function () { var f = !done; done = true; first = f; fire(); first = false; res(); });
      }, 0);
    });
  });

  var X = {
    ready: ready, api: api, user: function () { return ME; }, resolved: function () { return done; }, configured: ok,
    bind: function (fn) { sink = fn; if (done) { first = true; fire(); first = false; } },
    refresh: function () { return load().then(function (m) { fire(); return m; }); },
    signUp: function (name, email, pw) {
      var n = need(); if (n) return n;
      return S.auth.signUp({ email: email, password: pw, options: { data: { full_name: name } } }).then(chk).then(function (d) {
        if (d.user && d.user.identities && !d.user.identities.length) { var e = new Error("That email already has an account. Log in instead."); e.code = "user_already_exists"; throw e; }
        if (d.session) return load();
        PEND = { email: email, name: name }; return { pending: true, email: email, name: name };
      });
    },
    signIn: function (email, pw) {
      var n = need(); if (n) return n;
      return S.auth.signInWithPassword({ email: email, password: pw }).then(function (r) {
        if (r.error) {
          if (r.error.code === "email_not_confirmed" || /not confirmed/i.test(r.error.message || "")) {
            PEND = { email: email, name: "" };
            return S.auth.resend({ type: "signup", email: email }).then(function () { return { pending: true, email: email }; });
          }
          throw r.error;
        }
        return load();
      });
    },
    verifyCode: function (email, code) {
      var n = need(); if (n) return n;
      return S.auth.verifyOtp({ email: email, token: code, type: "signup" }).then(chk).then(load).then(function (m) {
        var nm = PEND && PEND.name; PEND = null;
        return nm ? api("/api/me/profile", { method: "POST", body: { name: nm } }).then(load) : m;
      });
    },
    resendCode: function (email) { var n = need(); return n || S.auth.resend({ type: "signup", email: email }).then(chk); },
    google: function () {
      var n = need(); if (n) return n;
      return S.auth.signInWithOAuth({ provider: "google", options: { redirectTo: location.origin + "/" } }).then(chk).then(function () { return new Promise(function () {}); });
    },
    signOut: function () { ME = null; lastUid = null; return S ? S.auth.signOut() : Promise.resolve(); },
    resetPassword: function (email) { var n = need(); return n || S.auth.resetPasswordForEmail(email).then(chk); },
    resetWithCode: function (email, code, pw) {
      var n = need(); if (n) return n;
      return S.auth.verifyOtp({ email: email, token: code, type: "recovery" }).then(chk).then(function () { return S.auth.updateUser({ password: pw }); }).then(chk).then(load);
    },
    resendVerification: function () { return ME ? Promise.resolve() : Promise.reject(new Error("Log in first.")); },
    checkVerified: function () { return Promise.resolve(!!(ME && ME.verified)); },
    save: function (o) { return api("/api/me/profile", { method: "POST", body: o }).then(load); },
    changePassword: function (cur, np) {
      var n = need(); if (n) return n;
      return S.auth.getUser().then(chk).then(function (d) {
        var u = d.user, pr = (u.app_metadata && u.app_metadata.providers) || [];
        if (pr.indexOf("email") < 0) throw new Error("You signed in with Google, so there is no password to change here.");
        return S.auth.signInWithPassword({ email: u.email, password: cur }).then(function (r) { if (r.error) throw r.error; return S.auth.updateUser({ password: np }); }).then(chk);
      });
    },
    signoutEverywhere: function () { return api("/api/me/signout-others", { method: "POST" }).then(function () { return X.signOut(); }); },
    deleteAccount: function () { return api("/api/me", { method: "DELETE" }).then(function () { return X.signOut(); }); },
    err: function (e) {
      var c = (e && e.code) || "", m = (e && e.message) || "", t = {
        invalid_credentials: "Wrong email or password.", user_already_exists: "That email already has an account. Log in instead.", email_exists: "That email already has an account. Log in instead.",
        weak_password: "Choose a stronger password (8+ characters).", validation_failed: "Enter a valid email.", over_request_rate_limit: "Too many tries. Wait a few minutes and try again.",
        over_email_send_rate_limit: "Too many emails sent. Wait a few minutes and try again.", otp_expired: "That code is wrong or has expired. Request a new one.",
        same_password: "Choose a password different from your old one.", user_banned: "This account has been disabled."
      };
      if (t[c]) return t[c];
      if (/invalid login/i.test(m)) return "Wrong email or password.";
      if (/token has expired|invalid/i.test(m) && /token|otp|code/i.test(m)) return t.otp_expired;
      if (/failed to fetch|network/i.test(m)) return "No connection. Check your internet.";
      return m || "Something went wrong. Try again.";
    }
  };
  window.SXA = X;
})();
