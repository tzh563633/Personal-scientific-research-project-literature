from __future__ import annotations

import shutil
import os
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from ..config import settings


def create_backup() -> Path:
    storage_root = settings.storage_path.resolve()
    backup_root = Path(settings.backup_root).resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_root / f"backup-{stamp}"
    target.mkdir()
    if settings.database_url.startswith("sqlite:///"):
        source = Path(settings.database_url.removeprefix("sqlite:///"))
        if source.exists():
            shutil.copy2(source, target / "database.sqlite")
    elif settings.database_url.startswith(("postgresql://", "postgresql+")):
        _dump_postgres(target / "database.dump")
    else:
        raise ValueError("Unsupported database URL for backup")
    _archive_storage(storage_root, backup_root, target / "storage.zip")
    _prune_backups(backup_root)
    return target


def _dump_postgres(destination: Path) -> None:
    url = make_url(settings.database_url)
    pg_dump = shutil.which("pg_dump16") or shutil.which("pg_dump")
    if not pg_dump:
        raise RuntimeError("PostgreSQL 16 pg_dump is required for PostgreSQL backups")
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    command = [
        pg_dump,
        "--format=custom",
        f"--file={destination}",
        f"--host={url.host or 'localhost'}",
        f"--port={url.port or 5432}",
        f"--username={url.username or ''}",
        url.database or "",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=300, env=env)


def _archive_storage(storage_root: Path, backup_root: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in storage_root.rglob("*"):
            if not path.is_file():
                continue
            if backup_root == path or backup_root in path.parents:
                continue
            archive.write(path, path.relative_to(storage_root).as_posix())


def _prune_backups(backup_root: Path) -> None:
    cutoff = datetime.now().timestamp() - settings.backup_retention_days * 86400
    for path in backup_root.iterdir():
        if path.stat().st_mtime >= cutoff:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
