from sqlalchemy import (
    Column, BigInteger, Integer, Float, String, DateTime, Date, Index,
    PrimaryKeyConstraint, Text
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class VehiclePosition(Base):
    __tablename__ = "vehicle_positions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agency = Column(String(50), nullable=False)
    vehicle_id = Column(String(100), nullable=False)
    trip_id = Column(String(200), nullable=True)
    route_id = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bearing = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    occupancy_status = Column(String(50), nullable=True)
    current_status = Column(String(50), nullable=True)
    stop_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_vp_agency_ts", "agency", timestamp.desc()),
        Index("idx_vp_vehicle", "vehicle_id", timestamp.desc()),
    )


class GtfsRoute(Base):
    __tablename__ = "gtfs_routes"

    agency = Column(String(50), nullable=False)
    route_id = Column(String(100), nullable=False)
    route_short_name = Column(String(50), nullable=True)
    route_long_name = Column(String(255), nullable=True)
    route_type = Column(Integer, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("agency", "route_id"),
    )


class GtfsStop(Base):
    __tablename__ = "gtfs_stops"

    agency = Column(String(50), nullable=False)
    stop_id = Column(String(100), nullable=False)
    stop_name = Column(String(255), nullable=True)
    stop_lat = Column(Float, nullable=True)
    stop_lon = Column(Float, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("agency", "stop_id"),
    )


# ── Weather Tables ───────────────────────────────────────────────────

class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    location_id = Column(String(20), nullable=False)
    location_name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    morning_forecast = Column(String(255), nullable=True)
    afternoon_forecast = Column(String(255), nullable=True)
    night_forecast = Column(String(255), nullable=True)
    summary_forecast = Column(String(255), nullable=True)
    summary_when = Column(String(50), nullable=True)
    min_temp = Column(Integer, nullable=True)
    max_temp = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_wf_loc_date", "location_id", "date"),
    )


class WeatherWarning(Base):
    __tablename__ = "weather_warnings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title_en = Column(String(500), nullable=True)
    title_bm = Column(String(500), nullable=True)
    heading_en = Column(String(500), nullable=True)
    heading_bm = Column(String(500), nullable=True)
    text_en = Column(Text, nullable=True)
    text_bm = Column(Text, nullable=True)
    instruction_en = Column(Text, nullable=True)
    instruction_bm = Column(Text, nullable=True)
    issued = Column(DateTime, nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    # Bounding box extracted from warning text (e.g. cyclone monitoring region)
    boundary_lat_min = Column(Float, nullable=True)
    boundary_lat_max = Column(Float, nullable=True)
    boundary_lng_min = Column(Float, nullable=True)
    boundary_lng_max = Column(Float, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())


class Earthquake(Base):
    __tablename__ = "earthquakes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    location = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    magnitude = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_eq_ts", "timestamp"),
    )


class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agency = Column(String(50), nullable=False)
    fetched_at = Column(DateTime, server_default=func.now())
    vehicle_count = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False)  # 'ok' | 'error' | 'empty'
    error_message = Column(String, nullable=True)
