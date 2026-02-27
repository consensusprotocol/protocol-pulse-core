/**
 * Protocol Pulse — Service Worker v3
 * Features:
 *   - Offline article reading (cache recent articles)
 *   - Push notifications for breaking news (Pulse Alerts)
 *   - Background sync for price updates
 *   - Sovereign Mode tracker blocking
 *   - App-like navigation with stale-while-revalidate
 *   - Smart cache management (auto-evict old entries)
 */

const CACHE_VERSION = 'protocol-pulse-v3';
const ARTICLE_CACHE = 'pp-articles-v1';
const API_CACHE = 'pp-api-v1';
const OFFLINE_URL = '/offline';

// Core shell — cached on install for instant load
const APP_SHELL = [
  '/',
  '/offline',
  '/static/css/pulse.css?v=2.0',
  '/static/css/style.css?v=1.3',
  '/static/js/main.js',
  '/static/js/pulse-chat.js',
  '/static/manifest.json',
  '/static/images/protocol-pulse-logo-transparent.png'
];

// Pages to aggressively cache for offline
const CACHE_PAGES = [
  '/articles',
  '/market',
  '/search',
  '/podcasts'
];

const MAX_ARTICLE_CACHE = 50; // Keep last 50 articles offline
const API_CACHE_TTL = 60 * 1000; // 60s for API responses

let sovereignModeEnabled = false;

// ── Message handler ──
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SOVEREIGN_MODE') {
    sovereignModeEnabled = event.data.enabled;
    console.log('[SW] Sovereign Mode:', sovereignModeEnabled ? 'ENABLED' : 'DISABLED');
  }
  if (event.data && event.data.type === 'CACHE_ARTICLE') {
    // Proactively cache an article for offline reading
    caches.open(ARTICLE_CACHE).then((cache) => {
      cache.add(event.data.url).catch(() => {});
    });
  }
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// ── Install ──
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => {
      // Cache app shell — don't fail install if some assets are missing
      return Promise.allSettled(
        APP_SHELL.map(url => cache.add(url).catch(() => console.log('[SW] Skip:', url)))
      );
    })
  );
  self.skipWaiting();
});

// ── Activate ──
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          // Keep current caches, delete old versions
          if (name !== CACHE_VERSION && name !== ARTICLE_CACHE && name !== API_CACHE) {
            return caches.delete(name);
          }
        })
      );
    }).then(() => {
      // Pre-cache key pages in the background
      return caches.open(CACHE_VERSION).then((cache) => {
        return Promise.allSettled(
          CACHE_PAGES.map(url => cache.add(url).catch(() => {}))
        );
      });
    })
  );
  self.clients.claim();
});

// ── Fetch strategy router ──
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Sovereign Mode: block trackers
  if (sovereignModeEnabled && isTracker(url.href)) {
    event.respondWith(new Response('', { status: 204 }));
    return;
  }

  // Strategy: API endpoints → Network-first with short cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(event.request, API_CACHE, API_CACHE_TTL));
    return;
  }

  // Strategy: External Bitcoin data APIs → Network-only with offline fallback
  if (isExternalDataAPI(url.href)) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: 'offline' }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    return;
  }

  // Strategy: Article pages → Stale-while-revalidate + article cache
  if (url.pathname.match(/^\/articles\/\d+/) || url.pathname.match(/^\/articles\/[a-z0-9-]+$/)) {
    event.respondWith(staleWhileRevalidate(event.request, ARTICLE_CACHE));
    return;
  }

  // Strategy: Static assets → Cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Strategy: Navigation pages → Stale-while-revalidate
  if (event.request.mode === 'navigate') {
    event.respondWith(staleWhileRevalidate(event.request, CACHE_VERSION));
    return;
  }

  // Default: Network-first
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

