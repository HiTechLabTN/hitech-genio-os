"""Tool registry and sandbox — Plan v1 §4.4.

Every capability the agents can use is declared here with a JSON schema, a
permission level and a single entry point. Nothing executes through ad-hoc text
parsing any more: callers name a tool, the registry checks permission, the
sandbox checks the command, and the caller audits the result.

Permission levels:
  safe       read-only, runs immediately
  confirm    writes/ordinary commands, runs when the profile allows writing
  dangerous  deletion/network/shell, always needs a human approval
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PERMISSIONS = ("safe", "confirm", "dangerous")

DANGEROUS_PATTERNS = [
    r"rm\s+-[a-z]*r[a-z]*f?\s+/\s*$",
    r"rm\s+-[a-z]*r[a-z]*f?\s+/\*",
    r"\bsudo\b",
    r"\bdoas\b",
    r"\bpkexec\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/(sd|nvme|vd)",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
    r":\(\)\s*\{",
    r"\bchmod\s+-R\s+777\s+/",
    r"\|\s*(ba|z)?sh\b",
    r"\bhistory\s+-c\b",
]

ALLOWED_BINARIES = {
    "python",
    "python3",
    "pip",
    "pip3",
    "pytest",
    "git",
    "ls",
    "cat",
    "echo",
    "printf",
    "mkdir",
    "touch",
    "cp",
    "mv",
    "rm",
    "find",
    "grep",
    "sed",
    "awk",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "tar",
    "zip",
    "unzip",
    "npm",
    "node",
    "npx",
    "bash",
    "sh",
    "docker",
    "du",
    "df",
    "date",
    "env",
    "which",
}

DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 300
MAX_OUTPUT = 4000


class ToolError(Exception):
    """Caller-facing tool failure."""


class ToolDenied(ToolError):
    """Permission/policy refusal (403)."""


class ToolNotFound(ToolError):
    """Unknown tool name (404)."""


@dataclass
class ToolContext:
    workspace: Path
    user: Optional[Dict[str, Any]] = None
    safety: Dict[str, Any] = field(default_factory=dict)
    profile: Dict[str, Any] = field(default_factory=dict)

    @property
    def role(self) -> str:
        return str((self.user or {}).get("role") or "viewer")

    @property
    def shell_policy(self) -> str:
        return str(self.safety.get("shell") or "confirm")

    @property
    def write_policy(self) -> str:
        return str(self.safety.get("write") or "allow_workspace")


@dataclass
class Tool:
    name: str
    description: str
    permission: str
    params: Dict[str, Any]
    handler: Callable[..., Dict[str, Any]]
    min_role: str = "member"

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission": self.permission,
            "params": self.params,
            "min_role": self.min_role,
        }


REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    if tool.permission not in PERMISSIONS:
        raise ValueError(f"permission invalide: {tool.permission}")
    REGISTRY[tool.name] = tool
    return tool


def get(name: str) -> Tool:
    tool = REGISTRY.get(name)
    if tool is None:
        raise ToolNotFound(f"أداة غير معروفة: {name}")
    return tool


def list_tools() -> List[Dict[str, Any]]:
    return [tool.describe() for tool in REGISTRY.values()]


# ---------------------------------------------------------------------------
# Sandbox helpers
# ---------------------------------------------------------------------------
def resolve_in_workspace(ctx: ToolContext, raw_path: str) -> Path:
    """Resolve a path and refuse anything outside the caller's workspace."""
    if not raw_path:
        raise ToolError("مسار فارغ")
    root = Path(ctx.workspace).resolve()
    target = (root / raw_path.lstrip("/")).resolve()
    if target != root and root not in target.parents:
        raise ToolDenied("المسار خارج الـ workspace")
    return target


def check_command(cmd: str) -> str:
    """Reject shell metacharacter attacks and binaries we do not allow."""
    cmd = (cmd or "").strip()
    if not cmd:
        raise ToolError("أمر فارغ")
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            raise ToolDenied(f"أمر ممنوع: {pattern}")
    binary = cmd.split()[0].split("/")[-1]
    if binary not in ALLOWED_BINARIES:
        raise ToolDenied(f"الأمر غير مسموح في الـ sandbox: {binary}")
    return cmd


def run_command(ctx: ToolContext, cmd: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    cmd = check_command(cmd)
    timeout = max(1, min(int(timeout or DEFAULT_TIMEOUT), MAX_TIMEOUT))
    root = Path(ctx.workspace)
    root.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(root), "LANG": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"الأمر تعدّى الـ timeout ({timeout}s)")
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return {
        "returncode": proc.returncode,
        "output": output[-MAX_OUTPUT:],
        "status": "success" if proc.returncode == 0 else "error",
    }


