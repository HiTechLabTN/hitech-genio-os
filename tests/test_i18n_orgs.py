"""Vérification des Phases 5 et 6 — التعريب/RTL + المؤسسات (§4.6, §4.7)."""

from __future__ import annotations

from core import i18n
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


def _add_user(owner, email, role="member"):
    return owner.post(
        "/api/admin/users",
        json={"email": email, "password": PASSWORD, "display_name": email, "role": role},
        headers={"X-Genio-CSRF": owner.csrf},
    )


# ---------------------------------------------------------------------------
# Phase 5 — i18n / RTL
# ---------------------------------------------------------------------------
def test_every_locale_has_every_key():
    report = i18n.key_report()
    assert report["ok"] is True, report["missing"]
    assert report["keys"] >= 20


def test_direction_is_data_not_a_guess():
    assert i18n.locale_info("ar-TN")["dir"] == "rtl"
    assert i18n.locale_info("ar")["dir"] == "rtl"
    assert i18n.locale_info("fr")["dir"] == "ltr"
    assert i18n.locale_info("en")["dir"] == "ltr"


def test_catalogue_is_public_before_login(server):
    _owner(server)  # accounts now exist, so /api needs a session
    anonymous = TestClient(server.app, client=("127.0.0.1", 50000))

    locales = anonymous.get("/api/i18n")
    assert locales.status_code == 200
    assert [item["id"] for item in locales.json()["locales"]] == ["ar-TN", "ar", "fr", "en"]

    derja = anonymous.get("/api/i18n/ar-TN").json()
    assert derja["dir"] == "rtl"
    assert derja["html_lang"] == "ar"
    assert derja["strings"]["action.send"] == "ابعث"

    french = anonymous.get("/api/i18n/fr").json()
    assert french["dir"] == "ltr"
    assert french["strings"]["action.send"] == "Envoyer"


def test_unknown_locale_is_rejected(server):
    client = TestClient(server.app, client=("127.0.0.1", 50000))
    assert client.get("/api/i18n/de").status_code == 400


# ---------------------------------------------------------------------------
# Phase 6 — entreprises
# ---------------------------------------------------------------------------
def test_org_can_be_created_and_listed(server):
    owner = _owner(server)
    created = owner.post(
        "/api/orgs", json={"name": "HiTech Lab TN"}, headers={"X-Genio-CSRF": owner.csrf}
    )
    assert created.status_code == 200, created.text
    org = created.json()["org"]
    assert org["members"] == 1

    listed = owner.get("/api/orgs").json()["orgs"]
    assert [item["name"] for item in listed] == ["HiTech Lab TN"]
    assert listed[0]["my_role"] == "owner"


def test_members_can_be_added_and_are_isolated(server):
    owner = _owner(server)
    org_id = owner.post(
        "/api/orgs", json={"name": "Genio Corp"}, headers={"X-Genio-CSRF": owner.csrf}
    ).json()["org"]["id"]
    _add_user(owner, "member@hitech.tn")

    added = owner.post(
        f"/api/orgs/{org_id}/members",
        json={"email": "member@hitech.tn", "role": "member"},
        headers={"X-Genio-CSRF": owner.csrf},
    )
    assert added.status_code == 200

    member = _login(server, "member@hitech.tn")
    assert [o["name"] for o in member.get("/api/orgs").json()["orgs"]] == ["Genio Corp"]
    assert member.get(f"/api/orgs/{org_id}/members").status_code == 200
    assert member.get(f"/api/orgs/{org_id}/report").status_code == 403

    outsider = _login(server, "member@hitech.tn")
    other_org = owner.post(
        "/api/orgs", json={"name": "Other"}, headers={"X-Genio-CSRF": owner.csrf}
    ).json()["org"]["id"]
    assert outsider.get(f"/api/orgs/{other_org}").status_code == 403


def test_usage_report_counts_member_tool_calls(server):
    owner = _owner(server)
    org_id = owner.post(
        "/api/orgs", json={"name": "Report Inc"}, headers={"X-Genio-CSRF": owner.csrf}
    ).json()["org"]["id"]

    owner.post(
        "/api/tools/write_file/invoke",
        json={"params": {"path": "report.txt", "content": "x"}},
        headers={"X-Genio-CSRF": owner.csrf},
    )

    report = owner.get(f"/api/orgs/{org_id}/report").json()["report"]
    assert report["members"] == 1
    assert report["tool_calls"] >= 1
    assert report["by_tool"].get("write_file", 0) >= 1


def test_org_owner_cannot_be_removed(server):
    owner = _owner(server)
    org_id = owner.post(
        "/api/orgs", json={"name": "Keep Owner"}, headers={"X-Genio-CSRF": owner.csrf}
    ).json()["org"]["id"]
    owner_id = owner.get("/api/me").json()["user"]["id"]

    refused = owner.request(
        "DELETE",
        f"/api/orgs/{org_id}/members/{owner_id}",
        headers={"X-Genio-CSRF": owner.csrf},
    )
    assert refused.status_code == 400


def test_audit_can_be_exported_as_csv(server):
    owner = _owner(server)
    owner.post(
        "/api/orgs", json={"name": "CSV Org"}, headers={"X-Genio-CSRF": owner.csrf}
    )

    export = owner.get("/api/admin/audit/export")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    lines = export.text.strip().splitlines()
    assert lines[0].startswith("id,created_at,actor,action")
    assert any("org.create" in line for line in lines)


def test_audit_export_is_admin_only(server):
    owner = _owner(server)
    _add_user(owner, "viewer@hitech.tn", role="viewer")
    viewer = _login(server, "viewer@hitech.tn")
    assert viewer.get("/api/admin/audit/export").status_code == 403
