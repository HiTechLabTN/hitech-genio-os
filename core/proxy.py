"""بروكسي محلي أمام المنصّة — Cloudflare Tunnel / nginx / cloudflared.

الإنتاج متاع go.hitech.tn: Cloudflare → (tunnel ولا nginx) على نفس الجهاز →
uvicorn على 127.0.0.1:8099. يعني كل الطلبات توصل من **127.0.0.1**، و بلا
هالمودويل:

* `request.client.host` = 127.0.0.1 للزوار الكل → سجل المحاولات و الـ audit
  يعمّرو IP غالط، و أي حدّ بالمعدّل يولي مشترك بين الناس الكل.
* `request.url.scheme` = http (TLS يتكسّر في Cloudflare) → الكوكي تتعمل بلا
  `Secure` في الإنتاج.

القاعدة: نصدّقو الهيدرات **غير** كي الـ peer بروحو loopback (البروكسي على نفس
الجهاز). طلب جاي من الشبكة直接 بهيدر `CF-Connecting-IP` مزيّف ما يتصدّقش.
"""

from __future__ import annotations

import ipaddress
from typing import Optional

from fastapi import Request

LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})

# Cloudflare يحطّ IP الحقيقي هنا؛ true-client-ip تستعملها CDN أخرى.
_CLIENT_IP_HEADERS = ("cf-connecting-ip", "true-client-ip")


def _valid_ip(value: str) -> Optional[str]:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def peer_host(request: Request) -> str:
    return (request.client.host if request.client else "") or ""


def from_local_proxy(request: Request) -> bool:
    """الطلب جاي من بروكسي على نفس الجهاز؟"""
    host = peer_host(request)
    return host in LOOPBACK or host.startswith("127.")


def _engine(request: Request):
    """المحرّك من scope (كان موجود) — باش نعرفو إعدادات الثقة."""
    app = request.scope.get("app")
    return getattr(getattr(app, "state", None), "engine", None)


def trusted_peer(request: Request) -> bool:
    """نصدّقو هيدرات البروكسي؟

    loopback، ولا شبكة داخلية مع أثر Cloudflare (tunnel/docker/nginx)،
    ولا CIDR معرّف في security.trusted_proxies.
    """
    if from_local_proxy(request):
        return True
    engine = _engine(request)
    if engine is None:
        return False
    from core import security

    return security.client_is_trusted(request, engine)


def client_ip(request: Request) -> str:
    """IP الحقيقي متاع الزائر، مع fallback آمن على IP الـ peer."""
    peer = peer_host(request)
    if not trusted_peer(request):
        return peer

    for header in _CLIENT_IP_HEADERS:
        raw = request.headers.get(header) or ""
        found = _valid_ip(raw.split(",")[0])
        if found:
            return found

    forwarded = request.headers.get("x-forwarded-for") or ""
    for candidate in forwarded.split(","):
        found = _valid_ip(candidate)
        if found:
            return found
    return peer


def is_https(request: Request) -> bool:
    """الطلب كان HTTPS عند المتصفّح حتى لو uvicorn يشوف http؟"""
    if request.url.scheme == "https":
        return True
    if not trusted_peer(request):
        # طلب مباشر من الشبكة: هيدراته ما تتصدّقش
        return False

    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if forwarded_proto in {"https", "wss"}:
        return True
    if forwarded_proto == "http":
        return False

    cf_visitor = (request.headers.get("cf-visitor") or "").lower()
    if "https" in cf_visitor:
        return True
    # Cloudflare دايمًا يكسّر TLS قبل الأصل، و يحطّ CF-Connecting-IP
    if request.headers.get("cf-connecting-ip"):
        return True

    return False
