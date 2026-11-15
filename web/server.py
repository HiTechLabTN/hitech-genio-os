import json
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import security
from core.engine import GenioEngine, AGENTS_REGISTRY, HISTORY_PATH, BASE_DIR

app = FastAPI(title="Genio OS v5.0 Singularity — Self-Evolving AI Studio")
engine = GenioEngine()


def _feature_gate(enabled: bool, feature: str, setting: str, env_var: str):
    """403 response when a dangerous capability was not explicitly enabled."""
    if enabled:
        return None
    return JSONResponse(
        {
            "ok": False,
            "error": f"{feature} is disabled. Set {setting} in config.json or {env_var}=1 to enable it.",
        },
        status_code=403,
    )


@app.middleware("http")
async def api_security_guard(request: Request, call_next):
    """المرحلة 0: /api/* للمحلي فقط، إلا إذا token معرّف في الإعدادات."""
    if request.url.path.startswith("/api"):
        try:
            security.check_api_access(request, engine)
        except HTTPException as exc:
            return JSONResponse(
                {"ok": False, "error": exc.detail}, status_code=exc.status_code
            )
    return await call_next(request)


class TaskRequest(BaseModel):
    agent_id: str = "Genio-Rayes"
    prompt: str
    model: Optional[str] = None


class PlaybookAddRequest(BaseModel):
    title: str
    pattern: str
    agent: str = "Azmi (Manual Rule)"


class ErrorResolutionAddRequest(BaseModel):
    error_signature: str
    target: str
    resolution: str


class ConfigUpdateRequest(BaseModel):
    ollama_host: str
    primary_model: str
    temperature: float = 0.2
    num_ctx: int = 8192


class FileReadRequest(BaseModel):
    path: str


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileDeleteRequest(BaseModel):
    path: str


class ShellCmdRequest(BaseModel):
    cmd: str


class RagDocRequest(BaseModel):
    filename: str
    content: str


class ModelPullRequest(BaseModel):
    model_name: str


@app.get("/api/status")
async def get_status():
    telemetry = engine.get_system_telemetry()
    ollama = await engine.check_ollama_status()
    files = engine.list_workspace_files()
    rag_docs = engine.list_rag_docs()
    return {
        "telemetry": telemetry,
        "ollama": ollama,
        "agents": AGENTS_REGISTRY,
        "files": files,
        "rag_docs": rag_docs
    }


@app.post("/api/task/stream")
async def stream_task(req: TaskRequest):
    return StreamingResponse(
        engine.stream_task_events(req.agent_id, req.prompt, req.model),
        media_type="text/event-stream"
    )


@app.post("/api/task")
async def run_task(req: TaskRequest):
    return await engine.dispatch_task(req.agent_id, req.prompt, req.model)


@app.get("/api/memory")
async def get_memory():
    return {
        "stats": engine.get_memory_stats(),
        "playbooks": engine.load_playbooks(),
        "error_resolutions": engine.load_error_resolutions(),
        "ledger": engine.get_recent_ledger(50)
    }


@app.post("/api/memory/playbook")
async def add_playbook(req: PlaybookAddRequest):
    pb = engine.add_playbook(req.title, req.pattern, req.agent)
    return {"ok": True, "playbook": pb}


@app.post("/api/memory/resolution")
async def add_resolution(req: ErrorResolutionAddRequest):
    engine.record_error_resolution(req.error_signature, req.target, req.resolution, fixed_by="Azmi (Human Expert)")
    engine.add_playbook(f"Fix: {req.target}", f"When encountering `{req.error_signature}`, apply: {req.resolution}", agent="Azmi (Human Expert)")
    return {"ok": True}


@app.post("/api/file/read")
async def read_file(req: FileReadRequest):
    target = (engine.workspace / req.path).resolve()
    if not str(target).startswith(str(engine.workspace.resolve())) or not target.is_file():
        return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)
    return {"ok": True, "path": req.path, "content": target.read_text(encoding="utf-8", errors="replace")}


