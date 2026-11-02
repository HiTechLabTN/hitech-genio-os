import os
import re
import json
import time
import hashlib
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
HISTORY_PATH = BASE_DIR / "logs" / "tasks_history.json"
EXPERIENCE_LEDGER = BASE_DIR / "memory" / "experience_ledger.jsonl"
ERROR_RESOLUTIONS = BASE_DIR / "memory" / "error_resolutions.json"
PLAYBOOKS_PATH = BASE_DIR / "memory" / "playbooks.json"

AGENTS_REGISTRY = {
    "Genio-Rayes": {
        "title": "El Rayes (PDG & Master Orchestrator)",
        "icon": "👑",
        "badge": "CEO / Architect",
        "role": (
            "You are Genio (El Rayes), the decisive Technical CEO & Master Architect of HiTech Lab TN. "
            "RULES:\n"
            "1. Before writing code, briefly state your architectural plan.\n"
            "2. NEVER output placeholders (`pass` or `TODO`). Write complete production files using:\n"
            "<write_file path=\"folder/filename.ext\">\nFULL CODE\n</write_file>\n"
            "3. Run verification or shell diagnostics using:\n"
            "<run_cmd>bash command</run_cmd>\n"
            "4. If you discover a reusable technique or tool, register a playbook lesson using:\n"
            "<learn_rule title=\"Short Title\">Reusable solution or command pattern</learn_rule>"
        )
    },
    "Dev-Lead": {
        "title": "Dev-Lead (Full-Stack, AI & QLoRA Engineer)",
        "icon": "💻",
        "badge": "Code & AI",
        "role": (
            "You are Dev-Lead, Principal Engineer for Python, FastAPI, Gradio, PyTorch, 4-bit NF4 QLoRA, and llama.cpp. "
            "Write 100% complete files using <write_file path=\"...\">...</write_file>, test syntax via <run_cmd>python3 -m py_compile ...</run_cmd>, "
            "and record reusable engineering patterns via <learn_rule title=\"...\">...</learn_rule>."
        )
    },
    "Infra-Ops": {
        "title": "Infra-Ops (Linux, Docker, Tailscale & Git)",
        "icon": "⚙️",
        "badge": "DevOps / SysAdmin",
        "role": (
            "You are Infra-Ops, Senior Linux & Distributed Systems Engineer managing server `tn` and GPU node `Legion`. "
            "Create scripts via <write_file>, run commands via <run_cmd>, and save sysadmin fixes via <learn_rule title=\"...\">...</learn_rule>."
        )
    },
    "QA-Sec": {
        "title": "QA-Sec (Testing, Auto-Heal & VRAM Auditor)",
        "icon": "🛡️",
        "badge": "Security & QA",
        "role": (
            "You are QA-Sec, Automated Quality & Self-Healing Auditor. Run tests via <run_cmd>, fix any syntax or runtime errors directly via <write_file>, "
            "and document every error resolution via <learn_rule title=\"Fix for ...\">...</learn_rule>."
        )
    },
    "Vision-UI": {
        "title": "Vision-UI (3D UX, Media, Playwright & Docs)",
        "icon": "🎨",
        "badge": "3D UI & Media",
        "role": (
            "You are Vision-UI, Creative Frontend & Documentation Architect. Build 3D HTML/CSS interfaces, Playwright visual scripts, and articles via <write_file>."
        )
    }
}


