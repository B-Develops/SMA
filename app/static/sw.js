'use strict';

const CACHE_NAME = 'sarkin-mota-v1';
const OFFLINE_URL = '/offline';

const ASSETS_TO_CACHE = [
  '/static/manifest.json',
  '/static/pwa.css',
  '/static/pwa-register.js',
  '/static/index.css',
  '/static/dropdown.css',
  '/static/mobile-style.css',
  '/static/header-navbar.css',
  '/static/dashboard.css',
  '/static/profile.css',
  '/static/login.css',
  '/static/browse-cars.css',
  '/static/view-details.css',
  '/static/my-listings.css',
  '/static/my-orders.css',
  '/static/settings.css',
  '/static/saved-cars.css',
  '/static/about.css',
  '/static/responsive-tables.css',
  '/static/shared-sidebar.css',
  '/static/icons/favicon.ico',
  '/static/icons/icon-16.png',
  '/static/icons/icon-32.png',
  '/static/icons/icon-72.png',
  '/static/icons/icon-96.png',
  '/static/icons/icon-128.png',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/apple-touch-icon.png',
  '/static/icons/maskable-512.png',
  '/static/Mercedes.png',
  '/static/Toyota.png',
  '/static/Honda.png',
  '/static/BMW.png',
  '/static/Ford.png',
  '/static/Hyundai.png',
  '/static/Lexus.png',
  '/static/Nissan.png',
  '/static/Light.png',
  '/static/light1.png',
  '/offline',
];

const API_CACHE_NAME = 'sarkin-mota-api-v1';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== API_CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/auth/') || url.pathname.startsWith('/dashboard') || url.pathname.startsWith('/admin/')) {
    event.respondWith(fetch(event.request).catch(() => caches.match('/static/icons/icon-192.png')));
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((response) => {
        return response || fetch(event.request).then((networkResponse) => {
          if (!networkResponse || networkResponse.status !== 200 || networkResponse.type === 'opaque') {
            return networkResponse;
          }
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseToCache));
          return networkResponse;
        });
      })
    );
    return;
  }

  if (url.origin === self.location.origin) {
    event.respondWith(
      fetch(event.request).catch(() => {
        if (event.request.mode === 'navigate') {
          return caches.match(OFFLINE_URL) || caches.match('/');
        }
      })
    );
    return;
  }
});