@app.post("/api/file/save")
async def save_file(req: FileWriteRequest):
    rel = req.path.strip().lstrip("/")
    target = (engine.workspace / rel).resolve()
    if not str(target).startswith(str(engine.workspace.resolve())):
        return JSONResponse({"ok": False, "error": "Invalid path"}, status_code=400)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    # Record human edit in experience ledger so agents learn from user edits
    engine.log_experience_jsonl({
        "agent": "Azmi (Human Edit)",
        "action": "manual_file_save",
        "path": rel,
        "bytes": len(req.content),
        "status": "success"
    })
    return {"ok": True, "path": rel, "bytes": len(req.content)}


@app.post("/api/file/delete")
async def delete_file(req: FileDeleteRequest):
    rel = req.path.strip().lstrip("/")
    target = (engine.workspace / rel).resolve()
    if str(target).startswith(str(engine.workspace.resolve())) and target.is_file():
        target.unlink()
        return {"ok": True}
    return JSONResponse({"ok": False, "error": "Cannot delete"}, status_code=400)


@app.post("/api/shell")
async def run_shell(req: ShellCmdRequest):
    gate = _feature_gate(
        security.shell_enabled(engine), "shell", "security.enable_shell", "GENIO_ENABLE_SHELL"
    )
    if gate:
        return gate
    res = engine.run_workspace_command(req.cmd, timeout=90)
    engine.log_experience_jsonl({
        "agent": "Web-Terminal",
        "cmd": req.cmd,
        "returncode": res["returncode"],
        "status": res["status"]
    })
    return {"ok": True, **res}


@app.post("/api/rag/add")
async def add_rag_doc(req: RagDocRequest):
    safe_name = Path(req.filename.strip()).name
    if not safe_name:
        return JSONResponse({"ok": False, "error": "Invalid filename"}, status_code=400)
    target = engine.rag_dir / safe_name
    target.write_text(req.content, encoding="utf-8")
    return {"ok": True, "name": safe_name}


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    engine.save_config({
        "ollama_host": req.ollama_host.strip(),
        "primary_model": req.primary_model.strip(),
        "temperature": req.temperature,
        "num_ctx": req.num_ctx
    })
    return {"ok": True, "config": engine.config}


@app.post("/api/models/pull")
async def pull_model(req: ModelPullRequest):
    url = f"{engine.config['ollama_host'].rstrip('/')}/api/pull"
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            r = await client.post(url, json={"name": req.model_name.strip(), "stream": False})
            return {"ok": r.status_code == 200, "response": r.text[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/update/check")
async def check_update():
    return engine.check_git_updates()


@app.post("/api/update/apply")
async def apply_update():
    gate = _feature_gate(
        security.update_enabled(engine), "update/apply", "security.enable_update", "GENIO_ENABLE_UPDATE"
    )
    if gate:
        return gate
    try:
        out = subprocess.check_output(["git", "pull", "origin", "main"], cwd=str(BASE_DIR), text=True, stderr=subprocess.STDOUT)
        return {"ok": True, "output": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).resolve().parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


import io
import zipfile
import mimetypes
from fastapi.responses import StreamingResponse, FileResponse

@app.get("/api/file/raw")
async def get_raw_file(path: str, download: bool = False):
    target = (engine.workspace / path).resolve()
    if not str(target).startswith(str(engine.workspace.resolve())) or not target.is_file():
        return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)
    mime, _ = mimetypes.guess_type(str(target))
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{target.name}"'
    return FileResponse(str(target), media_type=mime or "application/octet-stream", headers=headers)

@app.get("/api/workspace/zip")
async def export_workspace_zip(folder: str = ""):
    target_dir = (engine.workspace / folder).resolve()
    if not str(target_dir).startswith(str(engine.workspace.resolve())) or not target_dir.exists():
        target_dir = engine.workspace.resolve()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if target_dir.is_file():
            zf.write(target_dir, target_dir.name)
        else:
            for p in target_dir.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(target_dir))
    buf.seek(0)
    zip_name = f"{target_dir.name or 'workspace'}_project.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=security.bind_host(engine), port=int(engine.config.get("port", 8099)))
