var CACHE_NAME = 'evo-cache-v1';
var PRECACHE_URLS = ['/', '/frontend/share.css'];
self.addEventListener('install', function(e) {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE_NAME).then(function(c) { return c.addAll(PRECACHE_URLS); }));
});
self.addEventListener('activate', function(e) {
  e.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', function(e) {
  e.respondWith(caches.match(e.request).then(function(r) {
    return r || fetch(e.request).then(function(res) {
      var clone = res.clone();
      caches.open(CACHE_NAME).then(function(c) { if(e.request.method === 'GET') c.put(e.request, clone); });
      return res;
    });
  }).catch(function() { return new Response('离线模式', { status: 200, headers: { 'Content-Type': 'text/plain;charset=utf-8' } }); }));
});
