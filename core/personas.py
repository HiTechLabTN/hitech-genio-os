"""Persona packs and onboarding — Plan v1 §4.2.

A persona is **derived** from the profile, never hardcoded in a route: the
onboarding answers pick a pack, and the pack decides the system prompt, the
tools, the experience (mode), the model policy and the safety policy.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

MODES = ("chat", "dev", "enterprise")
MODE_LABELS = {
    "chat": "وضع المحادثة",
    "dev": "وضع التطوير",
    "enterprise": "وضع المؤسسة",
}

DEFAULT_PACK = "chat_general"

PACKS: Dict[str, Dict[str, Any]] = {
    "chat_general": {
        "label": "محادثة عامة",
        "description": "شات بسيط: أسئلة، شرح، تلخيص، بلا طرفية ولا كود.",
        "mode": "chat",
        "system_prompt": (
            "You are Genio, a helpful local assistant. Answer in the user's "
            "language (Tunisian Derja by default), keep technical terms in "
            "French/English, and stay concise and concrete."
        ),
        "tools": ["files", "rag"],
        "models": {"chat": "qwen2.5:7b-instruct"},
    },
    "student": {
        "label": "طالب",
        "description": "شرح الدروس، تلخيص، تمارين، وتحضير للامتحانات.",
        "mode": "chat",
        "system_prompt": (
            "You are Genio Study, a patient tutor. Explain step by step in "
            "Derja, use examples from Tunisian schools/universities, and "
            "always check understanding with a short question."
        ),
        "tools": ["files", "rag"],
        "models": {"chat": "gemma4:12b-32k"},
    },
    "dev_lead": {
        "label": "مطوّر",
        "description": "بناء تطبيقات ويب: كود كامل، IDE، طرفية، tests.",
        "mode": "dev",
        "system_prompt": (
            "You are Dev-Lead, principal engineer. Write complete files, never "
            "placeholders. Verify with tests and report the exact commands you ran."
        ),
        "tools": ["files", "shell_sandboxed", "git", "tests"],
        "models": {"chat": "gemma4:12b-32k", "code": "qwen2.5-coder:14b-32k"},
    },
    "devops": {
        "label": "DevOps / Infra",
        "description": "سيرفرات، Docker، نشر، مراقبة، وأتمتة.",
        "mode": "dev",
        "system_prompt": (
            "You are Infra-Ops, a senior Linux and Docker engineer. Prefer safe, "
            "reversible commands, explain risks before destructive steps, and "
            "always show how to verify the result."
        ),
        "tools": ["files", "shell_sandboxed", "git", "deploy"],
        "models": {"chat": "gemma4:12b-32k", "code": "qwen2.5-coder:14b-32k"},
    },
    "business_analyst": {
        "label": "محلّل أعمال",
        "description": "تحليل بيانات، تقارير، جداول، ودراسات جدوى.",
        "mode": "chat",
        "system_prompt": (
            "You are Genio Analyst. Structure every answer as: context, "
            "findings, recommendation. Use TND and Tunisian market context."
        ),
        "tools": ["files", "rag", "reports"],
        "models": {"chat": "gemma4:12b-32k"},
    },
    "support_agent": {
        "label": "دعم عملاء",
        "description": "ردود على العملاء، تصنيف التذاكر، وقاعدة أجوبة.",
        "mode": "chat",
        "system_prompt": (
            "You are Genio Support. Answer politely in the customer's language, "
            "stay factual, and hand off to a human when the request needs it."
        ),
        "tools": ["files", "rag"],
        "models": {"chat": "qwen2.5:7b-instruct"},
    },
    "content_creator": {
        "label": "محتوى وتسويق",
        "description": "منشورات، إعلانات، سكريبتات، ومحتوى بالدارجة.",
        "mode": "chat",
        "system_prompt": (
            "You are Genio Creator. Write native Tunisian Derja for social "
            "media, keep it short and punchy, and propose 3 variants."
        ),
        "tools": ["files"],
        "models": {"chat": "gemma4:12b-32k"},
    },
    "enterprise_admin": {
        "label": "مسؤول مؤسسة",
        "description": "فريق، صلاحيات، تقارير استعمال، وaudit.",
        "mode": "enterprise",
        "system_prompt": (
            "You are Genio Enterprise Admin assistant. Focus on governance, "
            "access control, usage reporting and audit trails."
        ),
        "tools": ["files", "rag", "admin", "audit"],
        "models": {"chat": "gemma4:12b-32k"},
    },
}

OCCUPATIONS = ("student", "employee", "freelance", "founder", "enterprise")
GOALS = (
    "chat",
    "writing",
    "code",
    "devops",
    "data",
    "marketing",
    "support",
    "pm",
)
LEVELS = ("beginner", "intermediate", "advanced")
REGISTERS = ("derja", "fusha", "fr", "en")
ENVS = ("local", "server", "offline")
SENSITIVITIES = ("low", "medium", "high")


class OnboardingError(ValueError):
    """Invalid onboarding answers."""


def pack_ids() -> List[str]:
    return list(PACKS)


def get_pack(name: Optional[str]) -> Dict[str, Any]:
    return dict(PACKS.get(str(name or DEFAULT_PACK), PACKS[DEFAULT_PACK]))


def public_packs() -> List[Dict[str, Any]]:
    return [
        {
            "id": key,
            "label": pack["label"],
            "description": pack["description"],
            "mode": pack["mode"],
            "tools": list(pack["tools"]),
        }
        for key, pack in PACKS.items()
    ]


def choose_pack(occupation: str, goals: List[str], technical_level: str) -> str:
    """Pick the closest pack: the smallest pack that fits the stated goal."""
    goals = [g for g in goals if g in GOALS]
    if occupation == "enterprise":
        return "enterprise_admin"
    if "code" in goals:
        return "dev_lead"
    if "devops" in goals:
        return "devops"
    if "data" in goals or "pm" in goals:
        return "business_analyst"
    if occupation == "student":
        return "student"
    if "support" in goals:
        return "support_agent"
    if "marketing" in goals or "writing" in goals:
        return "content_creator"
    if technical_level == "advanced" and "chat" in goals:
        return "dev_lead"
    return DEFAULT_PACK


def safety_for(data_sensitivity: str, technical_level: str) -> Dict[str, str]:
    """High sensitivity locks the shell; beginners never get it unlocked."""
    if data_sensitivity == "high":
        return {"shell": "deny", "write": "allow_workspace", "network": "deny"}
    if technical_level == "beginner":
        return {"shell": "confirm", "write": "allow_workspace", "network": "deny"}
    if data_sensitivity == "low" and technical_level == "advanced":
        return {"shell": "allow_workspace", "write": "allow_workspace", "network": "allowlist"}
    return {"shell": "confirm", "write": "allow_workspace", "network": "allowlist"}


def _pick(value: str, allowed: tuple, field: str, default: str) -> str:
    value = (value or default).strip().lower()
    if value not in allowed:
        raise OnboardingError(f"قيمة غير صحيحة في {field}: {value}")
    return value


def build_profile_from_onboarding(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Turn the 7 wizard answers into a complete profile payload."""
    occupation = _pick(answers.get("occupation"), OCCUPATIONS, "occupation", "employee")
    technical_level = _pick(
        answers.get("technical_level"), LEVELS, "technical_level", "intermediate"
    )
    register = _pick(answers.get("register"), REGISTERS, "register", "derja")
    env = _pick(answers.get("env"), ENVS, "env", "local")
    sensitivity = _pick(
        answers.get("data_sensitivity"), SENSITIVITIES, "data_sensitivity", "medium"
    )

    raw_goals = answers.get("goals") or ["chat"]
    if isinstance(raw_goals, str):
        raw_goals = [raw_goals]
    goals = [str(g).strip().lower() for g in raw_goals if str(g).strip()]
    unknown = [g for g in goals if g not in GOALS]
    if unknown:
        raise OnboardingError(f"أهداف غير معروفة: {', '.join(unknown)}")
    if not goals:
        goals = ["chat"]

    pack_id = choose_pack(occupation, goals, technical_level)
    pack = get_pack(pack_id)
    safety = safety_for(sensitivity, technical_level)

    tools = list(pack["tools"])
    if safety["shell"] == "deny":
        tools = [t for t in tools if t != "shell_sandboxed"]

    return {
        "locale": "ar-TN" if register == "derja" else register,
        "register": register,
        "technical_level": technical_level,
        "occupation": occupation,
        "persona_pack": pack_id,
        "mode": pack["mode"],
        "env": env,
        "data_sensitivity": sensitivity,
        "goals": goals,
        "sectors": [],
        "tools": tools,
        "safety": safety,
        "onboarding_done": 1,
    }


def resolve(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Effective persona for a profile: pack + safety override + mode."""
    pack_id = str(profile.get("persona_pack") or "")
    if pack_id not in PACKS:
        pack_id = DEFAULT_PACK
    pack = PACKS[pack_id]
    raw_safety = profile.get("safety")
    if isinstance(raw_safety, str):
        try:
            raw_safety = json.loads(raw_safety or "{}")
        except json.JSONDecodeError:
            raw_safety = {}
    safety = dict(raw_safety or {})
    mode = profile.get("mode") if profile.get("mode") in MODES else pack["mode"]
    return {
        "pack": pack_id,
        "label": pack["label"],
        "mode": mode,
        "system_prompt": pack["system_prompt"],
        "tools": list(pack["tools"]),
        "models": dict(pack["models"]),
        "safety": safety or safety_for("medium", "intermediate"),
    }
