from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..dependencies import AppServices, CurrentUser, require_roles
from ..models import (
    AuditEventResponse,
    DashboardResponse,
    Role,
    TemplateResponse,
)
from ..serializers import document_list_item, job_item, review_item
from ..utils import json_load, utc_now
from .common import DOCUMENT_SELECT
from .reviews import REVIEW_SELECT


router = APIRouter(tags=["operations"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    services: AppServices, current_user: CurrentUser
) -> dict[str, object]:
    del current_user
    metrics_row = services.database.fetch_one(
        """
        SELECT
          COUNT(*) AS total_documents,
          SUM(CASE WHEN status IN ('COMPLETED','APPROVED') THEN 1 ELSE 0 END)
            AS ready_documents,
          SUM(CASE WHEN status = 'NEEDS_REVIEW' THEN 1 ELSE 0 END)
            AS pending_review,
          ROUND(COALESCE(AVG(confidence), 0) * 100, 1)
            AS average_confidence
        FROM documents
        """
    ) or {}
    active_count = services.database.fetch_one(
        """
        SELECT COUNT(*) AS count FROM jobs
        WHERE status IN ('QUEUED','PROCESSING')
        """
    )
    categories = services.database.fetch_all(
        """
        SELECT COALESCE(category, 'UNCLASSIFIED') AS category, COUNT(*) AS count
        FROM documents
        GROUP BY COALESCE(category, 'UNCLASSIFIED')
        ORDER BY count DESC
        """
    )
    recent = services.database.fetch_all(
        f"{DOCUMENT_SELECT} ORDER BY d.updated_at DESC LIMIT 6"
    )
    active_jobs = services.database.fetch_all(
        """
        SELECT j.*, d.title AS document_title
        FROM jobs j JOIN documents d ON d.id = j.document_id
        WHERE j.status IN ('QUEUED','PROCESSING')
        ORDER BY j.created_at
        LIMIT 6
        """
    )
    reviews = services.database.fetch_all(
        f"""
        {REVIEW_SELECT}
        WHERE r.status = 'PENDING'
        ORDER BY r.created_at
        LIMIT 5
        """
    )
    return {
        "metrics": {
            "totalDocuments": metrics_row.get("total_documents", 0),
            "readyDocuments": metrics_row.get("ready_documents", 0),
            "pendingReview": metrics_row.get("pending_review", 0),
            "activeJobs": (active_count or {}).get("count", 0),
            "averageConfidence": metrics_row.get(
                "average_confidence", 0
            ),
        },
        "category_distribution": categories,
        "recent_documents": [
            document_list_item(row) for row in recent
        ],
        "active_jobs": [job_item(row) for row in active_jobs],
        "review_queue": [review_item(row) for row in reviews],
        "generated_at": utc_now(),
    }


@router.get("/templates", response_model=list[TemplateResponse])
def templates(
    services: AppServices, current_user: CurrentUser
) -> list[dict[str, object]]:
    del current_user
    rows = services.database.fetch_all(
        """
        SELECT * FROM templates
        WHERE active = 1
        ORDER BY name
        """
    )
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "document_type": row["document_type"],
            "description": row["description"],
            "fields": json_load(row["fields_json"], []),
            "active": bool(row["active"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.get("/audit", response_model=list[AuditEventResponse])
def audit_events(
    services: AppServices,
    current_user: Annotated[
        dict, Depends(require_roles(Role.admin))
    ],
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
) -> list[dict[str, object]]:
    del current_user
    rows = services.database.fetch_all(
        """
        SELECT a.*, u.name AS actor_name, u.email AS actor_email
        FROM audit_events a
        LEFT JOIN users u ON u.id = a.actor_id
        ORDER BY a.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "id": row["id"],
            "actor_name": row["actor_name"],
            "actor_email": row["actor_email"],
            "action": row["action"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "metadata": json_load(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
