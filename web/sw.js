// Kundali service worker: the app shell and knowledge files work offline; API calls go to the network.
// Bump VERSION on every deploy that changes web/ or data/ (the build sets it from the git commit).
const VERSION = 'kundali-v1';
const SHELL = ['./', './index.html', './config.js', './manifest.webmanifest', './data/places.json', './data/i18n_en.json',
  './data/knowledge/planets.json', './data/knowledge/houses.json', './data/knowledge/nakshatras.json', './data/knowledge/signs.json',
  './data/knowledge/numbers.json', './icons/icon-192.png', './icons/icon-512.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;          // API POSTs and CDNs: network only
  if (url.pathname.startsWith('/v1/') || url.pathname === '/health') return;
  // shell and data: network first (so updates arrive), cache as fallback (so it opens offline)
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request).then(m => m || (e.request.mode === 'navigate' ? caches.match('./index.html') : undefined))));
});
