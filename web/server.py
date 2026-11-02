import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.engine import GenioEngine, AGENTS_REGISTRY, HISTORY_PATH


app = FastAPI(title="Genio OS - Autonomous AI Enterprise")
engine = GenioEngine()




class TaskRequest(BaseModel):
    agent_id: str = "Genio-Rayes"
    prompt: str
    model: Optional[str] = None




class ConfigUpdateRequest(BaseModel):
    ollama_host: str
    primary_model: str




class FileReadRequest(BaseModel):
    path: str




@app.get("/api/status")
async def get_status():
    telemetry = engine.get_system_telemetry()
    ollama = await engine.check_ollama_status()
    files = engine.list_workspace_files()
    return {
        "telemetry": telemetry,
        "ollama": ollama,
        "agents": AGENTS_REGISTRY,
        "files": files
    }




@app.post("/api/task")
async def run_task(req: TaskRequest):
    result = await engine.dispatch_task(req.agent_id, req.prompt, req.model)
    return result




@app.post("/api/autopilot/hitech-trainer")
async def build_hitech_trainer(req: Request):
    """
    1-Click Autonomous Pipeline:
    Deploys the entire HITECH AI Trainer v2.0 project directly into /data/genio-os/workspace/hitech-ai-trainer
    and asks the active Agent team to audit and extend it.
    """
    project_dir = engine.workspace / "hitech-ai-trainer"
    project_dir.mkdir(parents=True, exist_ok=True)


    # Seed production-grade HITECH AI Trainer v2.0 core files immediately
    req_txt = (
        "torch>=2.2.0\ntorchvision>=0.17.0\naccelerate>=0.33.0\n"
        "transformers>=4.45.0\npeft>=0.12.0\ntrl>=0.10.0\ndatasets>=2.20.0\n"
        "bitsandbytes>=0.43.0\nllama-cpp-python>=0.2.90\ngradio>=4.40.0\n"
        "pillow>=10.2.0\npsutil>=5.9.0\n"
    )
    (project_dir / "requirements.txt").write_text(req_txt, encoding="utf-8")


    prompt = (
        "Create a complete, production-ready `ROADMAP.md` and `train_engine.py` inside `hitech-ai-trainer/` "
        "implementing 4-bit NF4 QLoRA, Ubatch size optimization (128-4096), Turbo KV Cache quantization, "
        "Multi-Token Prediction (MTP), and Jev Mode parallel JSON decoding. "
        "Use <write_file path=\"hitech-ai-trainer/...\"> tags and verify syntax with <run_cmd>."
    )
    res = await engine.dispatch_task("Dev-Lead", prompt)
    return res




@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    engine.save_config({
        "ollama_host": req.ollama_host.strip(),
        "primary_model": req.primary_model.strip()
    })
    return {"ok": True, "config": engine.config}




@app.post("/api/file")
async def read_workspace_file(req: FileReadRequest):
    target = (engine.workspace / req.path).resolve()
    if not str(target).startswith(str(engine.workspace.resolve())) or not target.is_file():
        return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)
    return {"ok": True, "path": req.path, "content": target.read_text(encoding="utf-8", errors="replace")}




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
