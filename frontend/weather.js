// ── Weather Layer for Leaflet Map ───────────────────────────────────
// Depends on: map (from map.js), API_BASE (from map.js)

const weatherMarkers = [];
let weatherLayerVisible = true;
let warningData = [];
let earthquakeMarkers = [];
let warningBoundaryLayers = [];

// ── Forecast icon mapping (Malay weather terms → icon/color) ────────
const FORECAST_STYLES = {
    "Tiada hujan":                    { icon: "☀️", color: "#f59e0b", label: "Clear" },
    "Hujan di satu dua tempat":       { icon: "🌦️", color: "#60a5fa", label: "Light Rain" },
    "Hujan di beberapa tempat":       { icon: "🌧️", color: "#3b82f6", label: "Rain" },
    "Hujan di kebanyakan tempat":     { icon: "🌧️", color: "#2563eb", label: "Heavy Rain" },
    "Hujan di seluruh tempat":        { icon: "⛈️", color: "#1d4ed8", label: "Widespread Rain" },
    "Ribut petir di satu dua tempat": { icon: "⛈️", color: "#dc2626", label: "Thunderstorm" },
    "Ribut petir di beberapa tempat": { icon: "⛈️", color: "#b91c1c", label: "Thunderstorms" },
    "Ribut petir di kebanyakan tempat":{ icon: "⛈️", color: "#991b1b", label: "Severe Storms" },
};

function getForecastStyle(forecast) {
    if (!forecast) return { icon: "❓", color: "#6b7280", label: "Unknown" };
    // Try exact match first, then partial
    if (FORECAST_STYLES[forecast]) return FORECAST_STYLES[forecast];
    for (const [key, style] of Object.entries(FORECAST_STYLES)) {
        if (forecast.includes(key) || key.includes(forecast)) return style;
    }
    // If contains "hujan" it's rain, "ribut" it's storm
    if (forecast.toLowerCase().includes("ribut")) return { icon: "⛈️", color: "#dc2626", label: forecast };
    if (forecast.toLowerCase().includes("hujan")) return { icon: "🌧️", color: "#3b82f6", label: forecast };
    return { icon: "☀️", color: "#f59e0b", label: forecast };
}

// ── Weather Markers on Map ──────────────────────────────────────────
function clearWeatherMarkers() {
    weatherMarkers.forEach(m => map.removeLayer(m));
    weatherMarkers.length = 0;
}

function clearEarthquakeMarkers() {
    earthquakeMarkers.forEach(m => map.removeLayer(m));
    earthquakeMarkers.length = 0;
}

function renderWeatherOnMap(points) {
    clearWeatherMarkers();
    if (!weatherLayerVisible) return;

    points.forEach(p => {
        if (!p.lat || !p.lng) return;

        const style = getForecastStyle(p.summary);

        const icon = L.divIcon({
            className: "weather-icon",
            html: `<div style="
                font-size: 18px;
                text-align: center;
                line-height: 1;
                filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
            ">${style.icon}</div>`,
            iconSize: [28, 28],
            iconAnchor: [14, 14],
        });

        const marker = L.marker([p.lat, p.lng], { icon, zIndexOffset: -100 });

        marker.bindPopup(`
            <div style="font-family: system-ui; font-size: 13px; min-width: 200px;">
                <div style="font-weight: bold; margin-bottom: 4px;">
                    ${style.icon} ${p.location_name}
                </div>
                <table style="width:100%; font-size: 12px;">
                    <tr><td style="color:#9ca3af">Temp</td><td>${p.min_temp}°C – ${p.max_temp}°C</td></tr>
                    <tr><td style="color:#9ca3af">Morning</td><td>${p.morning || "—"}</td></tr>
                    <tr><td style="color:#9ca3af">Afternoon</td><td>${p.afternoon || "—"}</td></tr>
                    <tr><td style="color:#9ca3af">Night</td><td>${p.night || "—"}</td></tr>
                    <tr><td style="color:#9ca3af">Summary</td><td><strong>${style.label}</strong></td></tr>
                </table>
            </div>
        `);

        marker.addTo(map);
        weatherMarkers.push(marker);
    });
}

function renderEarthquakesOnMap(quakes) {
    clearEarthquakeMarkers();
    if (!weatherLayerVisible) return;

    quakes.forEach(q => {
        if (!q.latitude || !q.longitude) return;

        const radius = Math.max(8, (q.magnitude || 3) * 5);
        const marker = L.circleMarker([q.latitude, q.longitude], {
            radius: radius,
            fillColor: "#ef4444",
            color: "#991b1b",
            weight: 2,
            opacity: 0.9,
            fillOpacity: 0.4,
        });

        marker.bindPopup(`
            <div style="font-family: system-ui; font-size: 13px;">
                <div style="font-weight: bold; margin-bottom: 4px;">🔴 Earthquake</div>
                <table style="width:100%; font-size: 12px;">
                    <tr><td style="color:#9ca3af">Location</td><td>${q.location || "—"}</td></tr>
                    <tr><td style="color:#9ca3af">Magnitude</td><td>${q.magnitude || "—"}</td></tr>
                    <tr><td style="color:#9ca3af">Depth</td><td>${q.depth ? q.depth + " km" : "—"}</td></tr>
                    <tr><td style="color:#9ca3af">Time</td><td>${q.timestamp ? new Date(q.timestamp).toLocaleString() : "—"}</td></tr>
                </table>
            </div>
        `);

        marker.addTo(map);
        earthquakeMarkers.push(marker);
    });
}

