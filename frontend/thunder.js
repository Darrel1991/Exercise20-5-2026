// ── Thunderstorm Analysis Dashboard JS ──────────────────────────────
const API = window.location.origin;

// ── State ───────────────────────────────────────────────────────────
let stations = [];
let currentAnalysis = null;
let charts = {};

// ── Map Setup ───────────────────────────────────────────────────────
const thunderMap = L.map("thunder-map", { center: [3.07, 101.52], zoom: 11 });

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
satelliteLayer.addTo(thunderMap);
labelsLayer.addTo(thunderMap);

function toggleSatellite() {
    const btn = document.getElementById("satellite-toggle-btn");
    if (satelliteActive) {
        thunderMap.removeLayer(satelliteLayer);
        thunderMap.removeLayer(labelsLayer);
        streetLayer.addTo(thunderMap);
        btn.textContent = "\u{1F6F0} Satellite";
        satelliteActive = false;
    } else {
        thunderMap.removeLayer(streetLayer);
        satelliteLayer.addTo(thunderMap);
        labelsLayer.addTo(thunderMap);
        btn.textContent = "\u{1F5FA} Street Map";
        satelliteActive = true;
    }
}

// ── Draggable map resize ────────────────────────────────────────────
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
        const newWidth = window.innerWidth - e.clientX;
        const clamped = Math.max(300, Math.min(newWidth, window.innerWidth * 0.7));
        panel.style.width = clamped + "px";
        thunderMap.invalidateSize();
    });
    document.addEventListener("mouseup", () => {
        if (!dragging) return;
        dragging = false;
        handle.classList.remove("dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        thunderMap.invalidateSize();
    });
})();

let stationMarkers = {};
let selectedMarker = null;

// ── Colors ──────────────────────────────────────────────────────────
function riskColor(score) {
    if (score >= 70) return "#ef4444";
    if (score >= 40) return "#f59e0b";
    return "#22c55e";
}

function severityBadge(sev) {
    const cls = { critical: "severity-critical", severe: "severity-severe", moderate: "severity-moderate" };
    return `<span class="text-xs px-1.5 py-0.5 rounded ${cls[sev] || ""}">${sev}</span>`;
}

// ── Init: Load stations ─────────────────────────────────────────────
let linesData = {};  // { "LRT3": { name, color, stations[] }, "KJ": ... }

async function loadStations() {
    try {
        const resp = await fetch(`${API}/api/thunder/stations`);
        const data = await resp.json();
        linesData = data.lines || {};

        // Flatten all stations
        stations = [];
        Object.values(linesData).forEach(line => {
            (line.stations || []).forEach(s => stations.push(s));
        });

        // Populate line selector
        const lineSel = document.getElementById("line-select");
        lineSel.innerHTML = '<option value="">-- Select a line --</option>';
        Object.entries(linesData).forEach(([key, line]) => {
            lineSel.innerHTML += `<option value="${key}">${line.name} (${line.stations.length} stations)</option>`;
        });

        // Line change → populate station dropdown
        lineSel.addEventListener("change", () => {
            const lineKey = lineSel.value;
            const stationSel = document.getElementById("station-select");
            if (!lineKey) {
                stationSel.innerHTML = '<option value="">-- Select a line first --</option>';
                return;
            }
            const line = linesData[lineKey];
            stationSel.innerHTML = '<option value="">-- Select a station --</option>';
            (line.stations || []).forEach(s => {
                stationSel.innerHTML += `<option value="${s.key}">${s.name}</option>`;
            });
        });

        // Draw each line on the map with its own color
        const stationSel = document.getElementById("station-select");
        Object.entries(linesData).forEach(([lineKey, line]) => {
            const color = line.color || "#374151";
            const lineStations = line.stations || [];

            // Draw track polyline
            if (lineStations.length > 1) {
                L.polyline(lineStations.map(s => [s.lat, s.lng]), {
                    color: color,
                    weight: 4,
                    opacity: 0.85,
                }).addTo(thunderMap);
            }

            // Place station markers
            lineStations.forEach(s => {
                const icon = L.divIcon({
                    className: "train-icon",
                    html: `<div style="
                        font-size: 16px;
                        line-height: 1;
                        filter: drop-shadow(0 1px 3px rgba(0,0,0,0.7));
                        color: ${color};
                    ">🚆</div>`,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10],
                    popupAnchor: [0, -10],
                });
                const marker = L.marker([s.lat, s.lng], { icon }).addTo(thunderMap);
                marker.bindPopup(`
                    <div style="font-family:system-ui;font-size:13px;">
                        <strong>🚆 ${s.name}</strong><br>
                        <span style="color:${color};font-weight:bold;">${line.name}</span><br>
                        <span style="color:#9ca3af">${s.lat.toFixed(4)}, ${s.lng.toFixed(4)}</span>
                    </div>
                `);
                marker.on("click", () => {
                    document.getElementById("line-select").value = lineKey;
                    // Trigger change to populate station dropdown
                    document.getElementById("line-select").dispatchEvent(new Event("change"));
                    setTimeout(() => { stationSel.value = s.key; }, 50);
                });
                stationMarkers[s.key] = marker;
            });
        });

        // Add legend to map
        addMapLegend();

        zoomToStations();
    } catch (err) {
        console.error("Failed to load stations:", err);
    }
}

function addMapLegend() {
    const legend = L.control({ position: "bottomleft" });
    legend.onAdd = function () {
        const div = L.DomUtil.create("div", "");
        div.style.cssText = "background:rgba(17,24,39,0.9);padding:8px 12px;border-radius:6px;font-size:12px;color:#d1d5db;line-height:1.8;";
        let html = '<div style="font-weight:bold;margin-bottom:4px;color:#fff;">Train Lines</div>';
        Object.entries(linesData).forEach(([key, line]) => {
            html += `<div><span style="display:inline-block;width:20px;height:3px;background:${line.color};vertical-align:middle;margin-right:6px;border-radius:2px;"></span>${line.name} (${line.stations.length})</div>`;
        });
        div.innerHTML = html;
        return div;
    };
    legend.addTo(thunderMap);
}

function zoomToStations() {
    if (stations.length === 0) return;
    const bounds = L.latLngBounds(stations.map(s => [s.lat, s.lng]));
    thunderMap.fitBounds(bounds, { padding: [30, 30] });
}

// ── Status ──────────────────────────────────────────────────────────
function setStatus(msg, loading) {
    const el = document.getElementById("status-text");
    el.textContent = loading ? `⏳ ${msg}` : msg;
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

        const tab = btn.dataset.tab;
        document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
        const panel = document.getElementById(`panel-${tab}`);
        if (panel) panel.classList.remove("hidden");

        // Resize charts on tab switch
        Object.values(charts).forEach(c => c.resize?.());
    });
});

// ── Analyze single station ──────────────────────────────────────────
document.getElementById("analyze-btn").addEventListener("click", runAnalysis);

