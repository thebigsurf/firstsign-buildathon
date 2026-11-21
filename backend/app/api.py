"""HTTP routes under /api. Thin: every behaviour lives in service.py, signal.py, agent.py."""

from __future__ import annotations

import mimetypes
import os
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from . import __version__
from .context import AppContext
from .errors import AppError, BadRequest, NotFound
from .ratelimit import client_ip
from .models import (
    ActionApproved,
    ActionApproveRequest,
    Alert,
    AshaReportResult,
    AuditEntry,
    ExplainRequest,
    Explanation,
    Health,
    Metrics,
    OrderCreate,
    OrderCreated,
    OrderRecord,
    ParsedOrder,
    RadarItem,
    SignalResponse,
    Telemetry,
)
from .parsing import MAX_MEDIA_BYTES, Upload
from .store import LocalStore

router = APIRouter(prefix="/api")


def ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def _upload(file: UploadFile | None) -> Upload | None:
    if file is None or not file.filename:
        return None
    data = file.file.read(MAX_MEDIA_BYTES + 1)  # never buffer more than the limit plus one byte
    if len(data) > MAX_MEDIA_BYTES:
        raise BadRequest("The file is larger than 20 MB. Please send a shorter note.", code="too_large")
    return Upload(data=data, filename=file.filename, content_type=file.content_type)


def throttle(request: Request) -> None:
    """Dependency for endpoints that can spend Gemini money: a per-IP sliding window (429 with Retry-After)."""
    ctx(request).limiter.check(client_ip(request))


# ------------------------------------------------------------------ reference


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    c = ctx(request)
    return Health(
        status="ok", model_fast=c.settings.model_fast[0], model_reason=c.settings.model_reason[0],
        storage=c.settings.storage, signal_backend=c.settings.signal_backend, offline=c.gemini.offline,
        version=__version__,
    )


@router.get("/catalogue")
def catalogue(request: Request) -> list[dict[str, Any]]:
    return ctx(request).ref.catalogue


@router.get("/groups")
def groups(request: Request) -> list[dict[str, Any]]:
    return ctx(request).ref.groups


@router.get("/pincodes")
def pincodes(request: Request) -> list[dict[str, Any]]:
    return ctx(request).ref.pincodes


@router.get("/chemists")
def chemists(request: Request) -> list[dict[str, Any]]:
    return ctx(request).ref.chemists


@router.get("/distributor")
def distributor(request: Request) -> dict[str, Any]:
    return ctx(request).ref.distributor


@router.get("/localities")
def localities(request: Request, pin: str | None = None) -> list[dict[str, Any]]:
    return [x for x in ctx(request).ref.localities if pin is None or x["pin"] == pin]


@router.get("/asha")
def asha_workers(request: Request) -> list[dict[str, Any]]:
    return ctx(request).ref.asha


# --------------------------------------------------------------------- orders


@router.get("/inbox")
def inbox(request: Request) -> list[dict[str, Any]]:
    return ctx(request).services.inbox()


def _media_response(request: Request, message_id: str) -> FileResponse:
    services = ctx(request).services
    item = services.find_message(message_id)
    if item is None or not item.get("media"):
        raise NotFound("Inbox media", message_id)
    path = services.message_media_path(item)
    if path is None:
        raise NotFound("Media file", item["media"])
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")


@router.get("/inbox/{message_id}/media")
def inbox_media(request: Request, message_id: str) -> FileResponse:
    return _media_response(request, message_id)


@router.get("/media/{message_id}")
def media(request: Request, message_id: str) -> FileResponse:
    """The audio or image of any inbox message (bundled sample or sent through the app), for replay."""
    return _media_response(request, message_id)


@router.post("/chemist/send", dependencies=[Depends(throttle)])
def chemist_send(
    request: Request,
    chemist_id: str = Form(...),
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
) -> dict[str, str]:
    """A chemist sends an order; it appears as a new message in the distributor inbox."""
    return ctx(request).services.send_from_chemist(chemist_id, _upload(file), text)


@router.post("/orders/parse", response_model=ParsedOrder, dependencies=[Depends(throttle)])
def orders_parse(
    request: Request,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    chemist_id: str | None = Form(default=None),
    message_id: str | None = Form(default=None),
) -> ParsedOrder:
    return ctx(request).services.parse_order(chemist_id, message_id, _upload(file), text)


@router.post("/orders", response_model=OrderCreated)
def orders_create(request: Request, body: OrderCreate) -> OrderCreated:
    return OrderCreated(order_id=ctx(request).services.create_order(body))


