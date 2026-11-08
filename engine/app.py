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


@app.post("/v1/match")
def match(req: MatchRequest):
    try:
        return handlers.match_from_payload(req.model_dump())
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


class PrashnaRequest(BaseModel):
    topic: str = "general"
    lat: float
    lon: float
    tz: str = "Asia/Kolkata"
    when: str | None = None
    kp_number: int | None = Field(None, ge=1, le=249)


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


# Serve the web page and the knowledge data from the same container (one deployable unit).
# Set KUNDALI_SERVE_WEB=0 when the web/ folder is hosted elsewhere (e.g. Cloudflare Pages).
_ROOT = Path(__file__).resolve().parents[1]
if os.environ.get("KUNDALI_SERVE_WEB", "1") == "1" and (_ROOT / "web").is_dir():
    app.mount("/data", StaticFiles(directory=_ROOT / "data"), name="data")
    app.mount("/", StaticFiles(directory=_ROOT / "web", html=True), name="web")
