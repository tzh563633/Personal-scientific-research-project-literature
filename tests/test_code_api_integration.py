import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app import models
from backend.app.config import settings
from backend.app.db import get_db
from backend.app.dependencies import get_current_user
from backend.app.main import app


def test_uploaded_code_project_can_be_inspected(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "osv_enabled", False)
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}",
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
        return models.User(id=1, username="tester", role="admin", password_hash="hash")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("src/app.py", "api_key=abcdef123456\nprint('ok')\n")
            handle.writestr("requirements.txt", "requests\nfastapi>=0.100\nunsafe-demo==1.0.0\n")
            handle.writestr(
                "package-lock.json",
                json.dumps(
                    {
                        "packages": {
                            "": {},
                            "node_modules/vue": {
                                "version": "3.5.0",
                                "resolved": "https://registry.npmjs.org/vue/-/vue-3.5.0.tgz",
                                "license": "MIT",
                            },
                        }
                    }
                ),
            )
            handle.writestr("binary.bin", b"\x00\x01\x02")
        archive.seek(0)

        client = TestClient(app)
        upload = client.post(
            "/api/v1/code/upload",
            files={"file": ("project.zip", archive.getvalue(), "application/zip")},
            data={"name": "api-inspection"},
        )
        assert upload.status_code == 200
        project_id = upload.json()["id"]
        assert not list((tmp_path / "storage" / "code").glob("*.zip"))

        tree = client.get(f"/api/v1/code/projects/{project_id}/tree")
        assert tree.status_code == 200
        assert "src" in {entry["name"] for entry in tree.json()["entries"]}

        dependencies = client.get(f"/api/v1/code/projects/{project_id}/dependencies")
        assert dependencies.status_code == 200
        body = dependencies.json()
        assert body["high_risk_count"] == 1
        assert body["review_count"] == 1
        assert any(item["license"] == "MIT" for item in body["dependencies"])

        audit = client.get(f"/api/v1/code/projects/{project_id}/security-audit")
        assert audit.status_code == 200
        audit_body = audit.json()
        assert audit_body["vulnerability_count"] == 1
        assert audit_body["highest_severity"] == "high"
        assert audit_body["osv_enabled"] is False
        assert any(
            vulnerability["id"] == "LOCAL-PY-DEMO-0001"
            for finding in audit_body["findings"]
            for vulnerability in finding["vulnerabilities"]
        )

        preview = client.get(
            f"/api/v1/code/projects/{project_id}/files/preview",
            params={"path": "src/app.py"},
        )
        assert preview.status_code == 200
        assert preview.json()["redacted"] is True
        assert "***REDACTED***" in preview.json()["content"]

        binary = client.get(
            f"/api/v1/code/projects/{project_id}/files/preview",
            params={"path": "binary.bin"},
        )
        assert binary.status_code == 422

        report = client.get(f"/api/v1/code/projects/{project_id}/inspection-report")
        assert report.status_code == 200
        assert "Code Inspection Report: api-inspection" in report.json()["markdown"]
        assert "Security Audit" in report.json()["markdown"]
        assert "Project code was not executed" in report.json()["markdown"]

        with Session(engine) as db:
            assert db.query(models.CodeProject).count() == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
