from pathlib import Path
import shutil
import tarfile
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..dependencies import get_current_user
from ..models import CodeProject, User
from ..schemas import (
    CodeSecurityAuditResponse,
    CodeProjectResponse,
    CodeInspectionReportResponse,
    DependencyAnalysisResponse,
    FilePreviewResponse,
    FileTreeResponse,
    GitBranchCreateRequest,
    GitBranchResponse,
    GitCommitResponse,
    GitCommitDetailResponse,
    GitDiffResponse,
    GitStatusResponse,
)
from ..services.files import ALLOWED_CODE_EXTENSIONS, relative_storage_path, safe_extract_archive, save_upload
from ..services.code_analysis import (
    analyze_dependencies,
    audit_project_security,
    git_commit_detail,
    git_branches,
    git_create_branch,
    git_commits,
    git_diff,
    git_status,
    generate_code_inspection_report,
    list_project_tree,
    preview_project_file,
)

router = APIRouter(prefix="/code", tags=["code"])


@router.post("/upload", response_model=CodeProjectResponse)
async def upload_code(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        archive, _, _ = await save_upload(file, "code", ALLOWED_CODE_EXTENSIONS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    project_name = name or Path(file.filename or "code-project").stem
    project = CodeProject(
        name=project_name,
        description=description,
        local_path="",
    )
    db.add(project)
    db.flush()
    project_dir = settings.storage_path / "code" / f"project-{project.id}"
    project_dir.mkdir(parents=True, exist_ok=True)
    try:
        extracted = safe_extract_archive(archive, project_dir)
    except (ValueError, OSError, EOFError, zipfile.BadZipFile, tarfile.TarError) as exc:
        db.rollback()
        shutil.rmtree(project_dir, ignore_errors=True)
        archive.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    archive.unlink(missing_ok=True)
    project.local_path = relative_storage_path(project_dir)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[CodeProjectResponse])
def list_projects(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(CodeProject).order_by(CodeProject.created_at.desc()).all()


@router.get("/projects/{project_id}", response_model=CodeProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/git/status", response_model=GitStatusResponse)
def get_git_status(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return git_status(project)


@router.get("/projects/{project_id}/git/branches", response_model=list[GitBranchResponse])
def list_git_branches(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return git_branches(project)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/projects/{project_id}/git/branches", response_model=GitBranchResponse)
def create_git_branch(
    project_id: int,
    payload: GitBranchCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return git_create_branch(project, payload.name, payload.from_branch)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/tree", response_model=FileTreeResponse)
def get_project_tree(
    project_id: int,
    path: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return list_project_tree(project, path, limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/files/preview", response_model=FilePreviewResponse)
def get_project_file_preview(
    project_id: int,
    path: str = Query(min_length=1, max_length=255),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return preview_project_file(project, path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/inspection-report", response_model=CodeInspectionReportResponse)
def get_project_inspection_report(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return generate_code_inspection_report(project)


@router.get("/projects/{project_id}/security-audit", response_model=CodeSecurityAuditResponse)
def get_project_security_audit(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return audit_project_security(project)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/git/commits", response_model=list[GitCommitResponse])
def list_git_commits(
    project_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return git_commits(project, limit)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/git/diff", response_model=GitDiffResponse)
def get_git_diff(
    project_id: int,
    path: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return git_diff(project, path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/projects/{project_id}/git/commits/{commit_hash}",
    response_model=GitCommitDetailResponse,
)
def get_git_commit_detail(
    project_id: int,
    commit_hash: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return git_commit_detail(project, commit_hash)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/dependencies", response_model=DependencyAnalysisResponse)
def list_dependencies(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = db.get(CodeProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return analyze_dependencies(project)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
