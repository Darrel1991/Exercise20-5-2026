# Malaysia Public Transport & Weather Dashboard — API Documentation

**Base URL:** `http://localhost:8000`
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## Transport APIs

### GET /api/vehicles

Get the latest position of all active vehicles (within the last 60 seconds).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agency` | string | `all` | Filter by agency key (e.g. `ktmb`, `mybas-johor`) or `all` |

**Response:**

```json
{
  "count": 204,
  "vehicles": [
    {
      "vehicle_id": "VX3035",
      "agency": "prasarana-rapid-bus-mrtfeeder",
      "trip_id": "260313021038S1",
      "route_id": "T451",
      "latitude": 2.9290,
      "longitude": 101.7888,
      "bearing": 172.0,
      "speed": 26.0,
      "occupancy_status": null,
      "current_status": null,
      "stop_id": null,
      "timestamp": "2026-03-14T07:12:59"
    }
  ]
}
```

---

### GET /api/vehicles/{vehicle_id}/history

Get the position trail for a specific vehicle over a time range.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `vehicle_id` | string | The vehicle identifier |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from` | ISO8601 datetime | none | Start of time range |
| `to` | ISO8601 datetime | none | End of time range |

**Response:**

```json
{
  "vehicle_id": "VX3035",
  "count": 48,
  "trail": [
    {
      "vehicle_id": "VX3035",
      "agency": "prasarana-rapid-bus-mrtfeeder",
      "trip_id": "260313021038S1",
      "route_id": "T451",
      "latitude": 2.9290,
      "longitude": 101.7888,
      "bearing": 172.0,
      "speed": 26.0,
      "occupancy_status": null,
      "current_status": null,
      "stop_id": null,
      "timestamp": "2026-03-14T07:12:59"
    }
  ]
}
```

---

### GET /api/agencies

List all enabled agencies with their latest ingestion status.

**Response:**

```json
{
  "agencies": [
    {
      "agency": "ktmb",
      "vehicle_count": 5,
      "last_fetched": "2026-03-14T15:35:41.897000",
      "status": "ok",
      "error_message": null
    },
    {
      "agency": "prasarana-rapid-bus-kl",
      "vehicle_count": 0,
      "last_fetched": "2026-03-14T15:35:42.123000",
      "status": "empty",
      "error_message": null
    }
  ]
}
```

**Status values:** `ok` | `empty` | `error` | `unknown`

---

## History APIs

### GET /api/history/snapshot

Get all vehicle positions at a specific point in time (±30 second window).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timestamp` | ISO8601 datetime | **required** | The target timestamp |
| `agency` | string | `all` | Filter by agency key |

**Response:**

```json
{
  "timestamp": "2026-03-14T07:00:00",
  "count": 180,
  "vehicles": [
    {
      "vehicle_id": "VX3035",
      "agency": "prasarana-rapid-bus-mrtfeeder",
      "trip_id": "260313021038S1",
      "route_id": "T451",
      "latitude": 2.9290,
      "longitude": 101.7888,
      "bearing": 172.0,
      "speed": 26.0,
      "timestamp": "2026-03-14T07:00:15"
    }
  ]
}
```

---

### GET /api/history/heatmap

Get lat/lng density points for heatmap rendering within a time range.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from` | ISO8601 datetime | **required** | Start of range |
| `to` | ISO8601 datetime | **required** | End of range |
| `agency` | string | `all` | Filter by agency key |

**Response:**

```json
{
  "count": 5200,
  "points": [
    { "lat": 3.139, "lng": 101.686 },
    { "lat": 1.480, "lng": 103.760 }
  ]
}
```

---

## Analysis APIs

### GET /api/analysis/stalled

Find vehicles whose position hasn't changed for N minutes (potential breakdowns or traffic jams).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agency` | string | `all` | Filter by agency key |
| `threshold_minutes` | integer | `5` | Minimum minutes without movement (min: 1) |

**Response:**

```json
{
  "count": 3,
  "threshold_minutes": 5,
  "vehicles": [
    {
      "vehicle_id": "VX2890",
      "agency": "prasarana-rapid-bus-mrtfeeder",
      "latitude": 3.0769,
      "longitude": 101.6704,
      "last_seen": "2026-03-14T07:13:01",
      "first_seen": "2026-03-14T07:05:01"
    }
  ]
}
```

---

### GET /api/analysis/coverage

