"""Zero-dependency local server for development:  python devserver.py [port]

Serves the web/ and data/ folders and the same JSON API as app.py.
(Production uses app.py with FastAPI.)
"""
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jyotish import access, handlers, people

ROOT = Path(__file__).resolve().parents[1]


class Handler(BaseHTTPRequestHandler):
    extra_headers: dict = {}

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in self.extra_headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _guard(self, path) -> bool:
        """Apply the access guard; on failure the response is already sent and False is returned."""
        status, body, hdrs, _org = access.guard(self.headers, path)
        self.extra_headers = hdrs
        if status != 200:
            self._json(status, body)
            return False
        return True

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE")
        self.end_headers()

    def _people(self, method):
        path = self.path.split("?")[0]
        payload = None
        if method in ("POST", "PUT"):
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"detail": "invalid JSON"})
        status, body = people.api(method, path, self.headers, payload)
        return self._json(status, body)

    def do_PUT(self):
        path = self.path.split("?")[0]
        if (path.startswith("/v1/people") or path.startswith("/v1/me")) and self._guard(path):
            return self._people("PUT")
        return self._json(404, {"error": "not found"})

    def do_DELETE(self):
        path = self.path.split("?")[0]
        if path.startswith("/v1/people") and self._guard(path):
            return self._people("DELETE")
        if not path.startswith("/v1/people"):
            return self._json(404, {"error": "not found"})

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if not self._guard(path):
            return
        if path.startswith("/v1/people") or path.startswith("/v1/me"):
            return self._people("GET")
        if path == "/health":
            return self._json(200, handlers.health())
        if path == "/v1/palm/catalog":
            from jyotish import palm
            return self._json(200, palm.catalog())
        if path == "/v1/ai/status":
            return self._json(200, handlers.ai_status_from_payload())
        if path == "/v1/panchang/card.png":
            from urllib.parse import parse_qs
            try:
                png = handlers.panchang_card_from_query({k: v[0] for k, v in parse_qs(query).items()})
            except handlers.BadRequest as exc:
                return self._json(422, {"detail": str(exc)})
            self.send_response(200); self.send_header("Content-Type", "image/png"); self.send_header("Content-Length", str(len(png))); self.send_header("Cache-Control", "public, max-age=600"); self.end_headers(); self.wfile.write(png); return
        if path == "/v1/panchang/eclipse":
            from urllib.parse import parse_qs
            try:
                return self._json(200, handlers.eclipse_from_query({k: v[0] for k, v in parse_qs(query).items()}))
            except handlers.BadRequest as exc:
                return self._json(422, {"detail": str(exc)})
        if path == "/v1/i18n/languages":
            return self._json(200, handlers.i18n_languages())
        if path == "/v1/consult/astrologers":
            return self._json(200, handlers.consult_astrologers_from_query())
        if path == "/v1/palm/trace/catalog":
            return self._json(200, handlers.palm_trace_catalog())
        if path == "/v1/vastu/catalog":
            return self._json(200, handlers.vastu_catalog())
        if path == "/v1/vastu/plan/catalog":
            return self._json(200, handlers.vastu_plan_catalog())
        if path == "/v1/panchang/day":
            from urllib.parse import parse_qs
            q = {k: v[0] for k, v in parse_qs(query).items()}
            try:
                return self._json(200, handlers.panchang_today_from_query(q))
            except handlers.BadRequest as exc:
                return self._json(400, {"detail": str(exc)})
        if path == "/v1/rashifal":
            from urllib.parse import parse_qs
            q = {k: v[0] for k, v in parse_qs(query).items()}
            try:
                return self._json(200, handlers.rashifal_from_query(q))
            except handlers.BadRequest as exc:
                return self._json(400, {"detail": str(exc)})
        if path == "/v1/panchang/month":
            from urllib.parse import parse_qs
            q = {k: v[0] for k, v in parse_qs(query).items()}
            try:
                return self._json(200, handlers.panchang_month_from_query(q))
            except handlers.BadRequest as exc:
                return self._json(400, {"detail": str(exc)})
        if path == "/v1/festivals":
            from urllib.parse import parse_qs
            q = {k: v[0] for k, v in parse_qs(query).items()}
            try:
                return self._json(200, handlers.festivals_from_query(q))
            except handlers.BadRequest as exc:
                return self._json(400, {"detail": str(exc)})
        if path == "/v1/places":
            from urllib.parse import parse_qs
            qs = parse_qs(query)
            try:
                limit = int(qs.get("limit", ["8"])[0])
            except ValueError:
                limit = 8
            return self._json(200, handlers.places_from_query(qs.get("q", [""])[0], limit))
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
        if not self._guard(self.path.split("?")[0]):
            return
        if self.path.split("?")[0].startswith("/v1/people"):
            return self._people("POST")
        routes = {"/v1/chart": handlers.chart_from_payload,
                  "/v1/numerology": handlers.numerology_from_payload,
                  "/v1/match": handlers.match_from_payload,
                  "/v1/tarot": handlers.tarot_from_payload,
                  "/v1/vastu": handlers.vastu_from_payload,
                  "/v1/vastu/plan": handlers.vastu_plan_upload_from_payload,
                  "/v1/vastu/zones": handlers.vastu_plan_from_payload,
                  "/v1/palm": handlers.palm_from_payload,
                  "/v1/palm/trace": handlers.palm_trace_from_payload,
                  "/v1/muhurta": handlers.muhurta_from_payload,
                  "/v1/muhurta/lagna": handlers.muhurta_lagna_from_payload,
                  "/v1/prashna": handlers.prashna_from_payload,
                  "/v1/rectify": handlers.rectify_from_payload,
                  "/v1/lalkitab/varshphal": handlers.lalkitab_varshphal_from_payload,
                  "/v1/varshaphal": handlers.varshaphal_from_payload,
                  "/v1/ask": handlers.ask_from_payload,
                  "/v1/notify/subscribe": handlers.notify_subscribe_from_payload,
                  "/v1/notify/verify": handlers.notify_verify_from_payload,
                  "/v1/notify/unsubscribe": handlers.notify_unsubscribe_from_payload,
                  "/v1/notify/status": handlers.notify_status_from_payload,
                  "/v1/notify/preview": handlers.notify_preview_from_payload,
                  "/v1/ai/chat": handlers.ai_chat_from_payload,
                  "/v1/ai/palm": handlers.ai_palm_from_payload,
                  "/v1/ai/status": handlers.ai_status_from_payload,
                  "/v1/ai/summary": handlers.ai_summary_from_payload,
                  "/v1/chart/year_ahead": handlers.year_ahead_from_payload,
                  "/v1/ai/calendar_text": handlers.ai_calendar_text_from_payload,
                  "/v1/ai/quiz": handlers.ai_quiz_from_payload,
                  "/v1/consult/request": handlers.consult_request_from_payload,
                  "/v1/consult/mine": handlers.consult_mine_from_payload,
                  "/v1/wallet": handlers.wallet_from_payload}
        header_routes = {"/v1/consult/get": handlers.consult_get_from_payload, "/v1/consult/message": handlers.consult_message_from_payload,
                         "/v1/consult/close": handlers.consult_close_from_payload, "/v1/consult/admin": handlers.consult_admin_from_payload,
                         "/v1/consult/draft": handlers.consult_draft_from_payload, "/v1/ai/extract_rules": handlers.ai_extract_rules_from_payload}
        if self.path in header_routes:
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                return self._json(200, header_routes[self.path](payload, dict(self.headers)))
            except handlers.BadRequest as exc:
                return self._json(422, {"detail": str(exc)})
            except json.JSONDecodeError:
                return self._json(400, {"detail": "invalid JSON"})
        if self.path.split("?")[0] == "/v1/notify/webhook":            # Relay inbound messages: raw body + signature headers
            length = int(self.headers.get("Content-Length", 0))
            try:
                return self._json(200, handlers.notify_webhook(self.rfile.read(length), dict(self.headers)))
            except PermissionError:
                return self._json(401, {"detail": "bad signature"})
        if self.path.split("?")[0] in handlers.REPORT_ROUTES:
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                route = self.path.split("?")[0]
                if route == "/v1/report":
                    html = handlers.report_from_payload(payload, brand=handlers.brand_for(self.headers))
                else:
                    html = getattr(handlers, handlers.REPORT_ROUTES[route])(payload)
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            except handlers.BadRequest as exc:
                return self._json(422, {"detail": str(exc)})
            except json.JSONDecodeError:
                return self._json(400, {"detail": "invalid JSON"})
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
    if handlers.start_notify_worker_if_enabled():
        print("WhatsApp notify worker running (KUNDALI_NOTIFY=1)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
