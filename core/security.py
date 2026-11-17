"""Security baseline — Plan v1 (المرحلة 0) / Plan v2 (Sprint 0).

Three guarantees, enforced in one place so they cannot drift from the API:

1. ``/api/*`` answers **loopback clients only** unless an API token is configured.
2. A configured token must be presented (``X-Genio-Token``, ``Authorization:
   Bearer`` or ``?token=``), compared in constant time.
3. Dangerous capabilities (``/api/shell``, ``/api/update/apply``) stay **off**
   unless explicitly enabled in ``config.json`` or through the environment.

Environment always wins over ``config.json`` so a service unit can tighten a
deployment without editing files: ``GENIO_API_TOKEN``, ``GENIO_HOST``,
``GENIO_ENABLE_SHELL``, ``GENIO_ENABLE_UPDATE``.
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import os
from typing import Any, Dict, List

from fastapi import HTTPException, Request, status

TOKEN_ENV = "GENIO_API_TOKEN"
TRUSTED_PROXIES_ENV = "GENIO_TRUSTED_PROXIES"
TRUSTED_NETWORKS_ENV = "GENIO_TRUSTED_NETWORKS"

# شبكات داخلية (docker bridge، شبكة السيرفر، cloudflared محلي…).
# الطلب منها يولي موثوق **كان** يحمل أثر Cloudflare (CF-Connecting-IP / Cf-Access).
DEFAULT_TRUSTED_NETWORKS = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")

# أي واحد من هالهيدرات يعني الطلب عدّى من Cloudflare قبل ما يوصلنا
CLOUDFLARE_HEADERS = (
    "cf-connecting-ip",
    "cf-access-jwt-assertion",
    "cf-access-client-id",
    "cf-ray",
    "cf-visitor",
    "true-client-ip",
)
TOKEN_HEADER = "X-Genio-Token"
TOKEN_QUERY = "token"

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})

_ENV_TO_SETTING = {
    "GENIO_HOST": "host",
    "GENIO_TRUSTED_PROXIES": "trusted_proxies",
    "GENIO_ENABLE_SHELL": "enable_shell",
    "GENIO_ENABLE_UPDATE": "enable_update",
}

# Browsers send the token as a header; a query parameter is accepted for curl
# and for the first visit of a remote deployment.
_TRUTHY = {"1", "true", "yes", "on"}


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in _TRUTHY
    return bool(value)


def settings(engine: Any) -> Dict[str, Any]:
    """Effective security settings: config.json overridden by the environment."""
    block: Dict[str, Any] = dict((getattr(engine, "config", None) or {}).get("security") or {})
    if os.environ.get(TOKEN_ENV):
        block["api_token"] = os.environ[TOKEN_ENV]
    for env_key, setting in _ENV_TO_SETTING.items():
        if os.environ.get(env_key):
            block[setting] = os.environ[env_key]
    return block


def api_token(engine: Any) -> str:
    return str(settings(engine).get("api_token") or "").strip()


def bind_host(engine: Any) -> str:
    """Loopback by default: exposing the platform must be a deliberate act."""
    return str(settings(engine).get("host") or "127.0.0.1").strip() or "127.0.0.1"


def shell_enabled(engine: Any) -> bool:
    return _flag(settings(engine).get("enable_shell"))


def update_enabled(engine: Any) -> bool:
    return _flag(settings(engine).get("enable_update"))


LOGGER = logging.getLogger("genio.security")


def client_is_loopback(request: Request) -> bool:
    host = (request.client.host if request.client else "") or ""
    return host in LOOPBACK_HOSTS or host.startswith("127.")


def trusted_proxies(engine: Any) -> List[str]:
    """CIDR/IPs متاع البروكسي (cloudflared / nginx / docker) — config أو env."""
    raw = os.environ.get(TRUSTED_PROXIES_ENV)
    if raw is None:
        raw = settings(engine).get("trusted_proxies") or ""
    if isinstance(raw, (list, tuple)):
        items = [str(item) for item in raw]
    else:
        items = str(raw).replace("\n", ",").split(",")
    return [item.strip() for item in items if item.strip()]


def trusted_networks(engine: Any) -> List[str]:
    """الشبكات الداخلية اللي نصدّقو منها هيدرات Cloudflare."""
    raw = os.environ.get(TRUSTED_NETWORKS_ENV)
    if raw is None:
        raw = settings(engine).get("trusted_networks")
    if raw is None:
        return list(DEFAULT_TRUSTED_NETWORKS)
    if isinstance(raw, (list, tuple)):
        items = [str(item) for item in raw]
    else:
        items = str(raw).replace("\n", ",").split(",")
    cleaned = [item.strip() for item in items if item.strip()]
    return cleaned or list(DEFAULT_TRUSTED_NETWORKS)


def cloudflare_evidence(request: Request) -> bool:
    """الطلب جاي عبر Cloudflare؟ (هيدر نشرو فيه CF، ماشي X-Forwarded-For)"""
    return any((request.headers.get(name) or "").strip() for name in CLOUDFLARE_HEADERS)


def _matches(host: str, entries: List[str]) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    for entry in entries:
        try:
            if address in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def client_is_trusted(request: Request, engine: Any) -> bool:
    """loopback، ولا بروكسي معرّف، ولا شبكة داخلية + أثر Cloudflare.

    الهدف: المنصّة تخدم وراء tunnel حتى كان ما تعرفش الـ CIDR متاعو بالضبط،
    بلا ما تتحلّ لطلب جاي من الإنترنت (حتى لو زيّد هيدرات CF).
    """
    host = (request.client.host if request.client else "") or ""
    if client_is_loopback(request):
        return True
    if _matches(host, trusted_proxies(engine)):
        return True
    return _matches(host, trusted_networks(engine)) and cloudflare_evidence(request)


def supplied_token(request: Request) -> str:
    supplied = (request.headers.get(TOKEN_HEADER) or "").strip()
    if not supplied:
        authorization = (request.headers.get("authorization") or "").strip()
        if authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
    if not supplied:
        supplied = (request.query_params.get(TOKEN_QUERY) or "").strip()
    return supplied


def check_api_access(request: Request, engine: Any) -> None:
    """Raise 401/403 when the caller may not touch ``/api/*``."""
    token = api_token(engine)
    if token:
        if not hmac.compare_digest(supplied_token(request), token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing API token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return
    if not client_is_trusted(request, engine):
        peer = ((request.client.host if request.client else "") or "?").strip()
        LOGGER.warning("blocked /api request from untrusted peer %s (%s)", peer, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"API is not reachable from this address (peer {peer}). "
                "Traffic must come from loopback, from security.trusted_networks "
                "with Cloudflare headers, or from security.trusted_proxies. "
                "Otherwise set security.api_token (GENIO_API_TOKEN)."
            ),
        )


def require_feature(enabled: bool, feature: str, hint: str) -> None:
    """Gate a dangerous endpoint behind an explicit opt-in flag."""
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{feature} is disabled. {hint}",
        )
