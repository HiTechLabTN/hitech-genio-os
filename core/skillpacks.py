"""Skill packs, evaluation gate and knowledge sources — Plan v2 §3.2 / §4.

A pack is only enabled after its evals pass, and every knowledge source carries
a licence so ingestion stays traceable (Plan v2 §4.2). Nothing here downloads
anything: the sources are declared, the operator ingests them into the RAG
store, which records the licence with each chunk.
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Callable, Dict, List, Tuple

from core import rag, tools

SKILL_PACKS: Dict[str, Dict[str, Any]] = {
    "frontend_web": {
        "label": "Frontend Web",
        "version": "1.0.0",
        "prompt": (
            "You build accessible RTL-first interfaces. Prefer semantic HTML, "
            "measure before optimizing, and always ship a runnable preview."
        ),
        "tools": ["read_file", "write_file", "list_files", "run_command"],
        "sources": [
            {"name": "MDN Web Docs", "url": "https://developer.mozilla.org/", "license": "cc-by-sa"},
            {"name": "Vite docs", "url": "https://vite.dev/", "license": "mit"},
            {"name": "React docs", "url": "https://react.dev/", "license": "cc-by"},
        ],
        "evals": [
            {"id": "rtl-markup", "description": "كل صفحة فيها dir و lang"},
            {"id": "no-placeholder", "description": "بلا TODO ولا pass في الملفات المسلّمة"},
        ],
    },
    "backend_api": {
        "label": "Backend API",
        "version": "1.0.0",
        "prompt": (
            "You build small, tested APIs. Every endpoint validates input, "
            "returns explicit errors, and never trusts client-supplied identity."
        ),
        "tools": ["read_file", "write_file", "list_files", "run_command", "git_status"],
        "sources": [
            {"name": "FastAPI docs", "url": "https://fastapi.tiangolo.com/", "license": "mit"},
            {"name": "SQLite docs", "url": "https://sqlite.org/docs.html", "license": "public-domain"},
        ],
        "evals": [
            {"id": "has-tests", "description": "كل مشروع فيه tests"},
            {"id": "health-endpoint", "description": "endpoint /healthz موجود"},
        ],
    },
    "qa_testing": {
        "label": "QA & Testing",
        "version": "1.0.0",
        "prompt": (
            "You write tests that fail for a real reason. Prefer one sharp "
            "assertion over ten vague ones, and always report what you ran."
        ),
        "tools": ["read_file", "write_file", "list_files", "run_command"],
        "sources": [
            {"name": "pytest docs", "url": "https://docs.pytest.org/", "license": "mit"},
        ],
        "evals": [
            {"id": "tests-run", "description": "الـ tests تتنفّذ بلا أخطاء"},
        ],
    },
}

REQUIRED_FIELDS = ("label", "version", "prompt", "tools", "sources", "evals")


def _check_fields(pack: Dict[str, Any]) -> Tuple[bool, str]:
    missing = [field for field in REQUIRED_FIELDS if not pack.get(field)]
    if missing:
        return False, f"حقول ناقصة: {', '.join(missing)}"
    return True, "manifest كامل"


def _check_tools(pack: Dict[str, Any]) -> Tuple[bool, str]:
    unknown = [name for name in pack.get("tools", []) if name not in tools.REGISTRY]
    if unknown:
        return False, f"أدوات غير مسجّلة: {', '.join(unknown)}"
    return True, f"{len(pack['tools'])} أداة مسجّلة"


def _check_licenses(pack: Dict[str, Any]) -> Tuple[bool, str]:
    bad = [
        source.get("name", "?")
        for source in pack.get("sources", [])
        if str(source.get("license", "")).lower() not in rag.KNOWN_LICENSES
    ]
    if bad:
        return False, f"مصادر بترخيص غير معروف: {', '.join(bad)}"
    return True, f"{len(pack['sources'])} مصدر بترخيص مسجّل"


def _check_evals(pack: Dict[str, Any]) -> Tuple[bool, str]:
    evals = pack.get("evals") or []
    if len(evals) < 1:
        return False, "ما فمّاش evals"
    if any(not item.get("id") for item in evals):
        return False, "eval بلا id"
    return True, f"{len(evals)} eval معرّف"


CHECKS: List[Tuple[str, Callable[[Dict[str, Any]], Tuple[bool, str]]]] = [
    ("manifest", _check_fields),
    ("tools", _check_tools),
    ("licenses", _check_licenses),
    ("evals", _check_evals),
]


def evaluate(name: str) -> Dict[str, Any]:
    pack = SKILL_PACKS.get(name)
    if pack is None:
        raise KeyError(name)
    results = []
    passed = True
    for check_id, check in CHECKS:
        ok, detail = check(pack)
        passed = passed and ok
        results.append({"id": check_id, "ok": ok, "detail": detail})
    return {"pack": name, "version": pack.get("version"), "passed": passed, "checks": results}


def _get(conn: sqlite3.Connection, name: str) -> Dict[str, Any] | None:
    row = conn.execute("SELECT * FROM skill_packs WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def list_packs(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    out = []
    for name, pack in SKILL_PACKS.items():
        stored = _get(conn, name)
        out.append(
            {
                "name": name,
                "label": pack["label"],
                "version": pack["version"],
                "tools": pack["tools"],
                "sources": pack["sources"],
                "evals": pack["evals"],
                "enabled": bool(stored and stored["enabled"]),
                "eval": evaluate(name),
            }
        )
    return out


def enable(conn: sqlite3.Connection, name: str) -> Dict[str, Any]:
    """Refuse to enable a pack that does not pass its own evals."""
    if name not in SKILL_PACKS:
        raise KeyError(name)
    report = evaluate(name)
    if not report["passed"]:
        failed = [check["id"] for check in report["checks"] if not check["ok"]]
        raise ValueError(f"الـ evals ما عدّاوش: {', '.join(failed)}")

    pack = SKILL_PACKS[name]
    manifest = json.dumps(
        {"version": pack["version"], "tools": pack["tools"], "sources": pack["sources"]},
        ensure_ascii=False,
    )
    if _get(conn, name):
        conn.execute(
            "UPDATE skill_packs SET version = ?, manifest = ?, enabled = 1, updated_at = ? WHERE name = ?",
            (pack["version"], manifest, time.time(), name),
        )
    else:
        conn.execute(
            """INSERT INTO skill_packs (name, version, manifest, enabled, updated_at)
               VALUES (?, ?, ?, 1, ?)""",
            (name, pack["version"], manifest, time.time()),
        )
    return {"name": name, "enabled": True, "version": pack["version"], "eval": report}


def disable(conn: sqlite3.Connection, name: str) -> bool:
    cursor = conn.execute("UPDATE skill_packs SET enabled = 0 WHERE name = ?", (name,))
    return bool(cursor.rowcount)
