from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..audit import write_audit
from ..dependencies import AppServices, CurrentUser, require_roles
from ..models import JobResponse, Role
from ..serializers import job_item
from ..utils import utc_now


router = APIRouter(prefix="/jobs", tags=["pipeline jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs(
    services: AppServices,
    current_user: CurrentUser,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    del current_user
    where = "WHERE j.status = ?" if status_filter else ""
    parameters: tuple[object, ...] = (
        (status_filter.upper(), limit) if status_filter else (limit,)
    )
    rows = services.database.fetch_all(
        f"""
        SELECT j.*, d.title AS document_title
        FROM jobs j
        JOIN documents d ON d.id = j.document_id
        {where}
        ORDER BY j.created_at DESC
        LIMIT ?
        """,
        parameters,
    )
    return [job_item(row) for row in rows]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    services: AppServices,
    current_user: CurrentUser,
) -> dict[str, object]:
    del current_user
    row = services.database.fetch_one(
        """
        SELECT j.*, d.title AS document_title
        FROM jobs j
        JOIN documents d ON d.id = j.document_id
        WHERE j.id = ?
        """,
        (job_id,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job_not_found",
        )
    return job_item(row)


@router.post("/{job_id}/retry")
def retry_job(
    job_id: str,
    services: AppServices,
    current_user: Annotated[
        dict,
        Depends(require_roles(Role.admin, Role.analyst)),
    ],
) -> dict[str, str]:
    job = services.database.fetch_one(
        "SELECT * FROM jobs WHERE id = ?", (job_id,)
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job_not_found",
        )
    if job["status"] not in {"FAILED", "CANCELLED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="only_failed_or_cancelled_jobs_can_be_retried",
        )
    now = utc_now()
    services.database.execute(
        """
        UPDATE jobs
        SET status = 'QUEUED', current_stage = 'QUEUED', progress = 0,
            attempt = 0, error_message = NULL, started_at = NULL,
            finished_at = NULL
        WHERE id = ?
        """,
        (job_id,),
    )
    services.database.execute(
        """
        UPDATE documents SET status = 'QUEUED', updated_at = ?
        WHERE id = ?
        """,
        (now, job["document_id"]),
    )
    write_audit(
        services.database,
        current_user["id"],
        "JOB_RETRIED",
        "job",
        job_id,
        {"documentId": job["document_id"]},
    )
    return {"jobId": job_id, "status": "QUEUED"}
