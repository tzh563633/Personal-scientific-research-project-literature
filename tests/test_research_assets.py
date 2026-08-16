import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models
from backend.app.config import settings
from backend.app.db import get_db
from backend.app.dependencies import get_current_user
from backend.app.main import app


def _git(directory: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=directory, check=True, capture_output=True, text=True)


def test_research_asset_crud_and_safe_branch_creation(tmp_path: Path, monkeypatch):
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_root", str(storage_root))
    project_dir = storage_root / "code" / "project-1"
    project_dir.mkdir(parents=True)
    (project_dir / "README.md").write_text("# Asset project\n", encoding="utf-8")
    _git(project_dir, "init")
    _git(project_dir, "config", "user.email", "assets@example.test")
    _git(project_dir, "config", "user.name", "Asset Test")
    _git(project_dir, "add", "README.md")
    _git(project_dir, "commit", "-m", "initial")

    engine = create_engine(
        f"sqlite:///{tmp_path / 'assets.db'}",
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
        return models.User(id=1, username="assets", role="admin", password_hash="hash")

    with testing_session() as db:
        db.add(models.CodeProject(id=1, name="Asset project", local_path="code/project-1"))
        db.commit()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        client = TestClient(app)

        method = client.post(
            "/api/v1/research-assets/methods",
            json={
                "name": "Difference-in-differences",
                "use_cases": "Policy evaluation",
                "steps": "Build panel data",
                "advantages": "Controls for fixed effects",
            },
        )
        assert method.status_code == 200
        method_id = method.json()["id"]
        updated_method = client.put(
            f"/api/v1/research-assets/methods/{method_id}",
            json={"name": "DID", "steps": "Check parallel trends"},
        )
        assert updated_method.status_code == 200
        assert updated_method.json()["name"] == "DID"

        tool = client.post(
            "/api/v1/research-assets/tools",
            json={"name": "Python", "purpose": "Data analysis", "installation": "conda install"},
        )
        assert tool.status_code == 200

        workflow = client.post(
            "/api/v1/research-assets/workflows",
            json={
                "name": "Literature review",
                "description": "Reusable literature workflow",
                "steps": ["Import PDFs", "Generate Excel", "Write review"],
            },
        )
        assert workflow.status_code == 200
        assert workflow.json()["steps"][-1] == "Write review"

        assert len(client.get("/api/v1/research-assets/methods").json()) == 1
        assert len(client.get("/api/v1/research-assets/tools").json()) == 1
        assert len(client.get("/api/v1/research-assets/workflows").json()) == 1

        branches = client.get("/api/v1/code/projects/1/git/branches")
        assert branches.status_code == 200
        assert any(item["current"] for item in branches.json())

        created_branch = client.post(
            "/api/v1/code/projects/1/git/branches",
            json={"name": "research/review-draft"},
        )
        assert created_branch.status_code == 200
        assert created_branch.json()["name"] == "research/review-draft"
        assert (project_dir / ".git" / "refs" / "heads" / "research" / "review-draft").exists()

        unsafe_branch = client.post(
            "/api/v1/code/projects/1/git/branches",
            json={"name": "../unsafe"},
        )
        assert unsafe_branch.status_code == 422

        assert client.delete(f"/api/v1/research-assets/methods/{method_id}").status_code == 200
        assert client.delete(f"/api/v1/research-assets/tools/{tool.json()['id']}").status_code == 200
        assert client.delete(f"/api/v1/research-assets/workflows/{workflow.json()['id']}").status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
