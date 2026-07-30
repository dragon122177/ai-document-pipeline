from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        app_env="test",
        token_secret="test-secret-with-enough-entropy",
        database_path=tmp_path / "docuflux-test.db",
        upload_directory=tmp_path / "uploads",
        worker_enabled=False,
        worker_poll_interval=0.05,
        pipeline_stage_delay=0,
    )
    app = create_app(settings, start_worker=False)
    with TestClient(app) as test_client:
        yield test_client


def login(
    client: TestClient,
    email: str = "admin@docuflux.demo",
) -> dict[str, Any]:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "demo1234"},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    session = login(client)
    return {"Authorization": f"Bearer {session['token']}"}


@pytest.fixture()
def analyst_headers(client: TestClient) -> dict[str, str]:
    session = login(client, "analyst@docuflux.demo")
    return {"Authorization": f"Bearer {session['token']}"}


@pytest.fixture()
def reviewer_headers(client: TestClient) -> dict[str, str]:
    session = login(client, "reviewer@docuflux.demo")
    return {"Authorization": f"Bearer {session['token']}"}
