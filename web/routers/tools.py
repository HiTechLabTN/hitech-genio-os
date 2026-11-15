"""Tool invocation, approvals and audit — Plan v1 §4.4 / §4.7."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core import auth as auth_core
from core import tools
from core.db import get_db
from core.engine import BASE_DIR, current_workspace
from core.personas import resolve
from web.routers.auth import current_user
from web.routers.persona import _profile_payload

router = APIRouter(prefix="/api", tags=["tools"])


class InvokeRequest(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict)
    approval_id: Optional[int] = None


class ApprovalDecision(BaseModel):
    approve: bool = True


def _user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return user


def context_for(user: Dict[str, Any]) -> tools.ToolContext:
    with get_db() as conn:
        profile = _profile_payload(auth_core.default_profile(conn, user["id"]))
    persona = resolve(profile)
    workspace = current_workspace(BASE_DIR / "workspace")
    return tools.ToolContext(
        workspace=workspace,
        user=user,
        safety=persona["safety"],
        profile=profile,
    )


def _error(exc: Exception) -> JSONResponse:
    if isinstance(exc, tools.ToolNotFound):
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
    if isinstance(exc, tools.ToolDenied):
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=403)
    return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


def execute(user: Dict[str, Any], tool: tools.Tool, params: Dict[str, Any]) -> Any:
    """Run a tool and record the call in the audit log, whatever happens."""
    ctx = context_for(user)
    started = time.time()
    try:
        result = tools.invoke(tool, ctx, params)
    except tools.ToolError as exc:
        with get_db() as conn:
            auth_core.audit(
                conn,
                "tool.invoke",
                user_id=user["id"],
                actor=user["email"],
                tool=tool.name,
                target=str(params.get("path") or params.get("cmd") or "")[:200],
                status="denied" if isinstance(exc, tools.ToolDenied) else "error",
                detail=str(exc),
            )
        return _error(exc)
    with get_db() as conn:
        auth_core.audit(
            conn,
            "tool.invoke",
            user_id=user["id"],
            actor=user["email"],
            tool=tool.name,
            target=str(params.get("path") or params.get("cmd") or "")[:200],
            detail=f"{round((time.time() - started) * 1000)}ms",
        )
    return result


@router.get("/tools")
def list_tools():
    return {"ok": True, "tools": tools.list_tools()}


@router.post("/tools/{name}/invoke")
def invoke_tool(name: str, payload: InvokeRequest, request: Request):
    user = _user(request)
    try:
        tool = tools.get(name)
    except tools.ToolNotFound as exc:
        return _error(exc)

    ctx = context_for(user)
    try:
        tools.preflight(tool, ctx)
    except tools.ToolError as exc:
        return _error(exc)
    if tools.requires_approval(tool, ctx):
        if payload.approval_id is None:
            with get_db() as conn:
                cursor = conn.execute(
                    """INSERT INTO approvals (user_id, tool, params, status, created_at)
                       VALUES (?, ?, ?, 'pending', ?)""",
                    (user["id"], name, json.dumps(payload.params, ensure_ascii=False), time.time()),
                )
                approval_id = int(cursor.lastrowid)
                auth_core.audit(
                    conn,
                    "tool.approval.request",
                    user_id=user["id"],
                    actor=user["email"],
                    tool=name,
                )
            return JSONResponse(
                {
                    "ok": False,
                    "requires_approval": True,
                    "approval_id": approval_id,
                    "tool": name,
                    "error": "الأداة تحتاج موافقة قبل التنفيذ",
                },
                status_code=status.HTTP_202_ACCEPTED,
            )
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE id = ?", (payload.approval_id,)
            ).fetchone()
            if row is None or row["user_id"] != user["id"] or row["tool"] != name:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "approval غير صالح")
            if row["status"] != "approved":
                raise HTTPException(status.HTTP_403_FORBIDDEN, "موافقة ما زالت ما تعطاتش")

    return execute(user, tool, payload.params)


@router.get("/approvals")
def list_approvals(request: Request):
    user = _user(request)
    with get_db() as conn:
        if auth_core.has_role(user, "admin"):
            rows = conn.execute(
                "SELECT * FROM approvals ORDER BY id DESC LIMIT 100"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE user_id = ? ORDER BY id DESC LIMIT 100",
                (user["id"],),
            ).fetchall()
    return {"ok": True, "approvals": [dict(row) for row in rows]}


@router.post("/approvals/{approval_id}/decide")
def decide_approval(approval_id: int, payload: ApprovalDecision, request: Request):
    user = _user(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval ما موجودش")
        if row["user_id"] != user["id"] and not auth_core.has_role(user, "admin"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "approval ماشي متاعك")
        if row["status"] != "pending":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "تمّت المعالجة قبل")
        conn.execute(
            "UPDATE approvals SET status = ?, decided_at = ?, decided_by = ? WHERE id = ?",
            ("approved" if payload.approve else "rejected", time.time(), user["id"], approval_id),
        )
        auth_core.audit(
            conn,
            "tool.approval.decide",
            user_id=user["id"],
            actor=user["email"],
            tool=row["tool"],
            status="ok" if payload.approve else "rejected",
        )

    if not payload.approve:
        return {"ok": True, "status": "rejected", "approval_id": approval_id}

    try:
        tool = tools.get(row["tool"])
    except tools.ToolNotFound as exc:
        return _error(exc)
    params = json.loads(row["params"] or "{}")
    result = execute(user, tool, params)
    if isinstance(result, JSONResponse):
        return result
    return {**result, "approval_id": approval_id}


@router.get("/audit")
def read_audit(request: Request, limit: int = 100):
    user = _user(request)
    if not auth_core.has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    limit = max(1, min(int(limit), 500))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"ok": True, "audit": [dict(row) for row in rows]}
