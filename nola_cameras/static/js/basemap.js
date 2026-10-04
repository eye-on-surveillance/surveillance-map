// Shared basemap helper: OpenStreetMap tiles.
// Requires the site to send a Referer (see SECURE_REFERRER_POLICY in settings) —
// OSM serves "Access blocked" tiles to referer-less requests.
function addBasemap(map) {
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
}
