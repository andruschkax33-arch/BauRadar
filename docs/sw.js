// BauRadar – Service Worker: App-Hülle offline verfügbar, Daten möglichst frisch
const CACHE = "bauradar-v1";
const SHELL = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "icon-192.png", "icon-180.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== location.origin) return;

  // Sammeldaten: immer zuerst aus dem Netz, nur bei Offline-Fehler aus dem Cache
  if (url.pathname.endsWith("items.json")) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // App-Hülle: aus dem Cache, sonst aus dem Netz
  event.respondWith(
    caches.match(event.request).then((hit) => hit || fetch(event.request))
  );
});
