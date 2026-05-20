# DataRoute — Installation Guide

Setup guide for running the Malaysia Public Transport Dashboard on a new Windows PC.

---

## Prerequisites

Install the following software before proceeding:

### 1. Python 3.10+

- Download from https://www.python.org/downloads/
- **Important:** During installation, check **"Add Python to PATH"**
- Verify after install:
  ```
  python --version
  ```

### 2. SQL Server (Express Edition is fine)

- Download SQL Server Express from https://www.microsoft.com/en-us/sql-server/sql-server-downloads
- During setup, note down your **server instance name** (e.g. `YOURPC\SQLEXPRESS`)
- Choose either:
  - **Windows Authentication** (default, no username/password needed)
  - **SQL Server Authentication** (requires setting a username and password)

### 3. ODBC Driver 17 for SQL Server

- Download from https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- Select **"ODBC Driver 17 for SQL Server"** (not version 18)
- Run the installer with default settings

### 4. Git (optional, for cloning)

- Download from https://git-scm.com/download/win
- Only needed if cloning from a repository; skip if you received the code as a ZIP

---

## Installation Steps

### Step 1 — Get the Code

Place the project folder on your PC (e.g. `C:\Users\YourName\Desktop\dataroute`).

### Step 2 — Open a Terminal

Open **Command Prompt** or **PowerShell** and navigate to the project folder:

```
cd C:\Users\YourName\Desktop\dataroute
```

### Step 3 — Create a Virtual Environment

```
python -m venv .venv
```

Activate it:

```
.venv\Scripts\activate
```

You should see `(.venv)` at the start of your terminal prompt.

### Step 4 — Install Dependencies

```
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, protobuf libraries, and other required packages.

### Step 5 — Configure Environment Variables

Copy the example environment file:

```
copy .env.example .env
```

Open `.env` in a text editor (Notepad is fine) and update the values:

```
DB_SERVER=YOURPC\SQLEXPRESS
DB_NAME=gtfs_dashboard
DB_USER=
DB_PASSWORD=
DB_DRIVER=ODBC Driver 17 for SQL Server

POLL_INTERVAL_SECONDS=30
STATIC_REFRESH_HOUR=4
ENABLE_AGENCIES=ktmb,prasarana-rapid-bus-kl,prasarana-rapid-bus-mrtfeeder,mybas-johor
```

**Configuration notes:**

| Variable | What to set |
|---|---|
| `DB_SERVER` | Your SQL Server instance name. Find it by opening **SQL Server Management Studio (SSMS)** — it shows the server name on the connect dialog. |
| `DB_USER` / `DB_PASSWORD` | Leave **blank** to use Windows Authentication (recommended). Fill in only if using SQL Server Authentication. |
| `DB_DRIVER` | Keep as `ODBC Driver 17 for SQL Server` unless you installed a different version. |
| `ENABLE_AGENCIES` | Comma-separated list of transit agencies to track. See the full list in `config.py`. |

### Step 6 — Run the Application

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first startup, the application will automatically:
1. Create the `gtfs_dashboard` database if it doesn't exist
2. Create all required tables
3. Start polling GTFS Realtime feeds every 30 seconds

### Step 7 — Open the Dashboard

Open a web browser and go to:

```
http://localhost:8000
```

- **Main dashboard** (vehicle map): http://localhost:8000
- **Flood analysis**: http://localhost:8000/flood
- **API docs** (Swagger): http://localhost:8000/docs

---

## Verifying the Installation

| Check | Expected Result |
|---|---|
| Terminal output shows `"Database 'gtfs_dashboard' ready."` | Database connection is working |
| Terminal output shows `"Starting ingestion scheduler..."` | Data polling has started |
| `http://localhost:8000` loads a map | Frontend is working |
| Vehicle markers appear on the map within 1–2 minutes | Data ingestion is working |

---

## Troubleshooting

### "ODBC Driver 17 for SQL Server is not installed"
Install the ODBC driver from the link in the Prerequisites section above.

### "Login failed for user"
- If using Windows Auth, make sure `DB_USER` and `DB_PASSWORD` are **blank** in `.env`
- If using SQL Auth, verify the credentials are correct in SSMS first

### "Cannot connect to SQL Server"
- Open **SQL Server Configuration Manager**
- Ensure **SQL Server Browser** service is running
- Ensure **TCP/IP** is enabled under SQL Server Network Configuration > Protocols
- Confirm the server instance name in `.env` matches your actual instance

### "pip install fails" or "module not found"
- Make sure the virtual environment is activated (you see `(.venv)` in the prompt)
- Try: `.venv\Scripts\activate` then re-run `pip install -r requirements.txt`

### No vehicles appearing on the map
- Wait 1–2 minutes — the first poll cycle needs to complete
- Check the terminal for error messages related to specific agencies
- Some agencies (e.g. `rapid-bus-kuantan`) may return errors intermittently — this is normal

---

## Stopping the Application

Press `Ctrl + C` in the terminal to stop the server.

---

## Project Structure (Quick Reference)

```
dataroute/
├── main.py                  → App entry point
├── config.py                → Settings and environment variables
├── requirements.txt         → Python dependencies
├── .env                     → Your local configuration (do not share)
├── db/                      → Database models and connection
├── ingestion/               → GTFS data fetching and scheduling
├── api/                     → REST API endpoints
├── analysis/                → Anomaly detection logic
├── flood_analysis/          → Flood zone analysis
└── frontend/                → Dashboard HTML, JS, CSS
    ├── index.html           → Main vehicle tracking dashboard
    ├── flood.html           → Flood analysis dashboard
    ├── map.js               → Leaflet map logic
    ├── charts.js            → Chart.js statistics
    ├── weather.js           → Weather overlay
    └── flood.js             → Flood analysis frontend
```
