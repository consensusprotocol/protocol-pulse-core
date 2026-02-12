const CACHE_NAME = 'protocol-pulse-v6-nexus';
const OFFLINE_URL = '/offline';
const DB_NAME = 'pulse-nexus-events';
const DB_STORE = 'events';
const DB_VERSION = 1;
const MAX_EVENTS = 100;

const STATIC_ASSETS = [
  '/',
  '/hub',
  '/signal-terminal',
  '/offline',
  '/static/css/style.css',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

const EVENT_ENDPOINTS = [
  '/api/hub/automation-log',
  '/api/signal-terminal/recent'
];

let sovereignModeEnabled = false;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(DB_STORE)) {
        const store = db.createObjectStore(DB_STORE, { keyPath: 'id', autoIncrement: true });
        store.createIndex('channel', 'channel', { unique: false });
        store.createIndex('ts', 'ts', { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function persistEvent(channel, payload) {
  try {
    const db = await openDb();
    const tx = db.transaction(DB_STORE, 'readwrite');
    const store = tx.objectStore(DB_STORE);
    store.add({
      channel: channel || 'unknown',
      payload: payload || {},
      ts: Date.now()
    });
    await new Promise((resolve) => (tx.oncomplete = resolve));

    const trimTx = db.transaction(DB_STORE, 'readwrite');
    const trimStore = trimTx.objectStore(DB_STORE);
    const allReq = trimStore.getAll();
    const all = await new Promise((resolve) => {
      allReq.onsuccess = () => resolve(allReq.result || []);
      allReq.onerror = () => resolve([]);
    });
    const byChannel = {};
    for (const row of all) {
      const ch = row.channel || 'unknown';
      if (!byChannel[ch]) byChannel[ch] = [];
      byChannel[ch].push(row);
    }
    for (const ch of Object.keys(byChannel)) {
      byChannel[ch].sort((a, b) => b.ts - a.ts);
      for (const stale of byChannel[ch].slice(MAX_EVENTS)) {
        trimStore.delete(stale.id);
      }
    }
    await new Promise((resolve) => (trimTx.oncomplete = resolve));
  } catch (e) {
    // Silent: storage failure should not break app usage.
  }
}

self.addEventListener('message', (event) => {
  if (!event.data) return;
  if (event.data.type === 'SOVEREIGN_MODE') {
    sovereignModeEnabled = !!event.data.enabled;
    return;
  }
  if (event.data.type === 'CACHE_EVENT') {
    event.waitUntil(persistEvent(event.data.channel, event.data.payload));
  }
});

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(cacheNames.map((cacheName) => (cacheName !== CACHE_NAME ? caches.delete(cacheName) : undefined)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const requestUrl = new URL(event.request.url);

  if (sovereignModeEnabled) {
    const blockedDomains = ['google-analytics.com', 'googletagmanager.com', 'doubleclick.net', 'clarity.ms'];
    if (blockedDomains.some((d) => requestUrl.host.includes(d))) {
      event.respondWith(new Response('', { status: 204 }));
      return;
    }
  }

  const isEventApi = EVENT_ENDPOINTS.some((path) => requestUrl.pathname === path);
  if (isEventApi) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.ok) {
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, response.clone()));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(event.request);
          if (cached) return cached;
          return new Response(JSON.stringify({ events: [], lines: [] }), {
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.ok) {
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, response.clone()));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(event.request);
          if (cached) return cached;
          return caches.match(OFFLINE_URL);
        })
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) return cachedResponse;
      return fetch(event.request).then((response) => {
        if (response && response.ok && response.type === 'basic') {
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, response.clone()));
        }
        return response;
      });
    })
  );
});

self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  const title = data.title || 'Protocol Pulse';
  const options = {
    body: data.body || 'New intelligence available',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    vibrate: [100, 50, 100],
    data: { url: data.url || '/hub' },
    actions: [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(event.notification.data.url) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(event.notification.data.url || '/hub');
    })
  );
});
