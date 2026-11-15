"""Vérification de la Phase 4 — الأوضاع + Model Router + RAG (§4.3, §4.5)."""

from __future__ import annotations

from core import rag, router as model_router
from starlette.testclient import TestClient

PASSWORD = "genio-test-pass"

DOC = """
# Docker sur le serveur

نستعملو `docker compose up -d` باش نشغلو الحاويات، ومبعد `docker ps` للتحقق.

# النسخ الاحتياطي

كل ليلة نعملو tar للمجلد memory ونحفظوه برا السيرفر.
"""


def _owner(server, email="owner@hitech.tn"):
    client = TestClient(server.app, client=("127.0.0.1", 50000))
    response = client.post(
        "/api/auth/bootstrap",
        json={"email": email, "password": PASSWORD, "display_name": "Owner"},
    )
    client.csrf = response.json()["csrf"]
    return client


def _login(server, email):
    client = TestClient(server.app, client=("127.0.0.1", 50000))
    client.csrf = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["csrf"]
    return client


def _ingest(client, name="ops.md", body=DOC, license="internal"):
    return client.post(
        "/api/rag/ingest",
        json={"name": name, "body": body, "license": license},
        headers={"X-Genio-CSRF": client.csrf},
    )


def test_ingest_and_search_return_citations(server):
    client = _owner(server)
    ingested = _ingest(client)
    assert ingested.status_code == 200, ingested.text
    body = ingested.json()
    assert body["chunks"] >= 2
    assert body["license"] == "internal"

    found = client.post(
        "/api/rag/search",
        json={"query": "docker compose"},
        headers={"X-Genio-CSRF": client.csrf},
    ).json()
    assert found["count"] >= 1
    top = found["results"][0]
    assert top["source"] == "ops.md"
    assert "internal" in top["citation"]
    assert top["score"] > 0
    assert "[ops.md#" in found["context"]


def test_unknown_licence_is_refused(server):
    response = _ingest(_owner(server), license="all-rights-reserved")
    assert response.status_code == 400
    assert "ترخيص" in response.json()["error"]


def test_empty_source_is_refused(server):
    response = _ingest(_owner(server), body="   ")
    assert response.status_code == 400


def test_sources_are_isolated_between_users(server):
    owner = _owner(server)
    _ingest(owner)
    owner.post(
        "/api/admin/users",
        json={"email": "member@hitech.tn", "password": PASSWORD, "role": "member"},
        headers={"X-Genio-CSRF": owner.csrf},
    )

    member = _login(server, "member@hitech.tn")
    assert member.get("/api/rag/sources").json()["sources"] == []
    found = member.post(
        "/api/rag/search",
        json={"query": "docker"},
        headers={"X-Genio-CSRF": member.csrf},
    ).json()
    assert found["count"] == 0


def test_source_can_be_deleted(server):
    client = _owner(server)
    source_id = _ingest(client).json()["source_id"]

    deleted = client.request(
        "DELETE",
        f"/api/rag/sources/{source_id}",
        headers={"X-Genio-CSRF": client.csrf},
    )
    assert deleted.status_code == 200
    assert client.get("/api/rag/sources").json()["sources"] == []


def test_chunking_keeps_headings():
    chunks = rag.split_chunks(DOC)
    assert chunks[0]["heading"] == "Docker sur le serveur"
    assert any(chunk["heading"] == "النسخ الاحتياطي" for chunk in chunks)


def test_router_uses_default_models_without_profile():
    plan = model_router.plan(None, "code")
    assert plan["model"] == model_router.DEFAULT_MODELS["code"]
    assert plan["status"] == "ok"


def test_router_reads_the_persona_policy():
    profile = {"persona_pack": "dev_lead", "mode": "dev", "safety": {}}
    plan = model_router.plan(profile, "code")
    assert plan["model"] == "qwen2.5-coder:14b-32k"
    assert plan["source"] == "profile"


def test_router_falls_back_when_model_is_missing():
    plan = model_router.plan(
        None, "code", available=["gemma4:12b-32k"], ollama_online=True
    )
    assert plan["status"] == "fallback"
    assert plan["model"] == "gemma4:12b-32k"
    assert plan["fallback_used"] is True


def test_router_reports_offline_clearly():
    plan = model_router.plan(None, "chat", ollama_online=False)
    assert plan["status"] == "offline"
    assert plan["model"] is None
    assert "Ollama" in plan["message"]


def test_experience_endpoint_matches_the_profile(server):
    client = _owner(server)
    client.post(
        "/api/onboarding/submit",
        json={
            "occupation": "freelance",
            "goals": ["code"],
            "technical_level": "advanced",
            "register": "derja",
            "env": "offline",
            "data_sensitivity": "low",
        },
        headers={"X-Genio-CSRF": client.csrf},
    )

    experience = client.get("/api/experience").json()
    assert experience["mode"] == "dev"
    assert experience["mode_label"] == "وضع التطوير"
    assert "shell_sandboxed" in experience["tools"]
    assert experience["models"]["code"].startswith("qwen2.5-coder")
    assert [m["id"] for m in experience["modes"]] == ["chat", "dev", "enterprise"]


def test_router_plan_endpoint(server):
    client = _owner(server)
    plan = client.get("/api/router/plan", params={"task": "code"}).json()["plan"]
    assert plan["task"] == "code"
    assert plan["model"]
