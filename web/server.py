import json
import subprocess
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.engine import GenioEngine, AGENTS_REGISTRY, HISTORY_PATH, BASE_DIR

app = FastAPI(title="Genio OS v4.0 Ultimate Enterprise Studio")
engine = GenioEngine()


class TaskRequest(BaseModel):
    agent_id: str = "Genio-Rayes"
    prompt: str
    model: Optional[str] = None
    use_rag: bool = True


class SwarmRequest(BaseModel):
    mission: str


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


@app.post("/api/task")
async def run_task(req: TaskRequest):
    return await engine.dispatch_task(req.agent_id, req.prompt, req.model, req.use_rag)


@app.post("/api/swarm")
async def run_swarm(req: SwarmRequest):
    return await engine.dispatch_swarm(req.mission)


@app.post("/api/autopilot/hitech-trainer")
async def build_hitech_trainer():
    project_dir = engine.workspace / "hitech-ai-trainer"
    project_dir.mkdir(parents=True, exist_ok=True)
    req_txt = (
        "torch>=2.2.0\ntorchvision>=0.17.0\naccelerate>=0.33.0\n"
        "transformers>=4.45.0\npeft>=0.12.0\ntrl>=0.10.0\ndatasets>=2.20.0\n"
        "bitsandbytes>=0.43.0\nllama-cpp-python>=0.2.90\ngradio>=4.40.0\n"
        "pillow>=10.2.0\npsutil>=5.9.0\nplaywright>=1.44.0\n"
    )
    (project_dir / "requirements.txt").write_text(req_txt, encoding="utf-8")
    prompt = (
        "Build the complete production files for `hitech-ai-trainer`: "
        "1) `hitech-ai-trainer/ROADMAP.md` with Mermaid architecture diagram, "
        "2) `hitech-ai-trainer/train_engine.py` supporting 4-bit NF4 QLoRA, Ubatch (128-4096), Turbo KV Cache, Multi-Token Prediction (MTP), and Jev Mode JSON decoding, "
        "3) `hitech-ai-trainer/app.py` with a 4-Tab Gradio UI. "
        "Write all files directly using <write_file path=\"...\"> tags and verify syntax using <run_cmd>."
    )
    return await engine.dispatch_task("Dev-Lead", prompt)


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
    return {"ok": True, "path": rel, "bytes": len(req.content)}


@app.post("/api/file/delete")
async def delete_file(req: FileDeleteRequest):
    rel = req.path.strip().lstrip("/")
    target = (engine.workspace / rel).resolve()
    if str(target).startswith(str(engine.workspace.resolve())) and target.is_file():
        target.unlink()
        return {"ok": True}
    return JSONResponse({"ok": False, "error": "Cannot delete file"}, status_code=400)


@app.post("/api/shell")
async def run_shell(req: ShellCmdRequest):
    res = engine.run_workspace_command(req.cmd, timeout=90)
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
    try:
        out = subprocess.check_output(["git", "pull", "origin", "main"], cwd=str(BASE_DIR), text=True, stderr=subprocess.STDOUT)
        return {"ok": True, "output": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/history")
async def get_history():
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).resolve().parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")