async function runAnalysis() {
    const stationKey = document.getElementById("station-select").value;
    if (!stationKey) { alert("Please select a station"); return; }

    const startDate = document.getElementById("start-date").value;
    const endDate = document.getElementById("end-date").value || new Date().toISOString().split("T")[0];

    setStatus(`Analyzing ${stationKey}...`, true);

    try {
        const resp = await fetch(
            `${API}/api/thunder/analysis/${stationKey}?start=${startDate}&end=${endDate}`
        );
        if (!resp.ok) throw new Error(`Analysis failed: ${resp.status}`);
        const data = await resp.json();
        currentAnalysis = data;

        updateKPIs(data);
        renderDailyCharts(data);
        renderMonthlyChart(data);
        renderStormsTable(data);
        renderHeatmap(data);
        renderSeverityChart(data);
        updateStationMarker(stationKey, data);

        setStatus(`${data.station_name} — Risk: ${data.summary.risk_score}/100`, false);
    } catch (err) {
        console.error(err);
        setStatus("Analysis failed", false);
    }
}

// ── Update KPIs ─────────────────────────────────────────────────────
function updateKPIs(data) {
    const s = data.summary;
    const scoreEl = document.getElementById("kpi-risk-score");
    scoreEl.textContent = s.risk_score;
    scoreEl.style.color = riskColor(s.risk_score);

    const levelEl = document.getElementById("kpi-risk-level");
    levelEl.textContent = `${s.risk_level.toUpperCase()} RISK`;
    levelEl.style.color = riskColor(s.risk_score);

    document.getElementById("kpi-storm-days").textContent = s.storm_days;
    document.getElementById("kpi-severe-gusts").textContent = s.storm_hours;
    document.getElementById("kpi-heavy-rain").textContent = `${s.max_hourly_rain_mm}`;

    const peak = s.peak_storm_month || "--";
    document.getElementById("kpi-peak-month").textContent = peak.substring(0, 3);
    document.getElementById("kpi-peak-month").title = peak;

    document.getElementById("kpi-combined").textContent = `${s.max_hourly_gust_kmh} km/h`;
    document.getElementById("kpi-extreme-rain").textContent = `${s.storm_hours} hrs`;

    // Storm events list (latest first, already sorted by backend)
    const list = document.getElementById("critical-events-list");
    const events = (data.storm_events || []).slice(0, 10);
    if (events.length === 0) {
        list.innerHTML = '<div class="text-gray-500 text-xs">No thunderstorm events found in this period</div>';
    } else {
        list.innerHTML = events.map(e => `
            <div class="bg-gray-700 rounded p-2 text-xs">
                <div class="flex justify-between">
                    <span class="text-gray-300">${e.date}</span>
                    <span class="text-purple-400">${e.storm_hours}h storm</span>
                </div>
                <div class="text-gray-400 mt-1">
                    🌧 Peak: ${e.max_rain_mmh} mm/h
                    💨 Max: ${e.max_gust_kmh} km/h
                </div>
            </div>
        `).join("");
    }
}

// ── Severity doughnut ───────────────────────────────────────────────
function renderSeverityChart(data) {
    const s = data.summary;
    const ctx = document.getElementById("severity-chart");
    if (charts.severity) charts.severity.destroy();

    charts.severity = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Storm Days", "Storm Hours", "Normal Days"],
            datasets: [{
                data: [
                    s.storm_days,
                    s.storm_hours,
                    Math.max(0, s.total_days_analyzed - s.storm_days),
                ],
                backgroundColor: ["#a855f7", "#ef4444", "#374151"],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
        },
    });
}

// ── Daily charts (aggregated from hourly data) ─────────────────────
function renderDailyCharts(data) {
    // Use the analysis data which already has monthly_totals
    // But for daily charts we need to aggregate from the storm_events
    // Actually, the analysis already computed daily rollups — use those
    const events = data.storm_events || [];
    const dates = events.map(e => e.date);
    const maxRains = events.map(e => e.max_rain_mmh);
    const maxGusts = events.map(e => e.max_gust_kmh);

    // Color by peak rain intensity
    const rainColors = maxRains.map(r => {
        if (r >= 30) return "#ef4444";
        if (r >= 25) return "#f59e0b";
        if (r >= 20) return "#a855f7";
        return "#06b6d4";
    });

    // Storm events rain chart (only storm days)
    const ctx1 = document.getElementById("daily-precip-chart");
    if (charts.dailyPrecip) charts.dailyPrecip.destroy();
    charts.dailyPrecip = new Chart(ctx1, {
        type: "bar",
        data: {
            labels: dates,
            datasets: [{
                label: "Peak Hourly Rain (mm/h)",
                data: maxRains,
                backgroundColor: rainColors,
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: {
                    ticks: { color: "#9ca3af" },
                    grid: { color: "#374151" },
                    title: { display: true, text: "Peak Rain (mm/h)", color: "#9ca3af" },
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterLabel: (ctx) => {
                            const i = ctx.dataIndex;
                            const e = events[i];
                            return `💨 Max gust: ${e.max_gust_kmh} km/h\n⏱ Storm hours: ${e.storm_hours}\n🌧 Total rain: ${e.total_rain_mm} mm`;
                        },
                    },
                },
            },
        },
    });

    // Gust chart
    const gustColors = maxGusts.map(g => {
        if (g >= 35) return "#ef4444";
        if (g >= 25) return "#a855f7";
        return "#6b7280";
    });

    const ctx2 = document.getElementById("daily-gust-chart");
    if (charts.dailyGust) charts.dailyGust.destroy();
    charts.dailyGust = new Chart(ctx2, {
        type: "bar",
        data: {
            labels: dates,
            datasets: [{
                label: "Max Gust (km/h)",
                data: maxGusts,
                backgroundColor: gustColors,
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: {
                    ticks: { color: "#9ca3af" },
                    grid: { color: "#374151" },
                    title: { display: true, text: "Max Gust (km/h)", color: "#9ca3af" },
                },
            },
            plugins: { legend: { display: false } },
        },
    });
}

// ── Monthly chart ───────────────────────────────────────────────────
function renderMonthlyChart(data) {
    const monthly = data.monthly_totals || {};
    const keys = Object.keys(monthly).sort();
    const stormDays = keys.map(k => monthly[k].storm_days);
    const rainTotals = keys.map(k => monthly[k].total_rain_mm);

    const ctx = document.getElementById("monthly-chart");
    if (charts.monthly) charts.monthly.destroy();

    charts.monthly = new Chart(ctx, {
        type: "bar",
        data: {
            labels: keys,
            datasets: [
                {
                    label: "Rainfall (mm)",
                    data: rainTotals,
                    backgroundColor: "#06b6d4",
                    yAxisID: "y",
                    order: 2,
                },
                {
                    label: "Storm Days",
                    data: stormDays,
                    type: "line",
                    borderColor: "#a855f7",
                    backgroundColor: "#a855f780",
                    pointRadius: 2,
                    tension: 0.3,
                    yAxisID: "y1",
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: "#9ca3af", maxRotation: 45 }, grid: { display: false } },
                y: {
                    position: "left",
                    title: { display: true, text: "Rainfall (mm)", color: "#9ca3af" },
                    ticks: { color: "#9ca3af" },
                    grid: { color: "#374151" },
                },
                y1: {
                    position: "right",
                    title: { display: true, text: "Storm Days", color: "#a855f7" },
                    ticks: { color: "#a855f7", stepSize: 1 },
                    grid: { display: false },
                },
            },
            plugins: {
                legend: { labels: { color: "#d1d5db" } },
            },
        },
    });
}

