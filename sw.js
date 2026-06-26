// AUTO-EVO-AI V0.1 — Service Worker (2026-06-25)
// 修复：JS 改为 Network-First，缓存版本号 +1 强制手机刷新

const CACHE_NAME = 'evo-ai-v0.7';
const STATIC_CACHE = 'evo-ai-static-v0.4';
const API_CACHE = 'evo-ai-api-v0.3';
const MAX_API_CACHE = 100;

// 需要预缓存的静态资源
const PRECACHE_URLS = [
    '/dashboard',
    '/manifest.json',
    '/icon-192.png',
    '/icon-512.png',
];

// 安装：预缓存核心资源
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(PRECACHE_URLS).catch(() => {
                // 预缓存失败不影响安装
                console.log('[SW] Precache partial');
            });
        })
    );
    self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((key) => key !== STATIC_CACHE && key !== API_CACHE)
                    .map((key) => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

// 请求拦截
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    const isApi = url.pathname.startsWith('/api/');
    const isJS = url.pathname.match(/\.js(\?|$)/);
    const isStatic = url.pathname.match(/\.(css|png|jpg|jpeg|gif|svg|ico|woff2?|ttf|eot)$/);
    
    // API请求：Network-First + 短期缓存
    if (isApi) {
        event.respondWith(networkFirst(event.request, API_CACHE, 5 * 60 * 1000));
        return;
    }
    
    // JS文件：Network-First（修复：必须走网络，避免缓存旧版JS导致功能失效）
    if (isJS) {
        event.respondWith(networkFirst(event.request, STATIC_CACHE, 0));
        return;
    }
    
    // 其他静态资源：Cache-First + 后台更新
    if (isStatic) {
        event.respondWith(cacheFirst(event.request, STATIC_CACHE));
        return;
    }
    
    // 主页面 & Dashboard：Stale-While-Revalidate
    if (url.pathname === '/' || url.pathname === '/dashboard') {
        event.respondWith(staleWhileRevalidate(event.request, STATIC_CACHE));
        return;
    }
    
    // 其他：Network-First
    event.respondWith(networkFirst(event.request, STATIC_CACHE, 24 * 60 * 60 * 1000));
});

// Cache-First策略
async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('Offline', { status: 503, statusText: 'Offline' });
    }
}

// Network-First策略
async function networkFirst(request, cacheName, maxAge) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
            // 限制API缓存数量
            if (cacheName === API_CACHE) {
                trimCache(cacheName, MAX_API_CACHE);
            }
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response(JSON.stringify({ detail: 'Network unavailable' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
        });
    }
}

// Stale-While-Revalidate策略
async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    const fetchPromise = fetch(request)
        .then((response) => {
            if (response.ok) cache.put(request, response.clone());
            return response;
        })
        .catch(() => cached);
    return cached || fetchPromise;
}

// 限制缓存条目数
async function trimCache(cacheName, maxItems) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    if (keys.length > maxItems) {
        const deleteCount = keys.length - maxItems;
        await Promise.all(keys.slice(0, deleteCount).map((key) => cache.delete(key)));
    }
}

// 后台同步
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-pending-ops') {
        event.waitUntil(syncPendingOperations());
    }
});

async function syncPendingOperations() {
    console.log('[SW] Syncing pending operations...');
}

// 推送通知
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : { title: 'AUTO-EVO-AI', body: 'New notification' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/icon-192.png',
            badge: '/icon-192.png',
            vibrate: [100, 50, 100],
            data: data.url || '/',
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        self.clients.openWindow(event.notification.data || '/dashboard')
    );
});
