"""Production API (FastAPI). Run:  uvicorn app:app --host 0.0.0.0 --port 8000

Put it behind Cloudflare (Tunnel). Restrict CORS_ORIGINS to your real site(s).
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jyotish import access, handlers, people

app = FastAPI(title="Kundali Engine", version=handlers.ENGINE_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o],
    allow_methods=["GET", "POST"], allow_headers=["*"],
)


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    """KUNDALI_AUTH = off | optional | required  (see jyotish/access.py)."""
    status, body, hdrs, _org = access.guard(request.headers, request.url.path)
    if status != 200:
        return JSONResponse(body, status_code=status, headers=hdrs)
    response = await call_next(request)
    for k, v in hdrs.items():
        response.headers[k] = v
    return response


class ChartRequest(BaseModel):
    name: str | None = None
    date: str = Field(examples=["1990-05-17"])
    time: str = Field(examples=["06:45"])
    tz: str = Field(examples=["Asia/Kolkata"])
    lat: float
    lon: float
    ayanamsa: str = "lahiri"
    year_days: float = 365.25
    as_of: str | None = None
    dasha_level: int = 2
    lang: str = "hi"


@app.api_route("/v1/people", methods=["GET", "POST"])
@app.api_route("/v1/people/{rest:path}", methods=["GET", "PUT", "DELETE"])
@app.api_route("/v1/me", methods=["GET", "PUT"])
async def saved_people(request: Request, rest: str = ""):
    """Saved birth data and astrologer profile per organisation (see jyotish/people.py)."""
    payload = None
    if request.method in ("POST", "PUT"):
        try:
            payload = await request.json()
        except ValueError:
            return JSONResponse({"detail": "invalid JSON"}, status_code=400)
    status, body = people.api(request.method, request.url.path, request.headers, payload)
    return JSONResponse(body, status_code=status)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    lang: str | None = None
    chart: ChartRequest | None = None


@app.post("/v1/ask")
def ask_question(req: AskRequest):
    """Answers from the app's own content (and the person's chart); see jyotish/ask.py."""
    try:
        return handlers.ask_from_payload(req.model_dump(exclude_none=True))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    return handlers.health()


@app.post("/v1/chart")
def chart(req: ChartRequest):
    try:
        return handlers.chart_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class NumerologyRequest(BaseModel):
    date: str = Field(examples=["1990-05-17"])
    name: str | None = None
    as_of: str | None = None


@app.post("/v1/numerology")
def numerology(req: NumerologyRequest):
    try:
        return handlers.numerology_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class Person(BaseModel):
    name: str | None = None
    date: str
    time: str
    tz: str
    lat: float
    lon: float


class MatchRequest(BaseModel):
    boy: Person
    girl: Person
    lang: str = "hi"


@app.post("/v1/match")
def match(req: MatchRequest):
    try:
        return handlers.match_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/match/report", response_class=HTMLResponse)
def match_report(req: MatchRequest):
    try:
        return HTMLResponse(handlers.match_report_from_payload(req.model_dump(exclude_none=True)))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class TarotRequest(BaseModel):
    spread: str = "three"
    question: str | None = None
    seed: int | str | None = None
    reversals: bool = True


@app.post("/v1/tarot")
def tarot(req: TarotRequest):
    try:
        return handlers.tarot_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/places")
def places(q: str = "", limit: int = 8):
    return handlers.places_from_query(q, limit)


@app.post("/v1/numerology/report", response_class=HTMLResponse)
@app.post("/v1/tarot/report", response_class=HTMLResponse)
@app.post("/v1/vastu/report", response_class=HTMLResponse)
@app.post("/v1/vastu/plan/report", response_class=HTMLResponse)
@app.post("/v1/palm/report", response_class=HTMLResponse)
@app.post("/v1/palm/trace/report", response_class=HTMLResponse)
@app.post("/v1/panchang/calendar/report", response_class=HTMLResponse)
@app.post("/v1/rashifal/report", response_class=HTMLResponse)
async def small_reports(request: Request):
    """Printable pages for numerology, tarot, vastu and palm (same payload as the JSON route, + lang)."""
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({"detail": "invalid JSON"}, status_code=400)
    fn = getattr(handlers, handlers.REPORT_ROUTES[request.url.path])
    try:
        return HTMLResponse(fn(payload if isinstance(payload, dict) else {}))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/report", response_class=HTMLResponse)
def report(req: ChartRequest, request: Request):
    try:
        return HTMLResponse(handlers.report_from_payload(req.model_dump(exclude_none=True), brand=handlers.brand_for(request.headers)))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class MuhurtaRequest(BaseModel):
    activity: str = "general"
    lat: float
    lon: float
    tz: str = "Asia/Kolkata"
    start: str | None = None
    days: int = Field(30, ge=1, le=60)
    chart: ChartRequest | None = None


@app.post("/v1/muhurta")
def muhurta(req: MuhurtaRequest):
    try:
        return handlers.muhurta_from_payload(req.model_dump(exclude_none=True))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class LalVarshRequest(ChartRequest):
    year: int | None = Field(None, ge=1900, le=2100)


@app.post("/v1/lalkitab/varshphal")
def lalkitab_varshphal(req: LalVarshRequest):
    try:
        return handlers.lalkitab_varshphal_from_payload(req.model_dump(exclude_none=True))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class MuhurtaReportRequest(MuhurtaRequest):
    lang: str = "hi"


@app.post("/v1/muhurta/report", response_class=HTMLResponse)
def muhurta_report(req: MuhurtaReportRequest):
    try:
        return HTMLResponse(handlers.muhurta_report_from_payload(req.model_dump(exclude_none=True)))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class PrashnaRequest(BaseModel):
    topic: str = "general"
    lat: float
    lon: float
    tz: str = "Asia/Kolkata"
    when: str | None = None
    kp_number: int | None = Field(None, ge=1, le=249)


class PrashnaReportRequest(PrashnaRequest):
    lang: str = "hi"


class RectifyEvent(BaseModel):
    type: str
    year: int = Field(..., ge=1900, le=2100)
    month: int | None = Field(None, ge=1, le=12)


class RectifyRequest(BaseModel):
    date: str
    time: str
    tz: str
    lat: float
    lon: float
    range_min: int = Field(120, ge=5, le=720)
    step_min: int = Field(2, ge=1, le=10)
    events: list[RectifyEvent] = []


@app.post("/v1/prashna/report", response_class=HTMLResponse)
def prashna_report(req: PrashnaReportRequest):
    try:
        return HTMLResponse(handlers.prashna_report_from_payload(req.model_dump(exclude_none=True)))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/rectify")
def rectify(req: RectifyRequest):
    try:
        return handlers.rectify_from_payload(req.model_dump(exclude_none=True))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/prashna")
def prashna(req: PrashnaRequest):
    try:
        return handlers.prashna_from_payload(req.model_dump(exclude_none=True))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class VastuItem(BaseModel):
    room: str
    direction: str | None = None
    degrees: float | None = None


class VastuRequest(BaseModel):
    items: list[VastuItem]


@app.post("/v1/vastu")
def vastu(req: VastuRequest):
    try:
        return handlers.vastu_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/vastu/catalog")
def vastu_catalog():
    return handlers.vastu_catalog()


class MuhurtaLagnaRequest(BaseModel):
    date: str
    lat: float
    lon: float
    tz: str = "Asia/Kolkata"
    activity: str = "marriage"
    groom_moon_sign: int | None = Field(None, ge=0, le=11)
    bride_moon_sign: int | None = Field(None, ge=0, le=11)
    groom_nakshatra: int | None = Field(None, ge=0, le=26)
    bride_nakshatra: int | None = Field(None, ge=0, le=26)


@app.post("/v1/muhurta/lagna")
def muhurta_lagna(req: MuhurtaLagnaRequest):
    try:
        return handlers.muhurta_lagna_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class NotifyRequest(BaseModel):
    model_config = {"extra": "allow"}
    phone: str | None = None


@app.post("/v1/notify/subscribe")
def notify_subscribe(req: NotifyRequest):
    try:
        return handlers.notify_subscribe_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/notify/verify")
def notify_verify(req: NotifyRequest):
    try:
        return handlers.notify_verify_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/notify/unsubscribe")
def notify_unsubscribe(req: NotifyRequest):
    try:
        return handlers.notify_unsubscribe_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/notify/status")
def notify_status(req: NotifyRequest):
    try:
        return handlers.notify_status_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/notify/preview")
def notify_preview(req: NotifyRequest):
    try:
        return handlers.notify_preview_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/ai/status")
def ai_status():
    return handlers.ai_status_from_payload()


@app.post("/v1/ai/chat")
def ai_chat(req: NotifyRequest):
    try:
        return handlers.ai_chat_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/ai/palm")
def ai_palm(req: NotifyRequest):
    try:
        return handlers.ai_palm_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/panchang/eclipse")
def panchang_eclipse(request: Request):
    try:
        return handlers.eclipse_from_query(dict(request.query_params))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/i18n/languages")
def i18n_languages():
    return handlers.i18n_languages()


@app.get("/v1/consult/astrologers")
def consult_astrologers():
    return handlers.consult_astrologers_from_query()


def _consult_route(fn, req: NotifyRequest, request: Request | None = None):
    try:
        return fn(req.model_dump(), dict(request.headers)) if request is not None else fn(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/v1/consult/request")
def consult_request(req: NotifyRequest):
    return _consult_route(handlers.consult_request_from_payload, req)


@app.post("/v1/consult/mine")
def consult_mine(req: NotifyRequest):
    return _consult_route(handlers.consult_mine_from_payload, req)


@app.post("/v1/wallet")
def wallet(req: NotifyRequest):
    return _consult_route(handlers.wallet_from_payload, req)


@app.post("/v1/consult/get")
def consult_get(req: NotifyRequest, request: Request):
    return _consult_route(handlers.consult_get_from_payload, req, request)


@app.post("/v1/consult/message")
def consult_message(req: NotifyRequest, request: Request):
    return _consult_route(handlers.consult_message_from_payload, req, request)


@app.post("/v1/consult/close")
def consult_close(req: NotifyRequest, request: Request):
    return _consult_route(handlers.consult_close_from_payload, req, request)


@app.post("/v1/consult/admin")
def consult_admin(req: NotifyRequest, request: Request):
    return _consult_route(handlers.consult_admin_from_payload, req, request)


@app.post("/v1/chart/year_ahead")
def chart_year_ahead(req: NotifyRequest):
    return _consult_route(handlers.year_ahead_from_payload, req)


@app.post("/v1/ai/summary")
def ai_summary(req: NotifyRequest):
    return _consult_route(handlers.ai_summary_from_payload, req)


@app.post("/v1/ai/calendar_text")
def ai_calendar_text(req: NotifyRequest):
    return _consult_route(handlers.ai_calendar_text_from_payload, req)


@app.post("/v1/ai/quiz")
def ai_quiz(req: NotifyRequest):
    return _consult_route(handlers.ai_quiz_from_payload, req)


@app.post("/v1/consult/draft")
def consult_draft(req: NotifyRequest, request: Request):
    return _consult_route(handlers.consult_draft_from_payload, req, request)


@app.post("/v1/ai/extract_rules")
def ai_extract_rules(req: NotifyRequest, request: Request):
    return _consult_route(handlers.ai_extract_rules_from_payload, req, request)


@app.post("/v1/notify/webhook")
async def notify_webhook(request: Request):
    try:
        return handlers.notify_webhook(await request.body(), dict(request.headers))
    except PermissionError:
        raise HTTPException(status_code=401, detail="bad signature")


@app.middleware("http")
async def _no_stale_shell(request: Request, call_next):
    """HTML, the service worker and i18n must never be served stale (browsers and Cloudflare otherwise keep the old app shell)."""
    resp = await call_next(request)
    p = request.url.path
    if p in ("/", "/index.html", "/sw.js", "/config.js") or p.endswith(".html") or (p.startswith("/data/i18n_") and p.endswith(".json")):
        resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp


@app.on_event("startup")
def _start_notify_worker():
    handlers.start_notify_worker_if_enabled()


@app.get("/v1/panchang/day")
def panchang_day(date: str | None = None, lat: float = 28.61, lon: float = 77.2, tz: str = "Asia/Kolkata"):
    try:
        return handlers.panchang_today_from_query({"date": date, "lat": lat, "lon": lon, "tz": tz})
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/rashifal")
def rashifal(date: str | None = None, period: str = "daily", tz: str = "Asia/Kolkata"):
    try:
        return handlers.rashifal_from_query({"date": date, "period": period, "tz": tz})
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/panchang/month")
def panchang_month(year: int | None = None, month: int | None = None, lat: float = 28.61, lon: float = 77.2, tz: str = "Asia/Kolkata"):
    try:
        return handlers.panchang_month_from_query({"year": year, "month": month, "lat": lat, "lon": lon, "tz": tz})
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/festivals")
def festivals(year: int | None = None, lat: float = 28.61, lon: float = 77.2, tz: str = "Asia/Kolkata"):
    try:
        return handlers.festivals_from_query({"year": year, "lat": lat, "lon": lon, "tz": tz})
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/vastu/plan/catalog")
def vastu_plan_catalog():
    return handlers.vastu_plan_catalog()


class VastuPlanUpload(BaseModel):
    filename: str = ""
    content_b64: str = Field(..., max_length=17 * 1024 * 1024)


@app.post("/v1/vastu/plan")
def vastu_plan_upload(req: VastuPlanUpload):
    try:
        return handlers.vastu_plan_upload_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class VastuRoomPoint(BaseModel):
    room: str
    x: float
    y: float


class VastuZonesRequest(BaseModel):
    polygon: list[list[float]] = Field(..., min_length=3, max_length=60)
    north_angle: float = 0.0
    rooms: list[VastuRoomPoint] = Field(default_factory=list, max_length=60)
    lat: float | None = None
    lon: float | None = None
    place: str | None = Field(None, max_length=120)


@app.post("/v1/vastu/zones")
def vastu_zones(req: VastuZonesRequest):
    try:
        return handlers.vastu_plan_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class VarshaphalRequest(ChartRequest):
    year: int
    return_lat: float | None = None
    return_lon: float | None = None
    return_tz: str | None = None


@app.post("/v1/varshaphal")
def varshaphal(req: VarshaphalRequest):
    try:
        return handlers.varshaphal_from_payload(req.model_dump(exclude_none=True))
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class PalmRequest(BaseModel):
    choices: dict[str, str]


@app.post("/v1/palm")
def palm_reading(req: PalmRequest):
    try:
        return handlers.palm_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/v1/palm/catalog")
def palm_catalog():
    from jyotish import palm as _palm
    return _palm.catalog()


@app.get("/v1/palm/trace/catalog")
def palm_trace_catalog():
    return handlers.palm_trace_catalog()


class PalmMark(BaseModel):
    line: str
    type: str
    x: float | None = None
    y: float | None = None


class PalmTraceRequest(BaseModel):
    landmarks: dict[str, list[float]]
    lines: dict[str, list[list[float]]] = Field(default_factory=dict)
    marks: list[PalmMark] = Field(default_factory=list, max_length=30)
    extras: dict[str, int] = Field(default_factory=dict)
    choices: dict[str, str] = Field(default_factory=dict)


@app.post("/v1/palm/trace")
def palm_trace(req: PalmTraceRequest):
    try:
        return handlers.palm_trace_from_payload(req.model_dump())
    except handlers.BadRequest as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# Serve the web page and the knowledge data from the same container (one deployable unit).
# Set KUNDALI_SERVE_WEB=0 when the web/ folder is hosted elsewhere (e.g. Cloudflare Pages).
_ROOT = Path(__file__).resolve().parents[1]
if os.environ.get("KUNDALI_SERVE_WEB", "1") == "1" and (_ROOT / "web").is_dir():
    app.mount("/data", StaticFiles(directory=_ROOT / "data"), name="data")
    app.mount("/", StaticFiles(directory=_ROOT / "web", html=True), name="web")
