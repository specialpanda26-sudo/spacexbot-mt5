/* sxb-sw v1 (OF1): when the server is asleep, restarting or down (Render 502/503/504), show the last good copy of the app, else our own page.
   It never touches /api/ (private data is never saved here) and never changes a POST. To switch it off: replace this file with one that only calls registration.unregister(). */
var V = 'sxb-v1', SHELL = '/', OFF = '/offline.html', WAIT = 12000;
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(V).then(function (c) { return c.add(new Request(OFF, { cache: 'reload' })); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k !== V; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); }));
});
function keep(key, r) { try { var c = r.clone(); caches.open(V).then(function (ch) { return ch.put(key, c); }).catch(function () {}); } catch (x) {} }
function race(req, key, fallback) {
  return new Promise(function (res) {
    var done = false, t = setTimeout(function () { if (!done) { done = true; fallback().then(res); } }, WAIT);
    fetch(req).then(function (r) {
      if (r.status >= 500) throw r;
      if (r.ok && !r.redirected) keep(key, r);
      if (!done) { done = true; clearTimeout(t); res(r); }
    }).catch(function () { if (!done) { done = true; clearTimeout(t); fallback().then(res); } });
  });
}
function page() {
  return caches.match(SHELL).then(function (m) { return m || caches.match(OFF); }).then(function (m) { return m || new Response('spaceXBot is offline. Try again soon.', { status: 503, headers: { 'Content-Type': 'text/plain' } }); });
}
self.addEventListener('fetch', function (e) {
  var req = e.request; if (req.method !== 'GET' || req.headers.get('range')) return;
  var u = new URL(req.url); if (u.origin !== self.location.origin) return;
  var p = u.pathname;
  if (req.mode === 'navigate') { e.respondWith(race(req, SHELL, page)); return; }
  if (p.indexOf('/static/') === 0 || p === '/config.js' || p === '/favicon.ico') {
    e.respondWith(race(req, req.url, function () { return caches.match(req.url).then(function (m) { return m || new Response('', { status: 504 }); }); }));
  }
});
