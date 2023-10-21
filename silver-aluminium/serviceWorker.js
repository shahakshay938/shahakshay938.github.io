const staticDevCoffee = "dev-coffee-site-v1"
const assets = [
    "/",
    "new-ui.html",
    "assets/css/style.css",
    "assets/css/fontawesome-all.css",
    "assets/images/sa.png",
    "assets/webfonts/fa-regular-400.ttf",
    "assets/webfonts/fa-regular-400.woff2",
    "assets/webfonts/fa-solid-900.ttf",
    "assets/webfonts/fa-solid-900.woff2",
]

self.addEventListener("install", installEvent => {
    installEvent.waitUntil(
        caches.open(staticDevCoffee).then(cache => {
            cache.addAll(assets)
        })
    )
})

self.addEventListener("fetch", fetchEvent => {
    fetchEvent.respondWith(
        caches.match(fetchEvent.request).then(res => {
            return res || fetch(fetchEvent.request)
        })
    )
})