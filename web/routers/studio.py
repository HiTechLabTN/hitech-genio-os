"""Vibe Studio endpoints — Plan v2 §10 (projects, missions, preview, export)."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

from core import auth as auth_core
from core import studio
from core.db import get_db
from core.engine import BASE_DIR, current_workspace
from web.routers.auth import current_user

router = APIRouter(prefix="/api", tags=["studio"])


class ProjectCreate(BaseModel):
    name: str = ""
    template: str = "landing"
    idea: str = ""


class MissionRequest(BaseModel):
    idea: str = ""


class DeployPlanRequest(BaseModel):
    target: str = "static"


def _user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return user


def _workspace() -> Path:
    workspace = current_workspace(BASE_DIR / "workspace") or (BASE_DIR / "workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _project(conn, user_id: int, project_id: int) -> Dict[str, Any]:
    project = studio.get_project(conn, user_id, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "المشروع ما موجودش")
    return project


@router.get("/projects/templates")
def templates():
    return {
        "ok": True,
        "templates": [
            {
                "id": key,
                "label": value["label"],
                "stack": value["stack"],
                "files": value["files"],
                "mobile": key in studio.MOBILE_TEMPLATES,
            }
            for key, value in studio.TEMPLATES.items()
        ],
    }


@router.post("/projects")
def create_project(payload: ProjectCreate, request: Request):
    user = _user(request)
    with get_db() as conn:
        try:
            project = studio.create_project(
                conn,
                user_id=user["id"],
                workspace=_workspace(),
                name=payload.name,
                template=payload.template,
                idea=payload.idea,
            )
        except studio.StudioError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        auth_core.audit(
            conn,
            "project.create",
            user_id=user["id"],
            actor=user["email"],
            target=project["slug"],
            detail=payload.template,
        )
    return {"ok": True, "project": project}


@router.get("/projects")
def list_projects(request: Request):
    user = _user(request)
    with get_db() as conn:
        return {"ok": True, "projects": studio.list_projects(conn, user["id"])}


@router.get("/projects/{project_id}")
def read_project(project_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        return {"ok": True, "project": _project(conn, user["id"], project_id)}


@router.post("/projects/{project_id}/mission")
def run_mission(project_id: int, payload: MissionRequest, request: Request):
    user = _user(request)
    with get_db() as conn:
        project = _project(conn, user["id"], project_id)
        try:
            result = studio.run_mission(
                conn,
                user_id=user["id"],
                workspace=_workspace(),
                project=project,
                idea=payload.idea,
            )
        except studio.StudioError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        auth_core.audit(
            conn,
            "project.mission",
            user_id=user["id"],
            actor=user["email"],
            target=project["slug"],
            status="ok" if result["passed"] else "error",
        )
    return {"ok": result["passed"], **result}


@router.get("/projects/{project_id}/files")
def project_files(project_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        project = _project(conn, user["id"], project_id)
    root = studio.project_dir(_workspace(), project["slug"])
    files = [
        {"path": str(path.relative_to(root)), "size": path.stat().st_size}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    return {"ok": True, "files": files}


@router.get("/projects/{project_id}/file")
def project_file(project_id: int, request: Request, path: str = "index.html"):
    user = _user(request)
    with get_db() as conn:
        project = _project(conn, user["id"], project_id)
    try:
        target = studio.read_project_file(_workspace(), project["slug"], path)
    except studio.StudioError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"ok": True, "path": path, "content": target.read_text(encoding="utf-8", errors="replace")}


@router.get("/projects/{project_id}/preview", response_class=HTMLResponse)
def project_preview(project_id: int, request: Request, path: str = "index.html"):
    user = _user(request)
    with get_db() as conn:
        project = _project(conn, user["id"], project_id)
    try:
        target = studio.read_project_file(_workspace(), project["slug"], path)
    except studio.StudioError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return HTMLResponse(target.read_text(encoding="utf-8", errors="replace"))


@router.get("/projects/{project_id}/export")
def export_project(project_id: int, request: Request):
    user = _user(request)
    with get_db() as conn:
        project = _project(conn, user["id"], project_id)
    root = studio.project_dir(_workspace(), project["slug"])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root))
    buffer.seek(0)
    with get_db() as conn:
        auth_core.audit(
            conn,
            "project.export",
            user_id=user["id"],
            actor=user["email"],
            target=project["slug"],
        )
    # HTTP headers are latin-1: keep an ASCII filename and add the UTF-8 one
    # (RFC 5987) so Arabic project names still download correctly.
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "-", project["slug"]) or "project"
    quoted = quote(f"{project['slug']}.zip")
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_name}.zip"; filename*=UTF-8\'\'{quoted}'
            )
        },
    )


@router.post("/projects/{project_id}/deploy-plan")
def deploy_plan(project_id: int, payload: DeployPlanRequest, request: Request):
    user = _user(request)
    with get_db() as conn:
        project = _project(conn, user["id"], project_id)
    try:
        plan = studio.deploy_plan(project, payload.target)
    except studio.StudioError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"ok": True, **plan}
