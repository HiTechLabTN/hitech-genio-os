"""Auth, profile and admin endpoints — Plan v1 §4.1 / §5.

Bootstrap model: until the first account exists the platform runs exactly as
before (single local operator, already gated to loopback by Phase 0). Creating
the first account turns sessions on for every ``/api`` route.
"""

from __future__ import annotations

import hmac
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from core import auth as auth_core
from core.auth import CSRF_HEADER, SESSION_COOKIE, AuthError
from core.db import get_db

router = APIRouter(prefix="/api", tags=["auth"])

# Reachable without a session (login itself, the one-time bootstrap, and the
# UI catalogue the login screen needs before anyone is signed in).
PUBLIC_PATHS = {"/api/auth/login", "/api/auth/bootstrap", "/api/auth/status"}
PUBLIC_PREFIXES = ("/api/i18n",)
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class BootstrapRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionRevokeRequest(BaseModel):
    id: Optional[str] = None
    all_others: bool = False


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


class CreateUserRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""
    role: str = "member"


class RoleUpdateRequest(BaseModel):
    role: str


class ProfileUpdateRequest(BaseModel):
    model_config = {"populate_by_name": True}

    locale: Optional[str] = None
    register_: Optional[str] = Field(default=None, alias="register")
    technical_level: Optional[str] = None
    occupation: Optional[str] = None
    persona_pack: Optional[str] = None
    mode: Optional[str] = None
    env: Optional[str] = None
    data_sensitivity: Optional[str] = None
    goals: Optional[list] = None
    sectors: Optional[list] = None
    tools: Optional[list] = None


# ---------------------------------------------------------------------------
# Request plumbing (used by the middleware in web/server.py)
# ---------------------------------------------------------------------------
def current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with get_db() as conn:
        return auth_core.session_user(conn, token)


def enforce(request: Request, user: Optional[Dict[str, Any]]) -> None:
    """Session required once accounts exist; CSRF required on mutations."""
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return
    with get_db() as conn:
        if auth_core.user_count(conn) == 0:
            return  # bootstrap mode
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    if request.method in MUTATING_METHODS:
        supplied = request.headers.get(CSRF_HEADER, "")
        if not hmac.compare_digest(supplied, str(user.get("csrf") or "")):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid CSRF token")


def _set_session(response: Response, session: Dict[str, Any], request: Request) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session["token"],
        max_age=int(session["expires_at"] - time.time()),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )


def _session_payload(user: Dict[str, Any], session: Dict[str, Any], request: Request) -> Dict[str, Any]:
    return {
        "ok": True,
        "user": user,
        "role_label": auth_core.ROLE_LABELS.get(user["role"], user["role"]),
        "csrf": session["csrf"],
    }


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------
@router.get("/auth/status")
def auth_status(request: Request):
    """بوّابة الواجهة: واش فمّا حسابات؟ وواش أنا داخل؟ (متاح بلا جلسة)"""
    user = current_user(request)
    with get_db() as conn:
        bootstrapped = auth_core.user_count(conn) > 0
        profile = auth_core.default_profile(conn, user["id"]) if user else None
    return {
        "ok": True,
        "bootstrapped": bootstrapped,
        "authenticated": user is not None,
        "user": user,
        "role_label": auth_core.ROLE_LABELS.get(user["role"], "") if user else "",
        "profile": profile,
        "onboarding_done": int((profile or {}).get("onboarding_done") or 0),
    }


@router.post("/auth/bootstrap")
def bootstrap(payload: BootstrapRequest, request: Request, response: Response):
    with get_db() as conn:
        if auth_core.user_count(conn) > 0:
            raise HTTPException(status.HTTP_409_CONFLICT, "already bootstrapped")
        try:
            user = auth_core.create_user(
                conn, payload.email, payload.password, payload.display_name, role="owner"
            )
        except AuthError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        session = auth_core.create_session(conn, user["id"])
        auth_core.audit(conn, "auth.bootstrap", user_id=user["id"], actor=user["email"])
    _set_session(response, session, request)
    return _session_payload(user, session, request)


