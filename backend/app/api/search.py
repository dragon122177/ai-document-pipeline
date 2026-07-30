from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Query

from ..dependencies import AppServices, CurrentUser
from ..models import SearchResult


router = APIRouter(prefix="/search", tags=["semantic-ready search"])


@router.get("", response_model=list[SearchResult])
def search_documents(
    services: AppServices,
    current_user: CurrentUser,
    query: Annotated[str, Query(alias="q", min_length=2, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[dict[str, object]]:
    del current_user
    terms = re.findall(r"[\w-]{2,}", query.lower(), flags=re.UNICODE)[:8]
    if not terms:
        return []
    match_query = " AND ".join(f'"{term}"*' for term in terms)
    rows = services.database.fetch_all(
        """
        SELECT d.id AS document_id, d.title, d.category, d.status,
               snippet(document_fts, 2, '<mark>', '</mark>', ' … ', 22)
                 AS snippet,
               bm25(document_fts, 2.0, 1.0) AS score,
               d.updated_at
        FROM document_fts
        JOIN documents d ON d.id = document_fts.document_id
        WHERE document_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (match_query, limit),
    )
    return [
        {
            "document_id": row["document_id"],
            "title": row["title"],
            "category": row["category"],
            "status": row["status"],
            "snippet": row["snippet"] or row["title"],
            "rank": round(abs(float(row["score"])), 4),
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]
