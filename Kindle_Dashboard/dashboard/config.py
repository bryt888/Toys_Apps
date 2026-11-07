"""Runtime configuration, read from environment variables and an optional .env file."""

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")


def _text(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


def _float(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    return float(value) if value else default


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _symbols(name: str, default: str) -> tuple[str, ...]:
    raw = _text(name, default)
    return tuple(part.strip().upper() for part in raw.split(",") if part.strip())


def _default_disk_mount() -> str:
    return "C:\\" if os.name == "nt" else "/"


@dataclass(frozen=True)
class Settings:
    title: str
    timezone_name: str
    host: str
    port: int
    debug: bool

    disk1_label: str
    disk1_mount: str
    disk2_label: str
    disk2_mount: str

    weather_enabled: bool
    weather_location: str
    weather_lat: float
    weather_lon: float
    weather_temp_unit: str
    weather_wind_unit: str
    weather_cache_seconds: int
    weather_retry_seconds: int

    stock_symbols: tuple[str, ...]
    stock_cache_seconds: int
    stock_retry_seconds: int

    render_cache_seconds: float
    render_concurrency: int
    font_dir: str

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @property
    def temp_suffix(self) -> str:
        return "°F" if self.weather_temp_unit == "fahrenheit" else "°C"

    @property
    def wind_suffix(self) -> str:
        return {"mph": "mph", "kmh": "km/h", "ms": "m/s", "kn": "kn"}.get(self.weather_wind_unit, self.weather_wind_unit)


def load_settings() -> Settings:
    tz_name = _text("DISPLAY_TZ", "UTC")
    try:
        ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError(f"invalid DISPLAY_TZ: {tz_name}") from exc

    return Settings(
        title=_text("DASHBOARD_TITLE", "HOMELAB"),
        timezone_name=tz_name,
        host=_text("LISTEN_ADDRESS", "0.0.0.0"),
        port=_int("PORT", 8070),
        debug=_bool("DEBUG", False),
        disk1_label=_text("DISK1_LABEL", "SYSTEM").upper(),
        disk1_mount=_text("DISK1_MOUNT", _default_disk_mount()),
        disk2_label=_text("DISK2_LABEL", "DATA").upper(),
        disk2_mount=_text("DISK2_MOUNT", ""),
        weather_enabled=_bool("WEATHER_ENABLED", False),
        weather_location=_text("WEATHER_LOCATION", "YOUR LOCATION"),
        weather_lat=_float("WEATHER_LAT", 0.0),
        weather_lon=_float("WEATHER_LON", 0.0),
        weather_temp_unit=_text("WEATHER_TEMP_UNIT", "fahrenheit"),
        weather_wind_unit=_text("WEATHER_WIND_UNIT", "mph"),
        weather_cache_seconds=_int("WEATHER_CACHE_SECONDS", 600),
        weather_retry_seconds=_int("WEATHER_RETRY_SECONDS", 60),
        stock_symbols=_symbols("STOCK_SYMBOLS", "QQQ,SPY,NVDA"),
        stock_cache_seconds=_int("STOCK_CACHE_SECONDS", 300),
        stock_retry_seconds=_int("STOCK_RETRY_SECONDS", 60),
        render_cache_seconds=max(0.0, _float("RENDER_CACHE_SECONDS", 2.0)),
        render_concurrency=max(1, _int("RENDER_CONCURRENCY", 2)),
        font_dir=_text("FONT_DIR", ""),
    )


settings = load_settings()
