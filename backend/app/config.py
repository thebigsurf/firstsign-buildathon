"""Environment-driven settings. Nothing here prints or logs the API key."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


# Time-saving assumptions for the metrics page (estimates, labelled as such in the UI).
MANUAL_MIN_PER_10_LINES = 3.0
REVIEW_MIN_PER_10_LINES = 0.5


def _chain(env_name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(env_name, default)
    return tuple(m.strip() for m in raw.split(",") if m.strip())


def _flag(env_name: str, default: bool = False) -> bool:
    return os.getenv(env_name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """All runtime configuration, resolved once at start-up."""

    gemini_api_key: str = field(default="", repr=False)
    model_fast: tuple[str, ...] = ("gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite")
    model_reason: tuple[str, ...] = ("gemini-4-hydrogen", "gemini-3.5-flash", "gemini-3.1-flash-lite")
    demo_offline: bool = False
    storage: str = "local"
    signal_backend: str = "local"
    data_dir: Path = REPO_ROOT / "data"
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"
    cache_dir: Path = BACKEND_DIR / ".cache"
    state_file: Path = BACKEND_DIR / ".state" / "state.json"
    gemini_timeout_s: float = 90.0
    gemini_max_attempts: int = 3
    gemini_deadline_s: float = 150.0  # total budget across the whole fallback chain for one request
    gemini_max_concurrency: int = 4
    parse_deadline_s: float = 25.0  # interactive parse: after this, fall back to the labelled sample and warm in background
    warm_deadline_s: float = 150.0  # background warm after a fallback may take as long as it needs
    google_cloud_project: str = "firstsign-buildathon"
    google_cloud_region: str = "asia-south1"
    bq_dataset: str = "firstsign"
    demo_as_of: str = ""  # optional ISO date override for "today"
    cover_days: int = 5   # stock radar: days of cover to suggest
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @property
    def offline(self) -> bool:
        """Mock mode: forced by DEMO_OFFLINE=1 or implied by a missing key."""
        return self.demo_offline or not self.gemini_api_key

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(REPO_ROOT / ".env")
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            model_fast=_chain("GEMINI_MODEL_FAST", "gemini-3.5-flash,gemini-3.8-flash,gemini-3.1-flash-lite"),
            model_reason=_chain("GEMINI_MODEL_REASON", "gemini-4-hydrogen,gemini-3.5-flash,gemini-3.1-flash-lite"),
            demo_offline=_flag("DEMO_OFFLINE"),
            storage=os.getenv("STORAGE", "local").strip().lower(),
            signal_backend=os.getenv("SIGNAL_BACKEND", "local").strip().lower(),
            data_dir=Path(os.getenv("DATA_DIR", str(REPO_ROOT / "data"))),
            frontend_dist=Path(os.getenv("FRONTEND_DIST", str(REPO_ROOT / "frontend" / "dist"))),
            cache_dir=Path(os.getenv("CACHE_DIR", str(BACKEND_DIR / ".cache"))),
            state_file=Path(os.getenv("STATE_FILE", str(BACKEND_DIR / ".state" / "state.json"))),
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", "firstsign-buildathon"),
            google_cloud_region=os.getenv("GOOGLE_CLOUD_REGION", "asia-south1"),
            bq_dataset=os.getenv("BQ_DATASET", "firstsign"),
            demo_as_of=os.getenv("DEMO_AS_OF", "").strip(),
            parse_deadline_s=float(os.getenv("PARSE_DEADLINE_S", "25")),
            warm_deadline_s=float(os.getenv("WARM_DEADLINE_S", "150")),
            cover_days=int(os.getenv("RADAR_COVER_DAYS", "5")),
        )