// ── Storms table ────────────────────────────────────────────────────
function renderStormsTable(data) {
    const events = data.storm_events || [];
    const el = document.getElementById("storms-table");

    if (events.length === 0) {
        el.innerHTML = '<div class="text-gray-500 text-sm">No significant storm events</div>';
        return;
    }

    el.innerHTML = `
        <div class="text-xs text-gray-500 mb-2">Thunderstorm = Rain \u226510mm/h, OR Rain \u22655mm/h + Gust \u226525km/h, OR Gust \u226535km/h. Sorted latest first.</div>
        <table class="w-full text-xs">
            <thead>
                <tr class="text-gray-400 border-b border-gray-600">
                    <th class="py-2 text-left">Date</th>
                    <th class="py-2 text-right">Storm Hours</th>
                    <th class="py-2 text-right">Total Rain (mm)</th>
                    <th class="py-2 text-right">Peak Rain (mm/h)</th>
                    <th class="py-2 text-right">Max Gust (km/h)</th>
                </tr>
            </thead>
            <tbody>
                ${events.map(e => `
                    <tr class="border-b border-gray-700 hover:bg-gray-750">
                        <td class="py-1.5 text-gray-300">${e.date}</td>
                        <td class="py-1.5 text-right text-purple-400 font-bold">${e.storm_hours}</td>
                        <td class="py-1.5 text-right text-cyan-400">${e.total_rain_mm}</td>
                        <td class="py-1.5 text-right" style="color:${e.max_rain_mmh >= 10 ? '#ef4444' : e.max_rain_mmh >= 5 ? '#a855f7' : '#9ca3af'}">${e.max_rain_mmh}</td>
                        <td class="py-1.5 text-right" style="color:${e.max_gust_kmh >= 35 ? '#ef4444' : e.max_gust_kmh >= 25 ? '#a855f7' : '#9ca3af'}">${e.max_gust_kmh}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;

    // Consecutive storm periods
    const periods = data.consecutive_storm_periods || [];
    if (periods.length > 0) {
        el.innerHTML += `
            <h4 class="text-sm font-semibold text-gray-300 mt-6 mb-2">Consecutive Storm Days (2+ days)</h4>
            <table class="w-full text-xs">
                <thead>
                    <tr class="text-gray-400 border-b border-gray-600">
                        <th class="py-2 text-left">Start</th>
                        <th class="py-2 text-left">End</th>
                        <th class="py-2 text-right">Days</th>
                        <th class="py-2 text-right">Storm Hours</th>
                        <th class="py-2 text-right">Total Rain (mm)</th>
                        <th class="py-2 text-right">Peak Rain (mm/h)</th>
                        <th class="py-2 text-right">Max Gust (km/h)</th>
                    </tr>
                </thead>
                <tbody>
                    ${periods.map(p => `
                        <tr class="border-b border-gray-700">
                            <td class="py-1.5 text-gray-300">${p.start}</td>
                            <td class="py-1.5 text-gray-300">${p.end}</td>
                            <td class="py-1.5 text-right text-purple-400 font-bold">${p.days}</td>
                            <td class="py-1.5 text-right text-red-400">${p.total_storm_hours}</td>
                            <td class="py-1.5 text-right text-cyan-400">${p.total_rain_mm}</td>
                            <td class="py-1.5 text-right" style="color:${p.max_rain_mmh >= 10 ? '#ef4444' : p.max_rain_mmh >= 5 ? '#a855f7' : '#9ca3af'}">${p.max_rain_mmh}</td>
                            <td class="py-1.5 text-right" style="color:${p.max_gust_kmh >= 35 ? '#ef4444' : p.max_gust_kmh >= 25 ? '#a855f7' : '#9ca3af'}">${p.max_gust_kmh}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }
}

// ── Heatmap ─────────────────────────────────────────────────────────
let selectedHeatmapMonth = null; // { year, month } for detail view
let heatmapDailyData = null;     // cached raw daily data for detail

function renderHeatmap(data) {
    const heatmap = data.heatmap || {};
    const el = document.getElementById("heatmap-container");

    // Hide detail panel on new render
    document.getElementById("heatmap-detail").classList.add("hidden");
    selectedHeatmapMonth = null;

    const years = Object.keys(heatmap).sort();
    if (years.length === 0) {
        el.innerHTML = '<div class="text-gray-500 text-sm">No data for this period</div>';
        return;
    }

    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    function getCell(y, m) {
        const cell = (heatmap[y] || {})[String(m)];
        if (!cell) return { storm: 0, heavy: 0, clear: 0, lightning: 0, total: 0 };
        const total = (cell.storm||0) + (cell.heavy||0) + (cell.clear||0);
        return { lightning: 0, ...cell, total };
    }

    // Color by worst category in the month
    function cellStyle(c) {
        if (c.storm > 0) return "background:#7f1d1d;color:#fca5a5;";
        if (c.heavy > 0) return "background:#78350f;color:#fde68a;";
        if (c.clear > 0) return "background:#14532d;color:#86efac;";
        return "background:#1f2937;color:#4b5563;";
    }

    function cellTooltip(c) {
        if (c.total === 0) return "No data";
        const extra = c.lightning > 0 ? `, \u26A1 ${c.lightning} lightning day(s) (WMO 95/96/99)` : "";
        return `${c.storm} thunderstorm, ${c.heavy} heavy rain, ${c.clear} clear (${c.total} days)${extra}`;
    }

    // Legend (3 tiers + lightning)
    let html = `<div class="flex flex-wrap gap-3 mb-3 text-xs text-gray-400">
        <span><span style="display:inline-block;width:12px;height:12px;background:#7f1d1d;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>T = Thunderstorm</span>
        <span><span style="display:inline-block;width:12px;height:12px;background:#78350f;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>H = Heavy Rain (\u22655mm/h)</span>
        <span><span style="display:inline-block;width:12px;height:12px;background:#14532d;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>C = Clear / Light Rain</span>
        <span><span style="color:#fbbf24;margin-right:4px;">\u26A1N</span>= Lightning days (WMO 95/96/99)</span>
    </div>
    <div class="text-xs text-gray-500 mb-2">Thunderstorm = WMO 95/96/99, OR rain\u226510mm/h, OR rain\u22655mm/h + gust\u226525km/h, OR gust\u226535km/h. Click a cell for daily breakdown.</div>`;

    html += '<table class="text-xs"><thead><tr><th class="text-gray-400 py-1 px-2">Year</th>';
    months.forEach(m => { html += `<th class="text-gray-400 py-1 text-center">${m}</th>`; });
    html += '</tr></thead><tbody>';

    years.forEach(y => {
        html += `<tr><td class="text-gray-300 py-1 px-2 font-medium">${y}</td>`;
        for (let m = 1; m <= 12; m++) {
            const c = getCell(y, m);
            if (c.total === 0) {
                html += '<td class="text-center"><div class="heatmap-cell" style="background:#1f2937;color:#4b5563;">-</div></td>';
                continue;
            }
            // Show breakdown: T/H/C + ⚡
            const parts = [];
            if (c.storm > 0) parts.push(`<span style="color:#fca5a5">${c.storm}T</span>`);
            if (c.heavy > 0) parts.push(`<span style="color:#fde68a">${c.heavy}H</span>`);
            if (c.clear > 0) parts.push(`<span style="color:#86efac">${c.clear}C</span>`);
            if (c.lightning > 0) parts.push(`<span style="color:#fbbf24">\u26A1${c.lightning}</span>`);
            html += `<td class="text-center"><div class="heatmap-cell" style="${cellStyle(c)};cursor:pointer;min-width:70px;" onclick="selectHeatmapMonth('${y}',${m})" title="${cellTooltip(c)}">${parts.join(" ")}</div></td>`;
        }
        html += '</tr>';
    });

    // Totals row
    html += '<tr><td class="text-gray-400 py-1 px-2 font-medium">Total</td>';
    for (let m = 1; m <= 12; m++) {
        let mT = 0, mH = 0, mC = 0, mL = 0;
        years.forEach(y => {
            const c = getCell(y, m);
            mT += c.storm; mH += c.heavy; mC += c.clear; mL += (c.lightning || 0);
        });
        const parts = [];
        if (mT) parts.push(`<span style="color:#fca5a5">${mT}T</span>`);
        if (mH) parts.push(`<span style="color:#fde68a">${mH}H</span>`);
        if (mC) parts.push(`<span style="color:#86efac">${mC}C</span>`);
        if (mL) parts.push(`<span style="color:#fbbf24">\u26A1${mL}</span>`);
        html += `<td class="text-center"><div class="heatmap-cell" style="background:#374151;min-width:70px;font-weight:bold;">${parts.join(" ") || "-"}</div></td>`;
    }
    html += '</tr>';

    html += "</tbody></table>";
    el.innerHTML = html;
}

