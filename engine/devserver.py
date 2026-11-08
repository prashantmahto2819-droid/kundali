"""Zero-dependency local server for development:  python devserver.py [port]

Serves the web/ and data/ folders and the same JSON API as app.py.
(Production uses app.py with FastAPI.)
"""
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jyotish import handlers

ROOT = Path(__file__).resolve().parents[1]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            return self._json(200, handlers.health())
        rel = "web/index.html" if path == "/" else path.lstrip("/")
        if not (rel.startswith("web/") or rel.startswith("data/")):
            rel = "web/" + rel
        target = (ROOT / rel).resolve()
        if ROOT not in target.parents or not target.is_file():
            return self._json(404, {"error": "not found"})
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json", "application/javascript"):
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self):
        routes = {"/v1/chart": handlers.chart_from_payload,
                  "/v1/numerology": handlers.numerology_from_payload,
                  "/v1/match": handlers.match_from_payload,
                  "/v1/tarot": handlers.tarot_from_payload}
        if self.path not in routes:
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            return self._json(200, routes[self.path](payload))
        except handlers.BadRequest as exc:
            return self._json(422, {"detail": str(exc)})
        except json.JSONDecodeError:
            return self._json(400, {"detail": "invalid JSON"})

    def log_message(self, fmt, *args):
        sys.stderr.write("[dev] " + fmt % args + "\n")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Kundali dev server on http://127.0.0.1:{port}  (backend: {handlers.backend().name})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
