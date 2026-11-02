"""
==============================================================================
GENIO OS - Autonomous Multi-Agent & Real File/Shell Execution Engine
==============================================================================
Unlike passive chatbots, Genio OS parses and executes real XML/JSON action blocks:
  - <write_file path="relative/path.py">...code...</write_file>
  - <run_cmd>pytest or bash command</run_cmd>
All operations are sandboxed inside /data/genio-os/workspace.
==============================================================================
"""


import os
import re
import json
import time
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
HISTORY_PATH = BASE_DIR / "logs" / "tasks_history.json"


AGENTS_REGISTRY = {
    "Genio-Rayes": {
        "title": "El Rayes (PDG & Master Orchestrator)",
        "icon": "👑",
        "color": "#00f2fe",
        "role": (
            "You are Genio (El Rayes), the decisive Technical CEO & Lead Architect of HiTech Lab TN. "
            "CRITICAL RULE: NEVER give theoretical advice, NEVER write placeholder functions (`pass` or `# TODO`), "
            "and NEVER lecture the user about management. "
            "When asked to build or modify a project, you MUST write complete, production-ready code directly into files "
            "using the exact tag format:\n"
            "<write_file path=\"project_folder/filename.ext\">\nFULL CODE HERE\n</write_file>\n"
            "And if you need to run shell commands (like git, pip, syntax check), use:\n"
            "<run_cmd>command here</run_cmd>\n"
            "Speak briefly in friendly Tunisian Arabic / Technical French/English, and let your real generated files do the talking."
        )
    },
    "Dev-Lead": {
        "title": "Dev-Lead (Full-Stack & AI Engineer)",
        "icon": "💻",
        "color": "#4facfe",
        "role": (
            "You are Dev-Lead, Senior Python, Gradio, PyTorch, QLoRA, and Rust/NixOS Engineer at HiTech Lab TN. "
            "STRICT REQUIREMENT: Output 100% complete, bug-free, production-ready files. Zero placeholders. "
            "Always save your code directly to disk using:\n"
            "<write_file path=\"path/to/file.py\">\nCOMPLETE CODE\n</write_file>\n"
            "Verify syntax using:\n"
            "<run_cmd>python3 -m py_compile path/to/file.py</run_cmd>"
        )
    },
    "Infra-Ops": {
        "title": "Infra-Ops (Linux, Docker, Tailscale & Git)",
        "icon": "⚙️",
        "color": "#43e97b",
        "role": (
            "You are Infra-Ops, System & DevOps Engineer managing server `tn`, `lab-1`, and `legion` over Tailscale. "
            "You write clean Bash scripts, Dockerfiles, systemd units, and execute real shell diagnostics using:\n"
            "<write_file path=\"script.sh\">\n#!/usr/bin/env bash\n...\n</write_file>\n"
            "<run_cmd>bash script.sh</run_cmd>"
        )
    },
    "QA-Sec": {
        "title": "QA-Sec (Testing, Security & VRAM Auditor)",
        "icon": "🛡️",
        "color": "#fa709a",
        "role": (
            "You are QA-Sec, Automated Quality Assurance & Security Auditor. "
            "Inspect files in the workspace, run syntax checks and unit tests via <run_cmd>, and fix any bugs directly via <write_file>."
        )
    },
    "Vision-UI": {
        "title": "Vision-UI (UX, Tutorials, Docs & Media)",
        "icon": "🎨",
        "color": "#f6d365",
        "role": (
            "You are Vision-UI, Documentation, UI/UX Designer, and Playwright Automation Specialist. "
            "You build modern HTML/CSS interfaces, Gradio themes, Mermaid architecture diagrams, and step-by-step tutorials using <write_file>."
        )
    }
}




