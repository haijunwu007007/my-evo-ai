self.addEventListener('install',function(){self.skipWaiting()});
self.addEventListener('activate',function(e){e.waitUntil(clients.claim().then(function(){return caches.keys().then(function(ks){return Promise.all(ks.map(function(k){return caches.delete(k)}))})}))});
self.addEventListener('fetch',function(e){e.respondWith(fetch(e.request).catch(function(){return new Response('',{status:503})}))});