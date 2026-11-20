"""Application wiring: one object that owns every long-lived component."""

from __future__ import annotations

from dataclasses import dataclass

from .agent import ExplainAgent
from .catalogue import Catalogue
from .config import Settings
from .gemini import GeminiClient
from .service import Services
from .signal import SignalService
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


def build_context(settings: Settings, store: Store | None = None) -> AppContext:
    """Load seed data and construct all components. Raises AppError if seed data is missing or invalid."""
    ref = Reference.load(settings.data_dir)
    store = store or build_store(settings)
    catalogue = Catalogue(ref.catalogue)
    gemini = GeminiClient(settings)
    signal = SignalService(ref, store, catalogue, settings)
    agent = ExplainAgent(gemini, signal, store, ref)
    services = Services(settings, ref, store, catalogue, gemini, signal)
    return AppContext(settings, ref, store, catalogue, gemini, signal, agent, services)
