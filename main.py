import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from db.connection import engine
from db.models import Base
from ingestion.scheduler import start_scheduler, stop_scheduler

from config import DB_SERVER, DB_NAME, DB_DRIVER, DB_USER, DB_PASSWORD

from api.vehicles import router as vehicles_router
from api.agencies import router as agencies_router
from api.history import router as history_router
from api.analysis import router as analysis_router
from api.weather import router as weather_router
from flood_analysis.router import router as flood_router
from thunder_analysis.router import router as thunder_router

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _ensure_database():
    """Create the database if it doesn't exist (connects to 'master' first)."""
    import pyodbc
    if DB_USER and DB_PASSWORD:
        conn_str = (
            f"DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};"
            f"DATABASE=master;UID={DB_USER};PWD={DB_PASSWORD}"
        )
    else:
        conn_str = (
            f"DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};"
            f"DATABASE=master;Trusted_Connection=yes"
        )
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(
            f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = ?)"
            f" CREATE DATABASE [{DB_NAME}]",
            DB_NAME,
        )
        conn.close()
        logger.info("Database '%s' ready.", DB_NAME)
    except Exception as exc:
        logger.error("Could not ensure database exists: %s", exc)
        raise


# ── App Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database exists, then create tables
    logger.info("Ensuring database exists...")
    _ensure_database()
    logger.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    logger.info("Starting ingestion scheduler...")
    start_scheduler()

    yield

    # Shutdown
    logger.info("Stopping scheduler...")
    stop_scheduler()


# ── FastAPI App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Malaysia Transport Dashboard API",
    description="GTFS Realtime vehicle tracking and disaster analysis",
    version="1.0.0",
    lifespan=lifespan,
    debug=True,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# API routes
app.include_router(vehicles_router)
app.include_router(agencies_router)
app.include_router(history_router)
app.include_router(analysis_router)
app.include_router(weather_router)
app.include_router(flood_router)
app.include_router(thunder_router)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serve the main dashboard page."""
    return FileResponse("frontend/index.html")


@app.get("/flood", include_in_schema=False)
def serve_flood_dashboard():
    """Serve the flood analysis dashboard."""
    return FileResponse("frontend/flood.html")


@app.get("/thunder", include_in_schema=False)
def serve_thunder_dashboard():
    """Serve the thunderstorm analysis dashboard."""
    return FileResponse("frontend/thunder.html")
