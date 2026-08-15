# P1 Progress

P1 is now active after the P0 audit passed.

The first P1 delivery slice is complete and has passed the repository,
container, and frontend regression checks.

## Delivered First Slice

- `GET /api/v1/code/projects/{project_id}/git/status`
- `GET /api/v1/code/projects/{project_id}/git/commits?limit=20`
- `GET /api/v1/code/projects/{project_id}/git/commits/{commit_hash}`
- `GET /api/v1/code/projects/{project_id}/git/diff?path=...`
- `GET /api/v1/code/projects/{project_id}/dependencies`

Git access is read-only and uses fixed subprocess argument arrays with
`shell=False`, a timeout, disabled external diff/text conversion and fsmonitor,
and a project path constrained to the platform storage root. Diff output is
limited to 200 KB. The dependency analyzer reads `requirements*.txt`,
`package.json`, `package-lock.json`, `Pipfile.lock`, `pyproject.toml`,
`poetry.lock`, and Conda environment files. It does not run project code,
install packages, or fetch from the network.

The frontend code page now provides a project inspection drawer with Git
status, commit details, bounded diffs, dependency manifests, and version-risk
labels. The backend image includes Git so these read-only APIs work in the
Docker deployment.

## Verification

- `pytest -q`: 20 passed
- Python compileall: passed
- frontend production build: passed
- Docker Compose config: passed
- backend/frontend images rebuilt successfully
- Runtime temporary-project check: Git available, 1 commit, 2 dependencies,
  1 high-risk dependency, 1 review dependency, working-tree diff available,
  commit detail available

## Follow-up P1

1. Add dependency source/license metadata when a local lockfile exposes it.
2. Add bounded file-tree browsing for registered code projects.
3. Add integration coverage for uploaded project archives and Git repositories.
