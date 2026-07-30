from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse

from ..audit import write_audit
from ..dependencies import (
    AppServices,
    CurrentUser,
    require_roles,
)
from ..models import (
    DocumentCreateResponse,
    DocumentDetail,
    DocumentListItem,
    Role,
    TextDocumentCreate,
)
from ..serializers import document_detail, document_list_item
from ..storage import StorageError
from ..utils import json_dump, json_load, new_id, slugify, utc_now
from .common import DOCUMENT_SELECT, get_document_or_404, queue_job


router = APIRouter(prefix="/documents", tags=["documents"])
Writer = Annotated[
    dict,
    Depends(require_roles(Role.admin, Role.analyst)),
]


def _parse_tags(value: str) -> list[str]:
    unique: list[str] = []
    for tag in value.replace(";", ",").split(","):
        normalized = tag.strip().lower()
        if normalized and normalized not in unique:
            unique.append(normalized[:32])
    return unique[:12]


def _duplicate_response(
    services: AppServices,
    sha256: str,
    user_id: str,
    idempotency_key: str,
) -> dict[str, object] | None:
    existing = services.database.fetch_one(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.sha256 = ? AND d.created_by = ?
        ORDER BY d.created_at DESC
        LIMIT 1
        """,
        (sha256, user_id),
    )
    if not existing:
        return None
    latest_job = services.database.fetch_one(
        """
        SELECT id FROM jobs
        WHERE document_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (existing["id"],),
    )
    if latest_job:
        job_id = latest_job["id"]
    else:
        job_id, _ = queue_job(
            services.database, existing["id"], idempotency_key
        )
    return {
        "document": document_list_item(existing),
        "job_id": job_id,
        "deduplicated": True,
    }


@router.post("/text", response_model=DocumentCreateResponse)
def create_text_document(
    payload: TextDocumentCreate,
    services: AppServices,
    current_user: Writer,
) -> dict[str, object]:
    normalized = payload.content.strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    idempotency_key = payload.idempotency_key or f"sha256:{digest}"
    duplicate = _duplicate_response(
        services, digest, current_user["id"], idempotency_key
    )
    if duplicate:
        return duplicate

    document_id = new_id("doc")
    now = utc_now()
    file_name = f"{slugify(payload.title)}.txt"
    with services.database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO documents (
              id,title,file_name,mime_type,size_bytes,sha256,storage_path,status,
              raw_text,tags_json,created_by,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                document_id,
                payload.title.strip(),
                file_name,
                "text/plain",
                len(normalized.encode("utf-8")),
                digest,
                None,
                "QUEUED",
                normalized,
                json_dump(payload.tags),
                current_user["id"],
                now,
                now,
            ),
        )
    job_id, _ = queue_job(
        services.database, document_id, idempotency_key
    )
    write_audit(
        services.database,
        current_user["id"],
        "DOCUMENT_CREATED",
        "document",
        document_id,
        {"source": "text", "jobId": job_id},
    )
    return {
        "document": document_list_item(
            get_document_or_404(services.database, document_id)
        ),
        "job_id": job_id,
        "deduplicated": False,
    }


