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
        "badge": "CEO / Architect",
        "role": (
            "You are Genio (El Rayes), the decisive Technical CEO & Master Architect of HiTech Lab TN. "
            "STRICT EXECUTION RULE: Never output theoretical fluff or empty placeholders (`pass` / `TODO`). "
            "Whenever asked to create or modify code, write the complete production file directly to disk using:\n"
            "<write_file path=\"folder/filename.ext\">\nCOMPLETE PRODUCTION CODE\n</write_file>\n"
            "And run verification or shell commands using:\n"
            "<run_cmd>bash command here</run_cmd>\n"
            "Speak naturally in Tunisian Technical Arabic (or the user's chosen language) with sharp engineering authority."
        )
    },
    "Dev-Lead": {
        "title": "Dev-Lead (Full-Stack, AI & QLoRA Engineer)",
        "icon": "💻",
        "badge": "Code & AI",
        "role": (
            "You are Dev-Lead, Principal Engineer specializing in Python, FastAPI, Gradio, PyTorch, 4-bit NF4 QLoRA, "
            "llama.cpp optimizations (Ubatch, Turbo KV, MTP, Jev Mode), and Rust/NixOS. "
            "Always generate 100% complete files using <write_file path=\"...\">...</write_file> and verify syntax using <run_cmd>."
        )
    },
    "Infra-Ops": {
        "title": "Infra-Ops (Linux, Docker, Tailscale & Git)",
        "icon": "⚙️",
        "badge": "DevOps / SysAdmin",
        "role": (
            "You are Infra-Ops, Senior Linux & Distributed Systems Engineer managing server `tn` and GPU node `Legion` over Tailscale. "
            "Write production Bash scripts, systemd services, Dockerfiles via <write_file> and run live diagnostics via <run_cmd>."
        )
    },
    "QA-Sec": {
        "title": "QA-Sec (Automated Testing, Security & VRAM Auditor)",
        "icon": "🛡️",
        "badge": "Security & QA",
        "role": (
            "You are QA-Sec, Chief Security & Quality Auditor. Inspect workspace code, run syntax/pytest checks via <run_cmd>, "
            "audit VRAM/RAM usage, and patch bugs directly on disk via <write_file>."
        )
    },
    "Vision-UI": {
        "title": "Vision-UI (3D UX, Media, Playwright & Docs)",
        "icon": "🎨",
        "badge": "3D UI & Media",
        "role": (
            "You are Vision-UI, Creative Director & Frontend/Documentation Architect. Build stunning 3D Cyberpunk HTML/CSS/JS interfaces, "
            "Playwright visual automation scripts, Mermaid diagrams, and bilingual technical articles using <write_file>."
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
        self.rag_dir = Path(self.config.get("rag_dir", str(BASE_DIR / "rag_docs")))
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.rag_dir.mkdir(parents=True, exist_ok=True)

    def save_config(self, updates: Dict[str, Any]):
        self.config.update(updates)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        self.reload_config()

    def get_system_telemetry(self) -> Dict[str, Any]:
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(str(self.workspace))
        load1, load5, load15 = os.getloadavg()
        return {
            "version": self.config.get("version", "4.0.0"),
            "node": self.config.get("node_name", "tn"),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "load_avg": f"{load1:.2f} / {load5:.2f}",
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "ollama_host": self.config["ollama_host"],
            "active_model": self.config["primary_model"],
            "temperature": self.config.get("temperature", 0.2),
            "num_ctx": self.config.get("num_ctx", 8192),
            "workspace": str(self.workspace),
            "port": self.config.get("port", 8099)
        }

    async def check_ollama_status(self) -> Dict[str, Any]:
        base = self.config["ollama_host"].rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                r = await client.get(f"{base}/api/tags")
                ps_r = await client.get(f"{base}/api/ps")
                if r.status_code == 200:
                    models_raw = r.json().get("models", [])
                    models = [m["name"] for m in models_raw]
                    details = [
                        {
                            "name": m["name"],
                            "size_gb": round(m.get("size", 0) / (1024**3), 2),
                            "family": m.get("details", {}).get("family", "llm"),
                            "quant": m.get("details", {}).get("quantization_level", "Q4")
                        }
                        for m in models_raw
                    ]
                    running = []
                    if ps_r.status_code == 200:
                        running = [m["name"] for m in ps_r.json().get("models", [])]
                    return {
                        "online": True,
                        "models": models,
                        "details": details,
                        "running": running,
                        "host": self.config["ollama_host"]
                    }
        except Exception as e:
            return {"online": False, "models": [], "details": [], "running": [], "host": self.config["ollama_host"], "error": str(e)}
        return {"online": False, "models": [], "details": [], "running": [], "host": self.config["ollama_host"]}

    def execute_tools_in_response(self, raw_text: str) -> List[Dict[str, Any]]:
        actions_log = []
        file_pattern = re.compile(r'<write_file\s+path=["\']([^"\']+)["\']\s*>(.*?)</write_file>', re.DOTALL)
        for match in file_pattern.finditer(raw_text):
            rel_path = match.group(1).strip().lstrip("/")
            content = match.group(2).strip("\n")
            content = re.sub(r'^```[a-zA-Z0-9_-]*\n', '', content)
            content = re.sub(r'\n```$', '', content)

            target_path = (self.workspace / rel_path).resolve()
            if not str(target_path).startswith(str(self.workspace.resolve())):
                actions_log.append({"type": "write_file", "path": rel_path, "status": "blocked"})
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content + "\n", encoding="utf-8")
            actions_log.append({
                "type": "write_file",
                "path": str(target_path.relative_to(self.workspace)),
                "bytes": len(content),
                "status": "success"
            })

        cmd_pattern = re.compile(r'<run_cmd>(.*?)</run_cmd>', re.DOTALL)
        for match in cmd_pattern.finditer(raw_text):
            cmd = match.group(1).strip()
            if not cmd:
                continue
            res = self.run_workspace_command(cmd)
            actions_log.append({"type": "run_cmd", **res})

        return actions_log

    def run_workspace_command(self, cmd: str, timeout: int = 60) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            out = (proc.stdout + "\n" + proc.stderr).strip()
            return {
                "cmd": cmd,
                "returncode": proc.returncode,
                "output": out[:4000],
                "status": "success" if proc.returncode == 0 else "error"
            }
        except Exception as e:
            return {"cmd": cmd, "returncode": -1, "output": str(e), "status": "error"}

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

    def list_rag_docs(self) -> List[Dict[str, Any]]:
        docs = []
        for p in sorted(self.rag_dir.rglob("*")):
            if p.is_file():
                docs.append({
                    "name": p.name,
                    "size_kb": round(p.stat().st_size / 1024, 2),
                    "preview": p.read_text(encoding="utf-8", errors="replace")[:300]
                })
        return docs

    def get_rag_context(self, query: str) -> str:
        snippets = []
        q_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
        for p in sorted(self.rag_dir.rglob("*")):
            if p.is_file() and p.stat().st_size < 500_000:
                txt = p.read_text(encoding="utf-8", errors="replace")
                score = sum(1 for w in q_words if w in txt.lower())
                if score > 0 or len(snippets) < 2:
                    snippets.append(f"--- [RAG Document: {p.name}] ---\n{txt[:1500]}")
        return "\n\n".join(snippets[:3])

    async def dispatch_task(self, agent_id: str, prompt: str, model_override: Optional[str] = None, use_rag: bool = True) -> Dict[str, Any]:
        agent = AGENTS_REGISTRY.get(agent_id, AGENTS_REGISTRY["Genio-Rayes"])
        model = model_override or self.config["primary_model"]
        url = f"{self.config['ollama_host'].rstrip('/')}/api/chat"

        existing_files = [f["path"] for f in self.list_workspace_files()[:50]]
        rag_text = self.get_rag_context(prompt) if use_rag else ""

        sys_prompt = (
            f"{agent['role']}\n\n"
            f"[WORKSPACE CONTEXT]\nRoot Path: {self.workspace}\n"
            f"Existing Files: {existing_files}\n"
        )
        if rag_text:
            sys_prompt += f"\n[KNOWLEDGE BASE / RAG CONTEXT]\n{rag_text}\n"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": float(self.config.get("temperature", 0.2)),
                "num_ctx": int(self.config.get("num_ctx", 8192))
            }
        }

        start_t = time.time()
        try:
            async with httpx.AsyncClient(timeout=360.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                reply_text = data.get("message", {}).get("content", "")
                eval_count = data.get("eval_count", 0)
                eval_dur = data.get("eval_duration", 1) / 1e9
                tok_per_sec = round(eval_count / eval_dur, 1) if eval_dur > 0 else 0
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
            "elapsed_sec": elapsed,
            "tokens_per_sec": tok_per_sec
        }
        self._append_history(record)
        return {"ok": True, **record}

    async def dispatch_swarm(self, mission: str) -> Dict[str, Any]:
        """
        Sequential Multi-Agent Swarm Pipeline (Beats CrewAI & OpenBot):
        1. Genio-Rayes creates architecture & ROADMAP.md
        2. Dev-Lead writes complete implementation files
        3. QA-Sec runs syntax & verification checks
        """
        steps = []
        r1 = await self.dispatch_task(
            "Genio-Rayes",
            f"SWARM MISSION STEP 1 (Architecture): Analyze this mission and create a detailed `ROADMAP.md` file using <write_file path=\"ROADMAP.md\">:\n{mission}"
        )
        steps.append(r1)

        r2 = await self.dispatch_task(
            "Dev-Lead",
            f"SWARM MISSION STEP 2 (Code Implementation): Based on the mission below, write all required production Python/Bash/HTML code files using <write_file path=\"...\"> tags (Zero placeholders):\n{mission}"
        )
        steps.append(r2)

        r3 = await self.dispatch_task(
            "QA-Sec",
            "SWARM MISSION STEP 3 (Audit & Verification): Inspect the newly created files in the workspace, run syntax verification commands using <run_cmd>python3 -m py_compile ...</run_cmd>, and summarize readiness."
        )
        steps.append(r3)
        return {"ok": True, "swarm_steps": steps}

    def check_git_updates(self) -> Dict[str, Any]:
        try:
            subprocess.run(["git", "fetch", "origin", "main"], cwd=str(BASE_DIR), capture_output=True, timeout=10)
            local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(BASE_DIR), text=True).strip()
            remote = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=str(BASE_DIR), text=True).strip()
            commits_behind = subprocess.check_output(["git", "rev-list", "--count", "HEAD..origin/main"], cwd=str(BASE_DIR), text=True).strip()
            changelog = subprocess.check_output(["git", "log", "-n", "5", "--pretty=format:%h - %s (%cr)"], cwd=str(BASE_DIR), text=True).strip()
            return {
                "update_available": local != remote and int(commits_behind) > 0,
                "commits_behind": int(commits_behind),
                "local_hash": local[:7],
                "remote_hash": remote[:7],
                "changelog": changelog.split("\n") if changelog else []
            }
        except Exception as e:
            return {"update_available": False, "commits_behind": 0, "error": str(e), "changelog": []}

    def _append_history(self, record: Dict[str, Any]):
        try:
            hist = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            hist = []
        hist.insert(0, record)
        HISTORY_PATH.write_text(json.dumps(hist[:80], indent=2, ensure_ascii=False), encoding="utf-8")