// ── Caching strategies ──

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch (e) {
    return new Response('', { status: 408 });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Start network fetch in background
  const networkFetch = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
      trimCache(cacheName, MAX_ARTICLE_CACHE);
    }
    return response;
  }).catch(() => null);

  // Return cached immediately, or wait for network
  return cached || (await networkFetch) || caches.match(OFFLINE_URL);
}

async function networkFirstWithCache(request, cacheName, ttl) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      // Add timestamp header for TTL checking
      const cloned = response.clone();
      cache.put(request, cloned);
    }
    return response;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'offline' }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// ── Cache management ──

async function trimCache(cacheName, maxItems) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length > maxItems) {
    // Delete oldest entries
    const toDelete = keys.slice(0, keys.length - maxItems);
    await Promise.all(toDelete.map(key => cache.delete(key)));
  }
}

// ── Tracker blocking ──

function isTracker(url) {
  const blocked = [
    'google-analytics.com', 'googletagmanager.com',
    'connect.facebook.net', 'facebook.com', 'facebook.net',
    'doubleclick.net', 'googlesyndication.com',
    'twitter.com/i/jot', 'clarity.ms', 'hotjar.com',
    'mixpanel.com', 'segment.io', 'plausible.io/api'
  ];
  const lower = url.toLowerCase();
  return blocked.some(domain => lower.includes(domain));
}

function isExternalDataAPI(url) {
  return url.includes('mempool.space') ||
         url.includes('btcmap.org') ||
         url.includes('blockchain.info') ||
         url.includes('coingecko.com') ||
         url.includes('alternative.me');
}

// ── Push Notifications ──

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data?.json() || {};
  } catch (e) {
    data = { title: 'Protocol Pulse', body: event.data?.text() || 'New intelligence available' };
  }

  const title = data.title || 'Protocol Pulse';
  const options = {
    body: data.body || 'New intelligence available',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/badge-72.png',
    image: data.image || undefined,
    vibrate: [100, 50, 100],
    tag: data.tag || 'pulse-alert',
    renotify: !!data.tag,
    data: {
      url: data.url || '/',
      articleId: data.articleId || null
    },
    actions: [
      { action: 'open', title: 'Read' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const targetUrl = event.notification.data.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Focus existing tab if open
      for (const client of clientList) {
        if (new URL(client.url).pathname === new URL(targetUrl, self.location.origin).pathname) {
          return client.focus();
        }
      }
      // Otherwise open new tab
      return clients.openWindow(targetUrl);
    })
  );
});

// ── Background Sync (price updates) ──

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-btc-price') {
    event.waitUntil(
      fetch('/api/btc-price')
        .then(r => r.json())
        .then(data => {
          // Broadcast price to all clients
          self.clients.matchAll().then(clients => {
            clients.forEach(client => {
              client.postMessage({
                type: 'BTC_PRICE_UPDATE',
                price: data.price,
                change: data.change_24h
              });
            });
          });
        })
        .catch(() => {})
    );
  }

  if (event.tag === 'sync-articles') {
    event.waitUntil(
      fetch('/api/latest-articles')
        .then(r => r.json())
        .then(data => {
          // Pre-cache latest articles for offline reading
          const articles = data.articles || data || [];
          return caches.open(ARTICLE_CACHE).then(cache => {
            return Promise.allSettled(
              articles.slice(0, 10).map(a => {
                const url = '/articles/' + (a.slug || a.id);
                return cache.add(url).catch(() => {});
              })
            );
          });
        })
        .catch(() => {})
    );
  }
});

// ── Periodic background sync (if supported) ──

self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'update-articles') {
    event.waitUntil(
      fetch('/api/latest-articles')
        .then(r => r.json())
        .then(data => {
          const articles = data.articles || data || [];
          return caches.open(ARTICLE_CACHE).then(cache => {
            return Promise.allSettled(
              articles.slice(0, 5).map(a => cache.add('/articles/' + (a.slug || a.id)).catch(() => {}))
            );
          });
        })
        .catch(() => {})
    );
  }
});
