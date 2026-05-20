// ── Flood Analysis Dashboard JS ─────────────────────────────────────
const API = window.location.origin;

// ── State ───────────────────────────────────────────────────────────
let locations = [];
let currentAnalysis = null;
let charts = {};

// ── Map Setup ───────────────────────────────────────────────────────
const floodMap = L.map("flood-map", { center: [4.0, 108.0], zoom: 6 });

const satelliteLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Esri World Imagery", maxZoom: 19 }
);
const labelsLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Esri Labels", maxZoom: 19 }
);
const streetLayer = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { attribution: "&copy; OpenStreetMap", maxZoom: 18 }
);

let satelliteActive = true;
satelliteLayer.addTo(floodMap);
labelsLayer.addTo(floodMap);

function toggleSatellite() {
    const btn = document.getElementById("satellite-toggle-btn");
    if (satelliteActive) {
        floodMap.removeLayer(satelliteLayer);
        floodMap.removeLayer(labelsLayer);
        streetLayer.addTo(floodMap);
        btn.textContent = "\u{1F6F0} Satellite";
        satelliteActive = false;
    } else {
        floodMap.removeLayer(streetLayer);
        satelliteLayer.addTo(floodMap);
        labelsLayer.addTo(floodMap);
        btn.textContent = "\u{1F5FA} Street Map";
        satelliteActive = true;
    }
}

