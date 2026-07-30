from __future__ import annotations

from typing import Any

from .database import Database
from .utils import json_load


def document_list_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "file_name": row["file_name"],
        "mime_type": row["mime_type"],
        "size_bytes": row["size_bytes"],
        "status": row["status"],
        "category": row.get("category"),
        "language": row.get("language"),
        "page_count": row["page_count"],
        "confidence": row.get("confidence"),
        "tags": json_load(row.get("tags_json"), []),
        "created_by_name": row.get("created_by_name", "Unknown"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def job_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "document_title": row.get("document_title", "Untitled document"),
        "status": row["status"],
        "current_stage": row["current_stage"],
        "progress": row["progress"],
        "attempt": row["attempt"],
        "max_retries": row["max_retries"],
        "error_message": row.get("error_message"),
        "created_at": row["created_at"],
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
    }


def review_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "document_title": row.get("document_title", "Untitled document"),
        "category": row.get("category"),
        "confidence": row.get("confidence"),
        "status": row["status"],
        "assigned_to_name": row.get("assigned_to_name"),
        "notes": row.get("notes"),
        "corrections": json_load(row.get("corrections_json"), {}),
        "risk_flags": json_load(row.get("risk_flags_json"), []),
        "created_at": row["created_at"],
        "decided_at": row.get("decided_at"),
    }


def document_detail(database: Database, document_id: str) -> dict[str, Any] | None:
    row = database.fetch_one(
        """
        SELECT d.*, u.name AS created_by_name
        FROM documents d
        JOIN users u ON u.id = d.created_by
        WHERE d.id = ?
        """,
        (document_id,),
    )
    if not row:
        return None

    latest_job = database.fetch_one(
        """
        SELECT j.*, d.title AS document_title
        FROM jobs j
        JOIN documents d ON d.id = j.document_id
        WHERE j.document_id = ?
        ORDER BY j.created_at DESC
        LIMIT 1
        """,
        (document_id,),
    )
    review = database.fetch_one(
        """
        SELECT r.*, d.title AS document_title, d.category, d.confidence,
               d.risk_flags_json, u.name AS assigned_to_name
        FROM reviews r
        JOIN documents d ON d.id = r.document_id
        LEFT JOIN users u ON u.id = r.assigned_to
        WHERE r.document_id = ?
        """,
        (document_id,),
    )
    chunks = database.fetch_all(
        """
        SELECT id, position, text, token_estimate
        FROM chunks
        WHERE document_id = ?
        ORDER BY position
        LIMIT 12
        """,
        (document_id,),
    )
    events: list[dict[str, Any]] = []
    if latest_job:
        events = database.fetch_all(
            """
            SELECT id, stage, level, message, progress, created_at
            FROM job_events
            WHERE job_id = ?
            ORDER BY created_at, rowid
            """,
            (latest_job["id"],),
        )

    return {
        **document_list_item(row),
        "sha256": row["sha256"],
        "raw_text": row["raw_text"],
        "redacted_text": row["redacted_text"],
        "summary": row["summary"],
        "keywords": json_load(row["keywords_json"], []),
        "entities": json_load(row["entities_json"], []),
        "fields": json_load(row["fields_json"], {}),
        "risk_flags": json_load(row["risk_flags_json"], []),
        "job": job_item(latest_job) if latest_job else None,
        "review": review_item(review) if review else None,
        "chunks": chunks,
        "events": events,
    }
