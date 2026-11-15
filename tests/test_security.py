"""Vérification de la couche sécurité (المرحلة 0 / Sprint 0).

Couvre les résultats attendus par les deux plans :
- loopback sans token  -> l'API répond ;
- distant sans token   -> refus (403) ;
- token configuré      -> 401 sans token, 200 avec le bon token ;
- shell et git pull    -> désactivés par défaut, activables explicitement.
"""

from __future__ import annotations

import pytest


def test_status_ok_from_loopback(loopback):
    response = loopback.get("/api/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "telemetry" in body
    assert len(body["agents"]) == 6


def test_remote_without_token_is_refused(remote):
    response = remote.get("/api/status")
    assert response.status_code == 403
    assert "loopback" in response.json()["error"]


def test_remote_cannot_use_shell_or_files(remote):
    assert remote.post("/api/shell", json={"cmd": "echo pwned"}).status_code == 403
    assert remote.post("/api/file/read", json={"path": "config.json"}).status_code == 403


def test_token_is_required_when_configured(remote, monkeypatch):
    monkeypatch.setenv("GENIO_API_TOKEN", "s3cret-token")

    assert remote.get("/api/status").status_code == 401
    assert remote.get("/api/status", headers={"X-Genio-Token": "wrong"}).status_code == 401

    ok = remote.get("/api/status", headers={"X-Genio-Token": "s3cret-token"})
    assert ok.status_code == 200

    bearer = remote.get("/api/status", headers={"Authorization": "Bearer s3cret-token"})
    assert bearer.status_code == 200

    query = remote.get("/api/status", params={"token": "s3cret-token"})
    assert query.status_code == 200


def test_shell_disabled_by_default(loopback):
    response = loopback.post("/api/shell", json={"cmd": "echo hello"})
    assert response.status_code == 403
    assert "disabled" in response.json()["error"]


def test_shell_works_only_when_explicitly_enabled(loopback, monkeypatch):
    monkeypatch.setenv("GENIO_ENABLE_SHELL", "1")

    response = loopback.post("/api/shell", json={"cmd": "echo genio-shell-ok"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["returncode"] == 0
    assert "genio-shell-ok" in body["output"]


def test_update_apply_disabled_by_default(loopback):
    response = loopback.post("/api/update/apply")
    assert response.status_code == 403
    assert "disabled" in response.json()["error"]


def test_path_traversal_is_blocked(loopback):
    response = loopback.post("/api/file/read", json={"path": "../../etc/passwd"})
    assert response.status_code == 404


def test_workspace_zip_is_served(loopback):
    response = loopback.get("/api/workspace/zip")
    assert response.status_code == 200
    assert response.content[:2] == b"PK"


def test_index_is_rtl_arabic(loopback):
    response = loopback.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'dir="rtl"' in html
    assert 'lang="ar"' in html


@pytest.mark.parametrize("path", ["/api/status", "/api/memory", "/api/update/check"])
def test_read_endpoints_open_on_loopback(loopback, path):
    assert loopback.get(path).status_code == 200