// ── Heatmap cell click → load daily detail ──────────────────────────
async function selectHeatmapMonth(year, month) {
    const monthNames = ["","January","February","March","April","May","June","July","August","September","October","November","December"];
    selectedHeatmapMonth = { year, month };

    const stationKey = currentAnalysis?.station_key;
    if (!stationKey) return;

    const mm = String(month).padStart(2, "0");
    const startDate = `${year}-${mm}-01`;
    // Last day of month, clamped to yesterday (archive API limit)
    const lastDay = new Date(parseInt(year), month, 0).getDate();
    let endDate = `${year}-${mm}-${String(lastDay).padStart(2, "0")}`;
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split("T")[0];
    if (endDate > yesterdayStr) endDate = yesterdayStr;
    if (startDate > yesterdayStr) {
        document.getElementById("heatmap-detail-table").innerHTML = '<div class="text-gray-400 text-sm">No archive data available yet for this month — data is available up to yesterday.</div>';
        document.getElementById("heatmap-detail").classList.remove("hidden");
        return;
    }

    const detailPanel = document.getElementById("heatmap-detail");
    const titleEl = document.getElementById("heatmap-detail-title");
    const tableEl = document.getElementById("heatmap-detail-table");

    titleEl.textContent = `Daily Breakdown — ${monthNames[month]} ${year}`;
    tableEl.innerHTML = '<div class="text-gray-400 text-sm">Loading daily data...</div>';
    detailPanel.classList.remove("hidden");

    try {
        // Use the new backend endpoint — same logic as heatmap
        const resp = await fetch(`${API}/api/thunder/daily/${stationKey}?year=${year}&month=${month}`);
        if (!resp.ok) throw new Error(`Failed: ${resp.status}`);
        const data = await resp.json();
        heatmapDailyData = data;

        const days = data.days || [];
        const dayNames = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

        if (days.length === 0) {
            tableEl.innerHTML = '<div class="text-gray-400 text-sm">No data available for this month yet.</div>';
            return;
        }

        let html = `
            <div class="text-xs text-gray-500 mb-2">Thunderstorm = WMO 95/96/99, OR Rain \u226510mm/h, OR Rain \u22655mm/h + Gust \u226525km/h, OR Gust \u226535km/h. Click a row for hourly detail.</div>
            <table class="w-full text-xs">
                <thead>
                    <tr class="text-gray-400 border-b border-gray-600">
                        <th class="py-2 text-left">Date</th>
                        <th class="py-2 text-left">Day</th>
                        <th class="py-2 text-right">Total Rain (mm)</th>
                        <th class="py-2 text-right">Peak Rain (mm/h)</th>
                        <th class="py-2 text-right">Max Gust (km/h)</th>
                        <th class="py-2 text-right">CAPE (J/kg)</th>
                        <th class="py-2 text-right">Storm Hours</th>
                        <th class="py-2 text-right">\u26A1 WMO</th>
                        <th class="py-2 text-center">Status</th>
                    </tr>
                </thead>
                <tbody>`;

        for (const d of days) {
            const dt = d.date;
            const dayName = dayNames[new Date(dt).getDay()];
            const isThunder = d.status === "THUNDERSTORM";
            const isStorm = d.status === "STORM";
            const isHeavy = d.status === "HEAVY";

            let statusHtml, rowBg;
            if (isThunder) {
                statusHtml = `<span class="text-xs px-1.5 py-0.5 rounded severity-critical">\u26C8 THUNDERSTORM (${d.wmo_thunder_hours}h WMO)</span>`;
                rowBg = "background: rgba(127,29,29,0.25);";
            } else if (isStorm) {
                statusHtml = `<span class="text-xs px-1.5 py-0.5 rounded severity-critical">STORM (${d.storm_hours}h)</span>`;
                rowBg = "background: rgba(127,29,29,0.15);";
            } else if (isHeavy) {
                statusHtml = `<span class="text-xs px-1.5 py-0.5 rounded severity-severe">HEAVY RAIN</span>`;
                rowBg = "background: rgba(120,53,15,0.15);";
            } else {
                statusHtml = '<span class="text-xs text-gray-600">\u2014</span>';
                rowBg = "";
            }

            html += `
                <tr class="border-b border-gray-700 cursor-pointer hover:bg-gray-600" style="${rowBg}" onclick="toggleHourly('${dt}','archive')" title="Click for hourly breakdown">
                    <td class="py-1.5 text-gray-300">${dt} <span class="text-gray-500 text-xs">\u25B8</span></td>
                    <td class="py-1.5 text-gray-400">${dayName}</td>
                    <td class="py-1.5 text-right text-cyan-400">${d.total_rain_mm.toFixed(1)}</td>
                    <td class="py-1.5 text-right" style="color:${d.max_rain_mmh >= 10 ? '#ef4444' : d.max_rain_mmh >= 5 ? '#a855f7' : '#9ca3af'}">${d.max_rain_mmh.toFixed(1)}</td>
                    <td class="py-1.5 text-right" style="color:${d.max_gust_kmh >= 35 ? '#ef4444' : d.max_gust_kmh >= 25 ? '#a855f7' : '#9ca3af'}">${d.max_gust_kmh.toFixed(1)}</td>
                    <td class="py-1.5 text-right" style="color:${d.max_cape >= 2000 ? '#ef4444' : d.max_cape >= 1000 ? '#f59e0b' : d.max_cape >= 500 ? '#a855f7' : '#9ca3af'}">${d.max_cape || '-'}</td>
                    <td class="py-1.5 text-right ${d.storm_hours > 0 ? 'text-red-400 font-bold' : 'text-gray-500'}">${d.storm_hours}</td>
                    <td class="py-1.5 text-right ${d.wmo_thunder_hours > 0 ? 'text-yellow-400 font-bold' : 'text-gray-600'}">${d.wmo_thunder_hours || '-'}</td>
                    <td class="py-1.5 text-center">${statusHtml}</td>
                </tr>
                <tr id="hourly-${dt}" class="hidden"><td colspan="9" class="p-0"><div id="hourly-c-${dt}" class="bg-gray-900 px-3 py-2"></div></td></tr>`;
        }

        html += "</tbody></table>";
        tableEl.innerHTML = html;
    } catch (err) {
        console.error(err);
        tableEl.innerHTML = '<div class="text-red-400 text-sm">Failed to load daily data</div>';
    }
}