// ── Draggable map resize ─────────────────────────────────────────────
(function initMapResize() {
    const handle = document.getElementById("map-drag-handle");
    const panel = document.getElementById("map-panel");
    if (!handle || !panel) return;

    let dragging = false;

    handle.addEventListener("mousedown", (e) => {
        e.preventDefault();
        dragging = true;
        handle.classList.add("dragging");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", (e) => {
        if (!dragging) return;
        const containerRight = window.innerWidth;
        const newWidth = containerRight - e.clientX;
        const clamped = Math.max(300, Math.min(newWidth, window.innerWidth * 0.7));
        panel.style.width = clamped + "px";
        floodMap.invalidateSize();
    });

    document.addEventListener("mouseup", () => {
        if (!dragging) return;
        dragging = false;
        handle.classList.remove("dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        floodMap.invalidateSize();
    });
})();

let locationMarkers = {};
let selectedMarker = null;

// ── Train Stations ──────────────────────────────────────────────────
const trainStations = [
    { name: "Bandar Utama", lat: 3.144864809, lng: 101.6187367 },
    { name: "Kayu Ara", lat: 3.134926033, lng: 101.616721 },
    { name: "BU 11", lat: 3.133549326, lng: 101.604751 },
    { name: "Damansara Idaman", lat: 3.122830914, lng: 101.5942203 },
    { name: "SS 7", lat: 3.10630141, lng: 101.5911281 },
    { name: "Glenmarie 2", lat: 3.095346976, lng: 101.5886934 },
    { name: "Kerjaya", lat: 3.082389102, lng: 101.5619675 },
    { name: "Stadium Shah Alam", lat: 3.079989521, lng: 101.5491153 },
    { name: "Dato Menteri", lat: 3.069938008, lng: 101.5211028 },
    { name: "UITM Shah Alam", lat: 3.0630352, lng: 101.5011799 },
    { name: "Seksyen 7 Shah Alam", lat: 3.067562022, lng: 101.4868013 },
    { name: "Bandar Baru Klang", lat: 3.062703543, lng: 101.4657694 },
    { name: "Pasar Besar Klang", lat: 3.068365265, lng: 101.4506957 },
    { name: "Jalan Meru", lat: 3.059081967, lng: 101.4519616 },
    { name: "Klang", lat: 3.047285518, lng: 101.4474364 },
    { name: "Taman Selatan", lat: 3.026925449, lng: 101.4423874 },
    { name: "Sri Andalas", lat: 3.0156538, lng: 101.4403298 },
    { name: "Klang Jaya", lat: 3.005494943, lng: 101.4418146 },
    { name: "Bandar Bukit Tinggi", lat: 2.993292684, lng: 101.4464987 },
    { name: "Johan Setia", lat: 2.976302412, lng: 101.4594896 },
];

const trainIcon = L.divIcon({
    className: "train-icon",
    html: `<div style="
        font-size: 18px;
        text-shadow: 0 1px 4px rgba(0,0,0,0.7);
        line-height: 1;
    ">🚆</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
});

const trainMarkerLayer = L.layerGroup();
trainStations.forEach(s => {
    const marker = L.marker([s.lat, s.lng], { icon: trainIcon });
    marker.bindPopup(`<div style="font-family: system-ui; font-size: 13px;">
        <strong>🚆 ${s.name}</strong><br>
        <span style="color:#9ca3af">Lat:</span> ${s.lat}<br>
        <span style="color:#9ca3af">Lng:</span> ${s.lng}
    </div>`);
    trainMarkerLayer.addLayer(marker);
});
trainMarkerLayer.addTo(floodMap);

// Draw rail line connecting stations in order
L.polyline(trainStations.map(s => [s.lat, s.lng]), {
    color: "#374151",
    weight: 3,
    opacity: 0.9,
    dashArray: "8 6",
}).addTo(floodMap);

function zoomToTrainStations() {
    const bounds = L.latLngBounds(trainStations.map(s => [s.lat, s.lng]));
    floodMap.fitBounds(bounds, { padding: [30, 30] });
}

// ── Risk colors ─────────────────────────────────────────────────────
function riskColor(score) {
    if (score >= 75) return "#ef4444";
    if (score >= 45) return "#f59e0b";
    return "#22c55e";
}

function riskClass(level) {
    return `risk-${level || "low"}`;
}

// ── Init: Load locations ────────────────────────────────────────────
async function loadLocations() {
    try {
        const resp = await fetch(`${API}/api/flood/locations`);
        const data = await resp.json();
        locations = data.locations || [];

        // Populate location select
        const sel = document.getElementById("location-select");
        sel.innerHTML = locations.map(l =>
            `<option value="${l.key}">${l.name} (${l.state})</option>`
        ).join("");

        // Populate compare select
        const cmp = document.getElementById("compare-select");
        cmp.innerHTML = locations.map(l =>
            `<option value="${l.key}">${l.name}</option>`
        ).join("");

        // Add markers to map
        locations.forEach(l => {
            const marker = L.circleMarker([l.lat, l.lng], {
                radius: 7,
                fillColor: "#06b6d4",
                color: "#0e7490",
                weight: 2,
                fillOpacity: 0.7,
            });
            marker.bindPopup(`
                <div style="font-family: system-ui; font-size: 13px;">
                    <strong>${l.name}</strong><br>
                    <span style="color:#9ca3af">State:</span> ${l.state}<br>
                    <span style="color:#9ca3af">River:</span> ${l.river || "—"}<br>
                    <span style="color:#9ca3af">Coords:</span> ${l.lat}, ${l.lng}
                </div>
            `);
            marker.on("click", () => {
                document.getElementById("location-select").value = l.key;
            });
            marker.addTo(floodMap);
            locationMarkers[l.key] = marker;
        });

        // Set default end dates
        const today = new Date().toISOString().split("T")[0];
        document.getElementById("end-date").value = today;
        document.getElementById("demand-end").value = today;

    } catch (err) {
        console.error("Failed to load locations:", err);
    }
}

// ── Highlight selected location on map ──────────────────────────────
function highlightLocation(key) {
    // Reset previous
    if (selectedMarker) {
        selectedMarker.setStyle({ fillColor: "#06b6d4", color: "#0e7490", weight: 2, radius: 7 });
    }
    const marker = locationMarkers[key];
    if (marker) {
        marker.setStyle({ fillColor: "#f59e0b", color: "#d97706", weight: 3, radius: 10 });
        floodMap.setView(marker.getLatLng(), 9);
        selectedMarker = marker;
    }
}

// ── Tab switching ───────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => {
            b.classList.remove("tab-active");
            b.classList.add("tab-inactive");
        });
        btn.classList.remove("tab-inactive");
        btn.classList.add("tab-active");

        document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
        document.getElementById(`panel-${btn.dataset.tab}`).classList.remove("hidden");

        // Resize charts when switching tabs
        setTimeout(() => {
            Object.values(charts).forEach(c => c.resize && c.resize());
        }, 50);
    });
});

// ── Status indicator ────────────────────────────────────────────────
function setStatus(msg, loading = false) {
    const el = document.getElementById("status-text");
    el.textContent = loading ? `${msg}...` : msg;
    el.className = loading ? "text-yellow-400 text-xs" : "text-gray-400 text-xs";

    const btn = document.getElementById("analyze-btn");
    btn.disabled = loading;
    btn.textContent = loading ? "Analyzing..." : "Analyze Flood Risk";
    btn.className = loading
        ? "w-full bg-gray-600 text-gray-400 text-sm font-semibold py-2 rounded cursor-not-allowed"
        : "w-full bg-cyan-600 hover:bg-cyan-700 text-white text-sm font-semibold py-2 rounded transition";
}

// ── Analyze ─────────────────────────────────────────────────────────
async function runAnalysis() {
    const key = document.getElementById("location-select").value;
    const start = document.getElementById("start-date").value;
    const end = document.getElementById("end-date").value;
    if (!key || !start || !end) return;

    highlightLocation(key);
    setStatus("Fetching data from Open-Meteo", true);

    try {
        // Fetch analysis + river discharge in parallel
        const [analysisResp, riverResp] = await Promise.all([
            fetch(`${API}/api/flood/analysis/${key}?start=${start}&end=${end}`),
            fetch(`${API}/api/flood/river/${key}?past_days=180&forecast_days=30`),
        ]);

        if (!analysisResp.ok) throw new Error(`Analysis failed: ${analysisResp.status}`);
        const analysis = await analysisResp.json();
        currentAnalysis = analysis;

        let river = null;
        if (riverResp.ok) river = await riverResp.json();

        // Update all UI
        updateKPIs(analysis);
        renderPrecipChart(analysis);
        renderMonthlyChart(analysis);
        renderYearlyChart(analysis);
        renderConsecutiveTable(analysis);
        renderMonsoonChart(analysis);
        renderExtremeEvents(analysis);
        if (river) renderRiverChart(river);

        setStatus(`Analysis complete — ${analysis.location_name}`);

    } catch (err) {
        console.error("Analysis failed:", err);
        setStatus("Error: " + err.message);
    }
}

// ── KPI Updates ─────────────────────────────────────────────────────
function updateKPIs(data) {
    const s = data.summary || {};
    const r = data.rain_day_counts || {};

    const scoreEl = document.getElementById("kpi-risk-score");
    scoreEl.textContent = s.risk_score ?? "--";
    scoreEl.className = `text-3xl font-bold ${riskClass(s.risk_level)}`;

    const levelEl = document.getElementById("kpi-risk-level");
    levelEl.textContent = `${(s.risk_level || "").toUpperCase()} RISK`;
    levelEl.className = `text-xs font-bold ${riskClass(s.risk_level)}`;

    document.getElementById("kpi-total-rain").textContent =
        s.total_precipitation_mm != null ? s.total_precipitation_mm.toLocaleString() : "--";
    document.getElementById("kpi-avg-daily").textContent =
        s.avg_daily_mm != null ? s.avg_daily_mm.toFixed(1) : "--";
    document.getElementById("kpi-heavy-days").textContent =
        (r.heavy_25mm || 0) + (r.very_heavy_40mm || 0);
    document.getElementById("kpi-extreme-days").textContent =
        r.extreme_60mm ?? "--";
}

// ── Daily Precipitation Chart ───────────────────────────────────────
function renderPrecipChart(data) {
    const daily = data.summary?.date_range ? data : null;
    if (!daily) return;

    // Use monthly data for large ranges, daily for shorter ones
    const monthly = data.monthly_totals || {};
    const months = Object.keys(monthly).sort();

    // For the main chart, show monthly if > 1 year of data, otherwise daily
    const totalDays = data.summary?.total_days_analyzed || 0;

    if (charts.precip) charts.precip.destroy();

    const ctx = document.getElementById("precip-chart").getContext("2d");

    if (totalDays > 400) {
        // Monthly view for long ranges
        charts.precip = new Chart(ctx, {
            type: "bar",
            data: {
                labels: months,
                datasets: [{
                    label: "Monthly Precipitation (mm)",
                    data: months.map(m => monthly[m]?.total_mm || 0),
                    backgroundColor: months.map(m => {
                        const val = monthly[m]?.total_mm || 0;
                        if (val > 500) return "rgba(239,68,68,0.7)";
                        if (val > 300) return "rgba(245,158,11,0.7)";
                        return "rgba(6,182,212,0.7)";
                    }),
                    borderColor: "rgba(6,182,212,0.9)",
                    borderWidth: 1,
                    borderRadius: 2,
                }]
            },
            options: chartOptions("Precipitation (mm)", "Month"),
        });
    } else {
        // Fetch raw daily data
        fetchDailyForChart(data);
    }
}

async function fetchDailyForChart(analysis) {
    const key = document.getElementById("location-select").value;
    const start = document.getElementById("start-date").value;
    const end = document.getElementById("end-date").value;

    try {
        const resp = await fetch(`${API}/api/flood/history/${key}?start=${start}&end=${end}`);
        if (!resp.ok) return;
        const data = await resp.json();
        const daily = data.daily || {};
        const times = daily.time || [];
        const precip = daily.precipitation_sum || [];

        if (charts.precip) charts.precip.destroy();
        const ctx = document.getElementById("precip-chart").getContext("2d");

        charts.precip = new Chart(ctx, {
            type: "bar",
            data: {
                labels: times,
                datasets: [{
                    label: "Daily Precipitation (mm)",
                    data: precip,
                    backgroundColor: precip.map(v => {
                        if (v >= 200) return "rgba(239,68,68,0.8)";
                        if (v >= 120) return "rgba(249,115,22,0.8)";
                        if (v >= 60) return "rgba(245,158,11,0.8)";
                        return "rgba(6,182,212,0.6)";
                    }),
                    borderWidth: 0,
                    borderRadius: 1,
                }]
            },
            options: chartOptions("Precipitation (mm)", "Date"),
        });
    } catch (err) {
        console.error("Failed to fetch daily data:", err);
    }
}

// ── Monthly Chart ───────────────────────────────────────────────────
function renderMonthlyChart(data) {
    const monthly = data.monthly_totals || {};
    const months = Object.keys(monthly).sort();

    if (charts.monthly) charts.monthly.destroy();
    const ctx = document.getElementById("monthly-chart").getContext("2d");

    charts.monthly = new Chart(ctx, {
        type: "bar",
        data: {
            labels: months,
            datasets: [
                {
                    label: "Total (mm)",
                    data: months.map(m => monthly[m]?.total_mm || 0),
                    backgroundColor: "rgba(6,182,212,0.6)",
                    borderColor: "rgba(6,182,212,1)",
                    borderWidth: 1,
                    borderRadius: 2,
                    order: 2,
                },
                {
                    label: "Max Daily (mm)",
                    data: months.map(m => monthly[m]?.max_daily_mm || 0),
                    type: "line",
                    borderColor: "#ef4444",
                    backgroundColor: "rgba(239,68,68,0.1)",
                    borderWidth: 2,
                    pointRadius: 2,
                    tension: 0.3,
                    order: 1,
                },
            ]
        },
        options: chartOptions("Precipitation (mm)", "Month"),
    });
}

// ── Yearly Chart ────────────────────────────────────────────────────
function renderYearlyChart(data) {
    const yearly = data.yearly_totals || {};
    const years = Object.keys(yearly).sort();

    if (charts.yearly) charts.yearly.destroy();
    const ctx = document.getElementById("yearly-chart").getContext("2d");

    charts.yearly = new Chart(ctx, {
        type: "bar",
        data: {
            labels: years,
            datasets: [
                {
                    label: "Total Precipitation (mm)",
                    data: years.map(y => yearly[y]?.total_mm || 0),
                    backgroundColor: "rgba(6,182,212,0.7)",
                    borderColor: "rgba(6,182,212,1)",
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: "Heavy Rain Days (25mm+)",
                    data: years.map(y => yearly[y]?.heavy_days || 0),
                    type: "line",
                    borderColor: "#f59e0b",
                    backgroundColor: "rgba(245,158,11,0.1)",
                    borderWidth: 2,
                    pointRadius: 4,
                    yAxisID: "y1",
                },
            ]
        },
        options: {
            ...chartOptions("Precipitation (mm)", "Year"),
            scales: {
                x: {
                    ticks: { color: "#9ca3af" },
                    grid: { color: "rgba(255,255,255,0.05)" },
                },
                y: {
                    beginAtZero: true,
                    position: "left",
                    ticks: { color: "#9ca3af" },
                    grid: { color: "rgba(255,255,255,0.05)" },
                    title: { display: true, text: "Precipitation (mm)", color: "#9ca3af" },
                },
                y1: {
                    beginAtZero: true,
                    position: "right",
                    ticks: { color: "#f59e0b" },
                    grid: { display: false },
                    title: { display: true, text: "Heavy Rain Days", color: "#f59e0b" },
                },
            },
        },
    });
}

// ── Consecutive Rain Table ──────────────────────────────────────────
function renderConsecutiveTable(data) {
    const periods = data.consecutive_rain_periods || [];
    const el = document.getElementById("consecutive-table");

    if (periods.length === 0) {
        el.innerHTML = '<div class="text-gray-500 text-sm">No consecutive rain periods found</div>';
        return;
    }

    el.innerHTML = `
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-400 text-xs border-b border-gray-700">
                    <th class="text-left py-2 px-2">Start</th>
                    <th class="text-left py-2 px-2">End</th>
                    <th class="text-right py-2 px-2">Days</th>
                    <th class="text-right py-2 px-2">Total (mm)</th>
                    <th class="text-right py-2 px-2">Avg/Day</th>
                    <th class="text-left py-2 px-2">Severity</th>
                </tr>
            </thead>
            <tbody>
                ${periods.map(p => {
                    const severity = p.total_mm >= 500 ? "Extreme" :
                                    p.total_mm >= 300 ? "Very High" :
                                    p.total_mm >= 150 ? "High" : "Moderate";
                    const sevColor = p.total_mm >= 500 ? "text-red-400" :
                                    p.total_mm >= 300 ? "text-orange-400" :
                                    p.total_mm >= 150 ? "text-yellow-400" : "text-gray-400";
                    return `
                        <tr class="border-b border-gray-700 hover:bg-gray-700">
                            <td class="py-2 px-2">${p.start}</td>
                            <td class="py-2 px-2">${p.end}</td>
                            <td class="py-2 px-2 text-right">${p.days}</td>
                            <td class="py-2 px-2 text-right font-bold text-cyan-400">${p.total_mm}</td>
                            <td class="py-2 px-2 text-right">${p.avg_mm_per_day}</td>
                            <td class="py-2 px-2 ${sevColor} font-semibold">${severity}</td>
                        </tr>
                    `;
                }).join("")}
            </tbody>
        </table>
    `;
}

// ── Monsoon Doughnut ────────────────────────────────────────────────
function renderMonsoonChart(data) {
    const m = data.monsoon_analysis || {};

    document.getElementById("monsoon-ne").textContent = `${m.ne_monsoon_mm || 0} mm (${m.monsoon_pct || 0}%)`;
    document.getElementById("monsoon-other").textContent = `${m.non_monsoon_mm || 0} mm`;

    if (charts.monsoon) charts.monsoon.destroy();
    const ctx = document.getElementById("monsoon-chart").getContext("2d");

    charts.monsoon = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["NE Monsoon (Nov-Mar)", "Non-Monsoon"],
            datasets: [{
                data: [m.ne_monsoon_mm || 0, m.non_monsoon_mm || 0],
                backgroundColor: ["rgba(6,182,212,0.7)", "rgba(107,114,128,0.5)"],
                borderColor: ["rgba(6,182,212,1)", "rgba(107,114,128,0.8)"],
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#9ca3af", font: { size: 10 }, boxWidth: 12 },
                },
            },
        },
    });
}

// ── Extreme Events List ─────────────────────────────────────────────
function renderExtremeEvents(data) {
    const events = data.extreme_events || [];
    const el = document.getElementById("extreme-events-list");

    if (events.length === 0) {
        el.innerHTML = '<div class="text-gray-500 text-xs">No extreme events in this period</div>';
        return;
    }

    el.innerHTML = events.map(e => {
        const sevColor = e.severity === "extreme" ? "bg-red-900 border-red-600" :
                        "bg-orange-900 border-orange-600";
        const icon = e.severity === "extreme" ? "🚨" : "⚠️";
        return `
            <div class="${sevColor} bg-opacity-30 border rounded px-2 py-1.5">
                <div class="flex justify-between items-center">
                    <span class="text-xs">${icon} ${e.date}</span>
                    <span class="text-xs font-bold text-cyan-400">${e.precipitation_mm} mm</span>
                </div>
                <div class="text-xs text-gray-500 capitalize">${e.severity.replace("_", " ")}</div>
            </div>
        `;
    }).join("");
}

// ── River Discharge Chart ───────────────────────────────────────────
function renderRiverChart(data) {
    const daily = data.daily || {};
    const times = daily.time || [];
    const discharge = daily.river_discharge || [];
    const dischargeMean = daily.river_discharge_mean || [];
    const dischargeMax = daily.river_discharge_max || [];

    if (charts.river) charts.river.destroy();
    const ctx = document.getElementById("river-chart").getContext("2d");

    const datasets = [{
        label: "River Discharge (m³/s)",
        data: discharge,
        borderColor: "#06b6d4",
        backgroundColor: "rgba(6,182,212,0.15)",
        borderWidth: 2,
        fill: true,
        pointRadius: 0,
        tension: 0.3,
    }];

    if (dischargeMean.length > 0) {
        datasets.push({
            label: "Mean Ensemble (m³/s)",
            data: dischargeMean,
            borderColor: "#8b5cf6",
            borderWidth: 1.5,
            borderDash: [4, 4],
            pointRadius: 0,
            tension: 0.3,
        });
    }
    if (dischargeMax.length > 0) {
        datasets.push({
            label: "Max Ensemble (m³/s)",
            data: dischargeMax,
            borderColor: "#ef4444",
            borderWidth: 1.5,
            borderDash: [4, 4],
            pointRadius: 0,
            tension: 0.3,
        });
    }

    charts.river = new Chart(ctx, {
        type: "line",
        data: { labels: times, datasets },
        options: chartOptions("Discharge (m³/s)", "Date"),
    });
}

// ── Compare ─────────────────────────────────────────────────────────
async function runComparison() {
    const sel = document.getElementById("compare-select");
    const selected = Array.from(sel.selectedOptions).map(o => o.value);
    if (selected.length < 2) {
        alert("Select at least 2 locations to compare");
        return;
    }

    const start = document.getElementById("start-date").value;
    const end = document.getElementById("end-date").value;

    setStatus("Comparing locations", true);

    try {
        const resp = await fetch(
            `${API}/api/flood/compare?locations=${selected.join(",")}&start=${start}&end=${end}`
        );
        if (!resp.ok) throw new Error(`Compare failed: ${resp.status}`);
        const data = await resp.json();

        renderCompareChart(data.comparison || []);
        renderCompareTable(data.comparison || []);

        // Switch to compare tab
        document.querySelector('[data-tab="compare"]').click();
        setStatus("Comparison complete");

    } catch (err) {
        console.error("Compare failed:", err);
        setStatus("Error: " + err.message);
    }
}

function renderCompareChart(comparison) {
    if (charts.compare) charts.compare.destroy();
    const ctx = document.getElementById("compare-chart").getContext("2d");

    const labels = comparison.map(c => c.location_name);

    charts.compare = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Risk Score",
                    data: comparison.map(c => c.risk_score),
                    backgroundColor: comparison.map(c => {
                        if (c.risk_score >= 75) return "rgba(239,68,68,0.7)";
                        if (c.risk_score >= 45) return "rgba(245,158,11,0.7)";
                        return "rgba(34,197,94,0.7)";
                    }),
                    borderRadius: 4,
                    yAxisID: "y",
                },
                {
                    label: "Avg Daily Rain (mm)",
                    data: comparison.map(c => c.avg_daily_mm),
                    type: "line",
                    borderColor: "#06b6d4",
                    backgroundColor: "rgba(6,182,212,0.1)",
                    borderWidth: 2,
                    pointRadius: 5,
                    pointBackgroundColor: "#06b6d4",
                    yAxisID: "y1",
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#d1d5db" } },
            },
            scales: {
                x: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(255,255,255,0.05)" } },
                y: {
                    beginAtZero: true,
                    position: "left",
                    max: 100,
                    ticks: { color: "#9ca3af" },
                    grid: { color: "rgba(255,255,255,0.05)" },
                    title: { display: true, text: "Risk Score", color: "#9ca3af" },
                },
                y1: {
                    beginAtZero: true,
                    position: "right",
                    ticks: { color: "#06b6d4" },
                    grid: { display: false },
                    title: { display: true, text: "Avg Daily Rain (mm)", color: "#06b6d4" },
                },
            },
        },
    });
}

function renderCompareTable(comparison) {
    const el = document.getElementById("compare-table");
    el.innerHTML = `
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-400 text-xs border-b border-gray-700">
                    <th class="text-left py-2 px-2">Location</th>
                    <th class="text-left py-2 px-2">State</th>
                    <th class="text-right py-2 px-2">Risk</th>
                    <th class="text-right py-2 px-2">Total (mm)</th>
                    <th class="text-right py-2 px-2">Avg/Day</th>
                    <th class="text-right py-2 px-2">Heavy Days</th>
                    <th class="text-right py-2 px-2">Extreme</th>
                </tr>
            </thead>
            <tbody>
                ${comparison.map(c => `
                    <tr class="border-b border-gray-700 hover:bg-gray-700">
                        <td class="py-2 px-2 font-semibold">${c.location_name}</td>
                        <td class="py-2 px-2 text-gray-400">${c.state}</td>
                        <td class="py-2 px-2 text-right">
                            <span class="font-bold ${riskClass(c.risk_level)}">${c.risk_score}</span>
                            <span class="text-xs text-gray-500 ml-1">${c.risk_level}</span>
                        </td>
                        <td class="py-2 px-2 text-right">${c.total_precipitation_mm.toLocaleString()}</td>
                        <td class="py-2 px-2 text-right">${c.avg_daily_mm}</td>
                        <td class="py-2 px-2 text-right text-yellow-400">${c.heavy_days}</td>
                        <td class="py-2 px-2 text-right text-red-400">${c.extreme_events}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

// ── Chart default options ───────────────────────────────────────────
function chartOptions(yLabel, xLabel) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: "#d1d5db", font: { size: 11 } } },
        },
        scales: {
            x: {
                ticks: { color: "#9ca3af", font: { size: 10 }, maxRotation: 45, maxTicksLimit: 30 },
                grid: { color: "rgba(255,255,255,0.05)" },
                title: xLabel ? { display: true, text: xLabel, color: "#6b7280" } : undefined,
            },
            y: {
                beginAtZero: true,
                ticks: { color: "#9ca3af" },
                grid: { color: "rgba(255,255,255,0.05)" },
                title: yLabel ? { display: true, text: yLabel, color: "#6b7280" } : undefined,
            },
        },
    };
}

// ═══════════════════════════════════════════════════════════════════
// ── DEMAND POINT / FLOOD ANALYSIS ───────────────────────────────────
// ═══════════════════════════════════════════════════════════════════

let demandMode = false;
let demandMarker = null;
let demandCircle = null;

// Toggle click-to-place mode
function toggleDemandMode() {
    demandMode = !demandMode;
    const btn = document.getElementById("place-point-btn");
    if (demandMode) {
        btn.textContent = "Placing... (click map)";
        btn.className = "text-xs bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-1.5 rounded transition animate-pulse";
        floodMap.getContainer().style.cursor = "crosshair";
    } else {
        btn.textContent = "Click Map to Place Point";
        btn.className = "text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded transition";
        floodMap.getContainer().style.cursor = "";
    }
}

// Handle map click for demand point
floodMap.on("click", function (e) {
    if (!demandMode) return;

    const lat = Math.round(e.latlng.lat * 10000) / 10000;
    const lng = Math.round(e.latlng.lng * 10000) / 10000;

    placeDemandPoint(lat, lng);
    toggleDemandMode();
});

function placeDemandPoint(lat, lng) {
    // Update input fields
    document.getElementById("demand-lat").value = lat;
    document.getElementById("demand-lng").value = lng;

    // Remove old marker
    if (demandMarker) floodMap.removeLayer(demandMarker);
    if (demandCircle) floodMap.removeLayer(demandCircle);

    // Add demand point marker (distinct triangle-like icon)
    const icon = L.divIcon({
        className: "demand-icon",
        html: `<div style="
            width: 20px; height: 20px;
            background: #10b981;
            border: 3px solid #ffffff;
            border-radius: 3px;
            transform: rotate(45deg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.5);
        "></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
    });
    demandMarker = L.marker([lat, lng], { icon }).addTo(floodMap);
    demandMarker.bindPopup(`<strong>Demand Point</strong><br>${lat}, ${lng}<br><em>Analyzing...</em>`);

    // Add a 10km radius circle to show area of influence
    demandCircle = L.circle([lat, lng], {
        radius: 10000, // 10km
        color: "#10b981",
        fillColor: "#10b981",
        fillOpacity: 0.08,
        weight: 2,
        dashArray: "6 4",
    }).addTo(floodMap);

    floodMap.setView([lat, lng], 10);
}

// Run demand point analysis
async function runDemandAnalysis() {
    const lat = parseFloat(document.getElementById("demand-lat").value);
    const lng = parseFloat(document.getElementById("demand-lng").value);
    const startDate = document.getElementById("demand-start").value;
    const endDate = document.getElementById("demand-end").value || new Date().toISOString().split("T")[0];

    if (isNaN(lat) || isNaN(lng)) {
        alert("Please place a point on the map or enter coordinates");
        return;
    }
    if (!startDate) { alert("Please select a start date"); return; }
    if (startDate > endDate) { alert("Start date must be before end date"); return; }

    if (!demandMarker) placeDemandPoint(lat, lng);

    setStatus(`Analyzing flood risk at ${lat}, ${lng} (${startDate} to ${endDate})`, true);

    const btn = document.getElementById("demand-analyze-btn");
    btn.disabled = true;
    btn.textContent = "Analyzing...";
    btn.className = "w-full bg-gray-600 text-gray-400 text-sm font-semibold py-2 rounded cursor-not-allowed";

    try {
        const resp = await fetch(`${API}/api/flood/custom?lat=${lat}&lng=${lng}&start=${startDate}&end=${endDate}`);
        if (!resp.ok) throw new Error(`Analysis failed: ${resp.status}`);
        const data = await resp.json();

        const dateLabel = `${startDate} to ${endDate}`;
        renderDemandResult(data, lat, lng, dateLabel);
        findNearbyLocations(lat, lng, data);

        const s = data.summary || {};
        demandMarker.setPopupContent(`
            <div style="font-family: system-ui; font-size: 13px; min-width: 200px;">
                <strong>Proposed Site</strong><br>
                <span style="color:#9ca3af">Coords:</span> ${lat}, ${lng}<br>
                <span style="color:#9ca3af">Risk Score:</span>
                <strong style="color:${riskColor(s.risk_score)}">${s.risk_score}/100 (${(s.risk_level || "").toUpperCase()})</strong><br>
                <span style="color:#9ca3af">Period:</span> ${dateLabel}<br>
                <span style="color:#9ca3af">Total Rain:</span> ${s.total_precipitation_mm?.toLocaleString()} mm<br>
                <span style="color:#9ca3af">Avg Daily:</span> ${s.avg_daily_mm} mm
            </div>
        `);
        demandMarker.openPopup();

        if (demandCircle) {
            const color = riskColor(s.risk_score);
            demandCircle.setStyle({ color, fillColor: color });
        }
        setStatus(`Site analysis complete — Risk: ${(s.risk_level || "").toUpperCase()}`);

    } catch (err) {
        console.error("Demand analysis failed:", err);
        setStatus("Error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Analyze This Location";
        btn.className = "w-full bg-cyan-600 hover:bg-cyan-700 text-white text-sm font-semibold py-2 rounded transition";
    }
}

// Render the full demand result
function renderDemandResult(data, lat, lng, dateLabel) {
    document.getElementById("demand-result").classList.remove("hidden");

    const s = data.summary || {};
    const r = data.rain_day_counts || {};
    const m = data.monsoon_analysis || {};

    // Risk verdict
    const verdictEl = document.getElementById("demand-verdict");
    const rColor = riskColor(s.risk_score);
    const recommendation = s.risk_level === "high"
        ? "NOT RECOMMENDED — High flood risk. Consider alternative locations or significant flood mitigation infrastructure."
        : s.risk_level === "moderate"
        ? "PROCEED WITH CAUTION — Moderate flood risk. Elevated platform and drainage systems recommended."
        : "SUITABLE — Low flood risk based on historical precipitation data.";

    const recIcon = s.risk_level === "high" ? "&#10060;" : s.risk_level === "moderate" ? "&#9888;&#65039;" : "&#9989;";
    const recBg = s.risk_level === "high" ? "border-red-600 bg-red-900"
                : s.risk_level === "moderate" ? "border-yellow-600 bg-yellow-900"
                : "border-green-600 bg-green-900";

    verdictEl.innerHTML = `
        <div class="${recBg} bg-opacity-30 border-2 rounded-lg p-4 mb-4">
            <div class="flex items-center gap-3 mb-2">
                <span class="text-2xl">${recIcon}</span>
                <div>
                    <div class="text-lg font-bold" style="color:${rColor}">${(s.risk_level || "").toUpperCase()} RISK — Score ${s.risk_score}/100</div>
                    <div class="text-sm text-gray-300">${recommendation}</div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-4 gap-2">
            <div class="bg-gray-700 rounded-lg p-3 text-center">
                <div class="text-lg font-bold text-cyan-400">${s.total_precipitation_mm?.toLocaleString() || "--"}</div>
                <div class="text-xs text-gray-400">Total Rain (mm)</div>
                <div class="text-xs text-gray-500">${dateLabel}</div>
            </div>
            <div class="bg-gray-700 rounded-lg p-3 text-center">
                <div class="text-lg font-bold text-blue-400">${s.avg_daily_mm || "--"}</div>
                <div class="text-xs text-gray-400">Avg Daily (mm)</div>
            </div>
            <div class="bg-gray-700 rounded-lg p-3 text-center">
                <div class="text-lg font-bold text-yellow-400">${(r.heavy_25mm || 0) + (r.very_heavy_40mm || 0)}</div>
                <div class="text-xs text-gray-400">Heavy Rain Days</div>
                <div class="text-xs text-gray-500">25mm+</div>
            </div>
            <div class="bg-gray-700 rounded-lg p-3 text-center">
                <div class="text-lg font-bold text-red-400">${r.extreme_60mm || 0}</div>
                <div class="text-xs text-gray-400">Extreme Days</div>
                <div class="text-xs text-gray-500">60mm+</div>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-2 mt-2">
            <div class="bg-gray-700 rounded-lg p-3">
                <div class="text-xs text-gray-400 mb-1">Monsoon Season Concentration</div>
                <div class="flex items-center gap-2">
                    <div class="flex-1 bg-gray-600 rounded-full h-3 overflow-hidden">
                        <div class="h-full rounded-full" style="width:${m.monsoon_pct || 0}%; background:${m.monsoon_pct > 70 ? '#ef4444' : m.monsoon_pct > 50 ? '#f59e0b' : '#22c55e'}"></div>
                    </div>
                    <span class="text-sm font-bold text-cyan-400">${m.monsoon_pct || 0}%</span>
                </div>
                <div class="text-xs text-gray-500 mt-1">${m.monsoon_pct > 70 ? "High concentration — seasonal flood risk" : m.monsoon_pct > 50 ? "Moderate concentration" : "Well distributed rainfall"}</div>
            </div>
            <div class="bg-gray-700 rounded-lg p-3">
                <div class="text-xs text-gray-400 mb-1">Sustained Rain Periods</div>
                <div class="text-lg font-bold text-orange-400">${(data.consecutive_rain_periods || []).length}</div>
                <div class="text-xs text-gray-500">periods of 3+ consecutive rainy days</div>
            </div>
        </div>
    `;

    // Monthly chart
    renderDemandMonthlyChart(data);

    // Yearly chart
    renderDemandYearlyChart(data);

    // Consecutive rain table
    renderDemandConsecutive(data);
}

function renderDemandMonthlyChart(data) {
    const monthly = data.monthly_totals || {};
    const months = Object.keys(monthly).sort();

    if (charts.demandMonthly) charts.demandMonthly.destroy();
    const ctx = document.getElementById("demand-monthly-chart").getContext("2d");

    charts.demandMonthly = new Chart(ctx, {
        type: "bar",
        data: {
            labels: months,
            datasets: [{
                label: "Monthly Precipitation (mm)",
                data: months.map(m => monthly[m]?.total_mm || 0),
                backgroundColor: months.map(m => {
                    const val = monthly[m]?.total_mm || 0;
                    if (val > 500) return "rgba(239,68,68,0.7)";
                    if (val > 300) return "rgba(245,158,11,0.7)";
                    return "rgba(6,182,212,0.6)";
                }),
                borderRadius: 2,
            }]
        },
        options: chartOptions("Precipitation (mm)", "Month"),
    });
}

function renderDemandYearlyChart(data) {
    const yearly = data.yearly_totals || {};
    const years = Object.keys(yearly).sort();

    if (charts.demandYearly) charts.demandYearly.destroy();
    const ctx = document.getElementById("demand-yearly-chart").getContext("2d");

    charts.demandYearly = new Chart(ctx, {
        type: "bar",
        data: {
            labels: years,
            datasets: [{
                label: "Yearly Precipitation (mm)",
                data: years.map(y => yearly[y]?.total_mm || 0),
                backgroundColor: "rgba(6,182,212,0.7)",
                borderColor: "rgba(6,182,212,1)",
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: chartOptions("Precipitation (mm)", "Year"),
    });
}

function renderDemandConsecutive(data) {
    const periods = (data.consecutive_rain_periods || []).slice(0, 10);
    const el = document.getElementById("demand-consecutive");

    if (periods.length === 0) {
        el.innerHTML = '<div class="text-gray-500 text-sm">No sustained rain periods found</div>';
        return;
    }

    el.innerHTML = `
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-400 text-xs border-b border-gray-700">
                    <th class="text-left py-1 px-2">Start</th>
                    <th class="text-left py-1 px-2">End</th>
                    <th class="text-right py-1 px-2">Days</th>
                    <th class="text-right py-1 px-2">Total (mm)</th>
                    <th class="text-right py-1 px-2">Avg/Day</th>
                </tr>
            </thead>
            <tbody>
                ${periods.map(p => `
                    <tr class="border-b border-gray-700 hover:bg-gray-700">
                        <td class="py-1 px-2">${p.start}</td>
                        <td class="py-1 px-2">${p.end}</td>
                        <td class="py-1 px-2 text-right">${p.days}</td>
                        <td class="py-1 px-2 text-right font-bold text-cyan-400">${p.total_mm}</td>
                        <td class="py-1 px-2 text-right">${p.avg_mm_per_day}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

// Find nearby monitored locations and show comparison
function findNearbyLocations(lat, lng, demandData) {
    const el = document.getElementById("demand-nearby");

    // Calculate distance to each location
    const nearby = locations.map(loc => {
        const dist = haversine(lat, lng, loc.lat, loc.lng);
        return { ...loc, distance_km: Math.round(dist * 10) / 10 };
    }).sort((a, b) => a.distance_km - b.distance_km).slice(0, 5);

    // Draw lines from demand point to nearby stations
    nearby.forEach(n => {
        const line = L.polyline([[lat, lng], [n.lat, n.lng]], {
            color: "#6b7280",
            weight: 1,
            dashArray: "4 4",
            opacity: 0.5,
        }).addTo(floodMap);
        // Store for cleanup
        if (!window._nearbyLines) window._nearbyLines = [];
        window._nearbyLines.push(line);
    });

    el.innerHTML = `
        <table class="w-full text-sm">
            <thead>
                <tr class="text-gray-400 text-xs border-b border-gray-700">
                    <th class="text-left py-1 px-2">Station</th>
                    <th class="text-left py-1 px-2">State</th>
                    <th class="text-right py-1 px-2">Distance</th>
                    <th class="text-left py-1 px-2">River</th>
                </tr>
            </thead>
            <tbody>
                ${nearby.map(n => `
                    <tr class="border-b border-gray-700 hover:bg-gray-700">
                        <td class="py-1 px-2 font-semibold">${n.name}</td>
                        <td class="py-1 px-2 text-gray-400">${n.state}</td>
                        <td class="py-1 px-2 text-right text-cyan-400">${n.distance_km} km</td>
                        <td class="py-1 px-2 text-xs text-gray-500">${n.river || "—"}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
        <div class="text-xs text-gray-500 mt-2">Nearest flood-monitored stations. Closer proximity to rivers increases flood risk.</div>
    `;
}

// Haversine distance formula (km)
function haversine(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Cleanup nearby lines when placing new point
function cleanupNearbyLines() {
    if (window._nearbyLines) {
        window._nearbyLines.forEach(l => floodMap.removeLayer(l));
        window._nearbyLines = [];
    }
}

// ── Event listeners ─────────────────────────────────────────────────
document.getElementById("analyze-btn").addEventListener("click", runAnalysis);
document.getElementById("compare-btn").addEventListener("click", runComparison);
document.getElementById("place-point-btn").addEventListener("click", toggleDemandMode);
document.getElementById("demand-analyze-btn").addEventListener("click", () => {
    cleanupNearbyLines();
    runDemandAnalysis();
});

// Allow Enter key to trigger analysis
document.getElementById("start-date").addEventListener("keypress", e => { if (e.key === "Enter") runAnalysis(); });
document.getElementById("end-date").addEventListener("keypress", e => { if (e.key === "Enter") runAnalysis(); });

// ── Init ────────────────────────────────────────────────────────────
loadLocations();
