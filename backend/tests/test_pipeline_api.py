from __future__ import annotations

from fastapi.testclient import TestClient


def test_text_ingestion_is_idempotent_and_processes(
    client: TestClient, analyst_headers: dict[str, str]
) -> None:
    payload = {
        "title": "Vertex invoice 400",
        "content": (
            "Invoice #VX-400. Invoice date July 29, 2026. "
            "Due date August 29, 2026. Total USD $2,450.00. "
            "Billing contact finance@vertex.example."
        ),
        "tags": ["finance", "vendor"],
        "idempotencyKey": "invoice-vx-400",
    }
    first = client.post(
        "/api/documents/text", headers=analyst_headers, json=payload
    )
    second = client.post(
        "/api/documents/text", headers=analyst_headers, json=payload
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["deduplicated"] is True
    assert first.json()["document"]["id"] == second.json()["document"]["id"]

    processed = client.app.state.services.processor.run_until_idle()
    assert processed == 1

    document_id = first.json()["document"]["id"]
    detail = client.get(
        f"/api/documents/{document_id}", headers=analyst_headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "COMPLETED"
    assert detail.json()["category"] == "INVOICE"
    assert detail.json()["fields"]["invoice_number"] == "VX-400"
    assert "[EMAIL_REDACTED]" in detail.json()["redactedText"]
    assert len(detail.json()["events"]) >= 6


def test_generic_document_routes_to_review_and_can_be_approved(
    client: TestClient,
    analyst_headers: dict[str, str],
    reviewer_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/documents/text",
        headers=analyst_headers,
        json={
            "title": "Operational note",
            "content": (
                "The blue team met today to discuss next steps for the "
                "internal migration and documented several open questions."
            ),
        },
    )
    document_id = created.json()["document"]["id"]
    client.app.state.services.processor.run_until_idle()

    detail = client.get(
        f"/api/documents/{document_id}", headers=reviewer_headers
    ).json()
    assert detail["status"] == "NEEDS_REVIEW"

    queue = client.get(
        "/api/reviews?status=PENDING", headers=reviewer_headers
    )
    review = next(
        item for item in queue.json() if item["documentId"] == document_id
    )
    decision = client.post(
        f"/api/reviews/{review['id']}/decision",
        headers=reviewer_headers,
        json={
            "decision": "APPROVED",
            "notes": "Verified against source.",
            "corrections": {"department": "Operations"},
        },
    )
    assert decision.status_code == 200

    approved = client.get(
        f"/api/documents/{document_id}", headers=reviewer_headers
    ).json()
    assert approved["status"] == "APPROVED"
    assert approved["fields"]["department"] == "Operations"


def test_supported_upload_is_searchable_and_exportable(
    client: TestClient, analyst_headers: dict[str, str]
) -> None:
    content = (
        b"Q3 2026 financial performance report. Revenue reached "
        b"$7.2 million with growth of 18.5% across the Pacific region."
    )
    response = client.post(
        "/api/documents/upload",
        headers=analyst_headers,
        files={"file": ("pacific-q3.txt", content, "text/plain")},
        data={"title": "Pacific Q3 report", "tags": "finance, quarterly"},
    )
    assert response.status_code == 200
    document_id = response.json()["document"]["id"]
    client.app.state.services.processor.run_until_idle()

    results = client.get(
        "/api/search?q=Pacific revenue", headers=analyst_headers
    )
    assert results.status_code == 200
    assert any(item["documentId"] == document_id for item in results.json())

    exported = client.get(
        f"/api/documents/{document_id}/export",
        headers=analyst_headers,
    )
    assert exported.status_code == 200
    assert exported.json()["schemaVersion"] == "1.0"
    assert "attachment" in exported.headers["content-disposition"]


def test_unsupported_upload_is_rejected(
    client: TestClient, analyst_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/documents/upload",
        headers=analyst_headers,
        files={"file": ("malware.exe", b"not really executable", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.json()["detail"].startswith("unsupported_file_type")


def test_dashboard_contains_operational_metrics(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/dashboard", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["totalDocuments"] >= 4
    assert payload["metrics"]["pendingReview"] >= 1
    assert len(payload["categoryDistribution"]) >= 4
