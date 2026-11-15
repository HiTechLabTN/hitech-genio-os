"""Organisations, members and usage reporting — Plan v1 §4.7 / Plan v2 §6."""

from __future__ import annotations

import sqlite3
import time
from typing import Any, Dict, List, Optional

ORG_ROLES = ("viewer", "member", "admin", "owner")  # ordre croissant de privilège


class OrgError(ValueError):
    """Invalid organisation operation."""


def create_org(conn: sqlite3.Connection, owner_id: int, name: str) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise OrgError("المنظمة تحتاج اسم")
    if conn.execute("SELECT 1 FROM orgs WHERE name = ?", (name,)).fetchone():
        raise OrgError("اسم المنظمة مستعمل")
    cursor = conn.execute(
        "INSERT INTO orgs (name, owner_id, created_at) VALUES (?, ?, ?)",
        (name, owner_id, time.time()),
    )
    org_id = int(cursor.lastrowid)
    conn.execute(
        "INSERT INTO org_members (org_id, user_id, role) VALUES (?, ?, 'owner')",
        (org_id, owner_id),
    )
    return get_org(conn, org_id) or {}


def get_org(conn: sqlite3.Connection, org_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """SELECT o.*, (SELECT COUNT(*) FROM org_members m WHERE m.org_id = o.id) AS members
             FROM orgs o WHERE o.id = ?""",
        (org_id,),
    ).fetchone()
    return dict(row) if row else None


def list_orgs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """SELECT o.*, m.role AS my_role,
                  (SELECT COUNT(*) FROM org_members mm WHERE mm.org_id = o.id) AS members
             FROM orgs o JOIN org_members m ON m.org_id = o.id
            WHERE m.user_id = ?
            ORDER BY o.id""",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def membership(conn: sqlite3.Connection, org_id: int, user_id: int) -> Optional[str]:
    row = conn.execute(
        "SELECT role FROM org_members WHERE org_id = ? AND user_id = ?", (org_id, user_id)
    ).fetchone()
    return row["role"] if row else None


def require_member(conn: sqlite3.Connection, org_id: int, user_id: int, minimum: str = "viewer") -> str:
    role = membership(conn, org_id, user_id)
    if role is None:
        raise OrgError("ماشي عضو في المنظمة")
    rank = {name: index for index, name in enumerate(ORG_ROLES)}
    if rank.get(role, -1) < rank.get(minimum, 99):
        raise OrgError(f"الصلاحية غير كافية (مطلوب: {minimum})")
    return role


def add_member(
    conn: sqlite3.Connection, org_id: int, user_id: int, role: str = "member"
) -> Dict[str, Any]:
    if role not in ORG_ROLES:
        raise OrgError("دور غير معروف")
    if conn.execute(
        "SELECT 1 FROM org_members WHERE org_id = ? AND user_id = ?", (org_id, user_id)
    ).fetchone():
        conn.execute(
            "UPDATE org_members SET role = ? WHERE org_id = ? AND user_id = ?",
            (role, org_id, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO org_members (org_id, user_id, role) VALUES (?, ?, ?)",
            (org_id, user_id, role),
        )
    return {"org_id": org_id, "user_id": user_id, "role": role}


def remove_member(conn: sqlite3.Connection, org_id: int, user_id: int) -> bool:
    cursor = conn.execute(
        "DELETE FROM org_members WHERE org_id = ? AND user_id = ?", (org_id, user_id)
    )
    return bool(cursor.rowcount)


def members(conn: sqlite3.Connection, org_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """SELECT m.user_id, m.role, u.email, u.display_name, u.role AS account_role
             FROM org_members m JOIN users u ON u.id = m.user_id
            WHERE m.org_id = ? ORDER BY m.user_id""",
        (org_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def usage_report(conn: sqlite3.Connection, org_id: int) -> Dict[str, Any]:
    """Usage numbers an organisation admin can actually act on."""
    member_rows = conn.execute(
        "SELECT user_id FROM org_members WHERE org_id = ?", (org_id,)
    ).fetchall()
    user_ids = [row["user_id"] for row in member_rows]
    if not user_ids:
        return {"org_id": org_id, "members": 0, "tool_calls": 0, "by_tool": {}, "events": 0}

    placeholders = ",".join("?" for _ in user_ids)
    tool_calls = conn.execute(
        f"""SELECT COUNT(*) FROM audit_log
             WHERE action = 'tool.invoke' AND user_id IN ({placeholders})""",
        user_ids,
    ).fetchone()[0]
    by_tool = {
        row["tool"]: row["calls"]
        for row in conn.execute(
            f"""SELECT tool, COUNT(*) AS calls FROM audit_log
                 WHERE action = 'tool.invoke' AND user_id IN ({placeholders})
                 GROUP BY tool ORDER BY calls DESC""",
            user_ids,
        ).fetchall()
    }
    denied = conn.execute(
        f"""SELECT COUNT(*) FROM audit_log
             WHERE status = 'denied' AND user_id IN ({placeholders})""",
        user_ids,
    ).fetchone()[0]
    events = conn.execute(
        f"""SELECT COUNT(*) FROM usage_events WHERE user_id IN ({placeholders})""",
        user_ids,
    ).fetchone()[0]
    return {
        "org_id": org_id,
        "members": len(user_ids),
        "tool_calls": int(tool_calls),
        "by_tool": by_tool,
        "denied": int(denied),
        "events": int(events),
    }


def audit_csv(conn: sqlite3.Connection, limit: int = 1000) -> str:
    """CSV export for an organisation review (no secrets, no file contents)."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "created_at", "actor", "action", "tool", "target", "status", "detail"])
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (max(1, min(limit, 5000)),)
    ).fetchall()
    for row in rows:
        writer.writerow(
            [
                row["id"],
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["created_at"])),
                row["actor"],
                row["action"],
                row["tool"],
                row["target"],
                row["status"],
                row["detail"],
            ]
        )
    return buffer.getvalue()
