const CACHE_NAME = 'protocol-pulse-v4';
const OFFLINE_URL = '/offline';

const STATIC_ASSETS = [
  '/',
  '/offline',
  '/static/css/style.css',
  '/static/manifest.json'
];

let sovereignModeEnabled = false;

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SOVEREIGN_MODE') {
    sovereignModeEnabled = event.data.enabled;
    console.log('[SW] Sovereign Mode:', sovereignModeEnabled ? 'ENABLED' : 'DISABLED');
  }
});

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  
  // SOVEREIGN MODE: Block external trackers and non-essential CDNs
  if (sovereignModeEnabled) {
    const blockedDomains = [
      'google-analytics.com',
      'googletagmanager.com',
      'connect.facebook.net',
      'facebook.com',
      'facebook.net',
      'doubleclick.net',
      'googlesyndication.com',
      'twitter.com/i/jot',
      'analytics.',
      'tracking.',
      'pixel.',
      'ads.',
      'adservice.',
      'adsense.',
      'clarity.ms',
      'hotjar.com',
      'mixpanel.com',
      'segment.io'
    ];
    
    const url = event.request.url.toLowerCase();
    const isBlocked = blockedDomains.some(domain => url.includes(domain));
    
    if (isBlocked) {
      console.log('[SW] SOVEREIGN MODE: Blocked external tracker:', url);
      event.respondWith(new Response('', { status: 204 }));
      return;
    }
  }
  
  // Allow essential Bitcoin data APIs
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('mempool.space') ||
      event.request.url.includes('btcmap.org') ||
      event.request.url.includes('blockchain.info')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => response)
        .catch(() => new Response(JSON.stringify({error: 'offline'}), {
          headers: {'Content-Type': 'application/json'}
        }))
    );
    return;
  }
  
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        fetch(event.request).then((response) => {
          if (response.ok) {
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, response);
            });
          }
        });
        return cachedResponse;
      }
      
      return fetch(event.request).then((response) => {
        if (response.ok && response.type === 'basic') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      }).catch(() => {
        if (event.request.mode === 'navigate') {
          return caches.match(OFFLINE_URL);
        }
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
    badge: '/static/icons/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/'
    },
    actions: [
      {action: 'open', title: 'View'},
      {action: 'dismiss', title: 'Dismiss'}
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action === 'dismiss') return;
  
  event.waitUntil(
    clients.matchAll({type: 'window'}).then((clientList) => {
      for (const client of clientList) {
        if (client.url === event.notification.data.url && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(event.notification.data.url);
      }
    })
  );
});