@router.post("/auth/login")
def login(payload: LoginRequest, request: Request, response: Response):
    with get_db() as conn:
        wait = auth_core.login_retry_after(conn, payload.email)
        if wait > 0:
            auth_core.audit(
                conn, "auth.login", actor=payload.email, status="locked", detail=f"retry_after={wait}"
            )
            conn.commit()
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"محاولات كثيرة — عاود بعد {wait} ثانية",
                headers={"Retry-After": str(wait)},
            )
        user = auth_core.authenticate(conn, payload.email, payload.password)
        if user is None:
            failures = auth_core.record_login_failure(conn, payload.email, _client_ip(request))
            auth_core.audit(
                conn, "auth.login", actor=payload.email, status="denied", detail=f"failures={failures}"
            )
            # العدد لازم يتسجّل قبل ما نرفضو الطلب (get_db ما تعملش commit وقت الاستثناء)
            conn.commit()
            if failures >= auth_core.LOGIN_MAX_ATTEMPTS:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"محاولات كثيرة — الحساب مقفول {auth_core.LOGIN_LOCKOUT // 60} دقيقة",
                    headers={"Retry-After": str(auth_core.LOGIN_LOCKOUT)},
                )
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"إيميل ولا كلمة سر غالطة (باقي {auth_core.LOGIN_MAX_ATTEMPTS - failures} محاولات)",
            )
        auth_core.clear_login_failures(conn, payload.email)
        session = auth_core.create_session(conn, user["id"])
        auth_core.audit(conn, "auth.login", user_id=user["id"], actor=user["email"])
    _set_session(response, session, request)
    return _session_payload(user, session, request)


@router.get("/auth/sessions")
def my_sessions(request: Request):
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    token = request.cookies.get(SESSION_COOKIE, "")
    with get_db() as conn:
        return {
            "ok": True,
            "sessions": auth_core.list_sessions(conn, int(user["id"]), token),
            "ttl_seconds": auth_core.SESSION_TTL,
        }


@router.post("/auth/sessions/revoke")
def revoke_sessions(payload: SessionRevokeRequest, request: Request):
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    token = request.cookies.get(SESSION_COOKIE, "")
    with get_db() as conn:
        if payload.all_others:
            removed = auth_core.revoke_other_sessions(conn, int(user["id"]), token)
        elif payload.id:
            removed = auth_core.revoke_session(conn, int(user["id"]), payload.id)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "حدّد id ولا all_others")
        if removed:
            auth_core.audit(
                conn,
                "auth.session.revoke",
                user_id=int(user["id"]),
                actor=user["email"],
                detail=f"removed={removed}",
            )
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "جلسة ما لقيناهاش")
    return {"ok": True, "removed": removed}


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with get_db() as conn:
            auth_core.delete_session(conn, token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    with get_db() as conn:
        profile = auth_core.default_profile(conn, user["id"])
    return {
        "ok": True,
        "user": user,
        "role_label": auth_core.ROLE_LABELS.get(user["role"], user["role"]),
        "profile": profile,
    }


@router.patch("/me/profile")
def update_profile(payload: ProfileUpdateRequest, request: Request):
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    updates = payload.model_dump(exclude_none=True, by_alias=True)
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ما فمّاش حتى تعديل")
    import json

    serialised = {}
    for key, value in updates.items():
        serialised[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
    serialised["updated_at"] = time.time()
    columns = ", ".join(f"{key} = ?" for key in serialised)
    with get_db() as conn:
        auth_core.default_profile(conn, user["id"])
        conn.execute(
            f"UPDATE profiles SET {columns} WHERE user_id = ?",
            (*serialised.values(), user["id"]),
        )
        profile = auth_core.default_profile(conn, user["id"])
    return {"ok": True, "profile": profile}


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
@router.get("/admin/users")
def admin_users(request: Request):
    user = current_user(request)
    if not auth_core.has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    with get_db() as conn:
        return {"ok": True, "users": auth_core.list_users(conn)}


@router.post("/admin/users")
def admin_create_user(payload: CreateUserRequest, request: Request):
    user = current_user(request)
    if not auth_core.has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    with get_db() as conn:
        try:
            created = auth_core.create_user(
                conn, payload.email, payload.password, payload.display_name, payload.role
            )
        except AuthError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        auth_core.audit(
            conn,
            "admin.user.create",
            user_id=user["id"],
            actor=user["email"],
            target=created["email"],
        )
    return {"ok": True, "user": created}


@router.post("/admin/users/{user_id}/role")
def admin_set_role(user_id: int, payload: RoleUpdateRequest, request: Request):
    user = current_user(request)
    if not auth_core.has_role(user, "owner"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "owner only")
    if payload.role not in auth_core.ROLE_RANK:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "دور غير معروف")
    with get_db() as conn:
        target = auth_core.get_user(conn, user_id)
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "المستعمل ما موجودش")
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (payload.role, user_id))
        auth_core.audit(
            conn,
            "admin.user.role",
            user_id=user["id"],
            actor=user["email"],
            target=target["email"],
            detail=payload.role,
        )
        updated = auth_core.get_user(conn, user_id)
    return {"ok": True, "user": updated}
