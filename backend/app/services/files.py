from __future__ import annotations

import hashlib
import mimetypes
import shutil
import tarfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import UploadFile

from ..config import settings

ALLOWED_PAPER_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CODE_EXTENSIONS = {
    ".zip",
    ".tar",
    ".gz",
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
}
MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_EXPANDED_BYTES = 1024 * 1024 * 1024


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extension_for(name: str) -> str:
    return Path(name).suffix.lower()


def validate_upload_name(name: str) -> str:
    if not name or len(name) > 255 or "\x00" in name:
        raise ValueError("Invalid file name")
    if "/" in name or "\\" in name:
        raise ValueError("File name must not contain a path")
    return name


def file_metadata(name: str, content_type: str | None = None) -> dict[str, str]:
    original_name = validate_upload_name(name)
    extension = extension_for(original_name)
    return {
        "original_name": original_name,
        "extension": extension,
        "mime_type": content_type or guess_mime(Path(original_name)),
    }


async def _validate_paper_signature(upload: UploadFile, extension: str) -> None:
    header = await upload.read(8)
    await upload.seek(0)
    content_type = (upload.content_type or "").lower()
    if extension == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise ValueError("PDF file signature is invalid")
        if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
            raise ValueError("PDF MIME type is invalid")
    elif extension == ".docx":
        if not header.startswith(b"PK"):
            raise ValueError("DOCX file signature is invalid")
        allowed = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/octet-stream",
        }
        if content_type and content_type not in allowed:
            raise ValueError("DOCX MIME type is invalid")


def validate_size(path: Path) -> None:
    if path.stat().st_size > settings.max_upload_bytes:
        path.unlink(missing_ok=True)
        raise ValueError(f"File exceeds {settings.max_upload_bytes} bytes")


async def save_upload(upload: UploadFile, category: str, allowed_extensions: set[str]) -> tuple[Path, str, int]:
    original_name = validate_upload_name(upload.filename or "")
    extension = extension_for(original_name)
    if extension not in allowed_extensions:
        raise ValueError(f"Unsupported file extension: {extension or 'missing'}")
    if category == "uploads":
        await _validate_paper_signature(upload, extension)
    target_dir = settings.storage_path / category
    target = target_dir / f"{uuid4().hex}{extension}"
    with target.open("wb") as handle:
        total = 0
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_bytes:
                target.unlink(missing_ok=True)
                raise ValueError(f"File exceeds {settings.max_upload_bytes} bytes")
            handle.write(chunk)
    validate_size(target)
    return target, sha256_path(target), target.stat().st_size


def relative_storage_path(path: Path) -> str:
    return path.relative_to(settings.storage_path).as_posix()


def absolute_storage_path(relative_path: str) -> Path:
    target = (settings.storage_path / relative_path).resolve()
    root = settings.storage_path.resolve()
    if root not in target.parents and target != root:
        raise ValueError("Path escapes storage root")
    return target


def safe_extract_archive(archive: Path, target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as handle:
            members = handle.infolist()
            _validate_archive_quota(len(members), sum(member.file_size for member in members))
            for member in members:
                if member.is_dir():
                    continue
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Archive contains a symbolic link")
                destination = _archive_destination(target_dir, member.filename)
                _validate_archive_path(target_dir, destination)
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(target_dir)
            extracted = [target_dir / member.filename for member in members if not member.is_dir()]
    elif archive.suffix.lower() in {".tar", ".gz", ".tgz"}:
        with tarfile.open(archive) as handle:
            members = handle.getmembers()
            _validate_archive_quota(len(members), sum(member.size for member in members if member.isfile()))
            for member in members:
                if member.issym() or member.islnk():
                    raise ValueError("Archive contains a link entry")
                destination = _archive_destination(target_dir, member.name)
                _validate_archive_path(target_dir, destination)
            handle.extractall(target_dir, filter="data")
            extracted = [target_dir / member.name for member in members if member.isfile()]
    else:
        destination = target_dir / archive.name
        shutil.copy2(archive, destination)
        extracted = [destination]
    return extracted


def _validate_archive_path(target_dir: Path, destination: Path) -> None:
    root = target_dir.resolve()
    if root not in destination.parents and destination != root:
        raise ValueError("Archive contains a path traversal entry")


def _archive_destination(target_dir: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalized)
    if member_path.is_absolute() or (member_path.parts and ":" in member_path.parts[0]):
        raise ValueError("Archive contains an absolute path entry")
    return (target_dir / Path(*member_path.parts)).resolve()


def _validate_archive_quota(member_count: int, expanded_bytes: int) -> None:
    if member_count > MAX_ARCHIVE_MEMBERS:
        raise ValueError(f"Archive contains too many entries (limit: {MAX_ARCHIVE_MEMBERS})")
    if expanded_bytes > MAX_ARCHIVE_EXPANDED_BYTES:
        raise ValueError(
            f"Archive expands beyond the configured limit ({MAX_ARCHIVE_EXPANDED_BYTES} bytes)"
        )


def guess_mime(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"