Get active vehicle count per agency for gap detection.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agency` | string | `all` | Filter by agency key |

**Response:**

```json
{
  "agencies": [
    { "agency": "prasarana-rapid-bus-mrtfeeder", "active_vehicles": 116 },
    { "agency": "mybas-johor", "active_vehicles": 88 },
    { "agency": "ktmb", "active_vehicles": 5 }
  ]
}
```

---

### GET /api/analysis/summary

Dashboard KPI summary — total active vehicles, stalled count, agency status.

**Response:**

```json
{
  "total_active_vehicles": 209,
  "stalled_vehicles": 3,
  "agencies_reporting": 3,
  "total_agencies": 4,
  "last_update": "2026-03-14T15:35:41.897000",
  "generated_at": "2026-03-14T07:36:00.123456"
}
```

---

## Weather APIs

### GET /api/weather/forecast

Get 7-day weather forecasts from MET Malaysia, optionally filtered.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | date (YYYY-MM-DD) | today onwards | Filter to a specific date |
| `location` | string | none | Filter by `location_id` (e.g. `Ds067`) or location name (e.g. `Kuala Lumpur`) |

**Response:**

```json
{
  "count": 360,
  "forecasts": [
    {
      "location_id": "Ds067",
      "location_name": "Kuala Lumpur",
      "date": "2026-03-14",
      "morning_forecast": "Tiada hujan",
      "afternoon_forecast": "Ribut petir di beberapa tempat",
      "night_forecast": "Tiada hujan",
      "summary_forecast": "Ribut petir di beberapa tempat",
      "summary_when": "Petang",
      "min_temp": 25,
      "max_temp": 34,
      "latitude": 3.139,
      "longitude": 101.6869
    }
  ]
}
```

**Forecast values (Malay):**

| Value | English |
|-------|---------|
| Tiada hujan | No rain |
| Hujan di satu dua tempat | Light rain in one or two areas |
| Hujan di beberapa tempat | Rain in several areas |
| Hujan di kebanyakan tempat | Rain in most areas |
| Hujan di seluruh tempat | Rain everywhere |
| Ribut petir di satu dua tempat | Thunderstorm in one or two areas |
| Ribut petir di beberapa tempat | Thunderstorms in several areas |
| Ribut petir di kebanyakan tempat | Thunderstorms in most areas |

---

### GET /api/weather/forecast/map

Get today's forecasts with coordinates for map rendering. Only returns locations that have lat/lng mapped.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | date (YYYY-MM-DD) | today | Target date |

**Response:**

```json
{
  "date": "2026-03-14",
  "count": 128,
  "points": [
    {
      "location_id": "Ds001",
      "location_name": "Langkawi",
      "lat": 6.35,
      "lng": 99.80,
      "summary": "Tiada hujan",
      "min_temp": 26,
      "max_temp": 35,
      "morning": "Tiada hujan",
      "afternoon": "Tiada hujan",
      "night": "Tiada hujan"
    }
  ]
}
```

---

### GET /api/weather/warnings

Get active weather warnings from MET Malaysia (strong winds, thunderstorms, sea level rise, etc.).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `active_only` | boolean | `true` | Only return warnings where `valid_to` is in the future |

**Response:**

```json
{
  "count": 9,
  "warnings": [
    {
      "id": 1,
      "title_en": "Thunderstorms Warning",
      "title_bm": "Amaran Ribut Petir",
      "heading_en": "Thunderstorms Warning",
      "text_en": "Thunderstorms, heavy rain and strong winds are expected over the states of Pahang (Jerantut, Temerloh)...",
      "text_bm": "Ribut petir, hujan lebat dan angin kencang dijangka di negeri Pahang...",
      "instruction_en": null,
      "issued": "2026-03-14T14:50:00",
      "valid_from": "2026-03-14T14:50:00",
      "valid_to": "2026-03-14T19:00:00"
    }
  ]
}
```

---

### GET /api/weather/earthquakes

Get recent earthquake records.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `20` | Number of recent earthquakes to return (1–100) |

**Response:**

```json
{
  "count": 3,
  "earthquakes": [
    {
      "id": 1,
      "location": "Near Coast of Central Chile",
      "latitude": -34.12,
      "longitude": -71.89,
      "magnitude": 5.2,
      "depth": 35.0,
      "timestamp": "2026-03-14T06:23:00"
    }
  ]
}
```

---

## Data Sources

| API Group | Source | Update Frequency |
|-----------|--------|-----------------|
| Vehicles | [GTFS Realtime](https://api.data.gov.my/gtfs-realtime/vehicle-position/) | Every 30 seconds |
| Agencies | Ingestion log (internal) | Every 30 seconds |
| Weather Forecast | [MET Malaysia](https://api.data.gov.my/weather/forecast) | Every 30 minutes |
| Weather Warnings | [MET Malaysia](https://api.data.gov.my/weather/warning) | Every 30 minutes |
| Earthquakes | [MET Malaysia](https://api.data.gov.my/weather/warning/earthquake) | Every 30 minutes |

## Supported Transport Agencies

| Key | Description |
|-----|-------------|
| `ktmb` | KTM Railway (national) |
| `prasarana-rapid-bus-kl` | RapidKL buses (Klang Valley) |
| `prasarana-rapid-bus-mrtfeeder` | MRT feeder buses |
| `prasarana-rapid-bus-kuantan` | Rapid Kuantan buses |
| `prasarana-rapid-bus-penang` | Rapid Penang buses |
| `mybas-kangar` | BAS.MY Kangar |
| `mybas-alor-setar` | BAS.MY Alor Setar |
| `mybas-kota-bharu` | BAS.MY Kota Bharu |
| `mybas-kuala-terengganu` | BAS.MY Kuala Terengganu |
| `mybas-ipoh` | BAS.MY Ipoh |
| `mybas-seremban-a` | BAS.MY Seremban (Operator A) |
| `mybas-seremban-b` | BAS.MY Seremban (Operator B) |
| `mybas-melaka` | BAS.MY Melaka |
| `mybas-johor` | BAS.MY Johor Bahru |
| `mybas-kuching` | BAS.MY Kuching |

## Location ID Prefixes (Weather)

| Prefix | Level | Example |
|--------|-------|---------|
| `St` | State | `St008` = W.P. Kuala Lumpur |
| `Ds` | District | `Ds067` = Kuala Lumpur |
| `Tn` | Town | `Tn008` = Kuala Lumpur |
| `Rc` | Recreation Centre | — |
| `Dv` | Division | — |

## Error Responses

All endpoints return standard HTTP error codes:

```json
{
  "detail": "Error description message"
}
```

| Code | Meaning |
|------|---------|
| `200` | Success |
| `404` | Endpoint not found |
| `422` | Validation error (missing/invalid parameters) |
| `500` | Internal server error |