// ── Export daily detail to Excel ─────────────────────────────────────
function exportDetailToExcel() {
    if (!heatmapDailyData) {
        alert("No daily data to export. Click a month cell first.");
        return;
    }

    // Use the same pre-computed daily data from backend
    const days = heatmapDailyData.days || [];
    const stationName = heatmapDailyData.station_name || currentAnalysis?.station_name || "Station";
    const monthNames = ["","January","February","March","April","May","June","July","August","September","October","November","December"];
    const monthLabel = selectedHeatmapMonth
        ? `${monthNames[selectedHeatmapMonth.month]} ${selectedHeatmapMonth.year}`
        : "";
    const dayNames = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];

    let csv = "\uFEFF";
    csv += `Daily Storm Analysis \u2014 ${stationName}\r\n`;
    csv += `Month: ${monthLabel}\r\n`;
    csv += `Criteria: Thunderstorm = WMO 95/96/99, OR Rain >= 10mm/h, OR Rain >= 5mm/h + Gust >= 25km/h, OR Gust >= 35km/h\r\n`;
    csv += `\r\n`;
    csv += `Date,Day,Total Rain (mm),Peak Rain (mm/h),Max Gust (km/h),CAPE (J/kg),Storm Hours,WMO Thunder Hours,Status\r\n`;

    for (const d of days) {
        const dayName = dayNames[new Date(d.date).getDay()];
        csv += `${d.date},${dayName},${d.total_rain_mm.toFixed(1)},${d.max_rain_mmh.toFixed(1)},${d.max_gust_kmh.toFixed(1)},${d.max_cape},${d.storm_hours},${d.wmo_thunder_hours},${d.status}\r\n`;
    }

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `storm_daily_${stationName.replace(/\s+/g, "_")}_${selectedHeatmapMonth?.year || ""}_${String(selectedHeatmapMonth?.month || "").padStart(2,"0")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Compare all stations ────────────────────────────────────────────
document.getElementById("compare-btn").addEventListener("click", runCompare);

async function runCompare() {
    const startDate = document.getElementById("start-date").value;
    const endDate = document.getElementById("end-date").value || new Date().toISOString().split("T")[0];
    const lineKey = document.getElementById("line-select").value;

    // Compare selected line's stations, or all if no line selected
    let stationsParam = "";
    if (lineKey && linesData[lineKey]) {
        const keys = linesData[lineKey].stations.map(s => s.key).join(",");
        stationsParam = `&stations=${keys}`;
    }

    const label = lineKey ? linesData[lineKey].name : "all stations";
    setStatus(`Comparing ${label} (this may take a moment)...`, true);

    try {
        const resp = await fetch(
            `${API}/api/thunder/compare?start=${startDate}&end=${endDate}${stationsParam}`
        );
        if (!resp.ok) throw new Error(`Compare failed: ${resp.status}`);
        const data = await resp.json();

        renderCompareChart(data);
        renderCompareTable(data);
        renderOverviewTable(data);
        updateStationMarkersFromCompare(data);

        // Switch to compare tab
        document.querySelectorAll(".tab-btn").forEach(b => {
            b.classList.remove("tab-active");
            b.classList.add("tab-inactive");
        });
        const compareBtn = document.querySelector('[data-tab="compare"]');
        compareBtn.classList.remove("tab-inactive");
        compareBtn.classList.add("tab-active");
        document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
        document.getElementById("panel-compare").classList.remove("hidden");

        setStatus(`Compared ${data.count} stations`, false);
    } catch (err) {
        console.error(err);
        setStatus("Compare failed", false);
    }
}

function renderCompareChart(data) {
    const comp = data.comparison || [];
    const ctx = document.getElementById("compare-chart");
    if (charts.compare) charts.compare.destroy();

    const colors = comp.map(c => riskColor(c.risk_score));

    charts.compare = new Chart(ctx, {
        type: "bar",
        data: {
            labels: comp.map(c => c.station_name),
            datasets: [
                {
                    label: "Risk Score",
                    data: comp.map(c => c.risk_score),
                    backgroundColor: colors,
                    order: 2,
                },
                {
                    label: "Storm Days",
                    data: comp.map(c => c.storm_days),
                    type: "line",
                    borderColor: "#a855f7",
                    pointBackgroundColor: "#a855f7",
                    pointRadius: 4,
                    tension: 0.3,
                    yAxisID: "y1",
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: "#9ca3af", maxRotation: 45 }, grid: { display: false } },
                y: {
                    position: "left",
                    title: { display: true, text: "Risk Score", color: "#9ca3af" },
                    ticks: { color: "#9ca3af" },
                    grid: { color: "#374151" },
                    max: 100,
                },
                y1: {
                    position: "right",
                    title: { display: true, text: "Storm Days", color: "#a855f7" },
                    ticks: { color: "#a855f7" },
                    grid: { display: false },
                },
            },
            plugins: {
                legend: { labels: { color: "#d1d5db" } },
            },
        },
    });
}

function renderCompareTable(data) {
    const comp = data.comparison || [];
    const el = document.getElementById("compare-table");

    el.innerHTML = `
        <table class="w-full text-xs">
            <thead>
                <tr class="text-gray-400 border-b border-gray-600">
                    <th class="py-2 text-left">#</th>
                    <th class="py-2 text-left">Station</th>
                    <th class="py-2 text-right">Risk</th>
                    <th class="py-2 text-right">Storm Days</th>
                    <th class="py-2 text-right">Storm Hours</th>
                    <th class="py-2 text-right">Peak Rain (mm/h)</th>
                    <th class="py-2 text-right">Max Gust (km/h)</th>
                    <th class="py-2 text-left">Peak Month</th>
                </tr>
            </thead>
            <tbody>
                ${comp.map((c, i) => `
                    <tr class="border-b border-gray-700 hover:bg-gray-750">
                        <td class="py-1.5 text-gray-400">${i + 1}</td>
                        <td class="py-1.5 text-gray-200 font-medium">${c.station_name}</td>
                        <td class="py-1.5 text-right font-bold" style="color:${riskColor(c.risk_score)}">${c.risk_score}</td>
                        <td class="py-1.5 text-right text-purple-400">${c.storm_days}</td>
                        <td class="py-1.5 text-right text-red-400">${c.storm_hours}</td>
                        <td class="py-1.5 text-right" style="color:${c.max_hourly_rain_mm >= 10 ? '#ef4444' : c.max_hourly_rain_mm >= 5 ? '#a855f7' : '#9ca3af'}">${c.max_hourly_rain_mm}</td>
                        <td class="py-1.5 text-right" style="color:${c.max_hourly_gust_kmh >= 35 ? '#ef4444' : c.max_hourly_gust_kmh >= 25 ? '#a855f7' : '#9ca3af'}">${c.max_hourly_gust_kmh}</td>
                        <td class="py-1.5 text-gray-300">${c.peak_storm_month}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function renderOverviewTable(data) {
    const el = document.getElementById("overview-table");
    // Reuse compare table for overview
    el.innerHTML = document.getElementById("compare-table").innerHTML;
}

// ── Update map markers with risk data ───────────────────────────────
function updateStationMarker(key, data) {
    const marker = stationMarkers[key];
    if (!marker) return;
    const s = data.summary;

    marker.setPopupContent(`
        <div style="font-family: system-ui; font-size: 13px; min-width: 200px;">
            <strong>🚆 ${data.station_name}</strong><br>
            <span style="color:#9ca3af">Risk:</span>
            <strong style="color:${riskColor(s.risk_score)}">${s.risk_score}/100 (${s.risk_level.toUpperCase()})</strong><br>
            <span style="color:#9ca3af">Storm Days:</span> ${s.storm_days}<br>
            <span style="color:#9ca3af">Storm Hours:</span> ${s.storm_hours}<br>
            <span style="color:#9ca3af">Peak Rain:</span> ${s.max_hourly_rain_mm} mm/h<br>
            <span style="color:#9ca3af">Peak Month:</span> ${s.peak_storm_month}
        </div>
    `);
}

function updateStationMarkersFromCompare(data) {
    (data.comparison || []).forEach(c => {
        const marker = stationMarkers[c.station_key];
        if (!marker) return;

        const icon = L.divIcon({
            className: "train-risk-icon",
            html: `<div style="
                font-size: 14px; text-align: center; line-height: 1;
                text-shadow: 0 1px 4px rgba(0,0,0,0.7);
            ">🚆<div style="
                font-size: 10px; font-weight: bold;
                color: ${riskColor(c.risk_score)};
                text-shadow: 0 0 3px rgba(0,0,0,0.9);
            ">${c.risk_score}</div></div>`,
            iconSize: [30, 36],
            iconAnchor: [15, 18],
            popupAnchor: [0, -18],
        });
        marker.setIcon(icon);

        marker.setPopupContent(`
            <div style="font-family: system-ui; font-size: 13px; min-width: 200px;">
                <strong>🚆 ${c.station_name}</strong><br>
                <span style="color:#9ca3af">Risk:</span>
                <strong style="color:${riskColor(c.risk_score)}">${c.risk_score}/100 (${c.risk_level.toUpperCase()})</strong><br>
                <span style="color:#9ca3af">Storm Days:</span> ${c.storm_days}<br>
                <span style="color:#9ca3af">Storm Hours:</span> ${c.storm_hours}<br>
                <span style="color:#9ca3af">Peak Rain:</span> ${c.max_hourly_rain_mm} mm/h
            </div>
        `);
    });
}

