"""RAG endpoints and the read-only model-router view — Phase 4 (§4.3 / §4.5)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from core import auth as auth_core
from core import rag, router as model_router
from core.db import get_db
from web.routers.auth import current_user
from web.routers.persona import _profile_payload

router = APIRouter(prefix="/api", tags=["rag"])


class IngestRequest(BaseModel):
    name: str
    body: str
    url: str = ""
    license: str = "unknown"


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


def _user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return user


def _profile(user_id: int) -> Dict[str, Any]:
    with get_db() as conn:
        return _profile_payload(auth_core.default_profile(conn, user_id))


@router.get("/router/plan")
def router_plan(request: Request, task: str = "chat"):
    user = _user(request)
    profile = _profile(user["id"])
    return {"ok": True, "plan": model_router.plan(profile, task)}


@router.post("/rag/ingest")
def ingest(payload: IngestRequest, request: Request):
    user = _user(request)
    if not auth_core.has_role(user, "member"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "member only")
    with get_db() as conn:
        try:
            result = rag.ingest(
                conn,
                user_id=user["id"],
                name=payload.name,
                body=payload.body,
                url=payload.url,
                license=payload.license,
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        auth_core.audit(
            conn,
            "rag.ingest",
            user_id=user["id"],
            actor=user["email"],
            target=payload.name,
            detail=payload.license,
        )
    return {"ok": True, **result}


@router.get("/rag/sources")
def sources(request: Request):
    user = _user(request)
    with get_db() as conn:
        return {"ok": True, "sources": rag.list_sources(conn, user["id"])}


@router.post("/rag/search")
def search(payload: SearchRequest, request: Request):
    user = _user(request)
    with get_db() as conn:
        results = rag.search(conn, user["id"], payload.query, payload.limit)
    return {
        "ok": True,
        "results": results,
        "context": rag.context_block(results),
        "count": len(results),
    }


@router.delete("/rag/sources/{source_id}")
def delete_source(source_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        deleted = rag.delete_source(conn, user["id"], source_id)
        if deleted:
            auth_core.audit(
                conn,
                "rag.delete",
                user_id=user["id"],
                actor=user["email"],
                target=str(source_id),
            )
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "المصدر ما موجودش")
    return {"ok": True}
