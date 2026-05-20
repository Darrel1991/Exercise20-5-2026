// ── Chart.js: Vehicles per Agency Bar Chart ─────────────────────────
let agencyChart = null;

function initAgencyChart() {
    const ctx = document.getElementById("agency-chart").getContext("2d");
    agencyChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: [],
            datasets: [{
                label: "Active Vehicles",
                data: [],
                backgroundColor: "#3b82f6",
                borderColor: "#2563eb",
                borderWidth: 1,
                borderRadius: 3,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { color: "#9ca3af", font: { size: 10 } },
                    grid: { color: "rgba(255,255,255,0.05)" },
                },
                y: {
                    ticks: { color: "#9ca3af", font: { size: 10 } },
                    grid: { display: false },
                },
            },
        },
    });
}

function updateAgencyChart(agencyCounts) {
    if (!agencyChart) initAgencyChart();

    // Sort by count descending
    const sorted = Object.entries(agencyCounts).sort((a, b) => b[1] - a[1]);

    agencyChart.data.labels = sorted.map(([k]) => k.replace("prasarana-rapid-bus-", "pr-").replace("mybas-", "mb-"));
    agencyChart.data.datasets[0].data = sorted.map(([, v]) => v);
    agencyChart.data.datasets[0].backgroundColor = sorted.map(([k]) => {
        if (k === "ktmb") return "#3b82f6";
        if (k.startsWith("prasarana")) return "#22c55e";
        return "#f97316";
    });
    agencyChart.update();
}

// ── KPI + Agency Status Updates ─────────────────────────────────────
const API_BASE = window.location.origin;

async function fetchSummary() {
    try {
        const resp = await fetch(`${API_BASE}/api/analysis/summary`);
        const data = await resp.json();

        document.getElementById("kpi-active").textContent = data.total_active_vehicles ?? "--";
        document.getElementById("kpi-stalled").textContent = data.stalled_vehicles ?? "--";
        document.getElementById("kpi-agencies").textContent =
            `${data.agencies_reporting ?? "--"}/${data.total_agencies ?? "--"}`;

        if (data.last_update) {
            const t = new Date(data.last_update);
            document.getElementById("kpi-last").textContent = t.toLocaleTimeString();
        }
    } catch (err) {
        console.error("Failed to fetch summary:", err);
    }
}

async function fetchAgencies() {
    try {
        const resp = await fetch(`${API_BASE}/api/agencies`);
        const data = await resp.json();
        const agencies = data.agencies || [];

        // Update agency list in sidebar
        const listEl = document.getElementById("agency-list");
        listEl.innerHTML = agencies.map(a => `
            <div class="flex items-center justify-between bg-gray-700 rounded px-2 py-1">
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full ${a.status === 'ok' ? 'bg-green-400' : a.status === 'error' ? 'bg-red-400' : a.status === 'empty' ? 'bg-yellow-400' : 'bg-gray-500'}"></span>
                    <span class="text-xs">${a.agency}</span>
                </div>
                <span class="text-xs text-gray-400">${a.vehicle_count ?? "—"}</span>
            </div>
        `).join("");

        // Update filter dropdown
        const filterEl = document.getElementById("agency-filter");
        const currentVal = filterEl.value;
        filterEl.innerHTML = '<option value="all">All Agencies</option>' +
            agencies.map(a => `<option value="${a.agency}">${a.agency}</option>`).join("");
        filterEl.value = currentVal;

        // Build count map for chart
        const counts = {};
        agencies.forEach(a => {
            if (a.vehicle_count != null) counts[a.agency] = a.vehicle_count;
        });
        updateAgencyChart(counts);

    } catch (err) {
        console.error("Failed to fetch agencies:", err);
    }
}

async function fetchCoverage() {
    try {
        const resp = await fetch(`${API_BASE}/api/analysis/coverage`);
        const data = await resp.json();
        const counts = {};
        (data.agencies || []).forEach(a => {
            counts[a.agency] = a.active_vehicles;
        });
        updateAgencyChart(counts);
    } catch (err) {
        console.error("Failed to fetch coverage:", err);
    }
}

// ── Stats refresh loop ──────────────────────────────────────────────
async function refreshStats() {
    await fetchSummary();
    await fetchAgencies();
}

// Init chart on load
initAgencyChart();

// Initial load + 30s interval
refreshStats();
setInterval(refreshStats, 30000);