@router.post("/upload", response_model=DocumentCreateResponse)
async def upload_document(
    services: AppServices,
    current_user: Writer,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",
    idempotency_key: Annotated[str, Form()] = "",
) -> dict[str, object]:
    try:
        stored = await services.storage.save(file)
    except StorageError as error:
        reason = str(error)
        code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if reason == "file_too_large"
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=code, detail=reason) from error

    resolved_key = idempotency_key.strip() or f"sha256:{stored.sha256}"
    duplicate = _duplicate_response(
        services, stored.sha256, current_user["id"], resolved_key
    )
    if duplicate:
        services.storage.remove(stored.path)
        return duplicate

    resolved_title = title.strip() or Path(stored.file_name).stem
    if len(resolved_title) < 3 or len(resolved_title) > 160:
        services.storage.remove(stored.path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="title_must_be_between_3_and_160_characters",
        )

    document_id = new_id("doc")
    now = utc_now()
    try:
        services.database.execute(
            """
            INSERT INTO documents (
              id,title,file_name,mime_type,size_bytes,sha256,storage_path,status,
              tags_json,created_by,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                document_id,
                resolved_title,
                stored.file_name,
                stored.mime_type,
                stored.size_bytes,
                stored.sha256,
                str(stored.path),
                "QUEUED",
                json_dump(_parse_tags(tags)),
                current_user["id"],
                now,
                now,
            ),
        )
        job_id, _ = queue_job(
            services.database, document_id, resolved_key
        )
    except Exception:
        services.storage.remove(stored.path)
        raise

    write_audit(
        services.database,
        current_user["id"],
        "DOCUMENT_UPLOADED",
        "document",
        document_id,
        {
            "fileName": stored.file_name,
            "sizeBytes": stored.size_bytes,
            "jobId": job_id,
        },
    )
    return {
        "document": document_list_item(
            get_document_or_404(services.database, document_id)
        ),
        "job_id": job_id,
        "deduplicated": False,
    }


@router.get("", response_model=list[DocumentListItem])
def list_documents(
    services: AppServices,
    current_user: CurrentUser,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    category: str | None = None,
    query: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    del current_user
    clauses: list[str] = []
    parameters: list[object] = []
    if status_filter:
        clauses.append("d.status = ?")
        parameters.append(status_filter.upper())
    if category:
        clauses.append("d.category = ?")
        parameters.append(category.upper())
    if query:
        clauses.append("(lower(d.title) LIKE ? OR lower(d.file_name) LIKE ?)")
        needle = f"%{query.strip().lower()}%"
        parameters.extend([needle, needle])
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = services.database.fetch_all(
        f"{DOCUMENT_SELECT}{where} ORDER BY d.updated_at DESC LIMIT ?",
        (*parameters, limit),
    )
    return [document_list_item(row) for row in rows]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    services: AppServices,
    current_user: CurrentUser,
) -> dict[str, object]:
    del current_user
    detail = document_detail(services.database, document_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document_not_found",
        )
    return detail


@router.post("/{document_id}/process")
def process_document(
    document_id: str,
    services: AppServices,
    current_user: Writer,
) -> dict[str, object]:
    document = get_document_or_404(services.database, document_id)
    active = services.database.fetch_one(
        """
        SELECT id,status FROM jobs
        WHERE document_id = ? AND status IN ('QUEUED','PROCESSING')
        ORDER BY created_at DESC LIMIT 1
        """,
        (document_id,),
    )
    if active:
        return {
            "jobId": active["id"],
            "status": active["status"],
            "deduplicated": True,
        }
    key = f"reprocess:{utc_now()}"
    job_id, _ = queue_job(services.database, document_id, key)
    write_audit(
        services.database,
        current_user["id"],
        "DOCUMENT_REPROCESS_REQUESTED",
        "document",
        document_id,
        {"jobId": job_id, "previousStatus": document["status"]},
    )
    return {"jobId": job_id, "status": "QUEUED", "deduplicated": False}


@router.get("/{document_id}/export")
def export_document(
    document_id: str,
    services: AppServices,
    current_user: CurrentUser,
) -> JSONResponse:
    detail = document_detail(services.database, document_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document_not_found",
        )
    payload = {
        "schemaVersion": "1.0",
        "exportedAt": utc_now(),
        "document": {
            "id": detail["id"],
            "title": detail["title"],
            "fileName": detail["file_name"],
            "status": detail["status"],
            "category": detail["category"],
            "language": detail["language"],
            "summary": detail["summary"],
            "keywords": detail["keywords"],
            "fields": detail["fields"],
            "entities": detail["entities"],
            "riskFlags": detail["risk_flags"],
            "confidence": detail["confidence"],
            "redactedText": detail["redacted_text"],
        },
    }
    write_audit(
        services.database,
        current_user["id"],
        "DOCUMENT_EXPORTED",
        "document",
        document_id,
    )
    response = JSONResponse(payload)
    safe_name = slugify(detail["title"])
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{safe_name}-analysis.json"'
    )
    return response
