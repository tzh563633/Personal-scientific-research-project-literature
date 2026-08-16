from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path, PurePosixPath

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..models import FolderDocument, Job, Paper, PaperFile, PaperFolder, now
from ..worker import enqueue_paper
from .files import (
    ALLOWED_PAPER_EXTENSIONS,
    file_metadata,
    guess_mime,
    relative_storage_path,
    save_upload,
)


def validate_host_folder_path(value: str) -> str:
    path = value.strip()
    if not path or "\x00" in path:
        raise ValueError("Folder path is invalid")
    if not (
        re.match(r"^[A-Za-z]:[\\/]", path)
        or path.startswith("\\\\")
        or path.startswith("/")
    ):
        raise ValueError("Folder path must be absolute")
    return path


def validate_relative_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if (
        not normalized
        or candidate.is_absolute()
        or ":" in (candidate.parts[0] if candidate.parts else "")
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise ValueError("Relative file path is invalid")
    return candidate.as_posix()


def parse_modified_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("modified_at must be an ISO-8601 timestamp") from exc
    return parsed.replace(tzinfo=None)


async def ingest_agent_document(
    db: Session,
    folder: PaperFolder,
    upload: UploadFile,
    relative_path: str,
    submitted_sha256: str | None = None,
    modified_at: str | None = None,
) -> tuple[FolderDocument, bool]:
    safe_relative_path = validate_relative_path(relative_path)
    parsed_modified_at = parse_modified_at(modified_at)
    existing_document = (
        db.query(FolderDocument)
        .filter(
            FolderDocument.folder_id == folder.id,
            FolderDocument.relative_path == safe_relative_path,
        )
        .first()
    )
    saved_path: Path | None = None
    try:
        saved_path, sha256, size = await save_upload(upload, "uploads", ALLOWED_PAPER_EXTENSIONS)
        if submitted_sha256 and submitted_sha256.lower() != sha256:
            raise ValueError("Uploaded file checksum does not match scan metadata")

        if existing_document and existing_document.sha256 == sha256 and existing_document.paper_id:
            existing_document.size_bytes = size
            existing_document.modified_at = parsed_modified_at
            existing_document.import_status = "duplicate"
            existing_document.parse_status = (
                db.get(Paper, existing_document.paper_id).status
                if db.get(Paper, existing_document.paper_id)
                else "missing"
            )
            existing_document.error = None
            db.commit()
            db.refresh(existing_document)
            saved_path.unlink(missing_ok=True)
            return existing_document, True

        duplicate_file = db.query(PaperFile).filter(PaperFile.sha256 == sha256).first()
        if duplicate_file:
            if existing_document is None:
                existing_document = FolderDocument(
                    folder_id=folder.id,
                    relative_path=safe_relative_path,
                    file_name=Path(safe_relative_path).name,
                    size_bytes=size,
                    modified_at=parsed_modified_at,
                    sha256=sha256,
                )
                db.add(existing_document)
            existing_document.size_bytes = size
            existing_document.modified_at = parsed_modified_at
            existing_document.sha256 = sha256
            existing_document.paper_id = duplicate_file.paper_id
            existing_document.import_status = "duplicate"
            existing_document.parse_status = (
                db.get(Paper, duplicate_file.paper_id).status if db.get(Paper, duplicate_file.paper_id) else "missing"
            )
            existing_document.error = None
            db.commit()
            db.refresh(existing_document)
            saved_path.unlink(missing_ok=True)
            return existing_document, True

        metadata = file_metadata(upload.filename or Path(safe_relative_path).name, upload.content_type)
        paper = Paper(
            title=Path(metadata["original_name"]).stem,
            file_path=relative_storage_path(saved_path),
            status="pending",
        )
        db.add(paper)
        db.flush()
        db.add(
            PaperFile(
                paper_id=paper.id,
                kind="original",
                path=relative_storage_path(saved_path),
                sha256=sha256,
                size_bytes=size,
                original_name=metadata["original_name"],
                extension=metadata["extension"],
                mime_type=metadata["mime_type"] or guess_mime(saved_path),
            )
        )
        job = Job(kind="paper_processing", entity_id=paper.id, status="pending", message="Queued from folder scan")
        db.add(job)
        if existing_document is None:
            existing_document = FolderDocument(
                folder_id=folder.id,
                relative_path=safe_relative_path,
                file_name=Path(safe_relative_path).name,
                size_bytes=size,
                modified_at=parsed_modified_at,
                sha256=sha256,
            )
            db.add(existing_document)
        existing_document.size_bytes = size
        existing_document.modified_at = parsed_modified_at
        existing_document.sha256 = sha256
        existing_document.paper_id = paper.id
        existing_document.import_status = "imported"
        existing_document.parse_status = "pending"
        existing_document.error = None
        db.commit()
        db.refresh(job)
        existing_document.parse_job_id = job.id
        db.commit()
        enqueue_paper(db, job.id)
        db.refresh(job)
        existing_document.parse_status = (
            db.get(Paper, paper.id).status if db.get(Paper, paper.id) else job.status
        )
        db.commit()
        db.refresh(existing_document)
        return existing_document, False
    except Exception:
        if saved_path is not None:
            saved_path.unlink(missing_ok=True)
        db.rollback()
        raise
