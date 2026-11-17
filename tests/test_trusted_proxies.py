"""الوصول عبر الدومين: البروكسي المحلي لازم يتعامل كـ loopback، أما غيره لا.

السيناريو الحقيقي (go.hitech.tn): Cloudflare → tunnel/nginx/docker → uvicorn،
فالـ peer ماشي 127.0.0.1، و المنصّة كانت ترد 403 «loopback-only» و الواجهة
تبقى على شاشة الدخول بلا كاتالوغ.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from core import security

ROOT = Path(__file__).resolve().parent.parent


def _client(server, peer: str, port: int = 50000) -> TestClient:
    return TestClient(server.app, client=(peer, port))


def test_config_ships_with_no_trusted_proxies():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    assert config["security"].get("trusted_proxies") == []


def test_config_ships_with_private_networks_for_the_tunnel():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    assert config["security"]["trusted_networks"] == [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]


def test_default_networks_apply_when_config_is_silent(server, monkeypatch):
    monkeypatch.setattr(server.engine, "config", {"security": {}}, raising=False)
    monkeypatch.delenv("GENIO_TRUSTED_NETWORKS", raising=False)
    assert security.trusted_networks(server.engine) == list(security.DEFAULT_TRUSTED_NETWORKS)


def test_unknown_peer_is_rejected_with_an_actionable_message(server):
    client = _client(server, "203.0.113.5")
    response = client.get("/api/i18n/fr")
    assert response.status_code == 403
    error = response.json()["error"]
    assert "203.0.113.5" in error
    assert "trusted_proxies" in error or "GENIO_TRUSTED_PROXIES" in error


def test_proxy_cidr_is_allowed_when_configured(server, monkeypatch):
    monkeypatch.setenv("GENIO_TRUSTED_PROXIES", "172.17.0.0/16")
    client = _client(server, "172.17.0.2")
    response = client.get("/api/i18n/fr")
    assert response.status_code == 200
    assert response.json()["dir"] == "ltr"


def test_cidr_does_not_widen_to_other_networks(server, monkeypatch):
    monkeypatch.setenv("GENIO_TRUSTED_PROXIES", "172.17.0.0/16")
    outsider = _client(server, "203.0.113.5")
    assert outsider.get("/api/i18n/fr").status_code == 403


def test_ipv6_default_loopback_still_works(server):
    client = _client(server, "::1")
    assert client.get("/api/i18n/ar-TN").status_code == 200


def test_loopback_is_always_trusted(server):
    client = _client(server, "127.0.0.1")
    assert client.get("/api/i18n/en").status_code == 200


def test_tunnel_peer_from_docker_with_cloudflare_headers_is_allowed(server):
    """الحالة الحقيقية: cloudflared/docker يكلّم من 172.x و يحطّ CF-Connecting-IP."""
    client = _client(server, "172.17.0.2")
    response = client.get("/api/i18n/fr", headers={"CF-Connecting-IP": "41.226.10.7"})
    assert response.status_code == 200
    assert response.json()["strings"]["auth.title.login"]


def test_tunnel_peer_from_10_x_with_access_jwt_is_allowed(server):
    """Cf-Access-Jwt-Assertion كافي كأثر (بلا ما نعرفو الـ CIDR بالضبط)."""
    client = _client(server, "10.0.0.5")
    response = client.get(
        "/api/i18n/ar-TN", headers={"Cf-Access-Jwt-Assertion": "eyJhbGciOi.test.token"}
    )
    assert response.status_code == 200
    assert response.json()["dir"] == "rtl"


@pytest.mark.parametrize(
    "peer",
    ["172.17.0.2", "10.0.0.5", "192.168.0.113", "100.64.1.2", "169.254.1.1", "fd00::1", "fe80::1"],
)
def test_any_internal_peer_with_cloudflare_headers_is_allowed(server, peer):
    """بلا حتى إعداد: كل شبكة داخلية + هيدر CF تتصدّق."""
    response = _client(server, peer).get("/api/i18n/fr", headers={"CF-Connecting-IP": "41.226.10.7"})
    assert response.status_code == 200, peer


@pytest.mark.parametrize("peer", ["41.226.10.7", "8.8.8.8", "203.0.113.5", "198.51.100.7"])
def test_internet_peer_with_cloudflare_headers_stays_blocked(server, peer):
    response = _client(server, peer).get(
        "/api/i18n/fr",
        headers={"CF-Connecting-IP": "41.226.10.7", "X-Forwarded-For": "41.226.10.7"},
    )
    assert response.status_code == 403, peer


def test_peer_rewritten_by_uvicorn_is_trusted(server):
    """uvicorn بعـ --proxy-headers يحطّ port 0: الـ peer الأصلي كان في allowlist."""
    client = _client(server, "41.226.10.7", port=0)
    response = client.get(
        "/api/i18n/ar-TN",
        headers={"CF-Connecting-IP": "41.226.10.7", "X-Forwarded-For": "41.226.10.7"},
    )
    assert response.status_code == 200
    assert response.json()["dir"] == "rtl"


def test_rewritten_peer_without_cloudflare_headers_stays_blocked(server):
    client = _client(server, "41.226.10.7", port=0)
    assert client.get("/api/i18n/fr", headers={"X-Forwarded-For": "41.226.10.7"}).status_code == 403


def test_private_peer_without_cloudflare_headers_stays_blocked(server):
    client = _client(server, "172.17.0.2")
    assert client.get("/api/i18n/fr").status_code == 403


def test_forwarded_for_alone_is_not_cloudflare_evidence(server):
    client = _client(server, "172.17.0.2")
    response = client.get("/api/i18n/fr", headers={"X-Forwarded-For": "41.226.10.7"})
    assert response.status_code == 403


def test_internet_peer_with_forged_cloudflare_headers_is_blocked(server):
    """طلب من الإنترنت ما يولي موثوق حتى لو زيّد هيدرات CF."""
    client = _client(server, "203.0.113.5")
    response = client.get(
        "/api/i18n/fr",
        headers={"CF-Connecting-IP": "127.0.0.1", "CF-Ray": "85abc", "Cf-Access-Jwt-Assertion": "x"},
    )
    assert response.status_code == 403
    assert "203.0.113.5" in response.json()["error"]


def test_real_client_ip_is_read_through_the_tunnel(server):
    from core import proxy
    from starlette.requests import Request

    raw = [
        (b"cf-connecting-ip", b"41.226.10.7"),
        (b"x-forwarded-proto", b"https"),
    ]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/status",
        "raw_path": b"/api/status",
        "query_string": b"",
        "headers": raw,
        "client": ("172.17.0.2", 50000),
        "server": ("127.0.0.1", 8099),
        "app": server.app,
    }
    req = Request(scope)
    assert proxy.client_ip(req) == "41.226.10.7"
    assert proxy.is_https(req) is True


def test_real_client_ip_from_internet_is_the_peer(server):
    from core import proxy
    from starlette.requests import Request

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/status",
        "raw_path": b"/api/status",
        "query_string": b"",
        "headers": [(b"cf-connecting-ip", b"1.2.3.4")],
        "client": ("203.0.113.5", 50000),
        "server": ("127.0.0.1", 8099),
        "app": server.app,
    }
    req = Request(scope)
    assert proxy.client_ip(req) == "203.0.113.5"
    assert proxy.is_https(req) is False


def test_matches_handles_plain_ips_and_garbage(monkeypatch):
    assert security._matches("172.17.0.2", ["172.17.0.0/16"]) is True
    assert security._matches("10.1.2.3", ["172.17.0.0/16"]) is False
    assert security._matches("10.1.2.3", ["10.1.2.3"]) is True
    assert security._matches("not-an-ip", ["10.0.0.0/8"]) is False
    assert security._matches("10.1.2.3", ["garbage", "10.0.0.0/8"]) is True


def test_env_wins_over_config(server, monkeypatch):
    monkeypatch.setattr(server.engine, "config", {"security": {"trusted_proxies": ["10.0.0.0/8"]}}, raising=False)
    assert security.trusted_proxies(server.engine) == ["10.0.0.0/8"]
    monkeypatch.setenv("GENIO_TRUSTED_PROXIES", "172.17.0.0/16, 192.168.0.0/16")
    assert security.trusted_proxies(server.engine) == ["172.17.0.0/16", "192.168.0.0/16"]
