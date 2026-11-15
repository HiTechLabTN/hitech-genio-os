"""Organisations, members, usage reports and audit export — Phase 6 (§4.7)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from core import auth as auth_core
from core import orgs
from core.db import get_db
from web.routers.auth import current_user

router = APIRouter(prefix="/api", tags=["orgs"])


class OrgCreate(BaseModel):
    name: str


class MemberAdd(BaseModel):
    email: str
    role: str = "member"


def _user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return user


@router.get("/orgs")
def list_orgs(request: Request):
    user = _user(request)
    with get_db() as conn:
        return {"ok": True, "orgs": orgs.list_orgs(conn, user["id"])}


@router.post("/orgs")
def create_org(payload: OrgCreate, request: Request):
    user = _user(request)
    if not auth_core.has_role(user, "member"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "member only")
    with get_db() as conn:
        try:
            org = orgs.create_org(conn, user["id"], payload.name)
        except orgs.OrgError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        auth_core.audit(
            conn, "org.create", user_id=user["id"], actor=user["email"], target=payload.name
        )
    return {"ok": True, "org": org}


@router.get("/orgs/{org_id}")
def read_org(org_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        try:
            orgs.require_member(conn, org_id, user["id"])
        except orgs.OrgError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
        org = orgs.get_org(conn, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "المنظمة ما موجودة")
    return {"ok": True, "org": org}


@router.get("/orgs/{org_id}/members")
def read_members(org_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        try:
            orgs.require_member(conn, org_id, user["id"])
        except orgs.OrgError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
        return {"ok": True, "members": orgs.members(conn, org_id)}


@router.post("/orgs/{org_id}/members")
def add_member(org_id: int, payload: MemberAdd, request: Request):
    user = _user(request)
    with get_db() as conn:
        try:
            orgs.require_member(conn, org_id, user["id"], minimum="admin")
        except orgs.OrgError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
        target = auth_core.get_user_by_email(conn, payload.email)
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "المستعمل ما موجودش")
        try:
            added = orgs.add_member(conn, org_id, target["id"], payload.role)
        except orgs.OrgError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        auth_core.audit(
            conn,
            "org.member.add",
            user_id=user["id"],
            actor=user["email"],
            target=target["email"],
            detail=payload.role,
        )
    return {"ok": True, **added}


@router.delete("/orgs/{org_id}/members/{user_id}")
def remove_member(org_id: int, user_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        try:
            orgs.require_member(conn, org_id, user["id"], minimum="admin")
        except orgs.OrgError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
        org = orgs.get_org(conn, org_id)
        if org and org["owner_id"] == user_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "ما تنجّمش تمحي المالك")
        if not orgs.remove_member(conn, org_id, user_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "العضو ما موجودش")
        auth_core.audit(
            conn, "org.member.remove", user_id=user["id"], actor=user["email"], target=str(user_id)
        )
    return {"ok": True}


@router.get("/orgs/{org_id}/report")
def report(org_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        try:
            orgs.require_member(conn, org_id, user["id"], minimum="admin")
        except orgs.OrgError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
        data = orgs.usage_report(conn, org_id)
        data["org"] = orgs.get_org(conn, org_id)
    return {"ok": True, "report": data}


@router.get("/admin/audit/export")
def audit_export(request: Request, limit: int = 1000):
    user = _user(request)
    if not auth_core.has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    with get_db() as conn:
        payload = orgs.audit_csv(conn, limit)
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="genio-audit.csv"'},
    )
