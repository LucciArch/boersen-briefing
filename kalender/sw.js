// Der Sprachkalender ist nach /sprachkalender/ umgezogen. Dieser Service Worker räumt nur noch auf.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith("kalender-")).map(k => caches.delete(k)));
    await self.registration.unregister();
    const all = await self.clients.matchAll({ type: "window" });
    all.forEach(c => c.navigate("https://lucciarch.github.io/sprachkalender/"));
  })());
});
