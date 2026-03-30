// Protocol Pulse — Service Worker disabled for fresh content delivery
// This SW immediately takes control and does NOT cache HTML pages
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => {
    e.waitUntil(
        caches.keys().then(names => Promise.all(
            names.map(name => caches.delete(name))
        )).then(() => self.clients.claim())
    );
});
self.addEventListener("fetch", e => {
    // Pass through — no caching
    return;
});
