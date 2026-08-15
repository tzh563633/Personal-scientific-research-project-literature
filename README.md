# Research Data Platform

Local-first research literature management and AI-assisted analysis platform.

## Quick start

1. Run `.\scripts\deploy-local.ps1` in PowerShell.
2. Open the printed web address and complete the first-run administrator setup.
3. Open `http://localhost:8025` to inspect development email notifications.
4. For phone access on the same Wi-Fi, open the printed LAN address.

See [docs/local-deployment.md](docs/local-deployment.md) for Windows
deployment, status, stop, Agent, and LAN access instructions.

The completed P0 audit is recorded in
[docs/p0-final-audit-report.md](docs/p0-final-audit-report.md).

P1 progress is tracked in [docs/p1-progress.md](docs/p1-progress.md).

P2 plan and acceptance criteria are tracked in
[docs/p2-plan-and-acceptance.md](docs/p2-plan-and-acceptance.md).

The P2 final report is recorded in
[docs/p2-final-report.md](docs/p2-final-report.md).

P3 plan and acceptance criteria are tracked in
[docs/p3-plan-and-acceptance.md](docs/p3-plan-and-acceptance.md).

The host Agent is optional for business workflows that need a Windows process:

```powershell
python -m agent.agent --base-url http://localhost:8000 --token "$env:AGENT_TOKEN"
```

## Local development

The backend defaults to SQLite when `DATABASE_URL` is omitted. Install
`backend/requirements.txt`, then run:

```powershell
uvicorn app.main:app --app-dir backend --reload
```

The frontend uses Vite:

```powershell
cd frontend
npm install
npm run dev
```

## Data safety

- Uploaded files live under `storage/`.
- Code uploads are stored but never executed.
- Remote commands are mapped to a fixed business allowlist.
- Daily backups can be created with `scripts/backup.ps1`.
- Real model and SMTP credentials are optional during development.
