from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from .utils import new_id, slugify


ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}
MIME_BY_EXTENSION = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class StorageError(ValueError):
    pass


@dataclass(slots=True)
class StoredFile:
    path: Path
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str


class LocalFileStorage:
    def __init__(self, directory: Path, max_bytes: int) -> None:
        self.directory = directory
        self.max_bytes = max_bytes
        directory.mkdir(parents=True, exist_ok=True)

    async def save(self, upload: UploadFile) -> StoredFile:
        original_name = Path(upload.filename or "document.txt").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise StorageError(
                f"unsupported_file_type:{suffix or 'missing-extension'}"
            )

        digest = hashlib.sha256()
        size = 0
        chunks: list[bytes] = []
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > self.max_bytes:
                raise StorageError("file_too_large")
            digest.update(chunk)
            chunks.append(chunk)

        if size == 0:
            raise StorageError("empty_file")

        safe_stem = slugify(Path(original_name).stem)[:80]
        stored_name = f"{safe_stem}-{new_id('bin')[4:12]}{suffix}"
        destination = self.directory / stored_name
        destination.write_bytes(b"".join(chunks))

        return StoredFile(
            path=destination,
            file_name=original_name,
            mime_type=MIME_BY_EXTENSION.get(
                suffix, upload.content_type or "application/octet-stream"
            ),
            size_bytes=size,
            sha256=digest.hexdigest(),
        )

    def remove(self, path: Path | None) -> None:
        if path and path.exists() and path.is_file():
            path.unlink()
