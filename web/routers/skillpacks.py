"""Skill packs + evaluation gate — Plan v2 §4.3."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status

from core import auth as auth_core
from core import skillpacks
from core.db import get_db
from web.routers.auth import current_user

router = APIRouter(prefix="/api", tags=["skillpacks"])


def _user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return user


@router.get("/skillpacks")
def list_packs(request: Request):
    _user(request)
    with get_db() as conn:
        return {"ok": True, "packs": skillpacks.list_packs(conn)}


@router.post("/skillpacks/{name}/eval")
def evaluate(name: str, request: Request):
    _user(request)
    try:
        return {"ok": True, "eval": skillpacks.evaluate(name)}
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"skill pack غير معروف: {name}")


@router.post("/skillpacks/{name}/enable")
def enable(name: str, request: Request):
    user = _user(request)
    if not auth_core.has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    with get_db() as conn:
        try:
            result = skillpacks.enable(conn, name)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"skill pack غير معروف: {name}")
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        auth_core.audit(
            conn,
            "skillpack.enable",
            user_id=user["id"],
            actor=user["email"],
            target=name,
            detail=result["version"],
        )
    return {"ok": True, **result}


@router.post("/skillpacks/{name}/disable")
def disable(name: str, request: Request):
    user = _user(request)
    if not auth_core.has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    with get_db() as conn:
        if not skillpacks.disable(conn, name):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "skill pack ما كانش مفعّل")
        auth_core.audit(
            conn, "skillpack.disable", user_id=user["id"], actor=user["email"], target=name
        )
    return {"ok": True, "name": name, "enabled": False}
