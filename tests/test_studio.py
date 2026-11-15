"""Vérification du Sprint 1 (plan v2) — Vibe Studio MVP.

معيار القبول: طلب بالدارجة → مشروع ويب يخدم + تحقّق + preview حي.
"""

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


def _project(client, name="متجر صغير", template="landing", idea="نحب تطبيق متجر إلكتروني صغير"):
    return client.post(
        "/api/projects",
        json={"name": name, "template": template, "idea": idea},
        headers={"X-Genio-CSRF": client.csrf},
    )


def test_templates_are_listed(server):
    templates = _owner(server).get("/api/projects/templates").json()["templates"]
    ids = {item["id"] for item in templates}
    assert ids == {"landing", "react-vite", "fastapi", "next", "flutter", "expo"}
    assert any(item["mobile"] for item in templates)


def test_landing_project_is_created_with_files(server):
    client = _owner(server)
    created = _project(client)
    assert created.status_code == 200, created.text
    project = created.json()["project"]
    assert project["template"] == "landing"

    files = client.get(f"/api/projects/{project['id']}/files").json()["files"]
    paths = {item["path"] for item in files}
    assert "index.html" in paths
    assert "README.md" in paths

    html = client.get(f"/api/projects/{project['id']}/preview").text
    assert 'dir="rtl"' in html
    assert "متجر" in html


def test_react_project_has_real_scaffold(server):
    client = _owner(server)
    project = _project(client, name="react-app", template="react-vite").json()["project"]

    files = {item["path"] for item in client.get(f"/api/projects/{project['id']}/files").json()["files"]}
    assert {"package.json", "src/main.jsx", "src/App.jsx", "vite.config.js"} <= files

    package = client.get(
        f"/api/projects/{project['id']}/file", params={"path": "package.json"}
    ).json()
    assert '"dev": "vite"' in package["content"]


def test_mission_runs_the_whole_dag(server):
    client = _owner(server)
    project = _project(client, template="fastapi", name="api").json()["project"]

    mission = client.post(
        f"/api/projects/{project['id']}/mission",
        json={"idea": "API بسيط للتذاكر"},
        headers={"X-Genio-CSRF": client.csrf},
    )
    assert mission.status_code == 200, mission.text
    body = mission.json()
    assert body["ok"] is True
    assert [task["stage"] for task in body["tasks"]] == ["pm", "architect", "coder", "qa"]
    assert all(task["status"] == "done" for task in body["tasks"])
    assert "uvicorn" in body["next"]

    files = {
        item["path"]
        for item in client.get(f"/api/projects/{project['id']}/files").json()["files"]
    }
    assert {"SPEC.md", "ARCHITECTURE.md"} <= files


def test_unknown_template_is_refused(server):
    response = _project(_owner(server), template="wordpress")
    assert response.status_code == 400
    assert "قالب" in response.json()["error"]


def test_preview_blocks_traversal(server):
    client = _owner(server)
    project = _project(client).json()["project"]
    response = client.get(
        f"/api/projects/{project['id']}/preview", params={"path": "../../../../etc/passwd"}
    )
    assert response.status_code == 404


def test_projects_are_private_to_their_owner(server):
    owner = _owner(server)
    project = _project(owner).json()["project"]
    owner.post(
        "/api/admin/users",
        json={"email": "other@hitech.tn", "password": PASSWORD, "role": "member"},
        headers={"X-Genio-CSRF": owner.csrf},
    )

    other = TestClient(server.app, client=("127.0.0.1", 50000))
    other.csrf = other.post(
        "/api/auth/login", json={"email": "other@hitech.tn", "password": PASSWORD}
    ).json()["csrf"]

    assert other.get("/api/projects").json()["projects"] == []
    assert other.get(f"/api/projects/{project['id']}").status_code == 404


def test_project_can_be_exported_as_zip(server):
    client = _owner(server)
    project = _project(client).json()["project"]
    export = client.get(f"/api/projects/{project['id']}/export")
    assert export.status_code == 200
    assert export.content[:2] == b"PK"


def test_deploy_plan_per_target(server):
    client = _owner(server)
    project = _project(client, template="react-vite").json()["project"]

    for target in ("static", "docker", "vps"):
        plan = client.post(
            f"/api/projects/{project['id']}/deploy-plan",
            json={"target": target},
            headers={"X-Genio-CSRF": client.csrf},
        ).json()
        assert plan["target"] == target
        assert plan["steps"]

    refused = client.post(
        f"/api/projects/{project['id']}/deploy-plan",
        json={"target": "ftp"},
        headers={"X-Genio-CSRF": client.csrf},
    )
    assert refused.status_code == 400


def test_mobile_build_plan(server):
    client = _owner(server)
    flutter_project = _project(client, template="flutter", name="flutter-app").json()["project"]
    plan = client.post(
        f"/api/projects/{flutter_project['id']}/deploy-plan",
        json={"target": "mobile"},
        headers={"X-Genio-CSRF": client.csrf},
    ).json()
    assert plan["target"] == "mobile"
    assert any("flutter build apk" in step for step in plan["steps"])

    web_project = _project(client, template="landing", name="site").json()["project"]
    refused = client.post(
        f"/api/projects/{web_project['id']}/deploy-plan",
        json={"target": "mobile"},
        headers={"X-Genio-CSRF": client.csrf},
    )
    assert refused.status_code == 400


def test_mobile_template_is_flagged(server):
    client = _owner(server)
    project = _project(client, template="expo", name="mobile").json()["project"]
    assert project["mobile"] is True
    files = {
        item["path"]
        for item in client.get(f"/api/projects/{project['id']}/files").json()["files"]
    }
    assert {"App.js", "app.json", "package.json"} <= files
