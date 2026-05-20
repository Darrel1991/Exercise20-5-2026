// ── Map Initialization ──────────────────────────────────────────────
const map = L.map("map", {
    center: [3.14, 101.69],   // Kuala Lumpur
    zoom: 7,
    zoomControl: true,
});

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18,
}).addTo(map);

// ── Agency colour scheme ────────────────────────────────────────────
const AGENCY_COLORS = {
    "ktmb":                         "#3b82f6",  // blue
    "prasarana-rapid-bus-kl":       "#22c55e",  // green
    "prasarana-rapid-bus-mrtfeeder":"#16a34a",  // darker green
    "prasarana-rapid-bus-kuantan":  "#4ade80",  // light green
    "prasarana-rapid-bus-penang":   "#86efac",  // pale green
    "mybas-kangar":                 "#f97316",  // orange
    "mybas-alor-setar":             "#fb923c",
    "mybas-kota-bharu":             "#fdba74",
    "mybas-kuala-terengganu":       "#fed7aa",
    "mybas-ipoh":                   "#ea580c",
    "mybas-seremban-a":             "#c2410c",
    "mybas-seremban-b":             "#9a3412",
    "mybas-melaka":                 "#f59e0b",
    "mybas-johor":                  "#d97706",
    "mybas-kuching":                "#b45309",
};

const STALLED_COLOR = "#ef4444";

function getColor(agency, isStalled) {
    if (isStalled) return STALLED_COLOR;
    return AGENCY_COLORS[agency] || "#8b5cf6";
}

function getVehicleType(agency) {
    if (agency === "ktmb") return "Train";
    if (agency.includes("mrtfeeder")) return "MRT Feeder";
    return "Bus";
}

// ── Marker management ───────────────────────────────────────────────
let markers = {};           // vehicle_id -> L.circleMarker
let stalledSet = new Set(); // vehicle_ids that are stalled
let currentFilter = "all";

function createMarker(v) {
    const isStalled = stalledSet.has(v.vehicle_id);
    const color = getColor(v.agency, isStalled);

    const marker = L.circleMarker([v.latitude, v.longitude], {
        radius: v.agency === "ktmb" ? 7 : 5,
        fillColor: color,
        color: isStalled ? "#991b1b" : "#1f2937",
        weight: isStalled ? 2 : 1,
        opacity: 1,
        fillOpacity: 0.85,
    });

    const speedStr = v.speed != null ? `${v.speed.toFixed(1)} km/h` : "N/A";
    const statusStr = isStalled ? '<span class="text-red-400 font-bold">STALLED</span>' : (v.current_status || "Active");

    marker.bindPopup(`
        <div style="font-family: system-ui; font-size: 13px; min-width: 180px;">
            <div style="font-weight: bold; margin-bottom: 4px;">${v.vehicle_id}</div>
            <table style="width:100%; font-size: 12px;">
                <tr><td style="color:#9ca3af">Agency</td><td>${v.agency}</td></tr>
                <tr><td style="color:#9ca3af">Type</td><td>${getVehicleType(v.agency)}</td></tr>
                <tr><td style="color:#9ca3af">Route</td><td>${v.route_id || "—"}</td></tr>
                <tr><td style="color:#9ca3af">Speed</td><td>${speedStr}</td></tr>
                <tr><td style="color:#9ca3af">Status</td><td>${statusStr}</td></tr>
                <tr><td style="color:#9ca3af">Last Update</td><td>${v.timestamp ? new Date(v.timestamp).toLocaleTimeString() : "—"}</td></tr>
            </table>
        </div>
    `);

    return marker;
}

function updateMarkers(vehicles) {
    const seen = new Set();

    vehicles.forEach(v => {
        seen.add(v.vehicle_id);

        if (currentFilter !== "all" && v.agency !== currentFilter) return;

        if (markers[v.vehicle_id]) {
            // Update existing marker position
            markers[v.vehicle_id].setLatLng([v.latitude, v.longitude]);
            const isStalled = stalledSet.has(v.vehicle_id);
            markers[v.vehicle_id].setStyle({
                fillColor: getColor(v.agency, isStalled),
                color: isStalled ? "#991b1b" : "#1f2937",
                weight: isStalled ? 2 : 1,
            });
        } else {
            // Create new marker
            markers[v.vehicle_id] = createMarker(v);
            markers[v.vehicle_id].addTo(map);
        }
    });

    // Remove markers for vehicles no longer active
    Object.keys(markers).forEach(vid => {
        if (!seen.has(vid)) {
            map.removeLayer(markers[vid]);
            delete markers[vid];
        }
    });
}

// ── Data fetching ───────────────────────────────────────────────────
const API_BASE = window.location.origin;

async function fetchVehicles() {
    try {
        const resp = await fetch(`${API_BASE}/api/vehicles?agency=${currentFilter}`);
        const data = await resp.json();
        updateMarkers(data.vehicles || []);
        updateConnectionStatus(true);
    } catch (err) {
        console.error("Failed to fetch vehicles:", err);
        updateConnectionStatus(false);
    }
}

async function fetchStalled() {
    try {
        const resp = await fetch(`${API_BASE}/api/analysis/stalled?threshold_minutes=5`);
        const data = await resp.json();
        stalledSet = new Set((data.vehicles || []).map(v => v.vehicle_id));
    } catch (err) {
        console.error("Failed to fetch stalled:", err);
    }
}

function updateConnectionStatus(connected) {
    const el = document.getElementById("connection-status");
    if (connected) {
        el.innerHTML = '<span class="w-2 h-2 rounded-full bg-green-400"></span><span class="text-gray-400 text-xs">Live</span>';
    } else {
        el.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-400"></span><span class="text-gray-400 text-xs">Disconnected</span>';
    }
}

// ── Filter ──────────────────────────────────────────────────────────
document.getElementById("agency-filter").addEventListener("change", (e) => {
    currentFilter = e.target.value;
    // Clear all markers and refetch
    Object.values(markers).forEach(m => map.removeLayer(m));
    markers = {};
    fetchVehicles();
});

// ── Refresh loop (every 30s) ────────────────────────────────────────
async function refresh() {
    await fetchStalled();
    await fetchVehicles();
    document.getElementById("last-update").textContent = `Updated: ${new Date().toLocaleTimeString()}`;
}

// Initial load
refresh();
setInterval(refresh, 30000);
