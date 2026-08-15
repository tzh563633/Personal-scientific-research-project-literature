from __future__ import annotations

import argparse
import socket
import time

import httpx


def execute_job(base_url: str, token: str, job: dict) -> dict:
    kind = job.get("kind")
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/v1/agent/execute",
        headers={"X-Agent-Token": token},
        json={"kind": kind, "payload": job.get("payload") or {}},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def run(base_url: str, token: str, interval: int, name: str) -> None:
    headers = {"X-Agent-Token": token}
    with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=30) as client:
        registration = client.post(
            "/api/v1/agent/register",
            json={
                "name": name,
                "capabilities": ["backup", "update_excel", "monitor_journals", "generate_review"],
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
