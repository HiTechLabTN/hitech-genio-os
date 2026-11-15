"""Vérification de la Phase 3 — Tool Registry + Sandbox + Audit (§4.4)."""

from __future__ import annotations

from starlette.testclient import TestClient

PASSWORD = "genio-test-pass"


def _owner(server):
    client = TestClient(server.app, client=("127.0.0.1", 50000))
    response = client.post(
        "/api/auth/bootstrap",
        json={"email": "owner@hitech.tn", "password": PASSWORD, "display_name": "Owner"},
    )
    client.csrf = response.json()["csrf"]
    return client


def _invoke(client, name, **params):
    return client.post(
        f"/api/tools/{name}/invoke",
        json={"params": params},
        headers={"X-Genio-CSRF": client.csrf},
    )


def _decide(client, approval_id, approve=True):
    return client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"approve": approve},
        headers={"X-Genio-CSRF": client.csrf},
    )


def test_registry_is_described(server):
    client = _owner(server)
    tools = client.get("/api/tools").json()["tools"]
    by_name = {tool["name"]: tool for tool in tools}
    assert set(by_name) >= {"read_file", "write_file", "run_command", "git_status"}
    assert by_name["run_command"]["permission"] == "dangerous"
    assert by_name["read_file"]["permission"] == "safe"
    assert by_name["write_file"]["params"]["path"]["type"] == "string"


def test_safe_tool_runs_immediately(server):
    client = _owner(server)
    _invoke(client, "write_file", path="hello.txt", content="salam")
    response = _invoke(client, "read_file", path="hello.txt")
    assert response.status_code == 200
    assert response.json()["result"]["content"] == "salam"


def test_write_outside_workspace_is_refused(server):
    client = _owner(server)
    response = _invoke(client, "write_file", path="../../escape.txt", content="x")
    assert response.status_code == 403
    assert "workspace" in response.json()["error"]


def test_dangerous_tool_needs_approval(server):
    client = _owner(server)
    response = _invoke(client, "run_command", cmd="echo bonjour")
    assert response.status_code == 202
    body = response.json()
    assert body["requires_approval"] is True
    approval_id = body["approval_id"]

    pending = client.get("/api/approvals").json()["approvals"]
    assert any(row["id"] == approval_id and row["status"] == "pending" for row in pending)

    approved = _decide(client, approval_id)
    assert approved.status_code == 200
    assert approved.json()["result"]["returncode"] == 0
    assert "bonjour" in approved.json()["result"]["output"]


def test_rejected_approval_does_not_run(server):
    client = _owner(server)
    approval_id = _invoke(client, "run_command", cmd="echo nope").json()["approval_id"]

    rejected = _decide(client, approval_id, approve=False)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    reuse = client.post(
        f"/api/tools/run_command/invoke",
        json={"params": {"cmd": "echo nope"}, "approval_id": approval_id},
        headers={"X-Genio-CSRF": client.csrf},
    )
    assert reuse.status_code == 403


def test_sandbox_blocks_dangerous_commands(server):
    client = _owner(server)
    approval_id = _invoke(client, "run_command", cmd="sudo rm -rf /").json()["approval_id"]
    response = _decide(client, approval_id)
    assert response.status_code == 403
    assert "ممنوع" in response.json()["error"]


def test_unknown_binary_is_refused(server):
    client = _owner(server)
    approval_id = _invoke(client, "run_command", cmd="nmap 127.0.0.1").json()["approval_id"]
    response = _decide(client, approval_id)
    assert response.status_code == 403


def test_shell_denied_by_profile_policy(server):
    client = _owner(server)
    client.post(
        "/api/onboarding/submit",
        json={
            "occupation": "enterprise",
            "goals": ["code"],
            "technical_level": "advanced",
            "register": "derja",
            "env": "local",
            "data_sensitivity": "high",
        },
        headers={"X-Genio-CSRF": client.csrf},
    )
    response = _invoke(client, "run_command", cmd="echo blocked")
    assert response.status_code == 403
    assert "shell" in response.json()["error"]


def test_every_invocation_is_audited(server):
    client = _owner(server)
    _invoke(client, "write_file", path="audited.txt", content="x")

    audit = client.get("/api/audit").json()["audit"]
    assert any(row["tool"] == "write_file" and row["action"] == "tool.invoke" for row in audit)


def test_audit_is_admin_only(server):
    owner = _owner(server)
    created = owner.post(
        "/api/admin/users",
        json={"email": "viewer@hitech.tn", "password": PASSWORD, "role": "viewer"},
        headers={"X-Genio-CSRF": owner.csrf},
    )
    assert created.status_code == 200

    viewer = TestClient(server.app, client=("127.0.0.1", 50000))
    viewer.csrf = viewer.post(
        "/api/auth/login", json={"email": "viewer@hitech.tn", "password": PASSWORD}
    ).json()["csrf"]

    assert viewer.get("/api/audit").status_code == 403
    assert viewer.get("/api/tools").status_code == 200


def test_unknown_tool_is_404(server):
    client = _owner(server)
    assert _invoke(client, "format_disk").status_code == 404
