from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import CodeProject
from ..schemas import (
    CodeInspectionReportResponse,
    DependencyAnalysisResponse,
    DependencyResponse,
    FileTreeEntryResponse,
    FilePreviewResponse,
    FileTreeResponse,
    GitCommitResponse,
    GitCommitDetailResponse,
    GitDiffResponse,
    GitStatusResponse,
)
from .files import absolute_storage_path

_SKIPPED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}
_MAX_SCAN_FILES = 10_000
_MAX_DEPENDENCIES = 5_000
_MAX_DIFF_BYTES = 200_000
_MAX_TREE_ENTRIES = 500
_MAX_PREVIEW_BYTES = 64 * 1024
_REQUIREMENTS_FILES = re.compile(r"^requirements(?:[-_.].*)?\.txt$", re.IGNORECASE)
_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*([^\s'\";]+)"),
    re.compile(r"(?i)\b(bearer)\s+([A-Za-z0-9._~+/-]{12,})"),
]


def project_directory(project: CodeProject) -> Path:
    path = absolute_storage_path(project.local_path)
    if not path.is_dir():
        raise ValueError("Project directory is missing")
    return path


def list_project_tree(
    project: CodeProject,
    relative_path: str | None = None,
    limit: int = _MAX_TREE_ENTRIES,
) -> FileTreeResponse:
    root = project_directory(project)
    normalized = ""
    target = root
    if relative_path:
        normalized = _safe_relative_path(root, relative_path)
        target = root / Path(*normalized.split("/"))
    if not target.exists() or not target.is_dir():
        raise ValueError("Project tree path is not a directory")
    entries: list[FileTreeEntryResponse] = []
    warnings: list[str] = []
    truncated = False
    for child in sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
        if len(entries) >= limit:
            truncated = True
            break
        if child.name in _SKIPPED_DIRECTORIES:
            continue
        if child.is_symlink():
            warnings.append(f"Skipped symlink: {child.name}")
            continue
        try:
            stat = child.stat()
        except OSError as exc:
            warnings.append(f"{child.name}: {exc}")
            continue
        entries.append(
            FileTreeEntryResponse(
                name=child.name,
                path=child.relative_to(root).as_posix(),
                kind="directory" if child.is_dir() else "file",
                size_bytes=None if child.is_dir() else stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return FileTreeResponse(
        project_id=project.id,
        path=normalized,
        entries=entries,
        truncated=truncated,
        warnings=warnings,
    )


def preview_project_file(
    project: CodeProject,
    relative_path: str,
    max_bytes: int = _MAX_PREVIEW_BYTES,
) -> FilePreviewResponse:
    root = project_directory(project)
    safe_path = _safe_relative_path(root, relative_path)
    target = root / Path(*safe_path.split("/"))
    if not target.exists() or not target.is_file():
        raise ValueError("Project preview path is not a file")
    if target.is_symlink():
        raise ValueError("Project preview path cannot be a symbolic link")
    size = target.stat().st_size
    with target.open("rb") as handle:
        sample = handle.read(min(max_bytes + 1, max_bytes + 4096))
    if _looks_binary(sample[:4096]):
        raise ValueError("Binary files cannot be previewed")
    truncated = len(sample) > max_bytes or size > max_bytes
    text = sample[:max_bytes].decode("utf-8-sig", errors="replace")
    redacted_text, redacted = _redact_secrets(text)
    return FilePreviewResponse(
        project_id=project.id,
        path=safe_path,
        size_bytes=size,
        content=redacted_text,
        truncated=truncated,
        redacted=redacted,
    )


def generate_code_inspection_report(project: CodeProject) -> CodeInspectionReportResponse:
    warnings: list[str] = []
    status = git_status(project)
    commits: list[GitCommitResponse] = []
    try:
        commits = git_commits(project, limit=5)
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        warnings.append(f"Git commits: {exc}")
    try:
        dependencies = analyze_dependencies(project)
    except (ValueError, OSError) as exc:
        dependencies = DependencyAnalysisResponse(project_id=project.id, scanned_files=0)
        warnings.append(f"Dependencies: {exc}")
    try:
        tree = list_project_tree(project, limit=80)
    except (ValueError, OSError) as exc:
        tree = FileTreeResponse(project_id=project.id)
        warnings.append(f"File tree: {exc}")

    lines = [
        f"# Code Inspection Report: {project.name}",
        "",
        f"- Project ID: {project.id}",
        f"- Generated at: {datetime.utcnow().isoformat(timespec='seconds')}Z",
        f"- Storage path: `{project.local_path}`",
        "",
        "## Git",
        "",
    ]
    if status.available:
        lines.extend(
            [
                f"- Branch: `{status.branch or 'unknown'}`",
                f"- Dirty: `{status.is_dirty}`",
                f"- Ahead/behind: `{status.ahead}/{status.behind}`",
                f"- Changed files: {len(status.changed_files)}",
            ]
        )
    else:
        lines.append(f"- Git unavailable: {status.error or 'unknown'}")
    if commits:
        lines.extend(["", "### Recent Commits", ""])
        for commit in commits:
            lines.append(f"- `{commit.commit_hash[:10]}` {commit.subject} ({commit.author})")

    lines.extend(
        [
            "",
            "## Dependencies",
            "",
            f"- Scanned files: {dependencies.scanned_files}",
            f"- Manifests: {len(dependencies.manifests)}",
            f"- Dependencies: {len(dependencies.dependencies)}",
            f"- High risk: {dependencies.high_risk_count}",
            f"- Review: {dependencies.review_count}",
        ]
    )
    for dependency in dependencies.dependencies[:50]:
        license_text = f", license={dependency.license}" if dependency.license else ""
        source = f", source={dependency.source_url}" if dependency.source_url else ""
        lines.append(
            f"- `{dependency.manager}` {dependency.name} {dependency.specifier or ''} "
            f"[{dependency.risk_level}{license_text}{source}]".strip()
        )
    if dependencies.warnings:
        warnings.extend(dependencies.warnings)

    lines.extend(["", "## File Tree", ""])
    for entry in tree.entries[:80]:
        marker = "/" if entry.kind == "directory" else ""
        lines.append(f"- `{entry.path}{marker}`")
    if tree.truncated:
        warnings.append("File tree output was truncated")
    if tree.warnings:
        warnings.extend(tree.warnings)

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Project code was not executed.",
            "- Project dependencies were not installed.",
            "- Network vulnerability databases were not queried.",
            "- File previews are bounded and redact common secret patterns.",
        ]
    )
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    return CodeInspectionReportResponse(
        project_id=project.id,
        generated_at=datetime.utcnow(),
        markdown="\n".join(lines).rstrip() + "\n",
        warnings=warnings,
    )


def git_status(project: CodeProject) -> GitStatusResponse:
    try:
        root = project_directory(project)
    except (ValueError, OSError) as exc:
        return GitStatusResponse(project_id=project.id, available=False, error=str(exc))
    if not (root / ".git").exists():
        return GitStatusResponse(project_id=project.id, available=False, error="Git repository not found")
    try:
        output = _run_git(root, ["status", "--porcelain=1", "-b"])
    except (FileNotFoundError, RuntimeError) as exc:
        return GitStatusResponse(project_id=project.id, available=False, error=str(exc))

    lines = output.splitlines()
    branch = None
    ahead = 0
    behind = 0
    changed_files: list[str] = []
    if lines and lines[0].startswith("## "):
        branch_line = lines[0][3:]
        branch = branch_line.split("...", 1)[0] or None
        ahead_match = re.search(r"ahead (\d+)", branch_line)
        behind_match = re.search(r"behind (\d+)", branch_line)
        ahead = int(ahead_match.group(1)) if ahead_match else 0
        behind = int(behind_match.group(1)) if behind_match else 0
        for line in lines[1:]:
            if len(line) >= 3:
                changed_files.append(line[3:])
    return GitStatusResponse(
        project_id=project.id,
        available=True,
        branch=branch,
        is_dirty=bool(changed_files),
        changed_files=changed_files[:_MAX_DEPENDENCIES],
        ahead=ahead,
        behind=behind,
    )


def git_commits(project: CodeProject, limit: int = 20) -> list[GitCommitResponse]:
    root = project_directory(project)
    if not (root / ".git").exists():
        return []
    output = _run_git(
        root,
        [
            "log",
            f"-n{limit}",
            "--date=iso-strict",
            "--pretty=format:%H%x1f%an%x1f%aI%x1f%s",
        ],
    )
    commits: list[GitCommitResponse] = []
    for line in output.splitlines():
        parts = line.split("\x1f", 3)
        if len(parts) != 4:
            continue
        authored_at = None
        try:
            authored_at = datetime.fromisoformat(parts[2])
        except ValueError:
            pass
        commits.append(
            GitCommitResponse(
                commit_hash=parts[0],
                author=parts[1],
                authored_at=authored_at,
                subject=parts[3],
            )
        )
    return commits


def git_diff(project: CodeProject, relative_path: str | None = None) -> GitDiffResponse:
    try:
        root = project_directory(project)
    except (ValueError, OSError) as exc:
        return GitDiffResponse(project_id=project.id, available=False, error=str(exc))
    if not (root / ".git").exists():
        return GitDiffResponse(project_id=project.id, available=False, error="Git repository not found")

    safe_path = None
    if relative_path:
        safe_path = _safe_relative_path(root, relative_path)
    arguments = ["diff", "--no-ext-diff", "--no-textconv", "--unified=3", "HEAD", "--"]
    if safe_path:
        arguments.append(safe_path)
    try:
        patch, truncated = _run_git_bounded(root, arguments)
    except (FileNotFoundError, RuntimeError) as exc:
        return GitDiffResponse(
            project_id=project.id,
            available=False,
            path=safe_path,
            error=str(exc),
        )
    return GitDiffResponse(
        project_id=project.id,
        available=True,
        path=safe_path,
        patch=patch,
        truncated=truncated,
    )


def git_commit_detail(project: CodeProject, commit_hash: str) -> GitCommitDetailResponse:
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", commit_hash):
        raise ValueError("Invalid Git commit hash")
    try:
        root = project_directory(project)
    except (ValueError, OSError) as exc:
        return GitCommitDetailResponse(
            project_id=project.id,
            commit_hash=commit_hash,
            available=False,
            error=str(exc),
        )
    if not (root / ".git").exists():
        return GitCommitDetailResponse(
            project_id=project.id,
            commit_hash=commit_hash,
            available=False,
            error="Git repository not found",
        )
    try:
        patch, truncated = _run_git_bounded(
            root,
            [
                "show",
                "--no-ext-diff",
                "--no-textconv",
                "--format=fuller",
                "--stat",
                commit_hash,
                "--",
            ],
        )
    except (FileNotFoundError, RuntimeError) as exc:
        return GitCommitDetailResponse(
            project_id=project.id,
            commit_hash=commit_hash,
            available=False,
            error=str(exc),
        )
    return GitCommitDetailResponse(
        project_id=project.id,
        commit_hash=commit_hash,
        available=True,
        patch=patch,
        truncated=truncated,
    )


def _run_git(root: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "--no-pager", "--no-optional-locks", *arguments],
        cwd=root,
        shell=False,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "Git command failed"
        raise RuntimeError(message)
    return result.stdout


def _run_git_bounded(root: Path, arguments: list[str]) -> tuple[str, bool]:
    process = subprocess.Popen(
        ["git", "-c", "core.fsmonitor=false", "--no-pager", "--no-optional-locks", *arguments],
        cwd=root,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output = bytearray()
    truncated = False
    try:
        while True:
            chunk = process.stdout.read(8192) if process.stdout else b""
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > _MAX_DIFF_BYTES:
                truncated = True
                process.kill()
                break
        stderr = process.stderr.read(8192) if process.stderr else b""
        return_code = process.wait(timeout=15)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise RuntimeError("Git diff timed out") from exc
    if return_code != 0 and not truncated:
        message = stderr.decode("utf-8", errors="replace").strip() or "Git command failed"
        raise RuntimeError(message)
    return bytes(output[:_MAX_DIFF_BYTES]).decode("utf-8", errors="replace"), truncated


def _safe_relative_path(root: Path, value: str) -> str:
    normalized = value.replace("\\", "/")
    path = Path(normalized)
    if not normalized or path.is_absolute() or any(part in {"", ".."} for part in normalized.split("/")):
        raise ValueError("Git path must stay inside the project")
    if normalized.split("/", 1)[0].endswith(":"):
        raise ValueError("Git path must stay inside the project")
    candidate = root / Path(*normalized.split("/"))
    if candidate.is_symlink():
        raise ValueError("Git path cannot be a symbolic link")
    target = candidate.resolve()
    root = root.resolve()
    if target != root and root not in target.parents:
        raise ValueError("Git path must stay inside the project")
    return "/".join(part for part in normalized.split("/") if part)


def _looks_binary(sample: bytes) -> bool:
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    text_bytes = sum(1 for byte in sample if byte in (9, 10, 13) or 32 <= byte <= 126 or byte >= 128)
    return text_bytes / len(sample) < 0.85


def _redact_secrets(text: str) -> tuple[str, bool]:
    redacted = False

    def replace_key_value(match: re.Match) -> str:
        nonlocal redacted
        redacted = True
        return f"{match.group(1)}=***REDACTED***"

    def replace_bearer(match: re.Match) -> str:
        nonlocal redacted
        redacted = True
        return f"{match.group(1)} ***REDACTED***"

    value = _SECRET_PATTERNS[0].sub(replace_key_value, text)
    value = _SECRET_PATTERNS[1].sub(replace_bearer, value)
    return value, redacted


def analyze_dependencies(project: CodeProject) -> DependencyAnalysisResponse:
    root = project_directory(project)
    dependencies: list[DependencyResponse] = []
    manifests: list[str] = []
    warnings: list[str] = []
    scanned_files = 0

    for path in _iter_project_files(root):
        scanned_files += 1
        name = path.name
        relative = path.relative_to(root).as_posix()
        try:
            if _REQUIREMENTS_FILES.match(name):
                manifests.append(relative)
                dependencies.extend(_parse_requirements(path, relative))
            elif name == "package.json":
                manifests.append(relative)
                dependencies.extend(_parse_package_json(path, relative))
            elif name == "package-lock.json":
                manifests.append(relative)
                dependencies.extend(_parse_package_lock(path, relative))
            elif name == "Pipfile.lock":
                manifests.append(relative)
                dependencies.extend(_parse_pipfile_lock(path, relative))
            elif name == "poetry.lock":
                manifests.append(relative)
                dependencies.extend(_parse_poetry_lock(path, relative))
            elif name == "pyproject.toml":
                manifests.append(relative)
                dependencies.extend(_parse_pyproject(path, relative))
            elif name in {"environment.yml", "environment.yaml"}:
                manifests.append(relative)
                dependencies.extend(_parse_conda_yaml(path, relative))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
            warnings.append(f"{relative}: {exc}")

    if len(dependencies) > _MAX_DEPENDENCIES:
        warnings.append(f"Dependency list truncated at {_MAX_DEPENDENCIES} entries")
        dependencies = dependencies[:_MAX_DEPENDENCIES]
    return DependencyAnalysisResponse(
        project_id=project.id,
        scanned_files=scanned_files,
        manifests=sorted(set(manifests)),
        dependencies=dependencies,
        warnings=warnings,
        high_risk_count=sum(item.risk_level == "high" for item in dependencies),
        review_count=sum(item.risk_level == "review" for item in dependencies),
    )


def _iter_project_files(root: Path):
    yielded = 0
    for directory, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        directories[:] = [name for name in directories if name not in _SKIPPED_DIRECTORIES]
        for filename in filenames:
            if yielded >= _MAX_SCAN_FILES:
                return
            path = Path(directory) / filename
            if path.is_symlink():
                continue
            yield path
            yielded += 1


def _parse_requirements(path: Path, source_file: str) -> list[DependencyResponse]:
    result: list[DependencyResponse] = []
    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(("-", "--")):
            continue
        line = line.split(" #", 1)[0].strip()
        match = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)", line)
        if match:
            result.append(
                _make_dependency(
                    "pip",
                    match.group(1),
                    match.group(2) or None,
                    source_file,
                )
            )
    return result


def _parse_package_json(path: Path, source_file: str) -> list[DependencyResponse]:
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    result: list[DependencyResponse] = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = document.get(section, {})
        if not isinstance(values, dict):
            continue
        result.extend(
            _make_dependency(
                "npm",
                str(name),
                str(specifier) if specifier is not None else None,
                source_file,
            )
            for name, specifier in values.items()
        )
    return result


def _parse_package_lock(path: Path, source_file: str) -> list[DependencyResponse]:
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    result: list[DependencyResponse] = []
    packages = document.get("packages", {})
    if isinstance(packages, dict):
        for package_path, metadata in packages.items():
            if not package_path.startswith("node_modules/") or not isinstance(metadata, dict):
                continue
            version = metadata.get("version")
            if version:
                result.append(
                    _make_dependency(
                        "npm-lock",
                        package_path.removeprefix("node_modules/"),
                        f"=={version}",
                        source_file,
                        source_url=_stringify_optional(metadata.get("resolved")),
                        license_text=_stringify_optional(metadata.get("license")),
                    )
                )
    if not result and isinstance(document.get("dependencies"), dict):
        result.extend(_parse_npm_lock_dependencies(document["dependencies"], source_file))
    return result


def _parse_npm_lock_dependencies(values: dict[str, Any], source_file: str) -> list[DependencyResponse]:
    result: list[DependencyResponse] = []
    for name, metadata in values.items():
        if not isinstance(metadata, dict):
            continue
        version = metadata.get("version")
        if version:
            result.append(
                _make_dependency(
                    "npm-lock",
                    str(name),
                    f"=={version}",
                    source_file,
                    source_url=_stringify_optional(metadata.get("resolved")),
                    license_text=_stringify_optional(metadata.get("license")),
                )
            )
        nested = metadata.get("dependencies")
        if isinstance(nested, dict):
            result.extend(_parse_npm_lock_dependencies(nested, source_file))
    return result


def _parse_pipfile_lock(path: Path, source_file: str) -> list[DependencyResponse]:
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    result: list[DependencyResponse] = []
    for section in ("default", "develop"):
        values = document.get(section, {})
        if not isinstance(values, dict):
            continue
        for name, metadata in values.items():
            specifier = metadata.get("version") if isinstance(metadata, dict) else None
            source_url = None
            if isinstance(metadata, dict):
                source_url = _stringify_optional(metadata.get("index"))
            result.append(_make_dependency("pipenv-lock", str(name), specifier, source_file, source_url=source_url))
    return result


def _parse_poetry_lock(path: Path, source_file: str) -> list[DependencyResponse]:
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    result: list[DependencyResponse] = []
    for package in document.get("package", []) or []:
        if not isinstance(package, dict) or not package.get("name"):
            continue
        version = package.get("version")
        source = package.get("source")
        source_url = source.get("url") if isinstance(source, dict) else None
        result.append(
            _make_dependency(
                "poetry-lock",
                str(package["name"]),
                f"=={version}" if version else None,
                source_file,
                source_url=_stringify_optional(source_url),
                license_text=_stringify_optional(package.get("license")),
            )
        )
    return result


def _parse_pyproject(path: Path, source_file: str) -> list[DependencyResponse]:
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    result: list[DependencyResponse] = []
    project = document.get("project", {})
    if isinstance(project, dict):
        for value in project.get("dependencies", []) or []:
            result.append(_dependency_from_requirement("pip", value, source_file))
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for values in optional.values():
                for value in values or []:
                    result.append(_dependency_from_requirement("pip", value, source_file))
    poetry = document.get("tool", {}).get("poetry", {})
    if isinstance(poetry, dict):
        values = poetry.get("dependencies", {})
        if isinstance(values, dict):
            for name, specifier in values.items():
                if name.lower() == "python":
                    continue
                result.append(
                    _make_dependency(
                        "pip",
                        str(name),
                        _stringify_specifier(specifier),
                        source_file,
                    )
                )
    return result


def _dependency_from_requirement(manager: str, value: Any, source_file: str) -> DependencyResponse:
    text = str(value).strip()
    match = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)", text)
    if not match:
        return _make_dependency(manager, text, None, source_file)
    return _make_dependency(manager, match.group(1), match.group(2) or None, source_file)


