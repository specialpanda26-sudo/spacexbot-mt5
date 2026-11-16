/* spaceXBot web client. Firebase handles sign-in; the server decides who you are and what you may do.
   Nothing about a person is kept in localStorage any more. */
(function () {
  "use strict";
  var cfg = (window.SXB && window.SXB.fb) || {}, ok = !!(cfg.apiKey && window.firebase), A = null, ME = null, sink = null, done = false, first = true;

  function norm(j) {
    return { uid: j.uid, name: j.name || (j.email || "").split("@")[0], email: j.email || "", verified: !!j.verified, admin: !!j.admin, active: !!j.active,
      plan_until: j.plan_until || 0, created: j.created || 0, dob: j.dob || null, age: j.age || null, gender: j.gender || null, prof: j.prof || {}, raw: j };
  }
  function tok(force) { return A && A.currentUser ? A.currentUser.getIdToken(!!force) : Promise.resolve(null); }
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
  function load() { return api("/api/me").then(function (j) { ME = norm(j); return ME; }); }
  function fire() { if (sink) sink(ME, first); }
  function need() { if (!ok) return Promise.reject(Object.assign(new Error("Sign-in is not set up on this server yet."), { code: "sxb/config" })); return null; }

  var ready = new Promise(function (res) {
    if (!ok) { done = true; res(); return; }
    firebase.initializeApp(cfg); A = firebase.auth();
    A.onAuthStateChanged(function (fu) {
      var p = fu ? load().catch(function () { ME = null; if (window.sxToast) window.sxToast("Cannot reach the server. Try again shortly."); }) : (ME = null, Promise.resolve());
      p.then(function () { var f = !done; done = true; first = f; fire(); first = false; res(); });
    });
  });

  var X = {
    ready: ready, api: api, user: function () { return ME; }, resolved: function () { return done; }, configured: ok,
    bind: function (fn) { sink = fn; if (done) { first = true; fire(); first = false; } },
    refresh: function () { return load().then(function (m) { fire(); return m; }); },
    signUp: function (name, email, pw) {
      var n = need(); if (n) return n;
      return A.createUserWithEmailAndPassword(email, pw).then(function (c) {
        return c.user.updateProfile({ displayName: name }).then(function () { return c.user.sendEmailVerification().catch(function () {}); })
          .then(function () { return load(); }).then(function () { return api("/api/me/profile", { method: "POST", body: { name: name } }); }).then(load);
      });
    },
    signIn: function (email, pw, remember) {
      var n = need(); if (n) return n;
      var P = firebase.auth.Auth.Persistence;
      return A.setPersistence(remember ? P.LOCAL : P.SESSION).then(function () { return A.signInWithEmailAndPassword(email, pw); }).then(load);
    },
    google: function () {
      var n = need(); if (n) return n;
      return A.signInWithPopup(new firebase.auth.GoogleAuthProvider()).then(load);
    },
    signOut: function () { ME = null; return A ? A.signOut() : Promise.resolve(); },
    resetPassword: function (email) { var n = need(); return n || A.sendPasswordResetEmail(email); },
    resendVerification: function () { var n = need(); if (n) return n; if (!A.currentUser) return Promise.reject(new Error("Log in first.")); return A.currentUser.sendEmailVerification(); },
    checkVerified: function () {
      var n = need(); if (n) return n; if (!A.currentUser) return Promise.resolve(false);
      return A.currentUser.reload().then(function () { return A.currentUser.getIdToken(true); }).then(load).then(function (m) { fire(); return m.verified; });
    },
    save: function (o) { return api("/api/me/profile", { method: "POST", body: o }).then(load); },
    changePassword: function (cur, np) {
      var n = need(); if (n) return n; var u = A.currentUser;
      if (!u || !u.providerData.some(function (p) { return p.providerId === "password"; })) return Promise.reject(new Error("You signed in with Google, so there is no password to change here."));
      return u.reauthenticateWithCredential(firebase.auth.EmailAuthProvider.credential(u.email, cur)).then(function () { return u.updatePassword(np); });
    },
    signoutEverywhere: function () { return api("/api/me/signout-others", { method: "POST" }).then(function () { return X.signOut(); }); },
    deleteAccount: function () { return api("/api/me", { method: "DELETE" }).then(function () { return X.signOut(); }); },
    err: function (e) {
      var c = (e && e.code) || "", m = {
        "auth/invalid-credential": "Wrong email or password.", "auth/wrong-password": "Wrong email or password.", "auth/user-not-found": "Wrong email or password.",
        "auth/invalid-login-credentials": "Wrong email or password.", "auth/email-already-in-use": "That email already has an account. Log in instead.",
        "auth/weak-password": "Choose a stronger password (8+ characters).", "auth/invalid-email": "Enter a valid email.",
        "auth/too-many-requests": "Too many tries. Wait a few minutes and try again.", "auth/popup-closed-by-user": "Google sign-in was cancelled.",
        "auth/cancelled-popup-request": "Google sign-in was cancelled.", "auth/popup-blocked": "Your browser blocked the Google window. Allow pop-ups and try again.",
        "auth/network-request-failed": "No connection. Check your internet.", "auth/requires-recent-login": "For security, log in again and retry.",
        "auth/user-disabled": "This account has been disabled."
      };
      return m[c] || (e && e.message) || "Something went wrong. Try again.";
    }
  };
  window.SXA = X;
})();
