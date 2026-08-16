import asyncio
import io
from pathlib import Path

from fastapi.testclient import TestClient
from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from agent.folder_scan import scan_pdf_folder
from backend.app import models
from backend.app.config import settings
from backend.app.db import get_db
from backend.app.dependencies import get_current_user
from backend.app.main import app
from backend.app.services import folders as folder_service


def test_agent_folder_scan_only_returns_pdf_files(tmp_path: Path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.7\none")
    (tmp_path / "b.txt").write_text("ignore", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.pdf").write_bytes(b"%PDF-1.7\ntwo")

    files, warnings = scan_pdf_folder(str(tmp_path), recursive=True)

    assert warnings == []
    assert [item["relative_path"] for item in files] == ["a.pdf", "nested/c.pdf"]
    assert all(item["sha256"] for item in files)


def test_folder_scan_api_creates_platform_and_agent_jobs(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'folders.db'}",
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    def override_user():
        return models.User(id=1, username="folders", role="admin", password_hash="hash")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        client = TestClient(app)
        folder = client.post(
            "/api/v1/folders",
            json={"name": "Test PDFs", "path": r"D:\papers", "recursive": True},
        )
        assert folder.status_code == 200
        folder_id = folder.json()["id"]

        response = client.post(f"/api/v1/folders/{folder_id}/scan", json={"max_files": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["kind"] == "folder_scan"
        assert body["status"] == "pending"

        with testing_session() as db:
            agent_job = db.query(models.AgentJob).one()
            assert agent_job.kind == "scan_folder"
            assert agent_job.payload["folder_id"] == folder_id
            assert agent_job.payload["max_files"] == 10
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_agent_document_ingest_links_folder_to_paper_and_deduplicates(tmp_path: Path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'ingest.db'}",
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "storage_root", str(tmp_path / "storage"))
    monkeypatch.setattr(folder_service, "enqueue_paper", lambda *_: None)

    async def ingest(db, folder):
        upload = UploadFile(
            filename="paper.pdf",
            file=io.BytesIO(b"%PDF-1.7\nfolder test"),
            headers={"content-type": "application/pdf"},
        )
        return await folder_service.ingest_agent_document(
            db,
            folder,
            upload,
            relative_path="nested/paper.pdf",
            modified_at="2026-08-16T10:00:00",
        )

    with Session(engine) as db:
        folder = models.PaperFolder(name="Folder", path=r"D:\papers")
        db.add(folder)
        db.commit()
        db.refresh(folder)

        document, duplicate = asyncio.run(ingest(db, folder))
        assert not duplicate
        assert document.paper_id is not None
        assert document.parse_job_id is not None
        assert document.relative_path == "nested/paper.pdf"
        assert db.query(models.Paper).count() == 1
        assert db.query(models.Job).count() == 1

        duplicate_document, duplicate = asyncio.run(ingest(db, folder))
        assert duplicate
        assert duplicate_document.id == document.id
        assert db.query(models.Paper).count() == 1


def test_windows_installer_has_click_to_install_and_non_destructive_copy():
    root = Path(__file__).resolve().parents[1]
    installer = (root / "installer" / "Install-ResearchPlatform.ps1").read_text(encoding="utf-8")
    entrypoint = (root / "installer" / "Install-ResearchPlatform.cmd").read_text(encoding="utf-8")

    assert "Install and Run" in installer
    assert "Start-InstalledPlatform" in installer
    assert "start-agent.ps1" in installer
    assert "/MIR" not in installer
    assert "Install-ResearchPlatform.ps1" in entrypoint