class GenioEngine:
    def __init__(self):
        self.reload_config()
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXPERIENCE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        if not HISTORY_PATH.exists():
            HISTORY_PATH.write_text("[]", encoding="utf-8")
        if not EXPERIENCE_LEDGER.exists():
            EXPERIENCE_LEDGER.write_text("", encoding="utf-8")
        if not ERROR_RESOLUTIONS.exists():
            ERROR_RESOLUTIONS.write_text("[]", encoding="utf-8")
        if not PLAYBOOKS_PATH.exists():
            default_playbooks = [
                {
                    "id": "pb-init-1",
                    "title": "Standard Python File Verification",
                    "pattern": "Always compile-check generated Python files using `python3 -m py_compile <file>` immediately after writing.",
                    "agent": "System",
                    "uses": 1,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            ]
            PLAYBOOKS_PATH.write_text(json.dumps(default_playbooks, indent=2, ensure_ascii=False), encoding="utf-8")

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
        load1, load5, _ = os.getloadavg()
        mem_stats = self.get_memory_stats()
        return {
            "version": self.config.get("version", "5.0.0"),
            "node": self.config.get("node_name", "tn"),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "load_avg": f"{load1:.2f} / {load5:.2f}",
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "ollama_host": self.config["ollama_host"],
            "active_model": self.config["primary_model"],
            "temperature": self.config.get("temperature", 0.2),
            "num_ctx": self.config.get("num_ctx", 8192),
            "workspace": str(self.workspace),
            "port": self.config.get("port", 8099),
            "memory_stats": mem_stats
        }

    async def check_ollama_status(self) -> Dict[str, Any]:
        base = self.config["ollama_host"].rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                r = await client.get(f"{base}/api/tags")
                if r.status_code == 200:
                    models_raw = r.json().get("models", [])
                    models = [m["name"] for m in models_raw]
                    details = [
                        {
                            "name": m["name"],
                            "size_gb": round(m.get("size", 0) / (1024**3), 2),
                            "quant": m.get("details", {}).get("quantization_level", "Q4")
                        }
                        for m in models_raw
                    ]
                    return {"online": True, "models": models, "details": details, "host": self.config["ollama_host"]}
        except Exception as e:
            return {"online": False, "models": [], "details": [], "host": self.config["ollama_host"], "error": str(e)}
        return {"online": False, "models": [], "details": [], "host": self.config["ollama_host"]}

    # ==========================================================================
    # SELF-EVOLVING MEMORY, JSONL LEDGER & PLAYBOOK ENGINE
    # ==========================================================================
    def load_playbooks(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(PLAYBOOKS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []

    def add_playbook(self, title: str, pattern: str, agent: str = "User/Override") -> Dict[str, Any]:
        pbs = self.load_playbooks()
        pb_id = "pb-" + hashlib.md5((title + pattern).encode()).hexdigest()[:6]
        for existing in pbs:
            if existing["id"] == pb_id or existing["title"].lower() == title.lower():
                existing["pattern"] = pattern
                existing["uses"] = existing.get("uses", 1) + 1
                existing["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                PLAYBOOKS_PATH.write_text(json.dumps(pbs, indent=2, ensure_ascii=False), encoding="utf-8")
                return existing
        new_pb = {
            "id": pb_id,
            "title": title.strip(),
            "pattern": pattern.strip(),
            "agent": agent,
            "uses": 1,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        pbs.insert(0, new_pb)
        PLAYBOOKS_PATH.write_text(json.dumps(pbs[:100], indent=2, ensure_ascii=False), encoding="utf-8")
        return new_pb

    def load_error_resolutions(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(ERROR_RESOLUTIONS.read_text(encoding="utf-8"))
        except Exception:
            return []

    def record_error_resolution(self, error_sig: str,failed_cmd_or_file: str, resolution: str, fixed_by: str = "Auto-Heal"):
        res_list = self.load_error_resolutions()
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error_signature": error_sig[:300],
            "target": failed_cmd_or_file,
            "resolution": resolution[:1000],
            "fixed_by": fixed_by
        }
        res_list.insert(0, entry)
        ERROR_RESOLUTIONS.write_text(json.dumps(res_list[:100], indent=2, ensure_ascii=False), encoding="utf-8")

    def log_experience_jsonl(self, event_data: Dict[str, Any]):
        event_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(EXPERIENCE_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + "\n")

    def get_recent_ledger(self, limit: int = 40) -> List[Dict[str, Any]]:
        if not EXPERIENCE_LEDGER.exists():
            return []
        lines = EXPERIENCE_LEDGER.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        out = []
        for ln in reversed(lines[-limit:]):
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return out

    def get_memory_stats(self) -> Dict[str, Any]:
        pbs = self.load_playbooks()
        errs = self.load_error_resolutions()
        ledger_count = 0
        if EXPERIENCE_LEDGER.exists():
            ledger_count = len(EXPERIENCE_LEDGER.read_text(encoding="utf-8", errors="replace").splitlines())
        return {
            "playbooks_count": len(pbs),
            "error_fixes_count": len(errs),
            "total_experiences": ledger_count
        }

    def retrieve_relevant_memory(self, prompt: str) -> str:
        """
        Finds matching playbooks, past successful tasks, and past error resolutions
        so agents NEVER repeat mistakes and immediately reuse proven solutions.
        """
        q_words = set(w.lower() for w in re.findall(r'\w+', prompt) if len(w) > 2)
        pbs = self.load_playbooks()
        scored_pbs = []
        for pb in pbs:
            text = (pb["title"] + " " + pb["pattern"]).lower()
            score = sum(2 for w in q_words if w in text) + pb.get("uses", 1)
            scored_pbs.append((score, pb))
        scored_pbs.sort(key=lambda x: x[0], reverse=True)

        top_pbs = [f"- [{p['title']}]: {p['pattern']}" for _, p in scored_pbs[:6]]
        errs = self.load_error_resolutions()[:5]
        err_lines = [f"- Avoid Error `{e['error_signature'][:100]}` -> Fix: {e['resolution'][:200]}" for e in errs]

        mem_block = "\n[SELF-EVOLVING INSTITUTIONAL MEMORY (APPLY IMMEDIATELY WITHOUT RE-INVENTING)]\n"
        if top_pbs:
            mem_block += "Proven Playbooks:\n" + "\n".join(top_pbs) + "\n"
        if err_lines:
            mem_block += "Past Error Resolutions (Do Not Repeat):\n" + "\n".join(err_lines) + "\n"
        return mem_block

    # ==========================================================================
    # TOOL EXECUTION & AUTO-SYNTAX VERIFICATION
    # ==========================================================================
    def execute_tools_in_response(self, raw_text: str, agent_id: str = "Agent") -> List[Dict[str, Any]]:
        actions_log = []

        # 1. Extract learned playbooks (<learn_rule title="...">...</learn_rule>)
        rule_pattern = re.compile(r'<learn_rule\s+title=["\']([^"\']+)["\']\s*>(.*?)</learn_rule>', re.DOTALL)
        for match in rule_pattern.finditer(raw_text):
            r_title = match.group(1).strip()
            r_body = match.group(2).strip()
            if r_title and r_body:
                pb = self.add_playbook(r_title, r_body, agent=agent_id)
                actions_log.append({"type": "learn_rule", "title": pb["title"], "status": "memorized"})

        # 2. Extract file writes (<write_file path="...">...</write_file>)
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

            # Automatic Syntax Check if Python file
            syntax_ok = True
            syntax_err = ""
            if target_path.suffix == ".py":
                chk = subprocess.run(
                    ["python3", "-m", "py_compile", str(target_path)],
                    capture_output=True, text=True
                )
                if chk.returncode != 0:
                    syntax_ok = False
                    syntax_err = chk.stderr.strip()

            actions_log.append({
                "type": "write_file",
                "path": str(target_path.relative_to(self.workspace)),
                "bytes": len(content),
                "status": "success" if syntax_ok else "syntax_error",
                "error": syntax_err
            })

        # 3. Extract shell commands (<run_cmd>...</run_cmd>)
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
                cmd, shell=True, cwd=str(self.workspace),
                capture_output=True, text=True, timeout=timeout
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

    # ==========================================================================
    # REAL-TIME BEHIND-THE-SCENES SSE STREAMING GENERATOR (WITH AUTO-HEAL)
    # ==========================================================================
    async def stream_task_events(self, agent_id: str, prompt: str, model_override: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Streams real-time Server-Sent Events (SSE) showing:
        - Memory retrieval & matched playbooks
        - Live token-by-token generation from Ollama (Legion)
        - Live tool execution (<write_file>, <run_cmd>, <learn_rule>)
        - Automatic Self-Healing loop if any command or syntax check fails!
        """
        def sse(event_type: str, payload: Dict[str, Any]) -> str:
            return f"data: {json.dumps({'event': event_type, **payload}, ensure_ascii=False)}\n\n"

        clean_prompt = re.sub(r'\[span_\d+\]\((start|end)_span\)', '', prompt).strip()
        agent = AGENTS_REGISTRY.get(agent_id, AGENTS_REGISTRY["Genio-Rayes"])
        model = model_override or self.config["primary_model"]
        url = f"{self.config['ollama_host'].rstrip('/')}/api/chat"

        yield sse("stage", {"agent": agent_id, "message": f"🧠 [{agent_id}] جاري استرجاع الخبرات السابقة والـ Playbooks من الذاكرة التطورية..."})
        memory_context = self.retrieve_relevant_memory(clean_prompt)
        existing_files = [f["path"] for f in self.list_workspace_files()[:50]]
        rag_text = self.get_rag_context(clean_prompt)

        sys_prompt = (
            f"{agent['role']}\n"
            f"{memory_context}\n"
            f"[WORKSPACE CONTEXT]\nRoot Path: {self.workspace}\nExisting Files: {existing_files}\n"
        )
        if rag_text:
            sys_prompt += f"\n[RAG KNOWLEDGE]\n{rag_text}\n"

        max_retries = int(self.config.get("auto_self_heal_retries", 2))
        attempt = 0
        current_prompt = clean_prompt

        while attempt <= max_retries:
            attempt += 1
            start_t = time.time()
            yield sse("stage", {
                "agent": agent_id,
                "message": f"⚡ [{agent_id}] متصل بـ {model} على Legion (المحاولة {attempt}/{max_retries+1}) — بدأ البث الحي للكواليس..."
            })

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": current_prompt}
                ],
                "stream": True,
                "options": {
                    "temperature": float(self.config.get("temperature", 0.2)),
                    "num_ctx": int(self.config.get("num_ctx", 8192))
                }
            }

            full_reply = ""
            token_count = 0
            try:
                async with httpx.AsyncClient(timeout=360.0) as client:
                    async with client.stream("POST", url, json=payload) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if not line.strip():
                                continue
                            chunk = json.loads(line)
                            tok = chunk.get("message", {}).get("content", "")
                            if tok:
                                full_reply += tok
                                token_count += 1
                                yield sse("token", {"agent": agent_id, "token": tok, "count": token_count})
                            if chunk.get("done"):
                                break
            except Exception as e:
                err_msg = f"تعذر الاتصال بـ Ollama: {str(e)}"
                self.log_experience_jsonl({
                    "agent": agent_id, "model": model, "prompt": clean_prompt[:300],
                    "status": "connection_error", "error": err_msg
                })
                yield sse("error", {"agent": agent_id, "error": err_msg})
                return

            elapsed = round(time.time() - start_t, 2)
            tps = round(token_count / elapsed, 1) if elapsed > 0 else 0

            yield sse("stage", {"agent": agent_id, "message": f"🛠️ [{agent_id}] اكتمل التوليد ({token_count} كلمة، {tps} tok/s). جاري تنفيذ الأوامر وكتابة الملفات في /data..."})
            actions = self.execute_tools_in_response(full_reply, agent_id=agent_id)

            errors_found = []
            for act in actions:
                yield sse("action", {"agent": agent_id, "action": act})
                if act.get("status") in ("error", "syntax_error"):
                    errors_found.append(act)

            # Log to JSONL Experience Ledger
            self.log_experience_jsonl({
                "agent": agent_id,
                "model": model,
                "attempt": attempt,
                "prompt": clean_prompt[:500],
                "actions": actions,
                "status": "failed_needs_heal" if errors_found else "success",
                "elapsed_sec": elapsed,
                "tokens_per_sec": tps
            })

            if not errors_found:
                record = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "agent": agent_id,
                    "model": model,
                    "prompt": clean_prompt,
                    "reply": full_reply,
                    "actions": actions,
                    "elapsed_sec": elapsed,
                    "tokens_per_sec": tps
                }
                self._append_history(record)
                yield sse("done", {
                    "agent": agent_id,
                    "elapsed_sec": elapsed,
                    "tokens_per_sec": tps,
                    "actions": actions,
                    "message": f"✅ [{agent_id}] اكتملت المهمة بنجاح وتم توثيق الخبرة في السجل الذكي!"
                })
                return

            # SELF-HEALING LOOP: An error happened in syntax or command execution!
            err_summary = json.dumps(errors_found, ensure_ascii=False)
            yield sse("heal", {
                "agent": agent_id,
                "attempt": attempt,
                "errors": errors_found,
                "message": f"🩹 [Auto-Self-Heal] رصد الوكيل خطأ برمجياً ويعمل الآن على إصلاحه تلقائياً وتعلم الدرس..."
            })

            if attempt <= max_retries:
                current_prompt = (
                    f"SELF-HEALING REQUIRED: Your previous execution produced the following error(s):\n{err_summary}\n\n"
                    f"1. Fix the code/command immediately using <write_file path=\"...\"> and <run_cmd>.\n"
                    f"2. Document how you fixed this error so we never repeat it using:\n"
                    f"<learn_rule title=\"Auto-Fix: ...\">Explain the root cause and fix</learn_rule>"
                )
                self.record_error_resolution(err_summary, agent_id, "Triggered automatic self-healing loop", fixed_by=agent_id)
            else:
                yield sse("done", {
                    "agent": agent_id,
                    "elapsed_sec": elapsed,
                    "tokens_per_sec": tps,
                    "actions": actions,
                    "message": f"⚠️ [{agent_id}] انتهت المحاولات التلقائية. تم تسجيل الخطأ في سجل التعلم ليقوم الريس بمراجعته."
                })
                return

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
                    snippets.append(f"--- [RAG: {p.name}] ---\n{txt[:1200]}")
        return "\n\n".join(snippets[:3])

    async def dispatch_task(self, agent_id: str, prompt: str, model_override: Optional[str] = None, use_rag: bool = True) -> Dict[str, Any]:
        # Synchronous wrapper for TUI compatibility
        full_reply = ""
        actions = []
        elapsed = 0.0
        tps = 0.0
        async for event_str in self.stream_task_events(agent_id, prompt, model_override):
            if event_str.startswith("data: "):
                ev = json.loads(event_str[6:])
                if ev.get("event") == "token":
                    full_reply += ev.get("token", "")
                elif ev.get("event") == "done":
                    actions = ev.get("actions", [])
                    elapsed = ev.get("elapsed_sec", 0.0)
                    tps = ev.get("tokens_per_sec", 0.0)
                elif ev.get("event") == "error":
                    return {"ok": False, "agent": agent_id, "error": ev.get("error")}
        return {"ok": True, "agent": agent_id, "reply": full_reply, "actions": actions, "elapsed_sec": elapsed, "tokens_per_sec": tps}

    def check_git_updates(self) -> Dict[str, Any]:
        try:
            subprocess.run(["git", "fetch", "origin", "main"], cwd=str(BASE_DIR), capture_output=True, timeout=10)
            local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(BASE_DIR), text=True).strip()
            remote = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=str(BASE_DIR), text=True).strip()
            behind = subprocess.check_output(["git", "rev-list", "--count", "HEAD..origin/main"], cwd=str(BASE_DIR), text=True).strip()
            changelog = subprocess.check_output(["git", "log", "-n", "5", "--pretty=format:%h - %s (%cr)"], cwd=str(BASE_DIR), text=True).strip()
            return {
                "update_available": local != remote and int(behind) > 0,
                "commits_behind": int(behind),
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
