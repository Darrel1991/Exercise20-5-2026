import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import POLL_INTERVAL_SECONDS, STATIC_REFRESH_HOUR, ENABLE_AGENCIES, WEATHER_POLL_MINUTES
from db.connection import SessionLocal
from db.models import WeatherForecast, WeatherWarning, Earthquake
from db.repository import bulk_insert_positions, log_ingestion, purge_old_positions
from ingestion.fetcher import fetch_agency
from ingestion.static_loader import load_all_static
from ingestion.weather_fetcher import fetch_forecasts, fetch_warnings, fetch_earthquakes

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _poll_all_agencies():
    """Fetch realtime positions for every enabled agency and insert into DB."""
    for agency_key in ENABLE_AGENCIES:
        db = SessionLocal()
        try:
            positions = fetch_agency(agency_key)
            if positions:
                count = bulk_insert_positions(db, positions)
                log_ingestion(db, agency_key, count, "ok")
            else:
                log_ingestion(db, agency_key, 0, "empty")
        except Exception as exc:
            logger.exception("Ingestion failed for %s", agency_key)
            try:
                log_ingestion(db, agency_key, None, "error", str(exc)[:4000])
            except Exception:
                logger.exception("Failed to log ingestion error for %s", agency_key)
        finally:
            db.close()


def _poll_weather():
    """Fetch weather forecasts, warnings, and earthquakes."""
    db = SessionLocal()
    try:
        # Forecasts — replace all with latest
        forecasts = fetch_forecasts()
        if forecasts:
            db.query(WeatherForecast).delete()
            db.bulk_insert_mappings(WeatherForecast, forecasts)
            db.commit()

        # Warnings — replace all with latest
        warnings = fetch_warnings()
        db.query(WeatherWarning).delete()
        if warnings:
            db.bulk_insert_mappings(WeatherWarning, warnings)
        db.commit()

        # Earthquakes — insert new only (check by timestamp)
        quakes = fetch_earthquakes()
        for q in quakes:
            exists = db.query(Earthquake).filter(
                Earthquake.latitude == q.get("latitude"),
                Earthquake.longitude == q.get("longitude"),
                Earthquake.timestamp == q.get("timestamp"),
            ).first()
            if not exists:
                db.add(Earthquake(**q))
        db.commit()

    except Exception:
        logger.exception("Weather ingestion failed")
        db.rollback()
    finally:
        db.close()


def _daily_static_refresh():
    """Reload GTFS static feeds for route/stop enrichment."""
    logger.info("Starting daily GTFS static refresh")
    load_all_static()


def _daily_purge():
    """Purge vehicle positions older than 30 days."""
    db = SessionLocal()
    try:
        deleted = purge_old_positions(db, days=30)
        logger.info("Purged %d old vehicle positions", deleted)
    except Exception:
        logger.exception("Failed to purge old positions")
    finally:
        db.close()


def start_scheduler():
    """Configure and start the background scheduler."""
    # Poll realtime feeds every N seconds
    scheduler.add_job(
        _poll_all_agencies,
        "interval",
        seconds=POLL_INTERVAL_SECONDS,
        id="poll_realtime",
        max_instances=1,
        coalesce=True,
    )

    # Refresh static feeds daily at configured hour
    scheduler.add_job(
        _daily_static_refresh,
        "cron",
        hour=STATIC_REFRESH_HOUR,
        minute=0,
        id="static_refresh",
        max_instances=1,
    )

    # Poll weather data every N minutes
    scheduler.add_job(
        _poll_weather,
        "interval",
        minutes=WEATHER_POLL_MINUTES,
        id="poll_weather",
        max_instances=1,
        coalesce=True,
    )

    # Purge old data daily at 3 AM
    scheduler.add_job(
        _daily_purge,
        "cron",
        hour=3,
        minute=0,
        id="daily_purge",
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        "Scheduler started — polling %d agencies every %ds",
        len(ENABLE_AGENCIES), POLL_INTERVAL_SECONDS,
    )


def stop_scheduler():
    scheduler.shutdown(wait=False)
