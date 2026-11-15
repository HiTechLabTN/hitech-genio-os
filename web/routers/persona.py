"""Onboarding, personas and experience switching — Plan v1 §4.2 / §4.3."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from core import auth as auth_core
from core import personas
from core.db import get_db
from web.routers.auth import current_user

router = APIRouter(prefix="/api", tags=["persona"])


class OnboardingRequest(BaseModel):
    model_config = {"populate_by_name": True}

    occupation: str = "employee"
    goals: List[str] = Field(default_factory=lambda: ["chat"])
    technical_level: str = "intermediate"
    register_: str = Field(default="derja", alias="register")
    env: str = "local"
    data_sensitivity: str = "medium"
    preferred_tools: List[str] = Field(default_factory=list)


class ModeRequest(BaseModel):
    mode: str


def _require_user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return user


def _profile_payload(profile: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(profile)
    for key in ("goals", "sectors", "tools"):
        try:
            out[key] = json.loads(out.get(key) or "[]")
        except (TypeError, json.JSONDecodeError):
            out[key] = []
    try:
        out["safety"] = json.loads(out.get("safety") or "{}")
    except (TypeError, json.JSONDecodeError):
        out["safety"] = {}
    return out


@router.get("/personas")
def list_personas():
    return {
        "ok": True,
        "personas": personas.public_packs(),
        "modes": [
            {"id": mode, "label": personas.MODE_LABELS[mode]} for mode in personas.MODES
        ],
    }


@router.post("/onboarding/submit")
def submit_onboarding(payload: OnboardingRequest, request: Request):
    user = _require_user(request)
    answers = payload.model_dump(by_alias=True)
    try:
        derived = personas.build_profile_from_onboarding(answers)
    except personas.OnboardingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if payload.preferred_tools:
        known = set(derived["tools"])
        derived["tools"] = sorted(known | {t for t in payload.preferred_tools if t in known})

    columns = {
        "locale": derived["locale"],
        "register": derived["register"],
        "technical_level": derived["technical_level"],
        "occupation": derived["occupation"],
        "persona_pack": derived["persona_pack"],
        "mode": derived["mode"],
        "env": derived["env"],
        "data_sensitivity": derived["data_sensitivity"],
        "goals": json.dumps(derived["goals"], ensure_ascii=False),
        "sectors": json.dumps(derived["sectors"], ensure_ascii=False),
        "tools": json.dumps(derived["tools"], ensure_ascii=False),
        "safety": json.dumps(derived["safety"], ensure_ascii=False),
        "onboarding_done": 1,
        "updated_at": time.time(),
    }
    assignments = ", ".join(f"{key} = ?" for key in columns)
    with get_db() as conn:
        auth_core.default_profile(conn, user["id"])
        conn.execute(
            f"UPDATE profiles SET {assignments} WHERE user_id = ?",
            (*columns.values(), user["id"]),
        )
        profile = _profile_payload(auth_core.default_profile(conn, user["id"]))
        auth_core.audit(
            conn,
            "onboarding.submit",
            user_id=user["id"],
            actor=user["email"],
            detail=derived["persona_pack"],
        )
    return {"ok": True, "profile": profile, "persona": personas.resolve(profile)}


@router.get("/experience")
def experience(request: Request):
    """Contract for the UI: which mode, tools, models and safety apply now."""
    user = _require_user(request)
    with get_db() as conn:
        profile = _profile_payload(auth_core.default_profile(conn, user["id"]))
    persona = personas.resolve(profile)
    return {
        "ok": True,
        "mode": persona["mode"],
        "mode_label": personas.MODE_LABELS.get(persona["mode"], persona["mode"]),
        "persona_pack": persona["pack"],
        "persona_label": persona["label"],
        "tools": persona["tools"],
        "allowed_tools": profile.get("tools") or [],
        "models": persona["models"],
        "safety": persona["safety"],
        "modes": [{"id": m, "label": personas.MODE_LABELS[m]} for m in personas.MODES],
    }


@router.get("/me/persona")
def my_persona(request: Request):
    user = _require_user(request)
    with get_db() as conn:
        profile = _profile_payload(auth_core.default_profile(conn, user["id"]))
    return {"ok": True, "profile": profile, "persona": personas.resolve(profile)}


@router.post("/mode")
def switch_mode(payload: ModeRequest, request: Request):
    user = _require_user(request)
    if payload.mode not in personas.MODES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "وضع غير معروف")
    with get_db() as conn:
        auth_core.default_profile(conn, user["id"])
        conn.execute(
            "UPDATE profiles SET mode = ?, updated_at = ? WHERE user_id = ?",
            (payload.mode, time.time(), user["id"]),
        )
        profile = _profile_payload(auth_core.default_profile(conn, user["id"]))
        auth_core.audit(
            conn, "mode.switch", user_id=user["id"], actor=user["email"], detail=payload.mode
        )
    return {"ok": True, "mode": payload.mode, "label": personas.MODE_LABELS[payload.mode], "persona": personas.resolve(profile)}