class GenioEngine:
    def __init__(self):
        self.reload_config()
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not HISTORY_PATH.exists():
            HISTORY_PATH.write_text("[]", encoding="utf-8")


    def reload_config(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.workspace = Path(self.config["workspace_dir"])
        self.workspace.mkdir(parents=True, exist_ok=True)


    def save_config(self, new_cfg: Dict[str, Any]):
        self.config.update(new_cfg)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        self.reload_config()


    def get_system_telemetry(self) -> Dict[str, Any]:
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(str(self.workspace))
        return {
            "node": self.config.get("node_name", "tn"),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "ollama_host": self.config["ollama_host"],
            "active_model": self.config["primary_model"],
            "workspace": str(self.workspace)
        }


    async def check_ollama_status(self) -> Dict[str, Any]:
        url = f"{self.config['ollama_host'].rstrip('/')}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    return {"online": True, "models": models, "host": self.config["ollama_host"]}
        except Exception as e:
            return {"online": False, "models": [], "host": self.config["ollama_host"], "error": str(e)}
        return {"online": False, "models": [], "host": self.config["ollama_host"]}


    def execute_tools_in_response(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Extracts <write_file path="...">...</write_file> and <run_cmd>...</run_cmd>
        and executes them directly inside /data/genio-os/workspace.
        """
        actions_log = []


        # 1. File Writing Tool
        file_pattern = re.compile(r'<write_file\s+path=["\']([^"\']+)["\']\s*>(.*?)</write_file>', re.DOTALL)
        for match in file_pattern.finditer(raw_text):
            rel_path = match.group(1).strip().lstrip("/")
            content = match.group(2).strip("\n")
            # Strip accidental markdown code fences inside <write_file>
            content = re.sub(r'^```[a-zA-Z0-9_-]*\n', '', content)
            content = re.sub(r'\n```$', '', content)


            target_path = (self.workspace / rel_path).resolve()
            if not str(target_path).startswith(str(self.workspace.resolve())):
                actions_log.append({"type": "write_file", "path": rel_path, "status": "blocked_path_traversal"})
                continue


            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content + "\n", encoding="utf-8")
            actions_log.append({
                "type": "write_file",
                "path": str(target_path.relative_to(self.workspace)),
                "bytes": len(content),
                "status": "success"
            })


        # 2. Command Execution Tool
        cmd_pattern = re.compile(r'<run_cmd>(.*?)</run_cmd>', re.DOTALL)
        for match in cmd_pattern.finditer(raw_text):
            cmd = match.group(1).strip()
            if not cmd:
                continue
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.workspace),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                out = (proc.stdout + "\n" + proc.stderr).strip()
                actions_log.append({
                    "type": "run_cmd",
                    "cmd": cmd,
                    "returncode": proc.returncode,
                    "output": out[:2000],
                    "status": "success" if proc.returncode == 0 else "error"
                })
            except Exception as e:
                actions_log.append({
                    "type": "run_cmd",
                    "cmd": cmd,
                    "status": "error",
                    "output": str(e)
                })


        return actions_log


    def list_workspace_files(self) -> List[Dict[str, Any]]:
        files = []
        for p in sorted(self.workspace.rglob("*")):
            if p.is_file() and ".git/" not in str(p) and "__pycache__" not in str(p):
                files.append({
                    "path": str(p.relative_to(self.workspace)),
                    "size_kb": round(p.stat().st_size / 1024, 2),
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
                })
        return files


    async def dispatch_task(self, agent_id: str, prompt: str, model_override: Optional[str] = None) -> Dict[str, Any]:
        agent = AGENTS_REGISTRY.get(agent_id, AGENTS_REGISTRY["Genio-Rayes"])
        model = model_override or self.config["primary_model"]
        url = f"{self.config['ollama_host'].rstrip('/')}/api/chat"


        existing_files = [f["path"] for f in self.list_workspace_files()[:40]]
        workspace_context = (
            f"\n[WORKSPACE CONTEXT]\nRoot Path: {self.workspace}\n"
            f"Existing Files: {existing_files}\n"
            "Remember: Use <write_file path=\"...\">...</write_file> to create/update files on disk, "
            "and <run_cmd>...</run_cmd> to run commands in the workspace."
        )


        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": agent["role"] + workspace_context},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192
            }
        }


        start_t = time.time()
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                reply_text = data.get("message", {}).get("content", "")
        except Exception as e:
            return {
                "ok": False,
                "agent": agent_id,
                "model": model,
                "error": f"تعذر الاتصال بـ Ollama على {self.config['ollama_host']}: {str(e)}",
                "actions": []
            }


        actions = self.execute_tools_in_response(reply_text)
        elapsed = round(time.time() - start_t, 2)


        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent": agent_id,
            "model": model,
            "prompt": prompt,
            "reply": reply_text,
            "actions": actions,
            "elapsed_sec": elapsed
        }
        self._append_history(record)
        return {"ok": True, **record}


    def _append_history(self, record: Dict[str, Any]):
        try:
            hist = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            hist = []
        hist.insert(0, record)
        HISTORY_PATH.write_text(json.dumps(hist[:50], indent=2, ensure_ascii=False), encoding="utf-8")