// ── Warning Boundary Rectangles on Map ──────────────────────────────
function clearWarningBoundaries() {
    warningBoundaryLayers.forEach(l => map.removeLayer(l));
    warningBoundaryLayers.length = 0;
}

function renderWarningBoundaries(_warnings) {
    clearWarningBoundaries();
}

// ── Sidebar: Warning Panel ──────────────────────────────────────────
function renderWarningPanel(warnings) {
    const el = document.getElementById("warning-list");
    if (!el) return;

    if (warnings.length === 0) {
        el.innerHTML = '<div class="text-gray-500 text-xs">No active warnings</div>';
        return;
    }

    el.innerHTML = warnings.map((w, idx) => {
        const isExpired = w.valid_to && new Date(w.valid_to) < new Date();
        const hasBoundary = !!w.boundary;
        const boundaryInfo = hasBoundary
            ? `<div class="text-xs text-yellow-400 mt-1">📍 Lat ${w.boundary.lat_min}°–${w.boundary.lat_max}°N, Lng ${w.boundary.lng_min}°–${w.boundary.lng_max}°E</div>
               <button onclick="zoomToWarningBoundary(${idx})" class="text-xs bg-red-700 hover:bg-red-600 text-white px-2 py-0.5 rounded mt-1">Zoom to Area</button>`
            : "";
        return `
            <div class="bg-red-900 bg-opacity-30 border border-red-700 rounded px-2 py-2 mb-1">
                <div class="text-xs font-bold text-red-400">${w.heading_en || w.title_en || "Warning"}</div>
                <div class="text-xs text-gray-300 mt-1">${(w.text_en || "").substring(0, 150)}${(w.text_en || "").length > 150 ? "..." : ""}</div>
                ${boundaryInfo}
                <div class="text-xs text-gray-500 mt-1">
                    ${w.valid_from ? "From: " + new Date(w.valid_from).toLocaleString() : ""}
                    ${w.valid_to ? " — To: " + new Date(w.valid_to).toLocaleString() : ""}
                    ${isExpired ? ' <span class="text-gray-600">(expired)</span>' : ""}
                </div>
            </div>
        `;
    }).join("");
}

// ── Zoom to warning boundary ────────────────────────────────────────
function zoomToWarningBoundary(idx) {
    const w = warningData[idx];
    if (!w || !w.boundary) return;
    const { lat_min, lat_max, lng_min, lng_max } = w.boundary;
    map.fitBounds([[lat_min, lng_min], [lat_max, lng_max]], { padding: [20, 20] });
}

// ── Data Fetching ───────────────────────────────────────────────────
async function fetchWeatherForecastMap() {
    try {
        const resp = await fetch(`${API_BASE}/api/weather/forecast/map`);
        const data = await resp.json();
        renderWeatherOnMap(data.points || []);
        updateWeatherSummary(data.points || []);
    } catch (err) {
        console.error("Failed to fetch weather forecast map:", err);
    }
}

async function fetchWeatherWarnings() {
    try {
        const resp = await fetch(`${API_BASE}/api/weather/warnings?active_only=true`);
        const data = await resp.json();
        warningData = data.warnings || [];
        renderWarningPanel(warningData);
        renderWarningBoundaries(warningData);
        // Update warning count badge
        const badge = document.getElementById("kpi-warnings");
        if (badge) badge.textContent = warningData.length;
    } catch (err) {
        console.error("Failed to fetch weather warnings:", err);
    }
}

async function fetchEarthquakes() {
    try {
        const resp = await fetch(`${API_BASE}/api/weather/earthquakes?limit=10`);
        const data = await resp.json();
        renderEarthquakesOnMap(data.earthquakes || []);
    } catch (err) {
        console.error("Failed to fetch earthquakes:", err);
    }
}

function updateWeatherSummary(points) {
    // Count forecast categories
    let rain = 0, storm = 0, clear = 0;
    points.forEach(p => {
        const s = p.summary || "";
        if (s.toLowerCase().includes("ribut")) storm++;
        else if (s.toLowerCase().includes("hujan")) rain++;
        else clear++;
    });

    const el = document.getElementById("weather-summary");
    if (el) {
        el.innerHTML = `
            <span class="text-yellow-400">☀️ ${clear}</span>
            <span class="text-blue-400 ml-2">🌧️ ${rain}</span>
            <span class="text-red-400 ml-2">⛈️ ${storm}</span>
        `;
    }
}

// ── Toggle ──────────────────────────────────────────────────────────
function toggleWeatherLayer() {
    weatherLayerVisible = !weatherLayerVisible;
    const btn = document.getElementById("weather-toggle");
    if (btn) {
        btn.textContent = weatherLayerVisible ? "Hide Weather" : "Show Weather";
        btn.className = weatherLayerVisible
            ? "text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded"
            : "text-xs bg-gray-600 hover:bg-gray-700 text-white px-2 py-1 rounded";
    }
    if (weatherLayerVisible) {
        fetchWeatherForecastMap();
        fetchEarthquakes();
        renderWarningBoundaries(warningData);
    } else {
        clearWeatherMarkers();
        clearEarthquakeMarkers();
        clearWarningBoundaries();
    }
}

// ── Init & Refresh ──────────────────────────────────────────────────
async function refreshWeather() {
    await fetchWeatherWarnings();
    if (weatherLayerVisible) {
        await fetchWeatherForecastMap();
        await fetchEarthquakes();
    }
}

// Attach toggle handler
document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("weather-toggle");
    if (btn) btn.addEventListener("click", toggleWeatherLayer);
});

// Initial load + refresh every 30 minutes
refreshWeather();
setInterval(refreshWeather, 30 * 60 * 1000);
