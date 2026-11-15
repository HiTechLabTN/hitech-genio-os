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
import os
from typing import Any, Dict

from fastapi import HTTPException, Request, status

TOKEN_ENV = "GENIO_API_TOKEN"
TOKEN_HEADER = "X-Genio-Token"
TOKEN_QUERY = "token"

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})

_ENV_TO_SETTING = {
    "GENIO_HOST": "host",
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


def client_is_loopback(request: Request) -> bool:
    host = (request.client.host if request.client else "") or ""
    return host in LOOPBACK_HOSTS or host.startswith("127.")


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
    if not client_is_loopback(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "API is loopback-only. Set security.api_token (or GENIO_API_TOKEN) "
                "to expose the platform safely."
            ),
        )


def require_feature(enabled: bool, feature: str, hint: str) -> None:
    """Gate a dangerous endpoint behind an explicit opt-in flag."""
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{feature} is disabled. {hint}",
        )
