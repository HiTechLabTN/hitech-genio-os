"""Vérification de la Phase 2 — Onboarding + Persona (Plan v1 §4.2).

معيار القبول: مستعمل جديد يوصل لإعداد مناسب (واجهة + أدوات) من 7 أسئلة.
"""

from __future__ import annotations

from core import personas

PASSWORD = "genio-test-pass"


def _owner(server):
    from starlette.testclient import TestClient

    client = TestClient(server.app, client=("127.0.0.1", 50000))
    response = client.post(
        "/api/auth/bootstrap",
        json={"email": "owner@hitech.tn", "password": PASSWORD, "display_name": "Owner"},
    )
    client.csrf = response.json()["csrf"]
    return client


def _onboard(client, **answers):
    payload = {
        "occupation": "employee",
        "goals": ["chat"],
        "technical_level": "intermediate",
        "register": "derja",
        "env": "local",
        "data_sensitivity": "medium",
    }
    payload.update(answers)
    return client.post(
        "/api/onboarding/submit", json=payload, headers={"X-Genio-CSRF": client.csrf}
    )


def test_personas_catalogue(server):
    body = _owner(server).get("/api/personas").json()
    assert len(body["personas"]) == 8
    assert {p["id"] for p in body["personas"]} >= {"chat_general", "dev_lead", "enterprise_admin"}
    assert [m["id"] for m in body["modes"]] == ["chat", "dev", "enterprise"]


def test_freelancer_asking_for_code_gets_dev_pack(server):
    client = _owner(server)
    response = _onboard(client, occupation="freelance", goals=["code"], technical_level="advanced")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["profile"]["persona_pack"] == "dev_lead"
    assert body["profile"]["mode"] == "dev"
    assert "shell_sandboxed" in body["profile"]["tools"]
    assert body["persona"]["mode"] == "dev"
    assert body["persona"]["system_prompt"]


def test_enterprise_account_gets_enterprise_mode(server):
    body = _onboard(_owner(server), occupation="enterprise", goals=["pm"]).json()
    assert body["profile"]["persona_pack"] == "enterprise_admin"
    assert body["profile"]["mode"] == "enterprise"


def test_high_sensitivity_locks_the_shell(server):
    body = _onboard(
        _owner(server), goals=["code"], data_sensitivity="high", technical_level="advanced"
    ).json()
    assert body["profile"]["safety"]["shell"] == "deny"
    assert body["profile"]["safety"]["network"] == "deny"
    assert "shell_sandboxed" not in body["profile"]["tools"]


def test_beginner_keeps_shell_on_confirmation(server):
    body = _onboard(_owner(server), goals=["code"], technical_level="beginner").json()
    assert body["profile"]["safety"]["shell"] == "confirm"


def test_onboarding_is_persisted_on_the_profile(server):
    client = _owner(server)
    _onboard(client, occupation="student", goals=["data"])
    profile = client.get("/api/me").json()["profile"]
    assert profile["onboarding_done"] == 1
    assert profile["persona_pack"] == "business_analyst"


def test_unknown_goal_is_rejected(server):
    response = _onboard(_owner(server), goals=["hack-the-planet"])
    assert response.status_code == 400
    assert "أهداف" in response.json()["error"]


def test_mode_switch_persists(server):
    client = _owner(server)
    _onboard(client)

    switched = client.post(
        "/api/mode", json={"mode": "dev"}, headers={"X-Genio-CSRF": client.csrf}
    )
    assert switched.status_code == 200
    assert switched.json()["label"] == "وضع التطوير"
    assert client.get("/api/me").json()["profile"]["mode"] == "dev"

    refused = client.post(
        "/api/mode", json={"mode": "nope"}, headers={"X-Genio-CSRF": client.csrf}
    )
    assert refused.status_code == 400


def test_unknown_pack_falls_back_to_chat():
    resolved = personas.resolve({"persona_pack": "does-not-exist", "mode": "bogus"})
    assert resolved["pack"] == "chat_general"
    assert resolved["mode"] == "chat"


def test_seven_answers_are_enough():
    """كل سؤال في الـ wizard عندو أثر على البروفيل النهائي."""
    derived = personas.build_profile_from_onboarding(
        {
            "occupation": "founder",
            "goals": ["code"],
            "technical_level": "advanced",
            "register": "fr",
            "env": "offline",
            "data_sensitivity": "low",
        }
    )
    assert derived["locale"] == "fr"
    assert derived["env"] == "offline"
    assert derived["register"] == "fr"
    assert derived["safety"]["network"] == "allowlist"
    assert derived["onboarding_done"] == 1
