from __future__ import annotations

from typing import Any

from .database import Database
from .utils import json_dump, new_id, utc_now


def write_audit(
    database: Database,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    database.execute(
        """
        INSERT INTO audit_events
          (id,actor_id,action,entity_type,entity_id,metadata_json,created_at)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            new_id("aud"),
            actor_id,
            action,
            entity_type,
            entity_id,
            json_dump(metadata or {}),
            utc_now(),
        ),
    )