// ── Forecast ────────────────────────────────────────────────────────
let forecastData = null;

const WMO_NAMES = {
    0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Fog",48:"Rime fog",51:"Light drizzle",53:"Mod drizzle",55:"Dense drizzle",
    56:"Freezing drizzle",57:"Dense freezing drizzle",
    61:"Slight rain",63:"Mod rain",65:"Heavy rain",
    66:"Freezing rain",67:"Heavy freezing rain",
    71:"Slight snow",73:"Mod snow",75:"Heavy snow",77:"Snow grains",
    80:"Slight showers",81:"Mod showers",82:"Violent showers",
    85:"Slight snow showers",86:"Heavy snow showers",
    95:"Thunderstorm",96:"T-storm + hail",99:"T-storm + heavy hail",
};

const WMO_ICONS = {
    0:"\u2600",1:"\u{1F324}",2:"\u26C5",3:"\u2601",
    45:"\u{1F32B}",48:"\u{1F32B}",
    51:"\u{1F326}",53:"\u{1F326}",55:"\u{1F326}",
    61:"\u{1F327}",63:"\u{1F327}",65:"\u{1F327}",
    80:"\u{1F326}",81:"\u{1F327}",82:"\u{1F327}",
    95:"\u26C8",96:"\u26C8",99:"\u26C8",
};

