from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from ..database import Database
from ..serializers import document_list_item
from ..utils import new_id, utc_now


DOCUMENT_SELECT = """
SELECT d.*, u.name AS created_by_name
FROM documents d
JOIN users u ON u.id = d.created_by
"""


def get_document_or_404(
    database: Database, document_id: str
) -> dict[str, Any]:
    document = database.fetch_one(
        f"{DOCUMENT_SELECT} WHERE d.id = ?", (document_id,)
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document_not_found",
        )
    return document


def queue_job(
    database: Database,
    document_id: str,
    idempotency_key: str,
) -> tuple[str, bool]:
    existing = database.fetch_one(
        """
        SELECT id FROM jobs
        WHERE document_id = ? AND idempotency_key = ?
        """,
        (document_id, idempotency_key),
    )
    if existing:
        return existing["id"], True

    job_id = new_id("job")
    now = utc_now()
    database.execute(
        """
        INSERT INTO jobs (
          id,document_id,status,current_stage,progress,attempt,max_retries,
          idempotency_key,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            job_id,
            document_id,
            "QUEUED",
            "QUEUED",
            0,
            0,
            2,
            idempotency_key,
            now,
        ),
    )
    database.execute(
        """
        UPDATE documents
        SET status = 'QUEUED', updated_at = ?
        WHERE id = ?
        """,
        (now, document_id),
    )
    return job_id, False


def serialized_document(database: Database, document_id: str) -> dict[str, Any]:
    return document_list_item(get_document_or_404(database, document_id))