def _make_dependency(
    manager: str,
    name: str,
    specifier: str | None,
    source_file: str,
    source_url: str | None = None,
    license_text: str | None = None,
) -> DependencyResponse:
    risk_level, risk_reason = _dependency_risk(manager, specifier, source_url)
    return DependencyResponse(
        manager=manager,
        name=name,
        specifier=specifier,
        source_file=source_file,
        risk_level=risk_level,
        risk_reason=risk_reason,
        source_url=source_url,
        license=license_text,
    )


def _dependency_risk(
    manager: str,
    specifier: str | None,
    source_url: str | None = None,
) -> tuple[str, str | None]:
    value = (specifier or "").strip().lower()
    source = (source_url or "").strip().lower()
    if not value or value in {"*", "latest"}:
        return "high", "No pinned version"
    source_markers = ("git+", "file:", "path:")
    if not manager.endswith("-lock"):
        source_markers = ("git+", "http://", "https://", "file:", "path:")
    if any(marker in f"{value} {source}" for marker in source_markers):
        return "high", "Dependency comes from a remote or local path"
    if value.startswith(("^", "~")) or any(marker in value for marker in (">", "<", "*")):
        return "review", "Version range may change during installation"
    return "low", None


def _stringify_optional(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def _stringify_specifier(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ", ".join(f"{key}={item}" for key, item in value.items())
    return str(value) if value is not None else None


def _parse_conda_yaml(path: Path, source_file: str) -> list[DependencyResponse]:
    result: list[DependencyResponse] = []
    in_dependencies = False
    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        stripped = raw_line.strip()
        if stripped == "dependencies:":
            in_dependencies = True
            continue
        if in_dependencies and stripped and not raw_line.startswith((" ", "\t", "-")):
            in_dependencies = False
        if in_dependencies and stripped.startswith("- ") and not stripped.startswith("- pip:"):
            value = stripped[2:].strip()
            if value:
                result.append(_dependency_from_requirement("conda", value, source_file))
    return result
