self.addEventListener('install',function(e){self.skipWaiting()})
self.addEventListener('activate',function(e){e.waitUntil(self.clients.claim())})
self.addEventListener('fetch',function(e){
  e.respondWith(
    fetch(e.request).catch(function(){return new Response('离线模式',{status:200,headers:{'Content-Type':'text/plain'}})})
  )
})