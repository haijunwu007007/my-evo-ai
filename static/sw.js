/* AUTO-EVO-AI Service Worker — 离线缓存策略 */
const CACHE = 'evo-v1';
const PRECACHE = ['/', '/admin', '/manifest.json', '/sw.js', '/workflow'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // API请求不缓存，走网络
  if (url.pathname.startsWith('/api/')) {
    return e.respondWith(fetch(e.request).catch(() => new Response(JSON.stringify({error:'离线'}), {status:503, headers:{'Content-Type':'application/json'}})));
  }
  // 静态资源：缓存优先，网络更新
  e.respondWith(
    caches.match(e.request).then(cached => {
      const fetchPromise = fetch(e.request).then(networkResp => {
        if (networkResp && networkResp.status === 200) {
          const clone = networkResp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return networkResp;
      }).catch(() => cached || new Response('离线', {status:503}));
      return cached || fetchPromise;
    })
  );
});
