"""Data sources: local system metrics (psutil), weather (Open-Meteo), stock quotes (yfinance).

Each remote source is wrapped in a small TTL cache so the e-ink display can request
images frequently without hammering upstream APIs. A failed refresh keeps the last
good value (marked stale) and is retried after a short back-off.
"""

import logging
import os
import platform
import socket
import threading
import time
from typing import Any, Callable, Optional

import psutil
import requests

from .config import settings

log = logging.getLogger("dashboard")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# The first psutil.cpu_percent() call returns a meaningless 0.0; prime it at import time.
psutil.cpu_percent(interval=None)


class CachedFetch:
    """Calls `fetch` at most once per `ttl` seconds; keeps the last good value on failure."""

    def __init__(self, fetch: Callable[[], Any], ttl: float, retry: float) -> None:
        self._fetch = fetch
        self._ttl = ttl
        self._retry = retry
        self._lock = threading.Lock()
        self._value: Any = None
        self._fetched_at: Optional[float] = None
        self._last_attempt: Optional[float] = None
        self._error: Optional[str] = None

    def get(self) -> tuple[Any, Optional[str]]:
        """Return (value, error). `value` may be stale when `error` is set."""
        with self._lock:
            now = time.monotonic()
            if self._fetched_at is not None and now - self._fetched_at < self._ttl:
                return self._value, None
            if self._last_attempt is not None and now - self._last_attempt < self._retry:
                return self._value, self._error
            self._last_attempt = now
            try:
                self._value = self._fetch()
                self._fetched_at = now
                self._error = None
            except Exception as exc:
                self._error = str(exc) or exc.__class__.__name__
                log.warning("fetch failed: %s", self._error)
            return self._value, self._error


# ---------------------------------------------------------------- system

def format_uptime(seconds: float) -> str:
    total = int(seconds)
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def _cpu_temperature() -> Optional[float]:
    """Best-effort CPU temperature. Only Linux exposes this through psutil."""
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        sensors = psutil.sensors_temperatures() or {}
    except Exception:
        return None
    readings: list[float] = []
    for chip, entries in sensors.items():
        if any(key in chip.lower() for key in ("coretemp", "k10temp", "zenpower", "cpu", "acpitz")):
            readings.extend(entry.current for entry in entries if entry.current is not None)
    return max(readings) if readings else None


def _disk(label: str, mount: str) -> dict:
    if not mount:
        return {"label": label, "mount": None}
    try:
        usage = psutil.disk_usage(mount)
    except Exception:
        return {"label": label, "mount": mount}
    return {
        "label": label,
        "mount": mount,
        "percent": usage.percent,
        "used": usage.used,
        "total": usage.total,
        "free": usage.free,
    }


def collect_system() -> dict:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
    disks = [
        _disk(settings.disk1_label, settings.disk1_mount),
        _disk(settings.disk2_label, settings.disk2_mount),
    ]
    return {
        "hostname": socket.gethostname() or platform.node() or "unknown host",
        "cpu": psutil.cpu_percent(interval=None),
        "mem": memory.percent,
        "mem_used": memory.used,
        "mem_total": memory.total,
        "swap": swap.percent,
        "load": load,
        "temperature": _cpu_temperature(),
        "uptime": format_uptime(time.time() - psutil.boot_time()),
        "disks": [disk for disk in disks if disk.get("mount")],
    }


# ---------------------------------------------------------------- weather

WEATHER_CONDITIONS = {
    0: "Clear",
    1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle", 56: "Drizzle", 57: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}


def _first(values: Any) -> Any:
    return values[0] if isinstance(values, list) and values else None


def _fetch_weather() -> dict:
    response = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": settings.weather_lat,
            "longitude": settings.weather_lon,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "temperature_unit": settings.weather_temp_unit,
            "wind_speed_unit": settings.weather_wind_unit,
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=5,
    )
    response.raise_for_status()
    payload = response.json()
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    code = current.get("weather_code")
    code = int(code) if code is not None else -1
    return {
        "temperature": current.get("temperature_2m"),
        "apparent_temperature": current.get("apparent_temperature"),
        "wind_speed": current.get("wind_speed_10m"),
        "is_day": current.get("is_day") != 0,
        "condition": WEATHER_CONDITIONS.get(code, "Unknown"),
        "high": _first(daily.get("temperature_2m_max")),
        "low": _first(daily.get("temperature_2m_min")),
        "precip_probability": _first(daily.get("precipitation_probability_max")),
        "fetched_at": time.time(),
    }


_weather_cache = CachedFetch(
    _fetch_weather,
    ttl=settings.weather_cache_seconds,
    retry=settings.weather_retry_seconds,
)


def collect_weather() -> dict:
    """Always returns a dict with `status` in {disabled, ok, stale, error}."""
    if not settings.weather_enabled:
        return {"status": "disabled"}
    data, error = _weather_cache.get()
    if data is None:
        return {"status": "error", "error": error or "weather unavailable"}
    return {**data, "status": "stale" if error else "ok"}


# ---------------------------------------------------------------- stocks

def _fetch_quote(symbol: str) -> dict:
    import yfinance as yf  # imported lazily so the server starts even if yfinance is broken

    info = yf.Ticker(symbol).fast_info
    price = float(info.last_price)
    previous = float(info.previous_close)
    change = price - previous
    return {
        "symbol": symbol,
        "price": price,
        "change": change,
        "change_pct": (change / previous * 100.0) if previous else None,
        "error": None,
    }


def _fetch_quotes() -> list[dict]:
    quotes = []
    for symbol in settings.stock_symbols:
        try:
            quotes.append(_fetch_quote(symbol))
        except Exception as exc:
            log.warning("quote failed for %s: %s", symbol, exc)
            quotes.append({"symbol": symbol, "price": None, "change": None, "change_pct": None,
                           "error": str(exc) or exc.__class__.__name__})
    if quotes and all(quote["price"] is None for quote in quotes):
        raise RuntimeError("no quotes available")
    return quotes


_stock_cache = CachedFetch(
    _fetch_quotes,
    ttl=settings.stock_cache_seconds,
    retry=settings.stock_retry_seconds,
)


def collect_stocks() -> dict:
    if not settings.stock_symbols:
        return {"quotes": [], "error": None}
    quotes, error = _stock_cache.get()
    return {"quotes": quotes or [], "error": error}


# ---------------------------------------------------------------- snapshot

def collect_snapshot() -> dict:
    """Gather every data source concurrently so slow APIs overlap rather than add up."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="collect") as pool:
        system_future = pool.submit(collect_system)
        weather_future = pool.submit(collect_weather)
        stocks_future = pool.submit(collect_stocks)
        return {
            "system": system_future.result(),
            "weather": weather_future.result(),
            "stocks": stocks_future.result(),
        }
