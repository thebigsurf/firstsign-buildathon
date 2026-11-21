"""Application wiring: one object that owns every long-lived component."""

from __future__ import annotations

from dataclasses import dataclass

from .agent import ExplainAgent
from .catalogue import Catalogue
from .config import Settings
from .extended import ExtendedData
from .gemini import GeminiClient
from .service import Services
from .ratelimit import RateLimiter
from .signal import SignalService
from .usage import UsageLedger
from .store import Reference, Store, build_store


@dataclass
class AppContext:
    settings: Settings
    ref: Reference
    store: Store
    catalogue: Catalogue
    gemini: GeminiClient
    signal: SignalService
    agent: ExplainAgent
    services: Services
    extended: ExtendedData
    limiter: RateLimiter


def build_context(settings: Settings, store: Store | None = None) -> AppContext:
    """Load seed data and construct all components. Raises AppError if seed data is missing or invalid."""
    ref = Reference.load(settings.data_dir)
    store = store or build_store(settings)
    catalogue = Catalogue(ref.catalogue)
    gemini = GeminiClient(settings, UsageLedger(store, usd_inr=settings.usd_inr, budget_inr=settings.daily_budget_inr))
    extended = ExtendedData(settings)
    signal = SignalService(ref, store, catalogue, settings, extended)
    agent = ExplainAgent(gemini, signal, store, ref)
    services = Services(settings, ref, store, catalogue, gemini, signal, extended)
    return AppContext(settings, ref, store, catalogue, gemini, signal, agent, services, extended, RateLimiter(settings.rate_limit_per_min))
