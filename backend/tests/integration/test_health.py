from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from app.api import health


def test_live(anon) -> None:
    assert anon.get("/health/live").json() == {"status": "ok"}


def test_ready_ok(anon) -> None:
    r = anon.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["checks"] == {"database": "ok", "redis": "ok"}


def test_ready_detecta_banco_indisponivel(anon, monkeypatch: pytest.MonkeyPatch) -> None:
    quebrado = create_engine(
        "postgresql+psycopg://x:y@127.0.0.1:1/nada", connect_args={"connect_timeout": 1}
    )
    monkeypatch.setattr(health, "get_engine", lambda: quebrado)
    r = anon.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["checks"]["database"] == "indisponivel"
