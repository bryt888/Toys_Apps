"""Draw the dashboard as 8-bit grayscale PNG frames for e-ink displays.

Layouts (sized for the older 600 x 800 Kindle):
  portrait          600 x 800  (native Kindle framebuffer)
  landscape         800 x 600  (browser preview)
  landscape-kindle  600 x 800  (landscape rotated into the portrait framebuffer)
"""

import io
import logging
import os
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont

from .config import settings

log = logging.getLogger("dashboard")

PORTRAIT = (600, 800)
LANDSCAPE = (800, 600)

BLACK, DARK, MID, LIGHT, WHITE = 0, 92, 145, 216, 255
MARGIN = 18
DEGREE = "\N{DEGREE SIGN}"

# Font lookup covers Linux (DejaVu), macOS and Windows (Arial/Consolas) so the same code runs anywhere.
_FONT_FILES = {
    False: ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"),
    True: ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf"),
}
_FONT_DIRS = (
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
    "C:\\Windows\\Fonts",
)


def _font_dirs() -> list[str]:
    dirs = [settings.font_dir] if settings.font_dir else []
    return dirs + list(_FONT_DIRS)


@lru_cache(maxsize=None)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for directory in _font_dirs():
        for name in _FONT_FILES[bold]:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                return ImageFont.truetype(path, size)
    log.warning("no TrueType font found; falling back to Pillow default")
    return ImageFont.load_default(size=size)


