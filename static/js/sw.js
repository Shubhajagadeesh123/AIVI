/**
 * Service Worker for BlindMate PWA
 * Provides offline capabilities and caching
 */

// Bumped from v2 -> v3. Changing this string is what forces the browser
// to treat this as a new service worker, throw away the old cache (see
// the activate handler below), and re-fetch fresh copies of everything -
// otherwise app.js/navigation.js changes never reach users, no matter
// how many times the server is redeployed or the page hard-refreshed.
// Bump this again any time app.js/navigation.js/styles.css change.
const CACHE_NAME = "blindmate-v3";
const urlsToCache = [
  "/",
  "/static/js/app.js",
  "/static/js/navigation.js",
  "/static/js/memory.js",
  "/static/js/sos.js",
  "/static/css/styles.css",
  "https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
  "https://cdn.jsdelivr.net/npm/@tensorflow/tfjs",
  "https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd",
];

// App code that changes frequently during development - always prefer a
// fresh copy from the network, only falling back to the cached version
// if the network request fails outright (e.g. actually offline). This
// replaces the old "cache-first" strategy, which - once a file was
// cached - would keep serving that exact cached copy forever, even
// after the real file on the server changed.
const NETWORK_FIRST_PATTERNS = [
  "/static/js/app.js",
  "/static/js/navigation.js",
  "/static/js/memory.js",
  "/static/js/sos.js",
  "/static/css/styles.css",
];

function isNetworkFirst(url) {
  return NETWORK_FIRST_PATTERNS.some((pattern) => url.includes(pattern));
}

// Install event - cache resources. Uses individual cache.add() calls
// wrapped so one failing resource (e.g. a CDN hiccup) doesn't cause the
// whole installation to fail, unlike cache.addAll() which is all-or-nothing.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Opened cache");
      return Promise.allSettled(
        urlsToCache.map((url) =>
          cache.add(url).catch((err) => {
            console.warn("Failed to cache (non-fatal):", url, err);
          }),
        ),
      );
    }),
  );
  self.skipWaiting();
});

// Fetch event.
// - App JS/CSS (NETWORK_FIRST_PATTERNS): always try the network first so
//   code changes are picked up immediately; fall back to the cache only
//   if the network request fails (genuinely offline).
// - Everything else (CDN libraries, the app shell): cache-first, since
//   those rarely change and cache-first is faster / works offline.
self.addEventListener("fetch", (event) => {
  const url = event.request.url;

  if (isNetworkFirst(url)) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          // Keep the cache updated with the latest version too, so the
          // offline fallback doesn't stay stale forever either.
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
          return networkResponse;
        })
        .catch(() => caches.match(event.request)),
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((response) => {
      // Return cached version or fetch from network
      return response || fetch(event.request);
    }),
  );
});

// Activate event - clean up old caches, and take control of any tabs
// that are already open right now. Without clients.claim(), a tab that
// was already open before this update would keep being served by the
// OLD service worker instance until the user manually closed and
// reopened it - clients.claim() makes the new version take over
// immediately instead.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log("Deleting old cache:", cacheName);
              return caches.delete(cacheName);
            }
          }),
        );
      })
      .then(() => self.clients.claim()),
  );
});