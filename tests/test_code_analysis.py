import json
from pathlib import Path

from backend.app import models
from backend.app.config import settings
from backend.app.services import code_analysis


def test_dependency_analysis_reads_manifests_without_execution(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    project_root = tmp_path / "code" / "project-1"
    project_root.mkdir(parents=True)
    (project_root / "requirements.txt").write_bytes(b"\xef\xbb\xbffastapi>=0.1\n# ignored\n")
    (project_root / "package.json").write_text(
        json.dumps({"dependencies": {"vue": "^3.0.0"}, "devDependencies": {"vite": "^6.0.0"}}),
        encoding="utf-8",
    )
    (project_root / "package-lock.json").write_text(
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
        encoding="utf-8",
    )
    (project_root / "pyproject.toml").write_text(
        "[project]\ndependencies = [\"sqlalchemy>=2\"]\n",
        encoding="utf-8",
    )
    (project_root / "environment.yml").write_text(
        "name: audit\ndependencies:\n  - python=3.11\n  - numpy\n",
        encoding="utf-8",
    )
    (project_root / "run.py").write_text("raise RuntimeError('must not execute')", encoding="utf-8")
    project = models.CodeProject(id=1, name="audit", local_path="code/project-1")

    result = code_analysis.analyze_dependencies(project)

    assert result.project_id == 1
    assert set(result.manifests) == {
        "requirements.txt",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "environment.yml",
    }
    names = {item.name for item in result.dependencies}
    assert {"fastapi", "vue", "vite", "sqlalchemy", "python", "numpy"} <= names
    locked_vue = next(item for item in result.dependencies if item.manager == "npm-lock" and item.name == "vue")
    assert locked_vue.source_url == "https://registry.npmjs.org/vue/-/vue-3.5.0.tgz"
    assert locked_vue.license == "MIT"
    assert result.high_risk_count >= 1
    assert result.review_count >= 1
    assert result.warnings == []


def test_git_status_is_modelled_and_read_only(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    project_root = tmp_path / "code" / "project-2"
    project_root.mkdir(parents=True)
    (project_root / ".git").mkdir()
    project = models.CodeProject(id=2, name="git", local_path="code/project-2")

    monkeypatch.setattr(
        code_analysis,
        "_run_git",
        lambda root, arguments: "## main...origin/main [ahead 2, behind 1]\n M app.py\n?? notes.md\n",
    )

    result = code_analysis.git_status(project)

    assert result.available is True
    assert result.branch == "main"
    assert result.is_dirty is True
    assert result.changed_files == ["app.py", "notes.md"]
    assert result.ahead == 2
    assert result.behind == 1


def test_git_status_returns_unavailable_for_non_repository(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    project_root = tmp_path / "code" / "project-3"
    project_root.mkdir(parents=True)
    project = models.CodeProject(id=3, name="plain", local_path="code/project-3")

    result = code_analysis.git_status(project)

    assert result.available is False
    assert result.error == "Git repository not found"


def test_git_diff_is_bounded_and_rejects_escape(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    project_root = tmp_path / "code" / "project-4"
    project_root.mkdir(parents=True)
    (project_root / ".git").mkdir()
    project = models.CodeProject(id=4, name="diff", local_path="code/project-4")
    monkeypatch.setattr(
        code_analysis,
        "_run_git_bounded",
        lambda root, arguments: ("diff -- app.py\n+safe\n", False),
    )

    result = code_analysis.git_diff(project, "app.py")

    assert result.available is True
    assert result.path == "app.py"
    assert result.patch.endswith("+safe\n")
    try:
        code_analysis.git_diff(project, "../outside.txt")
    except ValueError as exc:
        assert "inside the project" in str(exc)
    else:
        raise AssertionError("path traversal was accepted")


def test_git_commit_detail_requires_a_hash(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    project_root = tmp_path / "code" / "project-5"
    project_root.mkdir(parents=True)
    (project_root / ".git").mkdir()
    project = models.CodeProject(id=5, name="commit", local_path="code/project-5")
    monkeypatch.setattr(
        code_analysis,
        "_run_git_bounded",
        lambda root, arguments: ("commit detail", False),
    )

    result = code_analysis.git_commit_detail(project, "a" * 40)

    assert result.available is True
    assert result.patch == "commit detail"
    try:
        code_analysis.git_commit_detail(project, "not-a-hash")
    except ValueError as exc:
        assert "commit hash" in str(exc)
    else:
        raise AssertionError("invalid commit hash was accepted")


def test_file_tree_is_bounded_and_skips_heavy_directories(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    project_root = tmp_path / "code" / "project-6"
    (project_root / "src").mkdir(parents=True)
    (project_root / "node_modules").mkdir()
    (project_root / "src" / "app.py").write_text("print('ok')", encoding="utf-8")
    (project_root / "README.md").write_text("docs", encoding="utf-8")
    project = models.CodeProject(id=6, name="tree", local_path="code/project-6")

    root_tree = code_analysis.list_project_tree(project)
    src_tree = code_analysis.list_project_tree(project, "src")

    assert [entry.name for entry in root_tree.entries] == ["src", "README.md"]
    assert src_tree.entries[0].path == "src/app.py"
    try:
        code_analysis.list_project_tree(project, "../outside")
    except ValueError as exc:
        assert "inside the project" in str(exc)
    else:
        raise AssertionError("tree path traversal was accepted")
