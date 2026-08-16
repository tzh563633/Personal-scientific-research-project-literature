from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models
from backend.app.db import get_db
from backend.app.dependencies import get_current_user
from backend.app.main import app


def test_dashboard_overview_aggregates_core_workflow_state(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'dashboard.db'}",
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
        return models.User(id=1, username="dashboard", role="admin", password_hash="hash")

    with testing_session() as db:
        db.add_all(
            [
                models.Paper(title="Processed paper", status="processed"),
                models.Paper(title="Pending paper", status="pending"),
                models.Journal(name="Journal A", enabled=True),
                models.Journal(name="Journal B", enabled=False),
                models.Alert(paper_title="New alert"),
                models.ReviewOutput(content="# Review"),
                models.ExcelUpdate(status="succeeded", added_count=2),
                models.CodeProject(name="Research code", local_path="code/project-1"),
                models.Agent(name="online-agent", status="online"),
                models.Job(kind="parse", status="running", progress=20),
            ]
        )
        db.commit()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        response = TestClient(app).get("/api/v1/dashboard/overview")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    body = response.json()
    assert body["paper_count"] == 2
    assert body["processed_paper_count"] == 1
    assert body["pending_paper_count"] == 1
    assert body["journal_count"] == 2
    assert body["enabled_journal_count"] == 1
    assert body["alert_count"] == 1
    assert body["review_output_count"] == 1
    assert body["code_project_count"] == 1
    assert body["online_agent_count"] == 1
    assert body["active_job_count"] == 1
    assert body["latest_excel_update"]["added_count"] == 2
    assert body["recent_papers"][0]["title"] in {"Processed paper", "Pending paper"}
    assert body["recent_reviews"][0]["content"] == "# Review"
