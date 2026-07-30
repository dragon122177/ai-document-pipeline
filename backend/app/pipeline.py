from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from .audit import write_audit
from .database import Database
from .events import EventBroker
from .extractors import extract_file
from .intelligence import (
    DocumentIntelligenceProvider,
    redact_text,
    result_to_dict,
)
from .utils import json_dump, json_load, new_id, utc_now


LOGGER = logging.getLogger(__name__)


def split_chunks(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        end = min(len(normalized), cursor + size)
        if end < len(normalized):
            boundary = max(
                normalized.rfind("\n", cursor, end),
                normalized.rfind(". ", cursor, end),
                normalized.rfind(" ", cursor, end),
            )
            if boundary > cursor + size // 2:
                end = boundary + 1
        chunks.append(normalized[cursor:end].strip())
        if end >= len(normalized):
            break
        cursor = max(cursor + 1, end - overlap)
    return [chunk for chunk in chunks if chunk]


class PipelineProcessor:
    """Claims queued jobs and executes every document processing stage."""

    def __init__(
        self,
        database: Database,
        provider: DocumentIntelligenceProvider,
        broker: EventBroker,
        *,
        stage_delay: float = 0,
    ) -> None:
        self.database = database
        self.provider = provider
        self.broker = broker
        self.stage_delay = max(0, stage_delay)

    def process_next(self) -> bool:
        job_id = self._claim_next()
        if not job_id:
            return False
        self.process_job(job_id)
        return True

    def run_until_idle(self, max_jobs: int = 50) -> int:
        processed = 0
        while processed < max_jobs and self.process_next():
            processed += 1
        return processed

    def _claim_next(self) -> str | None:
        now = utc_now()
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM jobs
                WHERE status = 'QUEUED'
                ORDER BY created_at
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            job_id = row["id"]
            updated = connection.execute(
                """
                UPDATE jobs
                SET status = 'PROCESSING', current_stage = 'INGESTION',
                    progress = 2, attempt = attempt + 1,
                    started_at = COALESCE(started_at, ?), error_message = NULL
                WHERE id = ? AND status = 'QUEUED'
                """,
                (now, job_id),
            )
            if updated.rowcount != 1:
                return None
            connection.execute(
                """
                UPDATE documents
                SET status = 'PROCESSING', updated_at = ?
                WHERE id = (SELECT document_id FROM jobs WHERE id = ?)
                """,
                (now, job_id),
            )
        self._publish(job_id, "INGESTION", 2, "Pipeline worker claimed the job.")
        return job_id

    def process_job(self, job_id: str) -> None:
        job = self.database.fetch_one(
            """
            SELECT j.*, d.title, d.raw_text, d.storage_path, d.created_by,
                   d.page_count
            FROM jobs j
            JOIN documents d ON d.id = j.document_id
            WHERE j.id = ?
            """,
            (job_id,),
        )
        if not job:
            return
        try:
            document_id = job["document_id"]
            raw_text = job["raw_text"]
            page_count = job["page_count"]

            self._stage(job_id, "INGESTION", 12, "Source document loaded.")
            if not raw_text:
                if not job["storage_path"]:
                    raise ValueError("document_source_missing")
                extracted = extract_file(Path(job["storage_path"]))
                raw_text = extracted.text
                page_count = extracted.page_count
                self.database.execute(
                    """
                    UPDATE documents
                    SET raw_text = ?, page_count = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (raw_text, page_count, utc_now(), document_id),
                )
            if len(raw_text.strip()) < 20:
                raise ValueError("document_has_no_extractable_text")

            self._stage(
                job_id,
                "CLASSIFICATION",
                32,
                f"Classifying with {self.provider.name}.",
            )
            result = self.provider.analyze(raw_text, job["title"])
            analysis = result_to_dict(result)

            self._stage(
                job_id,
                "EXTRACTION",
                55,
                f"Extracted {len(result.entities)} entities and "
                f"{len(result.fields)} structured fields.",
            )
            redacted = redact_text(raw_text, result.entities)
            self._stage(
                job_id,
                "REDACTION",
                72,
                "Sensitive entities were redacted from the safe preview.",
            )

            chunks = split_chunks(raw_text)
            self._stage(
                job_id,
                "INDEXING",
                86,
                f"Prepared {len(chunks)} searchable text chunks.",
            )
            review_required = (
                result.confidence < 0.78
                or any(
                    risk.get("severity") == "HIGH"
                    for risk in result.risk_flags
                )
            )
            final_status = "NEEDS_REVIEW" if review_required else "COMPLETED"
            finished_at = utc_now()
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    UPDATE documents
                    SET status = ?, category = ?, language = ?, page_count = ?,
                        redacted_text = ?, summary = ?, keywords_json = ?,
                        entities_json = ?, fields_json = ?, risk_flags_json = ?,
                        confidence = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        final_status,
                        result.category,
                        result.language,
                        page_count,
                        redacted,
                        result.summary,
                        json_dump(result.keywords),
                        json_dump(result.entities),
                        json_dump(result.fields),
                        json_dump(result.risk_flags),
                        result.confidence,
                        finished_at,
                        document_id,
                    ),
                )
                connection.execute(
                    "DELETE FROM chunks WHERE document_id = ?", (document_id,)
                )
                connection.executemany(
                    """
                    INSERT INTO chunks
                      (id,document_id,position,text,token_estimate,created_at)
                    VALUES (?,?,?,?,?,?)
                    """,
                    [
                        (
                            new_id("chk"),
                            document_id,
                            position,
                            chunk,
                            max(1, len(chunk) // 4),
                            finished_at,
                        )
                        for position, chunk in enumerate(chunks)
                    ],
                )
                connection.execute(
                    "DELETE FROM document_fts WHERE document_id = ?",
                    (document_id,),
                )
                connection.execute(
                    """
                    INSERT INTO document_fts (document_id,title,content)
                    VALUES (?,?,?)
                    """,
                    (document_id, job["title"], raw_text),
                )
                if review_required:
                    reviewer = connection.execute(
                        """
                        SELECT id FROM users
                        WHERE role IN ('REVIEWER', 'ADMIN')
                        ORDER BY CASE role WHEN 'REVIEWER' THEN 0 ELSE 1 END
                        LIMIT 1
                        """
                    ).fetchone()
                    connection.execute(
                        """
                        INSERT INTO reviews
                          (id,document_id,status,assigned_to,created_at)
                        VALUES (?,?,?,?,?)
                        ON CONFLICT(document_id) DO UPDATE SET
                          status = 'PENDING',
                          assigned_to = excluded.assigned_to,
                          decided_by = NULL,
                          notes = NULL,
                          corrections_json = '{}',
                          created_at = excluded.created_at,
                          decided_at = NULL
                        """,
                        (
                            new_id("rev"),
                            document_id,
                            "PENDING",
                            reviewer["id"] if reviewer else None,
                            finished_at,
                        ),
                    )
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = ?, current_stage = 'VALIDATION', progress = 100,
                        finished_at = ?, error_message = NULL
                    WHERE id = ?
                    """,
                    (final_status, finished_at, job_id),
                )

            validation_message = (
                "Validation routed the document to human review."
                if review_required
                else "Validation passed; the document is ready."
            )
            self._publish(
                job_id,
                "VALIDATION",
                100,
                validation_message,
                level="WARNING" if review_required else "INFO",
            )
            write_audit(
                self.database,
                job["created_by"],
                "PIPELINE_COMPLETED",
                "document",
                document_id,
                {
                    "jobId": job_id,
                    "provider": self.provider.name,
                    "category": result.category,
                    "confidence": result.confidence,
                    "reviewRequired": review_required,
                    "analysisVersion": "2",
                },
            )
            self.broker.publish(
                "document.updated",
                {
                    "documentId": document_id,
                    "jobId": job_id,
                    "status": final_status,
                    "progress": 100,
                    "analysis": analysis,
                },
            )
        except Exception as error:
            LOGGER.exception("Document pipeline job %s failed", job_id)
            self._fail(job, error)

    def _stage(
        self, job_id: str, stage: str, progress: int, message: str
    ) -> None:
        self.database.execute(
            """
            UPDATE jobs SET current_stage = ?, progress = ?
            WHERE id = ?
            """,
            (stage, progress, job_id),
        )
        self._publish(job_id, stage, progress, message)
        if self.stage_delay:
            time.sleep(self.stage_delay)

    def _publish(
        self,
        job_id: str,
        stage: str,
        progress: int,
        message: str,
        *,
        level: str = "INFO",
    ) -> None:
        job = self.database.fetch_one(
            "SELECT document_id FROM jobs WHERE id = ?", (job_id,)
        )
        created_at = utc_now()
        self.database.execute(
            """
            INSERT INTO job_events
              (id,job_id,stage,level,message,progress,created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                new_id("evt"),
                job_id,
                stage,
                level,
                message,
                progress,
                created_at,
            ),
        )
        self.broker.publish(
            "job.progress",
            {
                "jobId": job_id,
                "documentId": job["document_id"] if job else None,
                "stage": stage,
                "progress": progress,
                "level": level,
                "message": message,
                "createdAt": created_at,
            },
        )

    def _fail(self, job: dict[str, Any], error: Exception) -> None:
        error_code = str(error)[:500] or error.__class__.__name__
        retry = int(job["attempt"]) < int(job["max_retries"])
        next_status = "QUEUED" if retry else "FAILED"
        document_status = "QUEUED" if retry else "FAILED"
        now = utc_now()
        self.database.execute(
            """
            UPDATE jobs
            SET status = ?, current_stage = 'FAILED',
                error_message = ?, finished_at = ?
            WHERE id = ?
            """,
            (next_status, error_code, None if retry else now, job["id"]),
        )
        self.database.execute(
            """
            UPDATE documents SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (document_status, now, job["document_id"]),
        )
        message = (
            f"Stage failed and will retry: {error_code}"
            if retry
            else f"Pipeline stopped after all retries: {error_code}"
        )
        self._publish(
            job["id"],
            "FAILED",
            0 if retry else 100,
            message,
            level="ERROR",
        )
        self.broker.publish(
            "document.updated",
            {
                "documentId": job["document_id"],
                "jobId": job["id"],
                "status": document_status,
                "error": error_code,
            },
        )


class PipelineWorker:
    def __init__(
        self, processor: PipelineProcessor, poll_interval: float = 0.5
    ) -> None:
        self.processor = processor
        self.poll_interval = max(0.05, poll_interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="docuflux-pipeline-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                if not self.processor.process_next():
                    self._stop.wait(self.poll_interval)
            except Exception:
                LOGGER.exception("Pipeline worker loop failed")
                self._stop.wait(self.poll_interval)
