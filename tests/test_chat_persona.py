"""مسار المحادثة يمرّ في الشخصية والـ model router — المرحلة 4 (§4.3 / §4.5).

قبل هذي البصّة كان ``/api/task`` يضرب Ollama مباشرة بـ ``primary_model``،
بلا شخصية وبلا سياسة أمان: يعني المراحل 2/3/4 كانو خارج المسار الحقيقي.
"""

from __future__ import annotations

import json

import pytest

from core.engine import GenioEngine

ONBOARDING = {
    "occupation": "freelance",
    "goals": ["code"],
    "technical_level": "advanced",
    "register": "derja",
    "env": "local",
    "data_sensitivity": "low",
}


def _onboard(client, **overrides):
    """bootstrap + onboarding، ونرجّعو CSRF متاع الجلسة."""
    response = client.post(
        "/api/auth/bootstrap",
        json={"email": "dev@genio.tn", "password": "genio-demo-2026"},
    )
    assert response.status_code == 200, response.text
    csrf = response.json()["csrf"]
    payload = {**ONBOARDING, **overrides}
    done = client.post("/api/onboarding/submit", json=payload, headers={"X-Genio-CSRF": csrf})
    assert done.status_code == 200, done.text
    return csrf


def _fake_ollama(monkeypatch, server, *, online: bool, models=None):
    async def _status():
        return {"online": online, "models": models or [], "details": [], "host": "test"}

    monkeypatch.setattr(server.engine, "check_ollama_status", _status)


# ---------------------------------------------------------------------------
# المحرّك: سياسة الـ shell
# ---------------------------------------------------------------------------
def test_engine_never_runs_run_cmd_when_shell_is_denied(tmp_path, monkeypatch):
    engine = GenioEngine()
    monkeypatch.setattr(engine, "workspace", tmp_path)
    marker = tmp_path / "must-not-exist.txt"
    actions = engine.execute_tools_in_response(
        f"<run_cmd>touch {marker}</run_cmd>", allow_shell=False
    )
    assert actions and actions[0]["type"] == "run_cmd"
    assert actions[0]["status"] == "blocked"
    assert not marker.exists()


def test_engine_still_runs_run_cmd_when_allowed(tmp_path, monkeypatch):
    engine = GenioEngine()
    monkeypatch.setattr(engine, "workspace", tmp_path)
    marker = tmp_path / "created.txt"
    actions = engine.execute_tools_in_response(
        f"<run_cmd>touch {marker}</run_cmd>", allow_shell=True
    )
    assert actions[0]["status"] == "success"
    assert marker.exists()


# ---------------------------------------------------------------------------
# الـ API: persona + plan يوصّلو للمحرّك
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sensitivity", ["high"])
def test_sensitive_persona_blocks_shell_in_the_chat_path(loopback, server, monkeypatch, sensitivity):
    csrf = _onboard(loopback, data_sensitivity=sensitivity)
    _fake_ollama(monkeypatch, server, online=True, models=["gemma4:12b-32k"])

    captured = {}

    async def fake_stream(agent_id, prompt, model_override=None, **kwargs):
        captured.update(kwargs)
        captured["model_override"] = model_override
        yield "data: " + json.dumps({"event": "done", "actions": []}) + "\n\n"

    monkeypatch.setattr(server.engine, "stream_task_events", fake_stream)

    response = loopback.post(
        "/api/task",
        json={"agent_id": "Genio-Rayes", "prompt": "اكتب لي سكريبت"},
        headers={"X-Genio-CSRF": csrf},
    )
    assert response.status_code == 200, response.text
    assert captured["allow_shell"] is False
    assert captured["persona"]["pack"]
    assert captured["model_plan"]["model"]
    assert captured["persona"]["system_prompt"]


def test_low_sensitivity_persona_keeps_shell(loopback, server, monkeypatch):
    csrf = _onboard(loopback, data_sensitivity="low", technical_level="advanced")
    _fake_ollama(monkeypatch, server, online=True, models=["gemma4:12b-32k"])

    captured = {}

    async def fake_stream(agent_id, prompt, model_override=None, **kwargs):
        captured.update(kwargs)
        yield "data: " + json.dumps({"event": "done", "actions": []}) + "\n\n"

    monkeypatch.setattr(server.engine, "stream_task_events", fake_stream)
    loopback.post(
        "/api/task",
        json={"prompt": "شغّل tests"},
        headers={"X-Genio-CSRF": csrf},
    )
    assert captured["allow_shell"] is True


def test_offline_router_returns_a_clear_message(loopback, server, monkeypatch):
    csrf = _onboard(loopback)
    _fake_ollama(monkeypatch, server, online=False)

    response = loopback.post(
        "/api/task",
        json={"prompt": "مرحبا"},
        headers={"X-Genio-CSRF": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "Ollama" in body["error"]


def test_stream_reports_the_offline_plan_as_an_sse_error(loopback, server, monkeypatch):
    csrf = _onboard(loopback)
    _fake_ollama(monkeypatch, server, online=False)

    with loopback.stream(
        "POST",
        "/api/task/stream",
        json={"prompt": "مرحبا"},
        headers={"X-Genio-CSRF": csrf},
    ) as response:
        events = [line for line in response.iter_lines() if line.strip()]

    payload = json.loads(events[0][len("data: "):])
    assert payload["event"] == "error"
    assert "Ollama" in payload["error"]


def test_persona_prompt_reaches_the_model_payload(loopback, server, monkeypatch):
    """نبرة الشخصية لازم توصل للـ system prompt، ماشي غير للموديل."""
    csrf = _onboard(loopback)
    _fake_ollama(monkeypatch, server, online=True, models=["gemma4:12b-32k"])

    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            yield json.dumps({"message": {"content": "سلام"}, "done": True})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, method, url, json=None):
            seen["payload"] = json
            return FakeResponse()

    monkeypatch.setattr("core.engine.httpx.AsyncClient", FakeClient)

    with loopback.stream(
        "POST",
        "/api/task/stream",
        json={"prompt": "مرحبا"},
        headers={"X-Genio-CSRF": csrf},
    ) as response:
        list(response.iter_lines())

    system_prompt = seen["payload"]["messages"][0]["content"]
    assert seen["payload"]["model"]
    assert "Genio" in system_prompt or len(system_prompt) > 200