@router.get("/orders", response_model=list[OrderRecord])
def orders_list(request: Request, limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    return list(reversed(ctx(request).store.list_orders()))[:limit]


@router.get("/telemetry", response_model=Telemetry)
def telemetry(request: Request) -> dict[str, Any]:
    """Gemini usage: calls, models, fallbacks, latency, grounded sources, cache hits."""
    return ctx(request).gemini.telemetry()


@router.get("/ai/usage")
def ai_usage(request: Request) -> dict[str, Any]:
    """Every Gemini call, summed: tokens by type, cost in INR, per-job averages, cache and fallback rates, latency."""
    c = ctx(request)
    summary = c.gemini.ledger.summary()
    summary["limits"] = {"rate_limit_per_min_per_ip": c.settings.rate_limit_per_min,
                         "gemini_max_concurrency": c.settings.gemini_max_concurrency,
                         "max_upload_mb": MAX_MEDIA_BYTES // (1024 * 1024), "max_text_chars": c.settings.max_text_chars,
                         "image_resolution": c.settings.image_resolution, "offline": c.gemini.offline,
                         "model_fast": list(c.settings.model_fast), "model_reason": list(c.settings.model_reason)}
    return summary


@router.get("/audit", response_model=list[AuditEntry])
def audit(request: Request, limit: int = Query(default=200, ge=1, le=2000)) -> list[dict[str, Any]]:
    return list(reversed(ctx(request).store.list_audit()))[:limit]


# --------------------------------------------------------------------- signal


@router.get("/signal", response_model=SignalResponse)
def signal(request: Request, days: int = Query(default=30, ge=1, le=60)) -> SignalResponse:
    return ctx(request).signal.signal(days)


@router.get("/alerts", response_model=list[Alert])
def alerts(request: Request) -> list[Alert]:
    return ctx(request).signal.alerts()


@router.get("/alerts/{alert_id}", response_model=Alert)
def alert_detail(request: Request, alert_id: str) -> Alert:
    return ctx(request).signal.alert(alert_id)


@router.get("/radar", response_model=list[RadarItem])
def radar(request: Request) -> list[RadarItem]:
    return ctx(request).signal.radar()


# ------------------------------------------------- simulated history, back-test, weather


def _with_note(rows: list[dict[str, Any]], note: str) -> JSONResponse:
    """A list response whose honest data note travels in the X-Data-Note header (the body stays a plain list)."""
    return JSONResponse(rows, headers={"X-Data-Note": note.encode("ascii", "replace").decode()})


@router.get("/overview")
def overview(request: Request) -> dict[str, Any]:
    """Landing-page tiles: 30 days of simulated history plus live approvals. Never zero when data/extended exists."""
    return ctx(request).services.overview()


@router.get("/backtest")
def backtest(request: Request, alert_id: str | None = None) -> dict[str, Any]:
    """The SIMULATED back-test: pharmacy signal vs ASHA vs official dates. Optionally filtered to one alert."""
    return ctx(request).services.backtest(alert_id)


@router.get("/environment")
def environment(request: Request, pin: str = Query(min_length=6, max_length=6),
                days: int = Query(default=30, ge=1, le=90)) -> JSONResponse:
    """REAL Open-Meteo weather and air quality for the pin's nearest grid point."""
    rows, note = ctx(request).services.environment(pin, days)
    return _with_note(rows, note)


@router.get("/stockouts")
def stockouts(request: Request, days: int = Query(default=14, ge=1, le=90)) -> JSONResponse:
    rows, note = ctx(request).services.stockouts(days)
    return _with_note(rows, note)


@router.get("/asha/history")
def asha_history(request: Request, pin: str | None = Query(default=None, min_length=6, max_length=6),
                 days: int = Query(default=30, ge=1, le=90)) -> JSONResponse:
    rows, note = ctx(request).services.asha_history(pin, days)
    return _with_note(rows, note)


# ---------------------------------------------------------------------- agent


@router.post("/agent/explain", response_model=Explanation, dependencies=[Depends(throttle)])
def agent_explain(request: Request, body: ExplainRequest) -> Explanation:
    return ctx(request).agent.explain(body.alert_id, body.refresh)


@router.post("/actions/approve", response_model=ActionApproved)
def actions_approve(request: Request, body: ActionApproveRequest) -> ActionApproved:
    return ctx(request).services.approve_action(body)


# ----------------------------------------------------------------------- ASHA


@router.get("/asha/visits")
def asha_visits(request: Request, asha_id: str = Query(min_length=1)) -> list[dict[str, Any]]:
    return ctx(request).services.asha_visits(asha_id)


@router.post("/asha/report", response_model=AshaReportResult, dependencies=[Depends(throttle)])
def asha_report(
    request: Request,
    asha_id: str = Form(...),
    locality_id: str = Form(...),
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
) -> AshaReportResult:
    return ctx(request).services.asha_report(asha_id, locality_id, _upload(file), text)


# -------------------------------------------------------------------- metrics


@router.get("/metrics", response_model=Metrics)
def metrics(request: Request) -> Metrics:
    return ctx(request).services.metrics()


@router.post("/demo/reset")
def demo_reset(request: Request) -> dict[str, str]:
    """Clear approvals, orders, audit and ASHA reports so the demo can be rerun. Local store only."""
    c = ctx(request)
    if os.getenv("ALLOW_DEMO_RESET", "1") != "1" or not isinstance(c.store, LocalStore):
        raise AppError(403, "forbidden", "Resetting demo state is disabled.")
    c.store.reset()
    return {"status": "reset"}
