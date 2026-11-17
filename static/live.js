/* spaceXBot web client. Supabase handles sign-in (Google, or email + 6-digit code); the server decides who you are and what you may do. */
(function () {
  "use strict";
  var cfg = (window.SXB && window.SXB.sb) || {}, ok = !!(cfg.url && cfg.key && window.supabase), S = null, ME = null, sink = null, done = false, first = true, PEND = null, lastUid = null, HOLD = false;

  function norm(j) {
    return { uid: j.uid, name: j.name || (j.email || "").split("@")[0], email: j.email || "", verified: !!j.verified, admin: !!j.admin, active: !!j.active,
      plan_until: j.plan_until || 0, created: j.created || 0, onboarded: j.onboarded !== false, dob: j.dob || null, age: j.age || null, gender: j.gender || null, prof: j.prof || {}, raw: j };
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
  function fire() { if (sink && !HOLD) sink(ME, first); }
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
    signUp: function (name, email, pw, extra) {
      var n = need(); if (n) return n;
      return S.auth.signUp({ email: email, password: pw, options: { data: { full_name: name, dob: extra && extra.dob, gender: extra && extra.gender } } }).then(chk).then(function (d) {
        if (d.user && d.user.identities && !d.user.identities.length) { var e = new Error("That email already has an account. Log in instead."); e.code = "user_already_exists"; throw e; }
        if (d.session) return extra ? api("/api/me/profile", { method: "POST", body: extra }).then(load) : load();
        PEND = { email: email, name: name, extra: extra || null }; return { pending: true, email: email, name: name };
      });
    },
    signIn: function (email, pw) {
      var n = need(); if (n) return n;
      return S.auth.signInWithPassword({ email: email, password: pw }).then(function (r) {
        if (r.error) {
          if (r.error.code === "email_not_confirmed" || /not confirmed/i.test(r.error.message || "")) {
            PEND = { email: email, name: "" };
            /* A code was already sent at sign-up. If this resend is rate-limited (Supabase: 1 per 60 s per user) the code screen must still open. */
            return S.auth.resend({ type: "signup", email: email }).then(function () { return { pending: true, email: email }; }, function () { return { pending: true, email: email }; });
          }
          throw r.error;
        }
        return load();
      });
    },
    verifyCode: function (email, code) {
      var n = need(); if (n) return n;
      return S.auth.verifyOtp({ email: email, token: code, type: "signup" }).then(chk).then(load).then(function (m) {
        var nm = PEND && PEND.name, b = Object.assign({}, (PEND && PEND.extra) || {}); PEND = null; if (nm) b.name = nm;
        return Object.keys(b).length ? api("/api/me/profile", { method: "POST", body: b }).then(load) : m;
      });
    },
    resendCode: function (email) { var n = need(); return n || S.auth.resend({ type: "signup", email: email }).then(chk); },
    google: function () {
      var n = need(); if (n) return n;
      var cap = window.Capacitor, gid = (window.SXB && window.SXB.gid) || "";
      var wv = /; wv\)/.test(navigator.userAgent), isNat = !!(cap && cap.isNativePlatform && cap.isNativePlatform());   /* sxb-no-browser */
      if (cap && cap.isNativePlatform && cap.isNativePlatform() && cap.registerPlugin && gid) {
        var raw = Array.prototype.map.call(crypto.getRandomValues(new Uint8Array(16)), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
        return crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw)).then(function (h) {
          var hashed = Array.prototype.map.call(new Uint8Array(h), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
          return cap.registerPlugin("GoogleSignIn").signIn({ serverClientId: gid, nonce: hashed });
        }).then(function (r) {
          if (!r || !r.idToken) throw new Error("Google sign-in failed. Try again.");
          return S.auth.signInWithIdToken({ provider: "google", token: r.idToken, nonce: raw });
        }).then(chk).then(load).catch(function (e) {
          if (e && (e.code === "CANCELLED" || /^cancel/i.test(String(e.message || "")))) { var c = new Error("Google sign-in was cancelled."); c.code = "cancelled"; throw c; }
          var c0 = e && e.code;
          if (c0 === "NO_ACCOUNT" || c0 === "FAILED" || c0 === "UNIMPLEMENTED") {
            var m0 = String((e && e.message) || c0); try { localStorage.setItem("sxb_g_why", m0 + " @ " + new Date().toISOString()); } catch (x) {}
            throw new Error("Google account list could not open: " + m0.slice(0, 160));
          }
          throw e;
        });
      }
      /* inside the app the browser page is never used: say what is missing instead */
      if (wv || isNat) return Promise.reject(new Error("The app could not open your Google accounts. (Capacitor " + (cap ? "found" : "missing") + ", native " + isNat + ", plugin " + typeof (cap && cap.registerPlugin) + ", id " + (gid ? "set" : "empty") + ")"));
      return S.auth.signInWithOAuth({ provider: "google", options: { redirectTo: location.origin + "/" } }).then(chk).then(function () { return new Promise(function () {}); });
    },
    signOut: function () { ME = null; lastUid = null; return S ? S.auth.signOut() : Promise.resolve(); },
    resetPassword: function (email) { var n = need(); return n || S.auth.resetPasswordForEmail(email).then(chk); },
    /* Reset runs in two steps so the code squares and the new-password screen can be separate pages.
       Between the steps the page is "held": the recovery sign-in must not push the app behind the overlay to #home. */
    resetVerify: function (email, code) {
      var n = need(); if (n) return n;
      HOLD = true;
      return S.auth.verifyOtp({ email: email, token: code, type: "recovery" }).then(chk).then(function () { return true; }).catch(function (e) { HOLD = false; throw e; });
    },
    resetSave: function (pw) {
      var n = need(); if (n) return n;
      return S.auth.updateUser({ password: pw }).then(chk).then(load).then(function (m) { HOLD = false; fire(); return m; });
    },
    resetAbort: function () { HOLD = false; ME = null; lastUid = null; return S ? S.auth.signOut().catch(function () {}) : Promise.resolve(); },
    resendVerification: function () { return ME ? Promise.resolve() : Promise.reject(new Error("Log in first.")); },
    checkVerified: function () { return Promise.resolve(!!(ME && ME.verified)); },
    finishOnboarding: function () { if (ME) ME.onboarded = true; return api("/api/me/profile", { method: "POST", body: { onboarded: true } }).catch(function () {}); },
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
        weak_password: "Choose a stronger password (8+ characters).", validation_failed: "Enter a valid email.", email_address_invalid: "Enter a valid email.",
        over_request_rate_limit: "Too many tries. Wait a few minutes and try again.", over_email_send_rate_limit: "Your code is already on its way. Use the one we sent.",
        otp_expired: "That code didn't match. Check it and try once more.", same_password: "Choose a password different from your old one.", user_banned: "This account has been disabled.",
        email_not_confirmed: "Confirm your email first. We sent you a code.", signup_disabled: "New sign-ups are turned off right now.", email_provider_disabled: "Email sign-in is turned off right now.",
        email_address_not_authorized: "We cannot send email to that address right now. Contact support.", user_not_found: "No account found for that email.",
        session_not_found: "Your session ended. Log in again.", session_expired: "Your session ended. Log in again.", reauthentication_needed: "Log in again to do that."
      };
      var sec = /(\d+)\s*seconds?/i.exec(m);
      if ((c === "over_email_send_rate_limit" || /only request this once every/i.test(m)) && sec) return "Your code is still good. Use the one we sent, or ask for a new one in " + (+sec[1] >= 120 ? Math.ceil(+sec[1] / 60) + " minutes." : sec[1] + " seconds.");
      if (t[c]) return t[c];
      if (/error sending (confirmation|recovery|magic link|email)/i.test(m) || (c === "unexpected_failure" && /email|smtp|mail/i.test(m))) return "We could not send the email. Try again in a minute.";
      if (/invalid login/i.test(m)) return "Wrong email or password.";
      if (/token has expired|invalid/i.test(m) && /token|otp|code/i.test(m)) return t.otp_expired;
      if (/failed to fetch|network/i.test(m)) return "No connection. Check your internet.";
      return m || "Something went wrong. Try again.";
    }
  };
  window.SXA = X;
})();
