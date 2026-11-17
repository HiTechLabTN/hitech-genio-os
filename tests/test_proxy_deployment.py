"""الإنتاج على go.hitech.tn: المنصّة ورى Cloudflare / nginx.

كل الطلبات توصل لـ uvicorn من 127.0.0.1 (tunnel ولا nginx)، و TLS يتكسّر في
Cloudflare. بلا هالتصحيح: IP الزائر = 127.0.0.1 للكل، و الكوكي بلا `Secure`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

from core import proxy

ROOT = Path(__file__).resolve().parent.parent
PASSWORD = "genio-demo-2026"


def _request(headers=None, client=("127.0.0.1", 50000), scheme="http") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": scheme,
        "path": "/api/health",
        "raw_path": b"/api/health",
        "query_string": b"",
        "headers": raw,
        "client": client,
        "server": ("127.0.0.1", 8099),
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# IP الحقيقي
# ---------------------------------------------------------------------------
def test_cloudflare_header_is_used_when_the_peer_is_the_local_proxy():
    req = _request({"CF-Connecting-IP": "41.226.10.7"})
    assert proxy.client_ip(req) == "41.226.10.7"


def test_forwarded_for_chain_takes_the_first_hop():
    req = _request({"X-Forwarded-For": "41.226.10.7, 162.158.1.1, 127.0.0.1"})
    assert proxy.client_ip(req) == "41.226.10.7"


def test_spoofed_headers_are_ignored_from_the_open_internet():
    req = _request({"CF-Connecting-IP": "1.2.3.4"}, client=("203.0.113.9", 1234))
    assert proxy.client_ip(req) == "203.0.113.9"


def test_garbage_header_falls_back_to_the_peer():
    req = _request({"CF-Connecting-IP": "not-an-ip"})
    assert proxy.client_ip(req) == "127.0.0.1"


def test_ipv6_is_normalised():
    req = _request({"CF-Connecting-IP": "2a01:cb00::1"})
    assert proxy.client_ip(req) == "2a01:cb00::1"


# ---------------------------------------------------------------------------
# HTTPS ورى البروكسي
# ---------------------------------------------------------------------------
def test_https_is_detected_from_the_forwarded_proto():
    assert proxy.is_https(_request({"X-Forwarded-Proto": "https"})) is True
    assert proxy.is_https(_request({"X-Forwarded-Proto": "http"})) is False


def test_https_is_detected_from_cloudflare_headers():
    assert proxy.is_https(_request({"CF-Visitor": '{"scheme":"https"}'})) is True
    assert proxy.is_https(_request({"CF-Connecting-IP": "41.226.10.7"})) is True


def test_https_headers_from_a_remote_peer_are_not_trusted():
    req = _request({"X-Forwarded-Proto": "https"}, client=("203.0.113.9", 1234))
    assert proxy.is_https(req) is False


def test_session_cookie_is_secure_when_cloudflare_terminates_tls(loopback):
    loopback.post(
        "/api/auth/bootstrap",
        json={"email": "owner@hitech.tn", "password": PASSWORD},
    )
    proxied = loopback.post(
        "/api/auth/login",
        json={"email": "owner@hitech.tn", "password": PASSWORD},
        headers={"X-Forwarded-Proto": "https", "CF-Connecting-IP": "41.226.10.7"},
    )
    assert proxied.status_code == 200
    cookie = proxied.headers["set-cookie"].lower()
    assert "genio_session" in cookie
    assert "secure" in cookie


def test_session_cookie_stays_plain_on_plain_http(loopback):
    loopback.post(
        "/api/auth/bootstrap",
        json={"email": "owner@hitech.tn", "password": PASSWORD},
    )
    plain = loopback.post(
        "/api/auth/login",
        json={"email": "owner@hitech.tn", "password": PASSWORD},
    )
    assert plain.status_code == 200
    assert "secure" not in plain.headers["set-cookie"].lower()


# ---------------------------------------------------------------------------
# ملفات النشر على سيرفر TN
# ---------------------------------------------------------------------------
def test_systemd_unit_runs_from_the_production_directory():
    unit = (ROOT / "deployment" / "genio-os.service").read_text(encoding="utf-8")
    assert "WorkingDirectory=/data/genio-os" in unit
    assert "Environment=GENIO_DATA_DIR=/data/genio-os" in unit
    assert "--host 127.0.0.1" in unit
    # بلا proxy headers في ExecStart: كان uvicorn يعوّض request.client بعنوان
    # الزائر، فالـ peer loopback يبان عام و يتصدّ 403. core/proxy.py يعالجهم.
    exec_start = next(line for line in unit.splitlines() if line.startswith("ExecStart="))
    assert "--proxy-headers" not in exec_start
    assert "--forwarded-allow-ips" not in exec_start


def test_nginx_vhost_keeps_sse_unbuffered_and_forwards_the_real_ip():
    conf = (ROOT / "deployment" / "nginx-go.hitech.tn.conf").read_text(encoding="utf-8")
    assert "server_name go.hitech.tn" in conf
    assert "proxy_buffering off" in conf
    assert "CF-Connecting-IP" in conf
    assert "proxy_pass http://127.0.0.1:8099" in conf
    assert "proxy_read_timeout 3600s" in conf


def test_deployment_readme_documents_the_domain_and_directory():
    readme = (ROOT / "deployment" / "README.md").read_text(encoding="utf-8")
    assert "go.hitech.tn" in readme
    assert "/data/genio-os" in readme
    assert "cloudflared" in readme


def test_api_token_is_not_required_behind_the_local_proxy(loopback):
    """ورى tunnel/nginx الـ peer هو 127.0.0.1 → /api يخدم بلا token."""
    response = loopback.get("/api/i18n/fr")
    assert response.status_code == 200
