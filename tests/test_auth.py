"""Vérification de la Phase 1 — الهوية والمستخدمين (Plan v1 §4.1).

معيار القبول: مستعملين 2 ما يشوفوش بعضهم؛ admin يشوف الكل؛ tests تغطّي auth.
"""

from __future__ import annotations

from starlette.testclient import TestClient

PASSWORD = "genio-test-pass"


def _client(server, host="127.0.0.1"):
    return TestClient(server.app, client=(host, 50000))


def _bootstrap(client, email="owner@hitech.tn", password=PASSWORD):
    return client.post(
        "/api/auth/bootstrap",
        json={"email": email, "password": password, "display_name": "Owner"},
    )


def _login(client, email, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _create_member(owner_client, email, role="member", password=PASSWORD):
    return owner_client.post(
        "/api/admin/users",
        json={"email": email, "password": password, "display_name": email, "role": role},
        headers={"X-Genio-CSRF": owner_client.csrf},
    )


def test_bootstrap_creates_owner_once(server):
    client = _client(server)
    response = _bootstrap(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["role"] == "owner"
    assert body["role_label"] == "المالك"
    assert body["csrf"]

    again = _bootstrap(_client(server), email="second@hitech.tn")
    assert again.status_code == 409


def test_short_password_is_rejected(server):
    response = _bootstrap(_client(server), password="short")
    assert response.status_code == 400
    assert "8" in response.json()["error"]


def test_session_is_required_once_accounts_exist(server):
    _bootstrap(_client(server))

    anonymous = _client(server)
    assert anonymous.get("/api/me").status_code == 401
    assert anonymous.get("/api/status").status_code == 401
    assert anonymous.post("/api/file/read", json={"path": "config.json"}).status_code == 401


def test_login_and_me(server):
    _bootstrap(_client(server))

    client = _client(server)
    assert _login(client, "owner@hitech.tn", "wrong-password").status_code == 401

    response = _login(client, "owner@hitech.tn")
    assert response.status_code == 200
    client.csrf = response.json()["csrf"]

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "owner@hitech.tn"
    assert me.json()["profile"]["persona_pack"] == "chat_general"


def test_logout_clears_session(server):
    client = _client(server)
    client.csrf = _bootstrap(client).json()["csrf"]
    assert client.get("/api/me").status_code == 200

    assert client.post(
        "/api/auth/logout", headers={"X-Genio-CSRF": client.csrf}
    ).status_code == 200
    assert client.get("/api/me").status_code == 401


def test_mutations_require_csrf(server):
    client = _client(server)
    response = _bootstrap(client)
    csrf = response.json()["csrf"]

    blocked = client.post("/api/file/save", json={"path": "note.txt", "content": "hi"})
    assert blocked.status_code == 403
    assert "CSRF" in blocked.json()["error"]

    allowed = client.post(
        "/api/file/save",
        json={"path": "note.txt", "content": "hi"},
        headers={"X-Genio-CSRF": csrf},
    )
    assert allowed.status_code == 200


def test_two_users_do_not_see_each_other(server):
    owner = _client(server)
    csrf = _bootstrap(owner).json()["csrf"]
    owner.csrf = csrf
    assert _create_member(owner, "member@hitech.tn").status_code == 200

    owner.post(
        "/api/file/save",
        json={"path": "owner-secret.txt", "content": "top secret"},
        headers={"X-Genio-CSRF": csrf},
    )

    member = _client(server)
    member.csrf = _login(member, "member@hitech.tn").json()["csrf"]

    files = member.get("/api/status").json()["files"]
    assert [f["path"] for f in files] == []

    stolen = member.post(
        "/api/file/read", json={"path": "../owner/owner-secret.txt"}
    )
    assert stolen.status_code in (403, 404)

    me = member.get("/api/me").json()
    assert me["user"]["workspace_slug"] != owner.get("/api/me").json()["user"]["workspace_slug"]


def test_admin_sees_all_users_but_viewer_does_not(server):
    owner = _client(server)
    owner.csrf = _bootstrap(owner).json()["csrf"]
    _create_member(owner, "admin@hitech.tn", role="admin")
    _create_member(owner, "viewer@hitech.tn", role="viewer")

    admin = _client(server)
    admin.csrf = _login(admin, "admin@hitech.tn").json()["csrf"]
    users = admin.get("/api/admin/users").json()["users"]
    assert {u["email"] for u in users} == {
        "owner@hitech.tn",
        "admin@hitech.tn",
        "viewer@hitech.tn",
    }

    viewer = _client(server)
    viewer.csrf = _login(viewer, "viewer@hitech.tn").json()["csrf"]
    assert viewer.get("/api/admin/users").status_code == 403


def test_only_owner_changes_roles(server):
    owner = _client(server)
    owner.csrf = _bootstrap(owner).json()["csrf"]
    _create_member(owner, "admin@hitech.tn", role="admin")

    admin = _client(server)
    admin.csrf = _login(admin, "admin@hitech.tn").json()["csrf"]
    owner_id = owner.get("/api/me").json()["user"]["id"]

    refused = admin.post(
        f"/api/admin/users/{owner_id}/role",
        json={"role": "viewer"},
        headers={"X-Genio-CSRF": admin.csrf},
    )
    assert refused.status_code == 403

    promoted = owner.post(
        f"/api/admin/users/{owner_id}/role",
        json={"role": "admin"},
        headers={"X-Genio-CSRF": owner.csrf},
    )
    assert promoted.status_code == 200
    assert promoted.json()["user"]["role"] == "admin"


def test_status_gate_drives_the_ui(server):
    anonymous = _client(server)
    fresh = anonymous.get("/api/auth/status").json()
    assert fresh["bootstrapped"] is False
    assert fresh["authenticated"] is False
    assert fresh["onboarding_done"] == 0

    owner = _client(server)
    _bootstrap(owner)

    inside = owner.get("/api/auth/status").json()
    assert inside["bootstrapped"] is True
    assert inside["authenticated"] is True
    assert inside["user"]["role"] == "owner"
    assert inside["onboarding_done"] == 0

    outside = _client(server).get("/api/auth/status").json()
    assert outside["bootstrapped"] is True
    assert outside["authenticated"] is False
    assert outside["user"] is None


def test_ui_assets_are_served(server):
    client = _client(server)
    assert client.get("/static/genio-app.js").status_code == 200
    assert client.get("/static/genio-app.css").status_code == 200

    html = client.get("/").text
    assert "/static/genio-app.js" in html
    assert "/static/genio-app.css" in html
    assert 'id="gioAuth"' in html
    assert 'id="gioStudio"' in html
    assert 'id="gioOnboarding"' in html


def test_profile_can_be_updated(server):
    client = _client(server)
    client.csrf = _bootstrap(client).json()["csrf"]

    response = client.patch(
        "/api/me/profile",
        json={"persona_pack": "dev_lead", "mode": "dev", "goals": ["build_web_apps"]},
        headers={"X-Genio-CSRF": client.csrf},
    )
    assert response.status_code == 200
    assert response.json()["profile"]["persona_pack"] == "dev_lead"
    assert response.json()["profile"]["mode"] == "dev"