async function loadForecast() {
    const stationKey = document.getElementById("station-select").value;
    if (!stationKey) { alert("Please select a station"); return; }

    const tableEl = document.getElementById("forecast-table");
    const summaryEl = document.getElementById("forecast-summary");
    tableEl.innerHTML = '<div class="text-gray-400 text-sm">Loading 16-day forecast...</div>';

    try {
        const resp = await fetch(`${API}/api/thunder/forecast/${stationKey}`);
        if (!resp.ok) throw new Error(`Forecast failed: ${resp.status}`);
        forecastData = await resp.json();
        forecastHourlyCache = null; // clear hourly cache for new station

        const d = forecastData.daily;
        const times = d.time || [];
        const precip = d.precipitation_sum || [];
        const rain = d.rain_sum || precip;
        const gusts = d.wind_gusts_10m_max || [];
        const hours = d.precipitation_hours || [];
        const prob = d.precipitation_probability_max || [];
        const codes = d.weathercode || [];
        const tMax = d.temperature_2m_max || [];
        const tMin = d.temperature_2m_min || [];
        const capeMax = d.cape_max || [];

        const dayNames = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

        // Summary KPIs
        const stormDays = codes.filter(c => c === 95 || c === 96 || c === 99).length;
        const maxRain = Math.max(...rain.map(r => r || 0));
        const maxGust = Math.max(...gusts.map(g => g || 0));
        const maxProb = Math.max(...prob.map(p => p || 0));

        document.getElementById("fc-storm-days").textContent = stormDays;
        document.getElementById("fc-max-rain").textContent = maxRain.toFixed(1);
        document.getElementById("fc-max-gust").textContent = maxGust.toFixed(1);
        document.getElementById("fc-max-prob").textContent = maxProb + "%";
        summaryEl.classList.remove("hidden");

        // Table
        let html = `
            <table class="w-full text-xs">
                <thead>
                    <tr class="text-gray-400 border-b border-gray-600">
                        <th class="py-2 text-left">Date</th>
                        <th class="py-2 text-left">Day</th>
                        <th class="py-2 text-center">Weather</th>
                        <th class="py-2 text-right">Rain (mm)</th>
                        <th class="py-2 text-right">Gusts (km/h)</th>
                        <th class="py-2 text-right">Rain Prob</th>
                        <th class="py-2 text-right">CAPE (J/kg)</th>
                        <th class="py-2 text-center">Lightning Risk</th>
                        <th class="py-2 text-right">Temp</th>
                        <th class="py-2 text-center">Alert</th>
                    </tr>
                </thead>
                <tbody>`;

        for (let i = 0; i < times.length; i++) {
            const dt = times[i];
            const mm = (rain[i] || 0);
            const g = gusts[i] || 0;
            const p = prob[i] || 0;
            const h = hours[i] || 0;
            const wc = codes[i] || 0;
            const dayName = dayNames[new Date(dt).getDay()];
            const icon = WMO_ICONS[wc] || "";
            const weatherName = WMO_NAMES[wc] || `WMO ${wc}`;
            const tempStr = `${(tMax[i] ?? "").toString()}/${(tMin[i] ?? "").toString()}`;

            const isThunder = wc === 95 || wc === 96 || wc === 99;
            const isHeavyRain = mm >= 15;
            const isGustWarn = g >= 25;

            let alert = "";
            let rowBg = "";
            if (isThunder && (isHeavyRain || isGustWarn)) {
                alert = '<span class="text-xs px-1.5 py-0.5 rounded severity-critical">CRITICAL</span>';
                rowBg = "background: rgba(127,29,29,0.2);";
            } else if (isThunder) {
                alert = '<span class="text-xs px-1.5 py-0.5 rounded severity-severe">STORM</span>';
                rowBg = "background: rgba(120,53,15,0.15);";
            } else if (isHeavyRain || isGustWarn) {
                alert = '<span class="text-xs px-1.5 py-0.5 rounded severity-moderate">WARNING</span>';
                rowBg = "background: rgba(30,58,95,0.15);";
            } else {
                alert = '<span class="text-xs text-gray-600">\u2014</span>';
            }

            html += `
                <tr class="border-b border-gray-700 cursor-pointer hover:bg-gray-600" style="${rowBg}" onclick="toggleHourly('${dt}','forecast')" title="Click for hourly breakdown">
                    <td class="py-1.5 text-gray-300">${dt} <span class="text-gray-500 text-xs">▸</span></td>
                    <td class="py-1.5 text-gray-400">${dayName}</td>
                    <td class="py-1.5 text-center" title="${weatherName}">${icon} <span class="text-gray-400">${weatherName}</span></td>
                    <td class="py-1.5 text-right" style="color:${mm >= 30 ? '#ef4444' : mm >= 15 ? '#a855f7' : '#9ca3af'}">${mm.toFixed(1)}</td>
                    <td class="py-1.5 text-right" style="color:${g >= 35 ? '#ef4444' : g >= 25 ? '#a855f7' : '#9ca3af'}">${g.toFixed(1)}</td>
                    <td class="py-1.5 text-right" style="color:${p >= 80 ? '#ef4444' : p >= 50 ? '#f59e0b' : '#9ca3af'}">${p}%</td>
                    <td class="py-1.5 text-right" style="color:${(capeMax[i] || 0) >= 2000 ? '#ef4444' : (capeMax[i] || 0) >= 1000 ? '#f59e0b' : '#9ca3af'}">${(capeMax[i] || 0).toFixed(0)}</td>
                    <td class="py-1.5 text-center">${
                        (capeMax[i] || 0) >= 2000 ? '<span class="severity-critical px-1.5 py-0.5 rounded text-xs">\u26A1 HIGH</span>' :
                        (capeMax[i] || 0) >= 1000 ? '<span class="severity-severe px-1.5 py-0.5 rounded text-xs">\u26A1 MODERATE</span>' :
                        (capeMax[i] || 0) >= 500 ? '<span class="severity-moderate px-1.5 py-0.5 rounded text-xs">\u26A1 LOW</span>' :
                        '<span class="text-gray-600">\u2014</span>'
                    }</td>
                    <td class="py-1.5 text-right text-gray-400">${tempStr}\u00B0C</td>
                    <td class="py-1.5 text-center">${alert}</td>
                </tr>
                <tr id="hourly-${dt}" class="hidden"><td colspan="10" class="p-0"><div id="hourly-c-${dt}" class="bg-gray-900 px-3 py-2"></div></td></tr>`;
        }

        html += "</tbody></table>";
        tableEl.innerHTML = html;

        // Chart
        renderForecastChart(forecastData);

        setStatus(`Forecast loaded for ${forecastData.station_name}`, false);
    } catch (err) {
        console.error(err);
        tableEl.innerHTML = '<div class="text-red-400 text-sm">Failed to load forecast</div>';
    }
}

function renderForecastChart(data) {
    const d = data.daily;
    const times = d.time || [];
    const rain = d.rain_sum || d.precipitation_sum || [];
    const gusts = d.wind_gusts_10m_max || [];
    const codes = d.weathercode || [];

    const barColors = times.map((_, i) => {
        const wc = codes[i];
        if (wc === 95 || wc === 96 || wc === 99) return "#a855f7";
        if ((rain[i] || 0) >= 20) return "#06b6d4";
        return "#374151";
    });

    const ctx = document.getElementById("forecast-chart");
    if (charts.forecast) charts.forecast.destroy();

    charts.forecast = new Chart(ctx, {
        type: "bar",
        data: {
            labels: times,
            datasets: [
                {
                    label: "Rain (mm)",
                    data: rain,
                    backgroundColor: barColors,
                    yAxisID: "y",
                    order: 2,
                },
                {
                    label: "Gusts (km/h)",
                    data: gusts,
                    type: "line",
                    borderColor: "#ef4444",
                    pointBackgroundColor: gusts.map(g => (g || 0) >= 33 ? "#ef4444" : "#6b7280"),
                    pointRadius: 4,
                    tension: 0.3,
                    yAxisID: "y1",
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: "#9ca3af" }, grid: { display: false } },
                y: {
                    position: "left",
                    title: { display: true, text: "Rain (mm)", color: "#9ca3af" },
                    ticks: { color: "#9ca3af" },
                    grid: { color: "#374151" },
                },
                y1: {
                    position: "right",
                    title: { display: true, text: "Gusts (km/h)", color: "#ef4444" },
                    ticks: { color: "#ef4444" },
                    grid: { display: false },
                },
            },
            plugins: {
                legend: { labels: { color: "#d1d5db" } },
                tooltip: {
                    callbacks: {
                        afterLabel: (ctx) => {
                            const i = ctx.dataIndex;
                            const wc = codes[i];
                            return WMO_NAMES[wc] || "";
                        },
                    },
                },
            },
        },
    });
}

