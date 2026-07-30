from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..audit import write_audit
from ..dependencies import AppServices, require_roles
from ..models import ReviewDecision, ReviewItem, Role
from ..serializers import review_item
from ..utils import json_dump, json_load, utc_now


router = APIRouter(prefix="/reviews", tags=["human review"])
Reviewer = Annotated[
    dict,
    Depends(require_roles(Role.admin, Role.reviewer)),
]


REVIEW_SELECT = """
SELECT r.*, d.title AS document_title, d.category, d.confidence,
       d.risk_flags_json, u.name AS assigned_to_name
FROM reviews r
JOIN documents d ON d.id = r.document_id
LEFT JOIN users u ON u.id = r.assigned_to
"""


@router.get("", response_model=list[ReviewItem])
def list_reviews(
    services: AppServices,
    current_user: Reviewer,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[dict[str, object]]:
    del current_user
    where = "WHERE r.status = ?" if status_filter else ""
    parameters = (status_filter.upper(),) if status_filter else ()
    rows = services.database.fetch_all(
        f"{REVIEW_SELECT} {where} ORDER BY r.created_at DESC",
        parameters,
    )
    return [review_item(row) for row in rows]


@router.post("/{review_id}/decision", response_model=ReviewItem)
def decide_review(
    review_id: str,
    payload: ReviewDecision,
    services: AppServices,
    current_user: Reviewer,
) -> dict[str, object]:
    review = services.database.fetch_one(
        f"{REVIEW_SELECT} WHERE r.id = ?", (review_id,)
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="review_not_found",
        )
    if review["status"] != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="review_already_decided",
        )

    now = utc_now()
    document = services.database.fetch_one(
        "SELECT fields_json FROM documents WHERE id = ?",
        (review["document_id"],),
    )
    existing_fields = json_load(
        document["fields_json"] if document else "{}", {}
    )
    updated_fields = {**existing_fields, **payload.corrections}
    with services.database.transaction() as connection:
        connection.execute(
            """
            UPDATE reviews
            SET status = ?, decided_by = ?, notes = ?,
                corrections_json = ?, decided_at = ?
            WHERE id = ?
            """,
            (
                payload.decision,
                current_user["id"],
                payload.notes.strip(),
                json_dump(payload.corrections),
                now,
                review_id,
            ),
        )
        connection.execute(
            """
            UPDATE documents
            SET status = ?, fields_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.decision,
                json_dump(updated_fields),
                now,
                review["document_id"],
            ),
        )
    write_audit(
        services.database,
        current_user["id"],
        f"DOCUMENT_{payload.decision}",
        "document",
        review["document_id"],
        {
            "reviewId": review_id,
            "correctionCount": len(payload.corrections),
        },
    )
    services.broker.publish(
        "review.decided",
        {
            "reviewId": review_id,
            "documentId": review["document_id"],
            "status": payload.decision,
            "decidedAt": now,
        },
    )
    updated = services.database.fetch_one(
        f"{REVIEW_SELECT} WHERE r.id = ?", (review_id,)
    )
    return review_item(updated)  # type: ignore[arg-type]
