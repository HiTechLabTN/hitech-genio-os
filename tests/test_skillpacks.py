"""Vérification du Sprint 2 (plan v2) — skill packs + eval gate.

معيار القبول: تحديث skill pack ما يتفعّلش بلا ما يعدّي evals.
"""

from __future__ import annotations

import copy

from core import rag, skillpacks
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


def _login(server, email):
    client = TestClient(server.app, client=("127.0.0.1", 50000))
    client.csrf = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["csrf"]
    return client


def test_packs_are_listed_with_their_eval(server):
    client = _owner(server)
    packs = client.get("/api/skillpacks").json()["packs"]
    assert {pack["name"] for pack in packs} == {"frontend_web", "backend_api", "qa_testing"}
    for pack in packs:
        assert pack["eval"]["passed"] is True
        assert pack["eval"]["checks"]
        assert pack["enabled"] is False


def test_every_source_has_a_known_licence():
    for name, pack in skillpacks.SKILL_PACKS.items():
        for source in pack["sources"]:
            assert source["license"] in rag.KNOWN_LICENSES, (name, source)


def test_pack_cannot_be_enabled_before_passing_evals(server, monkeypatch):
    broken = copy.deepcopy(skillpacks.SKILL_PACKS["qa_testing"])
    broken["sources"] = [{"name": "Random blog", "url": "", "license": "all-rights-reserved"}]
    monkeypatch.setitem(skillpacks.SKILL_PACKS, "qa_testing", broken)

    client = _owner(server)
    report = client.post(
        "/api/skillpacks/qa_testing/eval", headers={"X-Genio-CSRF": client.csrf}
    ).json()["eval"]
    assert report["passed"] is False
    assert any(check["id"] == "licenses" and not check["ok"] for check in report["checks"])

    refused = client.post(
        "/api/skillpacks/qa_testing/enable", headers={"X-Genio-CSRF": client.csrf}
    )
    assert refused.status_code == 400
    assert "evals" in refused.json()["error"]


def test_passing_pack_can_be_enabled_and_disabled(server):
    client = _owner(server)
    enabled = client.post(
        "/api/skillpacks/frontend_web/enable", headers={"X-Genio-CSRF": client.csrf}
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["enabled"] is True

    listed = {pack["name"]: pack for pack in client.get("/api/skillpacks").json()["packs"]}
    assert listed["frontend_web"]["enabled"] is True
    assert listed["backend_api"]["enabled"] is False

    disabled = client.post(
        "/api/skillpacks/frontend_web/disable", headers={"X-Genio-CSRF": client.csrf}
    )
    assert disabled.status_code == 200


def test_unknown_pack_is_404(server):
    client = _owner(server)
    assert (
        client.post(
            "/api/skillpacks/rust_ninja/eval", headers={"X-Genio-CSRF": client.csrf}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/skillpacks/rust_ninja/enable", headers={"X-Genio-CSRF": client.csrf}
        ).status_code
        == 404
    )


def test_only_admin_can_enable(server):
    owner = _owner(server)
    owner.post(
        "/api/admin/users",
        json={"email": "member@hitech.tn", "password": PASSWORD, "role": "member"},
        headers={"X-Genio-CSRF": owner.csrf},
    )
    member = _login(server, "member@hitech.tn")

    refused = member.post(
        "/api/skillpacks/backend_api/enable", headers={"X-Genio-CSRF": member.csrf}
    )
    assert refused.status_code == 403
    assert member.get("/api/skillpacks").status_code == 200


def test_enabling_is_audited(server):
    client = _owner(server)
    client.post(
        "/api/skillpacks/backend_api/enable", headers={"X-Genio-CSRF": client.csrf}
    )
    audit = client.get("/api/audit").json()["audit"]
    assert any(row["action"] == "skillpack.enable" for row in audit)
