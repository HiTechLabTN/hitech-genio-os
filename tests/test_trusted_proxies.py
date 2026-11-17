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


def _client(server, peer: str) -> TestClient:
    return TestClient(server.app, client=(peer, 50000))


def test_config_ships_with_no_trusted_proxies():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    assert config["security"].get("trusted_proxies") == []


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