function exportForecastToExcel() {
    if (!forecastData) {
        alert("No forecast data. Load a forecast first.");
        return;
    }

    const d = forecastData.daily;
    const times = d.time || [];
    const precip = d.precipitation_sum || [];
    const rain = d.rain_sum || precip;
    const gusts = d.wind_gusts_10m_max || [];
    const hours = d.precipitation_hours || [];
    const prob = d.precipitation_probability_max || [];
    const codes = d.weathercode || [];
    const tMax = d.temperature_2m_max || [];
    const tMin = d.temperature_2m_min || [];
    const stationName = forecastData.station_name || "Station";
    const dayNames = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];

    let csv = "\uFEFF";
    csv += `16-Day Weather Forecast \u2014 ${stationName}\r\n`;
    csv += `Generated: ${new Date().toISOString().split("T")[0]}\r\n`;
    csv += `Coordinates: ${forecastData.lat}, ${forecastData.lng}\r\n`;
    csv += `\r\n`;
    csv += `Date,Day,Weather Code,Weather,Rain (mm),Wind Gust (km/h),Rain Probability %,Rain Hours,Temp Max (C),Temp Min (C),Alert\r\n`;

    for (let i = 0; i < times.length; i++) {
        const dt = times[i];
        const mm = rain[i] || 0;
        const g = gusts[i] || 0;
        const p = prob[i] || 0;
        const h = hours[i] || 0;
        const wc = codes[i] || 0;
        const dayName = dayNames[new Date(dt).getDay()];
        const weather = (WMO_NAMES[wc] || "").replace(/,/g, ";");

        const isThunder = wc === 95 || wc === 96 || wc === 99;
        let alert = "Normal";
        if (isThunder && (mm >= 15 || g >= 25)) alert = "CRITICAL";
        else if (isThunder) alert = "STORM";
        else if (mm >= 15 || g >= 25) alert = "WARNING";

        csv += `${dt},${dayName},${wc},"${weather}",${mm.toFixed(1)},${g.toFixed(1)},${p},${h.toFixed(1)},${tMax[i] ?? ""},${tMin[i] ?? ""},${alert}\r\n`;
    }

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `forecast_${stationName.replace(/\s+/g, "_")}_${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Hourly drill-down (shared for heatmap detail + forecast) ────────
let forecastHourlyCache = null; // cached hourly forecast data

async function toggleHourly(dateStr, source) {
    const row = document.getElementById(`hourly-${dateStr}`);
    const content = document.getElementById(`hourly-c-${dateStr}`);
    if (!row || !content) return;

    // Toggle visibility
    if (!row.classList.contains("hidden")) {
        row.classList.add("hidden");
        return;
    }
    row.classList.remove("hidden");

    // Already loaded?
    if (content.dataset.loaded === "true") return;

    content.innerHTML = '<div class="text-gray-400 text-xs py-1">Loading hourly data...</div>';

    try {
        let hourlyData;

        if (source === "forecast") {
            // Use cached forecast hourly or fetch once
            if (!forecastHourlyCache) {
                const stationKey = forecastData?.station_key || document.getElementById("station-select").value;
                const resp = await fetch(`${API}/api/thunder/forecast-hourly/${stationKey}`);
                if (!resp.ok) throw new Error(`${resp.status}`);
                forecastHourlyCache = await resp.json();
            }
            hourlyData = forecastHourlyCache.hourly;
        } else {
            // Archive: fetch single day
            const stationKey = currentAnalysis?.station_key || document.getElementById("station-select").value;
            const resp = await fetch(`${API}/api/thunder/hourly/${stationKey}?date=${dateStr}`);
            if (!resp.ok) throw new Error(`${resp.status}`);
            const data = await resp.json();
            hourlyData = data.hourly;
        }

        // Filter to just this date's hours
        const times = hourlyData.time || [];
        const rainArr = hourlyData.rain || hourlyData.precipitation || [];
        const gustsArr = hourlyData.wind_gusts_10m || [];
        const codesArr = hourlyData.weathercode || [];
        const tempArr = hourlyData.temperature_2m || [];
        const capeArr = hourlyData.cape || [];
        // CAPE now available for both forecast and historical-forecast archive (2022+)
        const showCape = capeArr.some(v => v !== null && v !== undefined && v > 0);

        let html = `<table class="w-full text-xs">
            <thead><tr class="text-gray-500 border-b border-gray-700">
                <th class="py-1 text-left">Hour</th>
                <th class="py-1 text-right">Rain (mm)</th>
                <th class="py-1 text-right">Gust (km/h)</th>
                ${showCape ? '<th class="py-1 text-right">CAPE</th><th class="py-1 text-center">\u26A1</th>' : ''}
                <th class="py-1 text-center">Weather</th>
                <th class="py-1 text-right">Temp (\u00B0C)</th>
                <th class="py-1 text-left">Classification</th>
            </tr></thead><tbody>`;

        let found = false;
        for (let i = 0; i < times.length; i++) {
            if (!times[i].startsWith(dateStr)) continue;
            found = true;

            const hour = times[i].substring(11, 16);
            const r = rainArr[i] || 0;
            const g = gustsArr[i] || 0;
            const wc = codesArr[i] || 0;
            const t = tempArr[i] ?? "";
            const icon = WMO_ICONS[wc] || "";
            const wName = WMO_NAMES[wc] || "";

            // Option B thresholds (match backend config)
            let classification = "";
            let rowStyle = "";
            if (r >= 10) {
                classification = `<span class="severity-critical px-1.5 py-0.5 rounded">\u26C8 THUNDERSTORM</span> Rain ${r.toFixed(1)}mm/h \u2265 10mm/h`;
                rowStyle = "background:rgba(127,29,29,0.25);";
            } else if (r >= 5 && g >= 25) {
                classification = `<span class="severity-critical px-1.5 py-0.5 rounded">\u26C8 THUNDERSTORM</span> Rain ${r.toFixed(1)}mm/h + Gust ${g.toFixed(1)}km/h (convective)`;
                rowStyle = "background:rgba(127,29,29,0.25);";
            } else if (g >= 35) {
                classification = `<span class="severity-critical px-1.5 py-0.5 rounded">\u26C8 THUNDERSTORM</span> Gust ${g.toFixed(1)}km/h \u2265 35km/h`;
                rowStyle = "background:rgba(127,29,29,0.25);";
            } else if (r >= 5) {
                classification = `<span class="severity-severe px-1.5 py-0.5 rounded">\u{1F327} Heavy Rain</span>`;
                rowStyle = "background:rgba(120,53,15,0.15);";
            } else if (r >= 2) {
                classification = `<span class="severity-moderate px-1.5 py-0.5 rounded">\u{1F326} Light Rain</span>`;
                rowStyle = "background:rgba(30,58,95,0.15);";
            } else if (r >= 0.3) {
                classification = `<span class="text-gray-400">\u{1F4A7} Drizzle</span>`;
            } else {
                classification = `<span class="text-gray-600">\u2014 Clear</span>`;
            }

            const cape = capeArr[i] || 0;
            const capeCell = showCape
                ? `<td class="py-0.5 text-right font-mono" style="color:${cape >= 2000 ? '#ef4444' : cape >= 1000 ? '#f59e0b' : cape >= 500 ? '#a855f7' : '#6b7280'}">${cape.toFixed(0)}</td>
                   <td class="py-0.5 text-center">${cape >= 2000 ? '\u26A1\u26A1\u26A1' : cape >= 1000 ? '\u26A1\u26A1' : cape >= 500 ? '\u26A1' : '<span class="text-gray-700">\u2014</span>'}</td>`
                : '';

            html += `<tr class="border-b border-gray-800" style="${rowStyle}">
                <td class="py-0.5 text-gray-300 font-mono">${hour}</td>
                <td class="py-0.5 text-right font-mono" style="color:${r >= 10 ? '#ef4444' : r >= 5 ? '#f59e0b' : r >= 2 ? '#a855f7' : '#6b7280'}">${r.toFixed(1)}</td>
                <td class="py-0.5 text-right font-mono" style="color:${g >= 35 ? '#ef4444' : g >= 25 ? '#a855f7' : '#6b7280'}">${g.toFixed(1)}</td>
                ${capeCell}
                <td class="py-0.5 text-center" title="${wName}">${icon} <span class="text-gray-500">${wName}</span></td>
                <td class="py-0.5 text-right text-gray-400 font-mono">${t}</td>
                <td class="py-0.5 text-xs">${classification}</td>
            </tr>`;
        }

        if (!found) {
            const colspan = showCape ? 8 : 6;
            html += `<tr><td colspan="${colspan}" class="text-gray-500 py-1">No hourly data for this date</td></tr>`;
        }

        html += "</tbody></table>";
        content.innerHTML = html;
        content.dataset.loaded = "true";
    } catch (err) {
        console.error(err);
        content.innerHTML = '<div class="text-red-400 text-xs py-1">Failed to load hourly data</div>';
    }
}

// ── Init ────────────────────────────────────────────────────────────
document.getElementById("end-date").valueAsDate = new Date();
loadStations();
