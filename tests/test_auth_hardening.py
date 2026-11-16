"""قفل المحاولات وإدارة الجلسات — تقوية المرحلة 1 (v1 §4.1).

الجلسة كانت 7 أيام بلا حدّ للمحاولات: على جهاز مشترك ولا عبر tunnel،
كلمة السر تتخمّن بلا عقاب. هنا نتحقّقو من 429 + إبطال الجلسات.
"""

from __future__ import annotations

from starlette.testclient import TestClient

PASSWORD = "genio-demo-2026"


def _bootstrap(client):
    response = client.post(
        "/api/auth/bootstrap", json={"email": "owner@genio.tn", "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf"]


def test_login_locks_after_five_failures(loopback):
    _bootstrap(loopback)
    for _ in range(4):
        response = loopback.post(
            "/api/auth/login", json={"email": "owner@genio.tn", "password": "wrong-pass-1"}
        )
        assert response.status_code == 401
        assert "محاولات" in response.json()["error"]

    locked = loopback.post(
        "/api/auth/login", json={"email": "owner@genio.tn", "password": "wrong-pass-1"}
    )
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0

    # حتى بالكلمة الصحيحة: القفل يمنع المحاولة
    still_locked = loopback.post(
        "/api/auth/login", json={"email": "owner@genio.tn", "password": PASSWORD}
    )
    assert still_locked.status_code == 429


def test_successful_login_clears_the_failure_counter(loopback):
    _bootstrap(loopback)
    for _ in range(3):
        loopback.post(
            "/api/auth/login", json={"email": "owner@genio.tn", "password": "wrong-pass-1"}
        )
    ok = loopback.post("/api/auth/login", json={"email": "owner@genio.tn", "password": PASSWORD})
    assert ok.status_code == 200

    after = loopback.post(
        "/api/auth/login", json={"email": "owner@genio.tn", "password": "wrong-pass-1"}
    )
    assert after.status_code == 401  # عاد العدّاد من الصفر، ماشي 429


def test_lockout_is_per_email(loopback):
    _bootstrap(loopback)
    for _ in range(5):
        loopback.post(
            "/api/auth/login", json={"email": "owner@genio.tn", "password": "wrong-pass-1"}
        )
    other = loopback.post(
        "/api/auth/login", json={"email": "someone@genio.tn", "password": "wrong-pass-1"}
    )
    assert other.status_code == 401  # إيميل آخر ما تقفلش


def test_sessions_can_be_listed_and_revoked(server):
    first = TestClient(server.app, client=("127.0.0.1", 50000))
    csrf = _bootstrap(first)

    second = TestClient(server.app, client=("127.0.0.1", 50000))
    assert second.post(
        "/api/auth/login", json={"email": "owner@genio.tn", "password": PASSWORD}
    ).status_code == 200

    sessions = first.get("/api/auth/sessions").json()["sessions"]
    assert len(sessions) == 2
    assert sum(1 for item in sessions if item["current"]) == 1

    revoked = first.post(
        "/api/auth/sessions/revoke", json={"all_others": True}, headers={"X-Genio-CSRF": csrf}
    )
    assert revoked.status_code == 200
    assert revoked.json()["removed"] == 1

    assert second.get("/api/auth/status").json()["authenticated"] is False
    assert first.get("/api/auth/status").json()["authenticated"] is True


def test_revoking_a_single_session_by_id(server):
    first = TestClient(server.app, client=("127.0.0.1", 50000))
    csrf = _bootstrap(first)
    second = TestClient(server.app, client=("127.0.0.1", 50000))
    second.post("/api/auth/login", json={"email": "owner@genio.tn", "password": PASSWORD})

    target = next(item for item in first.get("/api/auth/sessions").json()["sessions"] if not item["current"])
    response = first.post(
        "/api/auth/sessions/revoke",
        json={"id": target["id"]},
        headers={"X-Genio-CSRF": csrf},
    )
    assert response.status_code == 200
    assert response.json()["removed"] == 1


def test_unknown_session_id_is_a_404(loopback):
    csrf = _bootstrap(loopback)
    response = loopback.post(
        "/api/auth/sessions/revoke", json={"id": "nope"}, headers={"X-Genio-CSRF": csrf}
    )
    assert response.status_code == 404


def test_revoke_requires_csrf(loopback):
    _bootstrap(loopback)
    response = loopback.post("/api/auth/sessions/revoke", json={"all_others": True})
    assert response.status_code == 403
