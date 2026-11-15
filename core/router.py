"""Model router — Plan v1 §4.5.

The profile's persona decides which model serves which kind of task. When the
local Ollama node does not have that model, the router degrades explicitly
instead of pretending: it reports ``status`` and lets the caller show a clear
message (Plan v2: «إذا Ollama طاح، رسالة واضحة + fallback»).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from core import personas

TASK_KINDS = ("chat", "code", "vision", "embeddings")

DEFAULT_MODELS: Dict[str, str] = {
    "chat": "gemma4:12b-32k",
    "code": "qwen2.5-coder:14b-32k",
    "vision": "minicpm-v:latest",
    "embeddings": "nomic-embed-text",
}

# Fallback order per task kind when the preferred model is missing.
FALLBACKS: Dict[str, List[str]] = {
    "chat": ["gemma4:12b-32k", "qwen2.5:7b-instruct", "gemma4:12b"],
    "code": ["qwen2.5-coder:14b-32k", "qwen2.5-coder:14b", "gemma4:12b-32k"],
    "vision": ["minicpm-v:latest", "qwen2.5vl:7b-32k"],
    "embeddings": ["nomic-embed-text", "bge-m3"],
}


def model_policy(profile: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Merge the persona policy over the built-in defaults."""
    policy = dict(DEFAULT_MODELS)
    if profile:
        policy.update(personas.resolve(profile).get("models") or {})
    return policy


def _normalise(name: str) -> str:
    return str(name or "").strip()


def _matches(model: str, available: Iterable[str]) -> bool:
    available = {_normalise(item) for item in available}
    if not available:
        return False
    if model in available:
        return True
    stem = model.split(":")[0]
    return any(item.split(":")[0] == stem for item in available)


def plan(
    profile: Optional[Dict[str, Any]] = None,
    task: str = "chat",
    available: Optional[Iterable[str]] = None,
    *,
    ollama_online: bool = True,
) -> Dict[str, Any]:
    """Pick the model for a task, with an explicit status the UI can show."""
    task = task if task in TASK_KINDS else "chat"
    policy = model_policy(profile)
    persona_models = personas.resolve(profile).get("models") if profile else {}
    preferred = _normalise(policy.get(task) or policy.get("chat") or DEFAULT_MODELS[task])

    result: Dict[str, Any] = {
        "task": task,
        "model": preferred,
        "policy": policy,
        "status": "ok",
        "source": "profile" if (persona_models or {}).get(task) else "default",
        "fallback_used": False,
    }

    if not ollama_online:
        result.update(
            status="offline",
            model=None,
            message="Ollama ماشي متاح توّا — المنصّة تبقى تخدم أما بلا توليد.",
        )
        return result

    if available is None:
        return result

    available_list = [_normalise(item) for item in available]
    if not available_list:
        result.update(status="no_models", model=None, message="ما فمّاش حتى موديل مثبّت في Ollama.")
        return result

    if _matches(preferred, available_list):
        result["model"] = next(
            (item for item in available_list if item == preferred or item.split(":")[0] == preferred.split(":")[0]),
            preferred,
        )
        return result

    for candidate in FALLBACKS.get(task, []):
        if _matches(candidate, available_list):
            result.update(
                model=candidate,
                status="fallback",
                fallback_used=True,
                message=f"{preferred} ما موجودش — نستعملو {candidate}.",
            )
            return result

    available_chat = _matches(policy.get("chat", ""), available_list)
    result.update(
        model=policy.get("chat") if available_chat else None,
        status="fallback" if available_chat else "unavailable",
        fallback_used=True,
        message=f"ما لقيناش موديل مناسب لـ {task}.",
    )
    return result
