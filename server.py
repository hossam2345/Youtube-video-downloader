#!/usr/bin/env python3
"""Local server so yt.html can download videos through ytp.py."""

from __future__ import annotations

import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
YTP_DIR = Path(r"d:\python files\ytp")
DOWNLOAD_DIR = HERE / "downloads"
HOST = "127.0.0.1"
PORT = 8765

sys.path.insert(0, str(YTP_DIR))
try:
    from ytp import download  # noqa: E402
    from yt_dlp.utils import DownloadError, YoutubeDLError  # noqa: E402
except ModuleNotFoundError as exc:  # pragma: no cover - startup guard
    if exc.name in {"yt_dlp", "ytp"}:
        raise SystemExit(
            "Missing required dependency. Install it with: python -m pip install yt-dlp"
        ) from exc
    raise

_download_lock = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/api/health":
            self._json(200, {"ok": True, "downloads": str(DOWNLOAD_DIR)})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/download":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "Invalid JSON body."})
            return

        url = str(payload.get("url") or "").strip()
        audio_only = bool(payload.get("audio_only"))
        if not url:
            self._json(400, {"ok": False, "error": "Paste a YouTube URL first."})
            return

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or not (
            host == "youtu.be"
            or host.endswith("youtube.com")
            or host.endswith("youtube-nocookie.com")
        ):
            self._json(400, {"ok": False, "error": "That doesn't look like a YouTube URL."})
            return

        if not _download_lock.acquire(blocking=False):
            self._json(409, {"ok": False, "error": "Another download is already running."})
            return

        try:
            path = download(url, DOWNLOAD_DIR, None, audio_only, quiet=True)
        except (DownloadError, YoutubeDLError) as exc:
            self._json(500, {"ok": False, "error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001 — return a usable error to the page
            self._json(500, {"ok": False, "error": f"Download failed: {exc}"})
            return
        finally:
            _download_lock.release()

        if not path.exists():
            self._json(500, {"ok": False, "error": f"Download finished, but the file was not found at: {path}"})
            return

        self._json(
            200,
            {
                "ok": True,
                "path": str(path),
                "filename": path.name,
            },
        )

    def _json(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main() -> int:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Open http://{HOST}:{PORT}/index.html", flush=True)
    print(f"Downloads folder: {DOWNLOAD_DIR}", flush=True)
    print("Leave this window open while you use the page. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
