from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path


DEFAULT_MAX_FILE_BYTES = 200 * 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_pdf_folder(
    folder_path: str,
    recursive: bool = True,
    max_files: int = 500,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> tuple[list[dict], list[str]]:
    root = Path(folder_path).expanduser().resolve()
    if not root.exists():
        raise ValueError("Registered folder does not exist")
    if not root.is_dir():
        raise ValueError("Registered folder is not a directory")
    if max_files < 1:
        raise ValueError("max_files must be positive")

    candidates = root.rglob("*") if recursive else root.glob("*")
    files: list[dict] = []
    warnings: list[str] = []
    for candidate in sorted(candidates, key=lambda item: str(item).lower()):
        if len(files) >= max_files:
            warnings.append(f"Scan stopped at the configured file limit ({max_files})")
            break
        if candidate.is_symlink() or not candidate.is_file() or candidate.suffix.lower() != ".pdf":
            continue
        try:
            resolved = candidate.resolve()
            if root not in resolved.parents:
                warnings.append(f"Skipped file outside registered folder: {candidate.name}")
                continue
            stat = resolved.stat()
            if stat.st_size > max_file_bytes:
                warnings.append(f"Skipped oversized PDF: {candidate.name}")
                continue
            files.append(
                {
                    "path": str(resolved),
                    "relative_path": resolved.relative_to(root).as_posix(),
                    "file_name": resolved.name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "sha256": _sha256(resolved),
                }
            )
        except (OSError, ValueError) as exc:
            warnings.append(f"Skipped unreadable file {candidate.name}: {exc}")
    return files, warnings