# ---------------------------------------------------------------------------
# Built-in tools
# ---------------------------------------------------------------------------
def _list_files(ctx: ToolContext, **_):
    root = Path(ctx.workspace)
    root.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(root)), "size": path.stat().st_size})
        if len(files) >= 500:
            break
    return {"files": files, "count": len(files)}


def _read_file(ctx: ToolContext, path: str = "", **_):
    target = resolve_in_workspace(ctx, path)
    if not target.is_file():
        raise ToolError("الملف ما موجودش")
    return {"path": path, "content": target.read_text(encoding="utf-8", errors="replace")[:200_000]}


def _write_file(ctx: ToolContext, path: str = "", content: str = "", **_):
    if ctx.write_policy == "deny":
        raise ToolDenied("الكتابة ممنوعة في هذا البروفيل")
    target = resolve_in_workspace(ctx, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": path, "bytes": len(content)}


def _delete_file(ctx: ToolContext, path: str = "", **_):
    target = resolve_in_workspace(ctx, path)
    if not target.is_file():
        raise ToolError("الملف ما موجودش")
    target.unlink()
    return {"path": path, "deleted": True}


def _run_command(ctx: ToolContext, cmd: str = "", timeout: int = DEFAULT_TIMEOUT, **_):
    if ctx.shell_policy == "deny":
        raise ToolDenied("الـ shell مقفول في هذا البروفيل")
    return run_command(ctx, cmd, timeout)


def _git_status(ctx: ToolContext, **_):
    root = Path(ctx.workspace)
    if not (root / ".git").exists():
        return {"is_repo": False, "output": ""}
    return {"is_repo": True, **run_command(ctx, "git status --short --branch")}


def _git_commit(ctx: ToolContext, message: str = "", **_):
    root = Path(ctx.workspace)
    if not (root / ".git").exists():
        raise ToolError("ما فمّاش git repo في الـ workspace")
    if not message.strip():
        raise ToolError("commit يحتاج رسالة")
    run_command(ctx, "git add -A")
    return {"committed": True, **run_command(ctx, f'git commit -m "{message.strip()[:200]}"')}


register(
    Tool(
        name="list_files",
        description="عرض الملفات في الـ workspace",
        permission="safe",
        params={},
        handler=_list_files,
        min_role="viewer",
    )
)
register(
    Tool(
        name="read_file",
        description="قراءة ملف من الـ workspace",
        permission="safe",
        params={"path": {"type": "string"}},
        handler=_read_file,
        min_role="viewer",
    )
)
register(
    Tool(
        name="write_file",
        description="كتابة ملف كامل في الـ workspace",
        permission="confirm",
        params={"path": {"type": "string"}, "content": {"type": "string"}},
        handler=_write_file,
    )
)
register(
    Tool(
        name="delete_file",
        description="حذف ملف من الـ workspace",
        permission="confirm",
        params={"path": {"type": "string"}},
        handler=_delete_file,
    )
)
register(
    Tool(
        name="run_command",
        description="تنفيذ أمر في sandbox داخل الـ workspace",
        permission="dangerous",
        params={"cmd": {"type": "string"}, "timeout": {"type": "integer"}},
        handler=_run_command,
    )
)
register(
    Tool(
        name="git_status",
        description="حالة الـ git في الـ workspace",
        permission="safe",
        params={},
        handler=_git_status,
        min_role="viewer",
    )
)
register(
    Tool(
        name="git_commit",
        description="commit لكل التغييرات في الـ workspace",
        permission="confirm",
        params={"message": {"type": "string"}},
        handler=_git_commit,
    )
)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
ROLE_RANK = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


def requires_approval(tool: Tool, ctx: ToolContext) -> bool:
    """Dangerous tools always need a human; shell policy can also force it."""
    if tool.permission == "dangerous":
        # An advanced profile with an explicit "allow_workspace" shell keeps the
        # flow fast, but only for admins/owners.
        if ctx.shell_policy == "allow_workspace" and ctx.role in ("admin", "owner"):
            return False
        return True
    if tool.permission == "confirm" and ctx.write_policy == "deny":
        return True
    return False


def preflight(tool: Tool, ctx: ToolContext) -> None:
    """Refuse before asking for an approval nobody could ever grant."""
    if ROLE_RANK.get(ctx.role, -1) < ROLE_RANK.get(tool.min_role, 1):
        raise ToolDenied(f"{tool.name} يحتاج صلاحية {tool.min_role}")
    if tool.name == "run_command" and ctx.shell_policy == "deny":
        raise ToolDenied("الـ shell مقفول في هذا البروفيل")


def invoke(tool: Tool, ctx: ToolContext, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = dict(params or {})
    preflight(tool, ctx)
    try:
        result = tool.handler(ctx, **params)
    except TypeError as exc:
        raise ToolError(f"واحد من الـ params غالط: {exc}")
    return {"ok": True, "tool": tool.name, "permission": tool.permission, "result": result}
