"""Shared fixtures. Unit tests run on a tiny simulated dataset (tests/fixtures); the API smoke test and the
back-test can also run on the real seed data in data/ when it is present."""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.catalogue import Catalogue  # noqa: E402
from app.config import REPO_ROOT, Settings  # noqa: E402
from app.context import AppContext, build_context  # noqa: E402
from app.main import create_app  # noqa: E402
from app.store import LocalStore, Reference  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
REAL_DATA = REPO_ROOT / "data"
needs_real_data = pytest.mark.skipif(not (REAL_DATA / "history.csv").exists(), reason="seed data not generated yet")


def make_settings(tmp_path: Path, data_dir: Path, **overrides: Any) -> Settings:
    base = Settings(
        gemini_api_key="", demo_offline=True, data_dir=data_dir, frontend_dist=tmp_path / "no_dist",
        cache_dir=tmp_path / "cache", state_file=tmp_path / "state.json",
    )
    return dataclasses.replace(base, **overrides)


@pytest.fixture()
def fixture_ctx(tmp_path: Path) -> AppContext:
    return build_context(make_settings(tmp_path, FIXTURES), LocalStore(tmp_path / "state.json"))


@pytest.fixture()
def real_ctx(tmp_path: Path) -> AppContext:
    return build_context(make_settings(tmp_path, REAL_DATA), LocalStore(tmp_path / "state.json"))


@pytest.fixture()
def fixture_catalogue() -> Catalogue:
    return Catalogue(Reference.load(FIXTURES).catalogue)


@pytest.fixture()
def real_catalogue() -> Catalogue:
    return Catalogue(Reference.load(REAL_DATA).catalogue)


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    """API client on the real seed data in offline mode (DEMO_OFFLINE=1)."""
    app = create_app(make_settings(tmp_path, REAL_DATA), LocalStore(tmp_path / "state.json"))
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fixture_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(make_settings(tmp_path, FIXTURES), LocalStore(tmp_path / "state.json"))
    with TestClient(app) as c:
        yield c
