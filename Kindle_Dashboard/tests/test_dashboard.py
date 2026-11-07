"""Offline tests: no network, no Glances, no Docker. Run with: python -m unittest discover -s tests"""

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.collectors import format_uptime  # noqa: E402
from dashboard.config import settings  # noqa: E402
from dashboard.render import PORTRAIT, LANDSCAPE, render_png  # noqa: E402
from PIL import Image  # noqa: E402
import io  # noqa: E402

GIB = 1024 ** 3


def fake_snapshot(weather=None, quotes=None, stock_error=None):
    return {
        "system": {
            "hostname": "test-host", "cpu": 12.0, "mem": 40.0, "mem_used": 6 * GIB, "mem_total": 16 * GIB,
            "swap": 0.0, "load": 0.5, "temperature": None, "uptime": "1d 2h 3m",
            "disks": [{"label": "SYSTEM", "mount": "/", "percent": 55.0, "used": 50 * GIB,
                       "total": 100 * GIB, "free": 50 * GIB}],
        },
        "weather": weather or {"status": "disabled"},
        "stocks": {"quotes": quotes or [], "error": stock_error},
    }


class FormatTests(unittest.TestCase):
    def test_uptime_with_days(self):
        self.assertEqual(format_uptime(3 * 86400 + 4 * 3600 + 5 * 60), "3d 4h 5m")

    def test_uptime_under_a_day(self):
        self.assertEqual(format_uptime(2 * 3600 + 30 * 60), "2h 30m")


class RenderTests(unittest.TestCase):
    now = datetime(2026, 11, 7, 14, 31, tzinfo=settings.tz)

    def _decode(self, png: bytes) -> Image.Image:
        return Image.open(io.BytesIO(png))

    def test_portrait_and_landscape_sizes(self):
        snapshot = fake_snapshot()
        self.assertEqual(self._decode(render_png(snapshot, "portrait", self.now)).size, PORTRAIT)
        self.assertEqual(self._decode(render_png(snapshot, "landscape", self.now)).size, LANDSCAPE)

    def test_kindle_landscape_is_rotated_to_portrait_framebuffer(self):
        image = self._decode(render_png(fake_snapshot(), "landscape-kindle", self.now))
        self.assertEqual(image.size, (LANDSCAPE[1], LANDSCAPE[0]))
        self.assertEqual(image.mode, "L")

    def test_stock_rows_render_with_up_and_down_and_missing_quote(self):
        quotes = [
            {"symbol": "QQQ", "price": 500.0, "change": 2.0, "change_pct": 0.4, "error": None},
            {"symbol": "SPY", "price": 600.0, "change": -3.0, "change_pct": -0.5, "error": None},
            {"symbol": "BAD", "price": None, "change": None, "change_pct": None, "error": "boom"},
        ]
        png = render_png(fake_snapshot(quotes=quotes), "portrait", self.now)
        self.assertEqual(self._decode(png).size, PORTRAIT)

    def test_weather_error_and_stale_states_render(self):
        for weather in ({"status": "error", "error": "timeout"},
                        {"status": "stale", "temperature": 40, "condition": "Rain", "high": 45, "low": 30,
                         "apparent_temperature": 38, "precip_probability": 80, "wind_speed": 12}):
            png = render_png(fake_snapshot(weather=weather), "landscape", self.now)
            self.assertEqual(self._decode(png).size, LANDSCAPE)

    def test_unknown_orientation_raises(self):
        with self.assertRaises(ValueError):
            render_png(fake_snapshot(), "sideways", self.now)


if __name__ == "__main__":
    unittest.main()
