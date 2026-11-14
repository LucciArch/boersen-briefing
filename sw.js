// Service Worker: App-Hülle offline verfügbar, Daten immer frisch (network-first)
const CACHE = "boerse-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/maskable-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  // Netz zuerst (Daten und Seite), bei Offline den letzten Stand aus dem Cache
  e.respondWith(
    fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); const key = url.pathname.endsWith("briefing.json") ? new Request(url.origin + url.pathname) : e.request; caches.open(CACHE).then(c => c.put(key, copy)); }
      return res;
    }).catch(() => caches.match(url.pathname.endsWith("briefing.json") ? new Request(url.origin + url.pathname) : e.request).then(r => r || caches.match("index.html")))
  );
});
