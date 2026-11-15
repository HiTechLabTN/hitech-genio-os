"""Users, sessions and RBAC — Plan v1 §4.1.

Passwords use ``hashlib.scrypt`` from the standard library: no extra dependency
to ship on an offline machine, and a memory-hard KDF. A session is an opaque
token stored in an HttpOnly cookie plus a CSRF token the browser must echo on
mutations.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROLES = ("viewer", "member", "admin", "owner")
ROLE_RANK = {role: rank for rank, role in enumerate(ROLES)}
ROLE_LABELS = {
    "owner": "المالك",
    "admin": "مدير",
    "member": "عضو",
    "viewer": "مشاهد",
}

SESSION_COOKIE = "genio_session"
CSRF_HEADER = "X-Genio-CSRF"
SESSION_TTL = 7 * 24 * 3600
MIN_PASSWORD_LENGTH = 8

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


class AuthError(Exception):
    """Raised for invalid credentials or refused role changes."""


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str, *, salt: Optional[str] = None) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"كلمة السر لازم 8 حروف على الأقل ({MIN_PASSWORD_LENGTH} minimum)")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), **_SCRYPT)
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, _ = stored.split("$", 2)
    except (AttributeError, ValueError):
        return False
    if scheme != "scrypt":
        return False
    try:
        candidate = hash_password(password, salt=salt)
    except AuthError:
        return False
    return hmac.compare_digest(candidate, stored)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return (cleaned or "user")[:40]


def _workspace_slug(conn: sqlite3.Connection, email: str, display_name: str) -> str:
    base = _slug(email.split("@")[0] or display_name or "user")
    slug, counter = base, 1
    while conn.execute("SELECT 1 FROM users WHERE workspace_slug = ?", (slug,)).fetchone():
        counter += 1
        slug = f"{base}-{counter}"
    return slug


def public_user(row: sqlite3.Row | Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    data.pop("password_hash", None)
    return data


def user_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def get_user(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row) if row else None


def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    return dict(row) if row else None


def list_users(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [public_user(row) for row in rows]


def create_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    display_name: str = "",
    role: str = "member",
) -> Dict[str, Any]:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise AuthError("إيميل غير صحيح")
    if role not in ROLE_RANK:
        raise AuthError(f"دور غير معروف: {role}")
    if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise AuthError("الإيميل مستعمل قبل")

    slug = _workspace_slug(conn, email, display_name)
    cursor = conn.execute(
        """INSERT INTO users (email, display_name, password_hash, role, workspace_slug, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            email,
            display_name.strip() or email.split("@")[0],
            hash_password(password),
            role,
            slug,
            time.time(),
        ),
    )
    conn.execute(
        """INSERT INTO profiles (user_id, updated_at) VALUES (?, ?)""",
        (cursor.lastrowid, time.time()),
    )
    return get_user(conn, int(cursor.lastrowid)) or {}


def default_profile(conn: sqlite3.Connection, user_id: int) -> Dict[str, Any]:
    row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO profiles (user_id, updated_at) VALUES (?, ?)", (user_id, time.time()))
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def create_session(conn: sqlite3.Connection, user_id: int, ttl: int = SESSION_TTL) -> Dict[str, Any]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = time.time()
    conn.execute(
        """INSERT INTO sessions (token, user_id, csrf, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        (token, user_id, csrf, now, now + ttl),
    )
    return {"token": token, "csrf": csrf, "expires_at": now + ttl}


def session_user(conn: sqlite3.Connection, token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    row = conn.execute(
        """SELECT u.*, s.token AS session_token, s.csrf AS csrf, s.expires_at AS expires_at
             FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token = ?""",
        (token,),
    ).fetchone()
    if row is None:
        return None
    if float(row["expires_at"]) < time.time():
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return None
    return public_user(row)


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def purge_expired_sessions(conn: sqlite3.Connection) -> int:
    cursor = conn.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
    return cursor.rowcount or 0


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> Optional[Dict[str, Any]]:
    row = get_user_by_email(conn, email)
    if row is None or not verify_password(password or "", row["password_hash"]):
        return None
    return public_user(row)


# ---------------------------------------------------------------------------
# RBAC + workspaces
# ---------------------------------------------------------------------------
def has_role(user: Optional[Dict[str, Any]], minimum: str) -> bool:
    if not user:
        return False
    return ROLE_RANK.get(str(user.get("role")), -1) >= ROLE_RANK.get(minimum, 99)


def require_role(user: Optional[Dict[str, Any]], minimum: str) -> Dict[str, Any]:
    if not has_role(user, minimum):
        raise AuthError(f"الصلاحية غير كافية (مطلوب: {minimum})")
    return user or {}


def user_workspace(base_workspace: Path, user: Dict[str, Any]) -> Path:
    """Every account gets its own folder: nobody sees another's files."""
    slug = str(user.get("workspace_slug") or f"user-{user.get('id', 0)}")
    return Path(base_workspace) / "users" / _slug(slug)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def audit(
    conn: sqlite3.Connection,
    action: str,
    *,
    user_id: Optional[int] = None,
    actor: str = "",
    tool: str = "",
    target: str = "",
    status: str = "ok",
    detail: str = "",
) -> None:
    conn.execute(
        """INSERT INTO audit_log (user_id, actor, tool, action, target, status, detail, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, actor, tool, action, target, status, detail[:500], time.time()),
    )
