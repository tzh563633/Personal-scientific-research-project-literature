# P1 Progress

P1 is now active after the P0 audit passed.

The first P1 delivery slice is complete and has passed the repository,
container, and frontend regression checks.

## Delivered First Slice

- `GET /api/v1/code/projects/{project_id}/git/status`
- `GET /api/v1/code/projects/{project_id}/git/commits?limit=20`
- `GET /api/v1/code/projects/{project_id}/git/commits/{commit_hash}`
- `GET /api/v1/code/projects/{project_id}/git/diff?path=...`
- `GET /api/v1/code/projects/{project_id}/tree?path=...`
- `GET /api/v1/code/projects/{project_id}/dependencies`

Git access is read-only and uses fixed subprocess argument arrays with
`shell=False`, a timeout, disabled external diff/text conversion and fsmonitor,
and a project path constrained to the platform storage root. Diff output is
limited to 200 KB. The dependency analyzer reads `requirements*.txt`,
`package.json`, `package-lock.json`, `Pipfile.lock`, `pyproject.toml`,
`poetry.lock`, and Conda environment files. Lockfile license and source URL
metadata are returned when present. It does not run project code, install
packages, or fetch from the network.

The frontend code page now provides a project inspection drawer with Git
status, commit details, bounded diffs, dependency manifests, and version-risk
labels. It also has a bounded file-tree tab that skips heavy or unsafe folders
such as `.git`, virtual environments, build outputs, and `node_modules`. The
backend image includes Git so these read-only APIs work in the Docker
deployment.

## Verification

- `pytest -q`: 21 passed
- Python compileall: passed
- frontend production build: passed
- Docker Compose config: passed
- backend/frontend images rebuilt successfully
- Runtime temporary-project check: Git available, 1 commit, 2 dependencies,
  1 high-risk dependency, 1 review dependency, working-tree diff available,
  commit detail available
- Runtime file-tree and lockfile check: root tree returned `src`,
  `package-lock.json`, and `requirements.txt`; `node_modules` was skipped;
  nested `src/app.py` was returned; lockfile dependency returned `MIT` license
  and a source URL

## Follow-up P1

1. Add richer dependency source/license metadata for more ecosystem lockfiles.
2. Add optional bounded file-preview for text files.
3. Add broader integration coverage for uploaded project archives and Git repositories.
