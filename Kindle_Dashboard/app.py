"""FastAPI server that renders the Kindle dashboard on demand. No Docker required.

Run:  uvicorn app:app --host 0.0.0.0 --port 8070
  or: python app.py
"""

import logging
import threading
import time
from datetime import datetime

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, PlainTextResponse

from dashboard.collectors import collect_snapshot
from dashboard.config import settings
from dashboard.render import render_png

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("dashboard")

app = FastAPI(title="Kindle Dashboard", docs_url=None, redoc_url=None, openapi_url=None)

# Image path -> renderer orientation.
IMAGE_ROUTES = {
    "/dash.png": "portrait",
    "/dash-landscape.png": "landscape",
    "/dash-landscape-kindle.png": "landscape-kindle",
}

_render_slots = threading.BoundedSemaphore(settings.render_concurrency)
_render_locks: dict[str, threading.Lock] = {name: threading.Lock() for name in IMAGE_ROUTES.values()}
_render_cache: dict[str, tuple[float, bytes, datetime]] = {}


def render_cached(orientation: str) -> tuple[bytes, datetime]:
    """Render once and reuse the PNG for a few seconds, so duplicate Kindle/browser requests are cheap."""
    with _render_locks[orientation]:
        cached = _render_cache.get(orientation)
        if cached and time.monotonic() - cached[0] <= settings.render_cache_seconds:
            return cached[1], cached[2]
        with _render_slots:
            rendered_at = datetime.now(settings.tz)
            snapshot = collect_snapshot()
            png = render_png(snapshot, orientation, rendered_at)
        _render_cache[orientation] = (time.monotonic(), png, rendered_at)
        return png, rendered_at


def _image_response(orientation: str) -> Response:
    try:
        png, rendered_at = render_cached(orientation)
    except Exception as exc:
        log.exception("render failed for %s: %s", orientation, exc)
        return PlainTextResponse("dashboard render failed\n", status_code=503)
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "X-Dashboard-Rendered-At": rendered_at.isoformat(),
        },
    )


@app.api_route("/dash.png", methods=["GET", "HEAD"])
def dash_portrait() -> Response:
    return _image_response(IMAGE_ROUTES["/dash.png"])


@app.api_route("/dash-landscape.png", methods=["GET", "HEAD"])
def dash_landscape() -> Response:
    return _image_response(IMAGE_ROUTES["/dash-landscape.png"])


@app.api_route("/dash-landscape-kindle.png", methods=["GET", "HEAD"])
def dash_landscape_kindle() -> Response:
    return _image_response(IMAGE_ROUTES["/dash-landscape-kindle.png"])


PREVIEW_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kindle Dashboard Preview - {label}</title>
  <style>
    :root {{ color-scheme: dark; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #171717; color: #eee; }}
    header {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
      padding: 12px 16px; background: #242424; border-bottom: 1px solid #444; }}
    h1 {{ margin: 0 12px 0 0; font-size: 17px; }}
    a, button {{ color: #fff; background: #333; border: 1px solid #666; border-radius: 5px;
      padding: 6px 10px; text-decoration: none; cursor: pointer; }}
    #status {{ margin-left: auto; color: #bbb; font-size: 13px; }}
    main {{ padding: 24px; text-align: center; }}
    img {{ max-width: 100%; height: auto; background: #fff; box-shadow: 0 8px 28px #000b; }}
  </style>
</head>
<body>
  <header>
    <h1>Kindle Dashboard - {label}</h1>
    <a href="{other_href}">View {other_label}</a>
    <button id="pause" type="button">Pause</button>
    <span id="status">Loading...</span>
  </header>
  <main><img id="frame" src="{image}" alt="Rendered dashboard"></main>
  <script>
    const frame = document.getElementById('frame');
    const status = document.getElementById('status');
    const pause = document.getElementById('pause');
    let paused = false;
    function refresh() {{
      if (paused || document.hidden) return;
      const next = new Image();
      next.onload = () => {{ frame.src = next.src; status.textContent = 'Updated ' + new Date().toLocaleTimeString(); }};
      next.onerror = () => {{ status.textContent = 'Render failed'; }};
      next.src = '{image}?preview=' + Date.now();
    }}
    pause.addEventListener('click', () => {{
      paused = !paused;
      pause.textContent = paused ? 'Resume' : 'Pause';
      if (!paused) refresh();
    }});
    setInterval(refresh, 5000);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
@app.get("/preview", response_class=HTMLResponse)
def preview_portrait() -> str:
    return PREVIEW_PAGE.format(label="Portrait", other_href="/preview/landscape",
                               other_label="landscape", image="/dash.png")


@app.get("/preview/landscape", response_class=HTMLResponse)
def preview_landscape() -> str:
    return PREVIEW_PAGE.format(label="Landscape", other_href="/preview",
                               other_label="portrait", image="/dash-landscape.png")


@app.get("/time", response_class=PlainTextResponse)
def server_time() -> str:
    # The Kindle client uses this to align its refresh with the minute boundary.
    return f"{int(time.time())}\n"


@app.get("/healthz", response_class=PlainTextResponse)
def healthz() -> str:
    return "ok\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
