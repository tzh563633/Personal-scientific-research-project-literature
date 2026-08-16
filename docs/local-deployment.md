# Windows Local Deployment

## Prerequisites

- Windows 10/11
- Docker Desktop running with Linux containers
- PowerShell 5.1 or newer
- Python 3.11 or newer for the optional host Agent

## Start

From the project root:

```powershell
.\scripts\deploy-local.ps1
```

For the one-click desktop workflow, create a Windows shortcut once:

```powershell
.\scripts\create-desktop-shortcut.ps1
```

After that, double-click `科研控制平台.lnk` on the Desktop. The launcher
reuses the local deployment script, waits for health checks, writes failures
to `storage/logs/platform-launcher.log`, and opens the platform in the
default browser.

The script creates `.env` with random local secrets when it does not exist,
rejects placeholder secrets, builds the images, waits for PostgreSQL
migrations and backend/frontend health, and prints the local and LAN URLs.

Open the printed web address and complete the first administrator setup.
Mailpit is available at `http://localhost:8025`.

The default frontend port is `80`. To use another free port, set
`FRONTEND_PORT` in `.env` before starting.

## Host Agent

The host Agent is deliberately outside Docker because it runs approved
Windows-side business tasks. Start it in a second PowerShell window:

```powershell
.\scripts\start-agent.ps1
```

The script reads `AGENT_TOKEN` from `.env`, checks the Python dependency, and
installs `agent/requirements.txt` when `httpx` is missing. It never accepts or
executes arbitrary PowerShell or CMD text.

## Status And Stop

```powershell
.\scripts\status-local.ps1
.\scripts\stop-local.ps1
```

`stop-local.ps1 -RemoveVolumes` also removes PostgreSQL and Redis Docker
volumes. Use that option only when intentionally resetting local data.

## LAN Access

Connect the phone and computer to the same trusted LAN, then open the LAN URL
printed by `deploy-local.ps1`. The frontend is exposed on the configured
frontend port; the backend and Mailpit remain bound to localhost.

Do not expose this HTTP deployment directly to the public Internet. Configure
HTTPS and an authenticated reverse proxy before any external deployment.
