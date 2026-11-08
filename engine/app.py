"""Production API (FastAPI). Run:  uvicorn app:app --host 0.0.0.0 --port 8000

Put it behind Cloudflare (Tunnel). Restrict CORS_ORIGINS to your real site(s).
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from jyotish import handlers

app = FastAPI(title="Kundali Engine", version=handlers.ENGINE_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o],
    allow_methods=["GET", "POST"], allow_headers=["*"],
)


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
def report(req: ChartRequest):
    try:
        return HTMLResponse(handlers.report_from_payload(req.model_dump(exclude_none=True)))
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