def text_width(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(value, font=face)


def fit_text(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.FreeTypeFont, width: float) -> str:
    if text_width(draw, value, face) <= width:
        return value
    shortened = value
    while shortened and text_width(draw, shortened + "…", face) > width:
        shortened = shortened[:-1]
    return shortened + "…" if shortened else "…"


def draw_rule(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int) -> None:
    draw.line([(x0, y), (x1, y)], fill=LIGHT, width=1)


def draw_bar(draw: ImageDraw.ImageDraw, x: int, y: int, width: int, height: int, percent: float) -> None:
    draw.rectangle([x, y, x + width, y + height], outline=MID, width=1)
    inner = width - 2
    filled = max(0, min(inner, round(inner * float(percent) / 100.0)))
    if filled:
        draw.rectangle([x + 1, y + 1, x + filled, y + height - 1], fill=BLACK)


def draw_triangle(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, up: bool, tone: int) -> None:
    if up:
        points = [(x, y + size), (x + size, y + size), (x + size / 2, y)]
    else:
        points = [(x, y), (x + size, y), (x + size / 2, y + size)]
    draw.polygon(points, fill=tone)


# ---------------------------------------------------------------- formatting

def fmt_percent(value: Any) -> str:
    return "--" if value is None else f"{float(value):.0f}%"


def fmt_load(value: Any) -> str:
    return "--" if value is None else f"{float(value):.2f}"


def fmt_temp(value: Any) -> str:
    return "--" if value is None else f"{float(value):.0f}{DEGREE}C"


def fmt_num(value: Any, suffix: str = "") -> str:
    return "--" if value is None else f"{float(value):.0f}{suffix}"


def fmt_memory(used: Any, total: Any) -> str:
    if used is None or total is None:
        return "-- / -- GiB"
    gib = 1024 ** 3
    return f"{float(used) / gib:.1f} / {float(total) / gib:.1f} GiB"


def fmt_disk_free(disk: dict) -> str:
    gib = 1024 ** 3
    free = disk.get("free") or 0
    total = disk.get("total") or 0
    return f"{free / gib:.0f} GiB free of {total / gib:.0f} GiB"


def fmt_price(value: float) -> str:
    return f"${value:,.2f}"


# ---------------------------------------------------------------- sections

def _header(draw: ImageDraw.ImageDraw, now: datetime, width: int, y: int, hostname: str,
            uptime: str, portrait: bool) -> None:
    f_title = font(28, bold=True)
    f_small = font(13)
    time_text = now.strftime("%H:%M")
    date_text = now.strftime("%a, %b %d").upper().replace(" 0", " ")
    draw.text((MARGIN, y), settings.title, font=f_title, fill=BLACK)
    draw.text((width - MARGIN, y), time_text, font=f_title, fill=BLACK, anchor="ra")
    draw.text((width - MARGIN - text_width(draw, time_text, f_title) - 14, y), date_text,
              font=f_title, fill=BLACK, anchor="ra")
    # Second line: hostname on the left, uptime on the right (same spot in both orientations).
    draw.text((MARGIN, y + 40), fit_text(draw, hostname, f_small, width - 2 * MARGIN - 170),
              font=f_small, fill=BLACK)
    draw.text((width - MARGIN, y + 41), f"Uptime {uptime}", font=f_small, fill=BLACK, anchor="ra")


def _metrics(draw: ImageDraw.ImageDraw, system: dict, x0: int, x1: int, y: int) -> None:
    labels = [
        ("CPU", fmt_percent(system.get("cpu"))),
        ("MEM", fmt_percent(system.get("mem"))),
        ("TEMP", fmt_temp(system.get("temperature"))),
        ("LOAD", fmt_load(system.get("load"))),
        ("SWAP", fmt_percent(system.get("swap"))),
    ]
    f_value = font(32, bold=True)
    f_label = font(13, bold=True)
    f_detail = font(11, bold=True)
    cell = (x1 - x0) / len(labels)
    for index, (label, value) in enumerate(labels):
        cx = int(x0 + cell * index + cell / 2)
        draw.text((cx, y), value, font=f_value, fill=BLACK, anchor="ma")
        draw.text((cx, y + 42), label, font=f_label, fill=BLACK, anchor="ma")
        if label == "MEM":
            draw.text((cx, y + 62),
                      fmt_memory(system.get("mem_used"), system.get("mem_total")),
                      font=f_detail, fill=DARK, anchor="ma")
        if index:
            draw.line([(int(x0 + cell * index), y + 4), (int(x0 + cell * index), y + 76)],
                      fill=LIGHT, width=1)


def _disks(draw: ImageDraw.ImageDraw, disks: list[dict], x0: int, x1: int, y: int,
           columns: int) -> None:
    f_label = font(13, bold=True)
    f_value = font(12)
    if not disks:
        draw.text((x0, y), "No disk configured (set DISK1_MOUNT)", font=f_value, fill=DARK)
        return
    gap = 16
    col_width = (x1 - x0 - gap * (columns - 1)) // columns
    for index, disk in enumerate(disks[:columns]):
        x = x0 + index * (col_width + gap)
        if "percent" not in disk:
            draw.text((x, y), f"{disk['label']}  --", font=f_label, fill=BLACK)
            draw.text((x + col_width, y), "not found", font=f_value, fill=DARK, anchor="ra")
            draw_bar(draw, x, y + 30, col_width, 18, 0)
            continue
        percent = float(disk["percent"])
        draw.text((x, y), f"{disk['label']} ({percent:.0f}%)", font=f_label, fill=BLACK)
        draw.text((x + col_width, y), fmt_disk_free(disk), font=f_value, fill=BLACK, anchor="ra")
        draw_bar(draw, x, y + 30, col_width, 18, percent)


def _stock_rows(draw: ImageDraw.ImageDraw, quotes: list[dict], error: Optional[str],
                x0: int, x1: int, y: int, row_h: int, max_rows: int) -> None:
    f_symbol = font(17, bold=True)
    f_price = font(17)
    f_change = font(15, bold=True)
    f_note = font(13)
    if not quotes:
        draw.text((x0, y), "No symbols configured (set STOCK_SYMBOLS)", font=f_note, fill=DARK)
        return
    if error and all(q.get("price") is None for q in quotes):
        draw.text((x0, y), "Stock quotes unavailable", font=f_note, fill=DARK)
        return
    width = x1 - x0
    for index, quote in enumerate(quotes[:max_rows]):
        row_y = y + index * row_h
        symbol = quote["symbol"]
        draw.text((x0, row_y), symbol, font=f_symbol, fill=BLACK)
        if quote.get("price") is None:
            draw.text((x1, row_y), "n/a", font=f_price, fill=DARK, anchor="ra")
            continue
        change = quote["change"]
        pct = quote.get("change_pct")
        up = change >= 0
        tone = BLACK if up else DARK
        pct_text = "--" if pct is None else f"{pct:+.2f}%"
        change_text = f"{change:+.2f}  {pct_text}"
        draw.text((x0 + width * 0.52, row_y), fmt_price(quote["price"]), font=f_price, fill=BLACK, anchor="ra")
        change_w = text_width(draw, change_text, f_change)
        draw.text((x1, row_y + 1), change_text, font=f_change, fill=tone, anchor="ra")
        draw_triangle(draw, int(x1 - change_w - 18), row_y + 3, 11, up, tone)


def _weather_block(draw: ImageDraw.ImageDraw, weather: dict, x0: int, x1: int, y: int,
                   compact: bool) -> None:
    f_title = font(16, bold=True)
    f_detail = font(13 if not compact else 12)
    f_temp = font(36 if not compact else 30, bold=True)
    location = settings.weather_location.upper()
    status = weather.get("status")
    if status in ("disabled", "error") or weather.get("temperature") is None:
        draw.text((x0, y), location, font=f_title, fill=BLACK)
        note = "Weather disabled" if status == "disabled" else "Weather unavailable"
        draw.text((x0, y + 30), note, font=f_detail, fill=DARK)
        return

    stale = "  (stale)" if status == "stale" else ""
    temp_text = fmt_num(weather.get("temperature"), settings.temp_suffix)
    temp_w = text_width(draw, temp_text, f_temp)
    if compact:
        # Narrow rail: location and condition on separate lines so neither gets truncated.
        draw.text((x0, y), fit_text(draw, location, f_title, x1 - x0 - temp_w - 24), font=f_title, fill=BLACK)
        draw.text((x0, y + 26), f"{weather.get('condition', 'Unknown')}{stale}", font=f_detail, fill=BLACK)
        draw.text((x0, y + 60), (
            f"Feels {fmt_num(weather.get('apparent_temperature'), DEGREE)}   "
            f"Rain {fmt_num(weather.get('precip_probability'), '%')}"), font=f_detail, fill=DARK)
        draw.text((x0, y + 80), f"Wind {fmt_num(weather.get('wind_speed'))} {settings.wind_suffix}",
                  font=f_detail, fill=DARK)
    else:
        title = fit_text(draw, f"{location}  {weather.get('condition', 'Unknown')}{stale}",
                         f_title, x1 - x0 - temp_w - 24)
        draw.text((x0, y), title, font=f_title, fill=BLACK)
        draw.text((x0, y + 30), (
            f"Feels {fmt_num(weather.get('apparent_temperature'), DEGREE)}   "
            f"Rain {fmt_num(weather.get('precip_probability'), '%')}   "
            f"Wind {fmt_num(weather.get('wind_speed'))} {settings.wind_suffix}"), font=f_detail, fill=DARK)
    draw.text((x1, y - 6), temp_text, font=f_temp, fill=BLACK, anchor="ra")
    draw.text((x1, y + 34 if not compact else y + 30),
              f"H {fmt_num(weather.get('high'), DEGREE)}   L {fmt_num(weather.get('low'), DEGREE)}",
              font=f_detail, fill=DARK, anchor="ra")


def _footer(draw: ImageDraw.ImageDraw, now: datetime, x0: int, x1: int, y: int) -> None:
    f_footer = font(11)
    draw.text((x0, y), now.strftime("updated %Y-%m-%d %H:%M:%S"), font=f_footer, fill=DARK)
    note = "Stocks: delayed quotes via Yahoo Finance"
    draw.text((x1, y), note, font=f_footer, fill=DARK, anchor="ra")


# ---------------------------------------------------------------- layouts

def render_portrait(snapshot: dict, now: datetime) -> Image.Image:
    width, height = PORTRAIT
    image = Image.new("L", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    system = snapshot["system"]

    _header(draw, now, width, 16, system["hostname"], system["uptime"], portrait=True)
    draw_rule(draw, MARGIN, width - MARGIN, 88)
    _metrics(draw, system, MARGIN, width - MARGIN, 100)
    draw_rule(draw, MARGIN, width - MARGIN, 186)

    f_section = font(17, bold=True)
    draw.text((MARGIN, 196), "DISK", font=f_section, fill=BLACK)
    _disks(draw, system["disks"], MARGIN, width - MARGIN, 224, columns=2)
    draw_rule(draw, MARGIN, width - MARGIN, 286)

    draw.text((MARGIN, 296), "STOCKS", font=f_section, fill=BLACK)
    stocks = snapshot["stocks"]
    _stock_rows(draw, stocks["quotes"], stocks["error"], MARGIN, width - MARGIN,
                326, row_h=44, max_rows=6)
    draw_rule(draw, MARGIN, width - MARGIN, 600)

    _weather_block(draw, snapshot["weather"], MARGIN, width - MARGIN, 618, compact=False)
    draw_rule(draw, MARGIN, width - MARGIN, 690)
    _footer(draw, now, MARGIN, width - MARGIN, 706)
    return image


def render_landscape(snapshot: dict, now: datetime) -> Image.Image:
    width, height = LANDSCAPE
    image = Image.new("L", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    system = snapshot["system"]
    left_x1 = 480
    rail_x0 = 514
    right = width - MARGIN

    _header(draw, now, width, 14, system["hostname"], system["uptime"], portrait=False)
    draw_rule(draw, MARGIN, right, 84)
    _metrics(draw, system, MARGIN, right, 94)
    draw_rule(draw, MARGIN, right, 180)
    draw.line([(496, 192), (496, 540)], fill=LIGHT, width=1)

    f_section = font(17, bold=True)
    draw.text((MARGIN, 192), "STOCKS", font=f_section, fill=BLACK)
    stocks = snapshot["stocks"]
    _stock_rows(draw, stocks["quotes"], stocks["error"], MARGIN, left_x1,
                222, row_h=36, max_rows=9)

    _weather_block(draw, snapshot["weather"], rail_x0, right, 192, compact=True)
    draw_rule(draw, rail_x0, right, 300)
    draw.text((rail_x0, 312), "DISK", font=f_section, fill=BLACK)
    for index, disk in enumerate(system["disks"][:2]):
        _disks(draw, [disk], rail_x0, right, 342 + index * 78, columns=1)
    if not system["disks"]:
        _disks(draw, [], rail_x0, right, 342, columns=1)

    draw_rule(draw, MARGIN, right, 552)
    _footer(draw, now, MARGIN, right, 564)
    return image


def render_landscape_kindle(snapshot: dict, now: datetime) -> Image.Image:
    """Landscape content rotated clockwise into the portrait framebuffer (power button on the right)."""
    return render_landscape(snapshot, now).rotate(-90, expand=True)


RENDERERS = {
    "portrait": render_portrait,
    "landscape": render_landscape,
    "landscape-kindle": render_landscape_kindle,
}


def render_png(snapshot: dict, orientation: str, now: Optional[datetime] = None) -> bytes:
    if orientation not in RENDERERS:
        raise ValueError(f"unsupported orientation: {orientation}")
    now = now or datetime.now(settings.tz)
    image = RENDERERS[orientation](snapshot, now)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
