from __future__ import annotations

import argparse
import socket
import time
from pathlib import Path

import httpx

from .folder_scan import scan_pdf_folder


def execute_remote_job(base_url: str, token: str, job: dict) -> dict:
    kind = job.get("kind")
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/v1/agent/execute",
        headers={"X-Agent-Token": token},
        json={"kind": kind, "payload": job.get("payload") or {}},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def execute_folder_scan(base_url: str, token: str, job: dict) -> dict:
    payload = job.get("payload") or {}
    folder_id = payload.get("folder_id")
    if not folder_id:
        return {"ok": False, "error": "Folder scan job is missing folder_id"}
    files, warnings = scan_pdf_folder(
        payload.get("path", ""),
        recursive=bool(payload.get("recursive", True)),
        max_files=int(payload.get("max_files", 500)),
    )
    imported = 0
    duplicates = 0
    errors = list(warnings)
    with httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"X-Agent-Token": token},
        timeout=300,
    ) as client:
        for item in files:
            path = Path(item["path"])
            try:
                with path.open("rb") as handle:
                    response = client.post(
                        f"/api/v1/agent/folders/{folder_id}/documents",
                        data={
                            "relative_path": item["relative_path"],
                            "sha256": item["sha256"],
                            "modified_at": item["modified_at"],
                        },
                        files={"file": (item["file_name"], handle, "application/pdf")},
                    )
                response.raise_for_status()
                body = response.json()
                if body.get("duplicate"):
                    duplicates += 1
                else:
                    imported += 1
            except (OSError, httpx.HTTPError, ValueError) as exc:
                errors.append(f"{item['relative_path']}: {exc}")
    return {
        "ok": True,
        "result": {
            "scanned": len(files),
            "imported": imported,
            "duplicates": duplicates,
            "errors": errors,
        },
    }


def execute_job(base_url: str, token: str, job: dict) -> dict:
    if job.get("kind") == "scan_folder":
        try:
            return execute_folder_scan(base_url, token, job)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    return execute_remote_job(base_url, token, job)


def run(base_url: str, token: str, interval: int, name: str) -> None:
    headers = {"X-Agent-Token": token}
    with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=30) as client:
        registration = client.post(
            "/api/v1/agent/register",
            json={
                "name": name,
                "capabilities": [
                    "backup",
                    "update_excel",
                    "monitor_journals",
                    "generate_review",
                    "scan_folder",
                ],
            },
        )
        registration.raise_for_status()
        agent_id = registration.json()["agent_id"]
        last_heartbeat = 0.0
        while True:
            now = time.monotonic()
            if now - last_heartbeat >= 30:
                heartbeat = client.post("/api/v1/agent/heartbeat", json={"agent_id": agent_id})
                heartbeat.raise_for_status()
                last_heartbeat = now
            response = client.post("/api/v1/agent/jobs/claim", json={"agent_id": agent_id})
            response.raise_for_status()
            job = response.json().get("job")
            if job:
                result = execute_job(base_url, token, job)
                result_response = client.post(f"/api/v1/agent/jobs/{job['id']}/result", json=result)
                result_response.raise_for_status()
            else:
                time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Research platform host Agent")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--name", default=socket.gethostname())
    args = parser.parse_args()
    run(args.base_url, args.token, args.interval, args.name)


if __name__ == "__main__":
    main()
