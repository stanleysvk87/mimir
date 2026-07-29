// Minimal service worker: just enough presence to satisfy PWA
// installability checks. Network-first, no offline caching of API data
// (a stale timeline is worse than none) -- only the app shell itself is
// cached so the icon/shell can still render if briefly offline.
const SHELL_CACHE = 'mimir-shell-v1'

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(['/', '/manifest.json', '/icon.svg']))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) return
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  )
})
