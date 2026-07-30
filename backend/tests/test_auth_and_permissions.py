from fastapi.testclient import TestClient

from .conftest import login


def test_login_returns_signed_session(client: TestClient) -> None:
    session = login(client, "analyst@docuflux.demo")

    assert session["user"]["role"] == "ANALYST"
    assert session["token"].count(".") == 2

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {session['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "analyst@docuflux.demo"


def test_invalid_credentials_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@docuflux.demo", "password": "incorrect"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"


def test_reviewer_cannot_ingest_documents(
    client: TestClient, reviewer_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/documents/text",
        headers=reviewer_headers,
        json={
            "title": "Restricted test",
            "content": "This document contains enough text to pass validation.",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_permissions"


def test_only_admin_can_read_audit_log(
    client: TestClient, analyst_headers: dict[str, str]
) -> None:
    response = client.get("/api/audit", headers=analyst_headers)
    assert response.status_code == 403
