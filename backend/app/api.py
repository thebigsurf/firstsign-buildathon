"""HTTP routes under /api. Thin: every behaviour lives in service.py, signal.py, agent.py."""

from __future__ import annotations

import mimetypes
import os
from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse

from . import __version__
from .context import AppContext
from .errors import AppError, NotFound
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
from .parsing import Upload
from .store import LocalStore

router = APIRouter(prefix="/api")


def ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def _upload(file: UploadFile | None) -> Upload | None:
    if file is None or not file.filename:
        return None
    return Upload(data=file.file.read(), filename=file.filename, content_type=file.content_type)


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


@router.get("/inbox/{message_id}/media")
def inbox_media(request: Request, message_id: str) -> FileResponse:
    c = ctx(request)
    item = c.ref.inbox_item(message_id)
    if item is None or not item.get("media"):
        raise NotFound("Inbox media", message_id)
    path = c.ref.resolve_data_path(item["media"])
    if path is None:
        raise NotFound("Sample file", item["media"])
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")


@router.post("/orders/parse", response_model=ParsedOrder)
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


# ---------------------------------------------------------------------- agent


@router.post("/agent/explain", response_model=Explanation)
def agent_explain(request: Request, body: ExplainRequest) -> Explanation:
    return ctx(request).agent.explain(body.alert_id, body.refresh)


@router.post("/actions/approve", response_model=ActionApproved)
def actions_approve(request: Request, body: ActionApproveRequest) -> ActionApproved:
    return ctx(request).services.approve_action(body)


# ----------------------------------------------------------------------- ASHA


@router.get("/asha/visits")
def asha_visits(request: Request, asha_id: str = Query(min_length=1)) -> list[dict[str, Any]]:
    return ctx(request).services.asha_visits(asha_id)


@router.post("/asha/report", response_model=AshaReportResult)
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
