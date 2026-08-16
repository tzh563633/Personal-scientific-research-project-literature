from backend.app.main import app


def test_json_api_routes_have_explicit_response_models():
    binary_routes = {
        ("/api/v1/excel/download", "GET"),
        ("/api/v1/papers/{paper_id}/files/{file_id}", "GET"),
        ("/api/v1/agent/folders/{folder_id}/documents", "POST"),
    }
    missing = []
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in operations.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            if (path, method.upper()) in binary_routes:
                continue
            responses = operation.get("responses", {})
            has_json_response = any(
                "application/json" in response.get("content", {})
                for response in responses.values()
            )
            if not has_json_response:
                missing.append(f"{method.upper()} {path}")
    assert missing == []


def test_agent_contracts_are_modelled():
    expected = {
        ("POST", "/api/v1/agent/register"),
        ("POST", "/api/v1/agent/heartbeat"),
        ("POST", "/api/v1/agent/execute"),
        ("POST", "/api/v1/agent/jobs/claim"),
        ("POST", "/api/v1/agent/jobs/{job_id}/result"),
        ("POST", "/api/v1/agent/folders/{folder_id}/documents"),
    }
    actual = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1/agent")
        for method in operations
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    assert expected.issubset(actual)
    for path, operations in app.openapi()["paths"].items():
        if path.startswith("/api/v1/agent"):
            for operation in operations.values():
                if isinstance(operation, dict):
                    assert any(
                        "application/json" in response.get("content", {})
                        for response in operation.get("responses", {}).values()
                    )


def test_dashboard_overview_contract_is_registered():
    operation = app.openapi()["paths"]["/api/v1/dashboard/overview"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
