#!/usr/bin/env bash
# ==============================================================================
# 🚀 GENIO OS v5.0 (SINGULARITY EDITION) — Live Streaming + Self-Evolving Memory
# ==============================================================================
# Author: Mohamed Azmi Kaaniche (HiTech Lab TN)
# Repository: https://github.com/HiTechLabTN/hitech-genio-os
# Target Path: /data/genio-os
# Features:
#   - Real-Time SSE Token & Behind-The-Scenes Telemetry Streaming (Zero Timeouts)
#   - Self-Evolving JSONL Memory Ledger (Logs successes, errors, auto-fixes)
#   - Auto-Playbook & Dynamic Tool Synthesizer (Learns & reuses proven patterns)
#   - 6-in-1 3D Studio (Operations+Live Stream, IDE, Terminal, Memory/Playbooks, RAG, Admin)
# ==============================================================================

# Self-heal Windows CRLF (\r) and UTF-8 BOM if present
if grep -q $'\r' "$0" 2>/dev/null; then
    sed -i 's/\r$//' "$0"
    sed -i '1s/^\xEF\xBB\xBF//' "$0"
    exec bash "$0" "$@"
fi

set -u

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_CYAN='\033[38;5;51m'
C_BLUE='\033[38;5;39m'
C_GREEN='\033[38;5;46m'
C_YELLOW='\033[38;5;226m'
C_RED='\033[38;5;196m'
C_PURPLE='\033[38;5;141m'
C_GRAY='\033[38;5;245m'

INSTALL_DIR="/data/genio-os"
DIAG_LOG="/tmp/genio_install_diag.log"
> "$DIAG_LOG"

step_header() {
    echo -e "\n${C_PURPLE}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${C_RESET}"
    echo -e "${C_PURPLE}┃${C_RESET} 🧠 ${C_CYAN}${C_BOLD}$1${C_RESET}"
    echo -e "${C_PURPLE}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${C_RESET}"
}

info_msg() { echo -e "  ${C_BLUE}ℹ️  $1${C_RESET}"; }
ok_msg()   { echo -e "  ${C_GREEN}✅ $1${C_RESET}"; }
warn_msg() { echo -e "  ${C_YELLOW}⚠️  $1${C_RESET}"; }

find_free_port() {
    local port="${1:-8099}"
    while ss -tuln 2>/dev/null | grep -q ":${port} " || lsof -i :"${port}" >/dev/null 2>&1; do
        port=$((port + 1))
    done
    echo "$port"
}

clear
echo -e "${C_CYAN}${C_BOLD}"
cat << "BANNER"
   ______           _          ____  _____             ______   ____ 
  / ____/__  ____  (_)___     / __ \/ ___/   _   __   / ____/  / __ \
 / / __/ _ \/ __ \/ / __ \   / / / /\__ \   | | / /  /___ \   / / / /
/ /_/ /  __/ / / / / /_/ /  / /_/ /___/ /   | |/ /  ____/ / _/ /_/ / 
\____/\___/_/ /_/_/\____/   \____//____/    |___/  /_____/ (_)____/  
                                                                     
  ⚡ HiTech Self-Evolving AI Enterprise v5.0 (Singularity Edition) ⚡
  Live Behind-The-Scenes Stream • Auto-Learning JSON Ledger • Playbooks
BANNER
echo -e "${C_RESET}"

step_header "[1/5] تجهيز البنية التحتية ومسارات الذاكرة التطورية في /data/genio-os"

sudo mkdir -p /data
sudo chown -R "$USER":"$USER" /data
mkdir -p "${INSTALL_DIR}"/{core,web/static,workspace,rag_docs,logs,memory/playbooks,memory/tools_ evolved}

EXISTING_PORT=""
DETECTED_OLLAMA="http://pop-os:11434"
DEFAULT_MODEL="qwen2.5-coder:14b"

if [ -f "${INSTALL_DIR}/config.json" ]; then
    EXISTING_PORT=$(jq -r '.port // empty' "${INSTALL_DIR}/config.json" 2>/dev/null || echo "")
    SAVED_HOST=$(jq -r '.ollama_host // empty' "${INSTALL_DIR}/config.json" 2>/dev/null || echo "")
    SAVED_MODEL=$(jq -r '.primary_model // empty' "${INSTALL_DIR}/config.json" 2>/dev/null || echo "")
    [ -n "$SAVED_HOST" ] && DETECTED_OLLAMA="$SAVED_HOST"
    [ -n "$SAVED_MODEL" ] && DEFAULT_MODEL="$SAVED_MODEL"
fi

sudo systemctl stop genio-os.service 2>/dev/null || true
FINAL_PORT=$(find_free_port "${EXISTING_PORT:-8099}")

cat << EOF > "${INSTALL_DIR}/config.json"
{
  "version": "5.0.0-Singularity",
  "enterprise_name": "Genio OS v5.0 — Self-Evolving Studio",
  "node_name": "$(hostname)",
  "ollama_host": "${DETECTED_OLLAMA}",
  "primary_model": "${DEFAULT_MODEL}",
  "vision_model": "minicpm-v:latest",
  "workspace_dir": "${INSTALL_DIR}/workspace",
  "rag_dir": "${INSTALL_DIR}/rag_docs",
  "memory_dir": "${INSTALL_DIR}/memory",
  "port": ${FINAL_PORT},
  "temperature": 0.2,
  "num_ctx": 8192,
  "auto_self_heal_retries": 2
}
EOF
ok_msg "تم ضبط الإعدادات والمنفذ ${FINAL_PORT} وربط عقدة ${DETECTED_OLLAMA}"

# ==============================================================================
# STAGE 2: SELF-EVOLVING CORE ENGINE + LIVE SSE STREAMING (core/engine.py)
# ==============================================================================
step_header "[2/5] بناء المحرك التطوري والبث المباشر للكواليس (Live Stream + JSONL Memory)"

cat << 'EOF' > "${INSTALL_DIR}/core/engine.py"
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
EOF

# ==============================================================================
# STAGE 3: FASTAPI SERVER WITH LIVE SSE STREAMING & MEMORY API (web/server.py)
# ==============================================================================
step_header "[3/5] بناء سيرفر البث الفوري والذاكرة التطورية (FastAPI SSE + Memory APIs)"

cat << 'EOF' > "${INSTALL_DIR}/web/server.py"
import json
import subprocess
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.engine import GenioEngine, AGENTS_REGISTRY, HISTORY_PATH, BASE_DIR

app = FastAPI(title="Genio OS v5.0 Singularity — Self-Evolving AI Studio")
engine = GenioEngine()


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
    try:
        out = subprocess.check_output(["git", "pull", "origin", "main"], cwd=str(BASE_DIR), text=True, stderr=subprocess.STDOUT)
        return {"ok": True, "output": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).resolve().parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")
EOF

# ==============================================================================
# STAGE 4: 6-IN-1 3D STUDIO UI WITH LIVE STREAM MONITOR & MEMORY LAB
# ==============================================================================
step_header "[4/5] بناء الواجهة التفاعلية v5.0 (غرفة الكواليس الحية + مختبر الذاكرة والـ JSON Logs)"

cat << 'EOF' > "${INSTALL_DIR}/web/static/index.html"
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#040710">
<title>Genio OS v5.0 Singularity — Live Streaming & Self-Evolving AI</title>
<style>
  :root {
    --bg-deep: #040710;
    --bg-glass: rgba(14, 22, 40, 0.82);
    --bg-card: rgba(22, 33, 58, 0.68);
    --cyan: #00f2fe;
    --blue: #4facfe;
    --purple: #a855f7;
    --green: #00e676;
    --amber: #ffd740;
    --red: #ff5252;
    --text: #f8fafc;
    --muted: #94a3b8;
    --border: rgba(0, 242, 254, 0.25);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background:
      radial-gradient(circle at 12% 15%, rgba(0, 242, 254, 0.13), transparent 35%),
      radial-gradient(circle at 88% 20%, rgba(168, 85, 247, 0.13), transparent 35%),
      linear-gradient(180deg, #040710 0%, #091022 100%);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }

  header {
    background: rgba(6, 10, 22, 0.9);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid var(--border);
    padding: 11px 16px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .brand-wrap { display: flex; align-items: center; gap: 10px; }
  .brand-logo {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; box-shadow: 0 0 18px rgba(0, 242, 254, 0.5);
  }
  .brand-title {
    font-size: 1.1rem; font-weight: 900;
    background: linear-gradient(90deg, var(--cyan), #fff, var(--purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .brand-sub { font-size: 0.7rem; color: var(--muted); }
  .telemetry-bar { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .pill {
    background: var(--bg-card); border: 1px solid var(--border);
    padding: 4px 10px; border-radius: 999px; font-size: 0.75rem;
    display: flex; align-items: center; gap: 5px;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); }
  .dot.off { background: var(--red); box-shadow: 0 0 8px var(--red); }

  .nav-tabs {
    display: flex; overflow-x: auto; gap: 8px; padding: 10px 16px;
    background: rgba(8, 13, 26, 0.8); border-bottom: 1px solid rgba(255,255,255,0.07);
  }
  .tab-btn {
    background: var(--bg-card); color: var(--muted); border: 1px solid transparent;
    padding: 8px 14px; border-radius: 11px; font-weight: 700; font-size: 0.83rem;
    cursor: pointer; white-space: nowrap; transition: all 0.2s;
  }
  .tab-btn:hover, .tab-btn.active {
    color: #040710; background: linear-gradient(135deg, var(--cyan), var(--blue));
    box-shadow: 0 5px 18px rgba(0, 242, 254, 0.35);
  }

  .studio-section { display: none; padding: 14px; flex: 1; }
  .studio-section.active { display: block; }
  .grid-2 { display: grid; grid-template-columns: 300px 1fr; gap: 14px; }
  .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
  @media (max-width: 960px) { .grid-2 { grid-template-columns: 1fr; } }

  .panel {
    background: var(--bg-glass); backdrop-filter: blur(16px);
    border: 1px solid var(--border); border-radius: 15px; padding: 14px;
    display: flex; flex-direction: column; gap: 11px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.45);
  }
  .panel-title {
    font-size: 0.92rem; font-weight: 800; color: var(--cyan);
    border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 7px;
    display: flex; justify-content: space-between; align-items: center;
  }

  .agent-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 11px; padding: 9px 11px; cursor: pointer; transition: all 0.2s;
    display: flex; justify-content: space-between; align-items: center; font-size: 0.86rem;
  }
  .agent-card:hover, .agent-card.active {
    border-color: var(--cyan); background: rgba(0, 242, 254, 0.12);
  }
  .badge {
    font-size: 0.66rem; padding: 2px 7px; border-radius: 99px;
    background: rgba(168, 85, 247, 0.22); color: #e9d5ff; border: 1px solid rgba(168, 85, 247, 0.4);
  }

  /* Live Behind-The-Scenes Telemetry Box */
  .live-kawaliss {
    background: #02050b;
    border: 1px solid rgba(0, 242, 254, 0.35);
    border-radius: 12px;
    padding: 10px 12px;
    font-family: monospace;
    font-size: 0.78rem;
    max-height: 150px;
    overflow-y: auto;
    color: #38bdf8;
    direction: ltr;
    text-align: left;
  }
  .kawaliss-line { margin-bottom: 4px; }
  .kawaliss-heal { color: var(--amber); font-weight: bold; }
  .kawaliss-action { color: var(--green); font-weight: bold; }

  .chat-stream {
    min-height: 310px; max-height: 52vh; overflow-y: auto;
    display: flex; flex-direction: column; gap: 11px; padding: 4px;
  }
  .msg {
    background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
    border-right: 4px solid var(--cyan); border-radius: 11px; padding: 11px;
    font-size: 0.88rem; line-height: 1.6;
  }
  .msg.user { border-right-color: var(--amber); background: rgba(255, 215, 64, 0.05); }
  .action-chip {
    display: inline-block; background: rgba(0, 230, 118, 0.14); color: var(--green);
    border: 1px solid var(--green); padding: 2px 8px; border-radius: 6px;
    font-size: 0.73rem; margin: 4px 4px 0 0; direction: ltr;
  }
  .action-chip.err {
    background: rgba(255, 82, 82, 0.15); color: var(--red); border-color: var(--red);
  }

  textarea, input, select {
    width: 100%; background: rgba(8, 13, 26, 0.92); color: var(--text);
    border: 1px solid var(--border); border-radius: 9px; padding: 9px 11px;
    font-family: inherit; font-size: 0.88rem; outline: none;
  }
  .code-editor {
    font-family: monospace; font-size: 0.82rem; line-height: 1.5;
    min-height: 390px; direction: ltr; text-align: left; color: #a5f3fc; background: #03060c;
  }
  .btn-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .btn {
    background: linear-gradient(135deg, var(--cyan), var(--blue)); color: #040710;
    font-weight: 800; border: none; border-radius: 9px; padding: 9px 14px;
    cursor: pointer; font-size: 0.84rem; transition: all 0.2s;
  }
  .btn.purple { background: linear-gradient(135deg, #a855f7, #ec4899); color: #fff; }
  .btn.secondary { background: rgba(255,255,255,0.07); color: var(--text); border: 1px solid var(--border); }
  .btn.danger { background: rgba(255, 82, 82, 0.2); color: var(--red); border: 1px solid var(--red); }

  .file-item {
    font-family: monospace; font-size: 0.78rem; padding: 7px 9px;
    background: rgba(255,255,255,0.03); border-radius: 7px; cursor: pointer;
    display: flex; justify-content: space-between; direction: ltr;
  }
  .file-item:hover { background: rgba(0, 242, 254, 0.14); }
  .terminal-out {
    background: #020409; color: #4ade80; font-family: monospace; font-size: 0.8rem;
    padding: 12px; border-radius: 11px; min-height: 300px; max-height: 52vh;
    overflow-y: auto; direction: ltr; text-align: left; white-space: pre-wrap;
    border: 1px solid rgba(74, 222, 128, 0.3);
  }
</style>
</head>
<body>

<header>
  <div class="brand-wrap">
    <div class="brand-logo">🧠</div>
    <div>
      <div class="brand-title">GENIO OS v5.0 SINGULARITY</div>
      <div class="brand-sub">Live Behind-The-Scenes Stream • Self-Evolving JSON Memory • Autonomous Swarm</div>
    </div>
  </div>

  <div class="telemetry-bar">
    <div class="pill"><span id="ollamaDot" class="dot"></span> <span id="ollamaLabel">Ollama...</span></div>
    <div class="pill">🧠 RAM: <span id="ramLabel">--</span></div>
    <div class="pill">💾 /data: <span id="diskLabel">--</span></div>
    <div class="pill">📚 Playbooks: <span id="pbCountLabel">0</span> | 🛠️ Fixes: <span id="fixCountLabel">0</span></div>
  </div>
</header>

<nav class="nav-tabs">
  <button class="tab-btn active" onclick="openTab('tab-ops', this)">👑 غرفة العمليات & البث الحي للكواليس</button>
  <button class="tab-btn" onclick="openTab('tab-memory', this)">🧠 الذاكرة التطورية وسجل JSON (Self-Learning)</button>
  <button class="tab-btn" onclick="openTab('tab-ide', this)">💻 استوديو الكود الحي (Live Web IDE)</button>
  <button class="tab-btn" onclick="openTab('tab-term', this)">🖥️ طرفية السيرفر (Web Terminal)</button>
  <button class="tab-btn" onclick="openTab('tab-rag', this)">📚 قاعدة المعرفة (RAG)</button>
  <button class="tab-btn" onclick="openTab('tab-admin', this)">⚙️ الإدارة والنماذج</button>
</nav>

<!-- TAB 1: OPERATIONS + REAL-TIME STREAMING -->
<section id="tab-ops" class="studio-section active">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">👥 الوكلاء المستقلون (Agents)</div>
      <div id="agentsContainer" style="display:flex;flex-direction:column;gap:7px;"></div>

      <div class="panel-title" style="margin-top:6px;">🚀 تشغيل السرب والمشاريع (Live Stream)</div>
      <button class="btn purple" onclick="runSwarmLive()">🐝 إطلاق السرب الحي (Rayes ➔ Dev ➔ QA)</button>
    </div>

    <div class="panel">
      <div class="panel-title">
        <span>📡 رادار الكواليس المباشر (Live Behind-The-Scenes Activity Monitor)</span>
        <span id="liveTokenCounter" style="color:var(--green);font-size:0.78rem;">جاهز للبث الحي</span>
      </div>
      <div id="kawalissBox" class="live-kawaliss">
        <div class="kawaliss-line">[System] Genio OS v5.0 Live Stream Ready. Any task will stream tokens, file writes, shell checks, and auto-heals in real time...</div>
      </div>

      <div class="panel-title">
        <span>💬 سجل التنفيذ المباشر (<span id="curAgentName">Genio-Rayes</span>)</span>
      </div>
      <div id="chatStream" class="chat-stream">
        <div class="msg">
          👋 <b>مرحباً يا ريس عزمي في الإصدار التطوري Genio OS v5.0 Singularity!</b><br>
          • <b>بث حي للكواليس (Zero Timeout):</b> تشوف كل كلمة تتكتب وكل ملف يتصنع لحظة بلحظة بدون انقطاع.<br>
          • <b>تعلم ذاتي وإصلاح تلقائي (Self-Healing):</b> إذا غلط الوكيل في Syntax أو أمر، يصلّح روحو وحدو ويحفظ الدرس في <code>experience_ledger.jsonl</code> و <code>playbooks.json</code> باش ما عادش يعاود الغلطة ويبني على خبراته السابقة!
        </div>
      </div>

      <textarea id="promptBox" rows="3" placeholder="اكتب مهمتك للوكيل أو للسرب... (سترى كل خطوة في رادار الكواليس المباشر لحظة بلحظة)"></textarea>
      <div class="btn-row">
        <button class="btn" style="flex:2;" onclick="streamSingleAgentTask()">⚡ بث مباشر وتنفيذ عبر الوكيل المختار</button>
        <button class="btn purple" style="flex:1;" onclick="runSwarmLive()">🐝 بث السرب الكامل (Swarm Stream)</button>
      </div>
    </div>
  </div>
</section>

<!-- TAB 2: SELF-EVOLVING MEMORY & JSONL LEDGER -->
<section id="tab-memory" class="studio-section">
  <div class="grid-3">
    <!-- Learned Playbooks -->
    <div class="panel">
      <div class="panel-title">
        <span>📘 الـ Playbooks والخبرات المكتسبة تلقائياً</span>
        <button class="btn secondary" style="padding:3px 8px;font-size:0.72rem;" onclick="loadMemoryTab()">🔄</button>
      </div>
      <input id="pbTitle" type="text" placeholder="عنوان القاعدة أو الخبرة (مثال: إعداد Gradio 4-bit)">
      <textarea id="pbPattern" rows="3" placeholder="اكتب القاعدة أو الكود المرجعي ليطبقه الوكلاء دائماً بدون إعادة تفكير..."></textarea>
      <button class="btn" onclick="addManualPlaybook()">➕ ترسيخ القاعدة في ذاكرة الوكلاء</button>
      <div id="playbooksList" style="display:flex;flex-direction:column;gap:8px;max-height:330px;overflow-y:auto;"></div>
    </div>

    <!-- Error Resolutions -->
    <div class="panel">
      <div class="panel-title">🩹 سجل الأخطاء وطريقة إصلاحها وتجاوزها</div>
      <input id="errSig" type="text" placeholder="نوع الخطأ (مثال: ModuleNotFoundError / Port in use)">
      <input id="errTarget" type="text" placeholder="الملف أو الأمر المعني">
      <textarea id="errRes" rows="2" placeholder="كيف تم إصلاحه؟ (سيحفظ كدرس دائم للوكلاء)"></textarea>
      <button class="btn purple" onclick="addManualResolution()">🛠️ تسجيل طريقة الإصلاح في الذاكرة</button>
      <div id="resolutionsList" style="display:flex;flex-direction:column;gap:8px;max-height:330px;overflow-y:auto;"></div>
    </div>

    <!-- Raw JSONL Experience Ledger -->
    <div class="panel">
      <div class="panel-title">📊 السجل الخام للعمليات (`experience_ledger.jsonl`)</div>
      <p style="font-size:0.76rem;color:var(--muted);">يُسجل كل عملية، سرعة التوليد، الملفات المكتوبة، والأخطاء بصيغة JSONL لمعالجتها وتطوير الوكلاء.</p>
      <pre id="ledgerViewer" dir="ltr" style="background:#020409;color:#a5f3fc;padding:10px;border-radius:10px;font-size:0.74rem;max-height:430px;overflow:auto;"></pre>
    </div>
  </div>
</section>

<!-- TAB 3: LIVE WEB IDE -->
<section id="tab-ide" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">
        <span>📂 ملفات `/data/genio-os/workspace`</span>
        <button class="btn secondary" style="padding:3px 8px;font-size:0.75rem;" onclick="refreshAll()">🔄</button>
      </div>
      <input id="newFilePath" type="text" dir="ltr" placeholder="folder/new_file.py">
      <button class="btn secondary" onclick="createNewFile()">➕ إنشاء / فتح ملف</button>
      <div id="ideFilesList" style="display:flex;flex-direction:column;gap:6px;max-height:400px;overflow-y:auto;"></div>
    </div>

    <div class="panel">
      <div class="panel-title">
        <span>📝 محرر الكود: <code id="currentEditPath" style="color:var(--amber);">اختر ملفاً</code></span>
        <div class="btn-row">
          <button class="btn" onclick="saveCurrentFile()">💾 حفظ (يتعلم الوكيل من تعديلك)</button>
          <button class="btn secondary" onclick="runCurrentPythonFile()">▶️ تشغيل وفحص</button>
          <button class="btn danger" onclick="deleteCurrentFile()">🗑️ حذف</button>
        </div>
      </div>
      <textarea id="codeEditor" class="code-editor"></textarea>
      <pre id="ideRunOutput" dir="ltr" style="background:#020409;color:#38bdf8;padding:10px;border-radius:8px;font-size:0.78rem;max-height:150px;overflow:auto;display:none;"></pre>
    </div>
  </div>
</section>

<!-- TAB 4: WEB TERMINAL -->
<section id="tab-term" class="studio-section">
  <div class="panel">
    <div class="panel-title">
      <span>🖥️ طرفية السيرفر (`tn` — `/data/genio-os/workspace`)</span>
      <div class="btn-row">
        <button class="btn secondary" onclick="quickCmd('ls -la')">ls -la</button>
        <button class="btn secondary" onclick="quickCmd('df -h /data && free -h')">الذاكرة والقرص</button>
        <button class="btn secondary" onclick="quickCmd('cat /data/genio-os/memory/playbooks.json')">عرض Playbooks JSON</button>
      </div>
    </div>
    <div id="termOutput" class="terminal-out">hitech@tn:/data/genio-os/workspace$ # جاهز...</div>
    <div class="btn-row">
      <input id="shellInput" type="text" dir="ltr" placeholder="اكتب أمر لينكس..." onkeydown="if(event.key==='Enter') executeShell()">
      <button class="btn" onclick="executeShell()">⚡ تنفيذ</button>
    </div>
  </div>
</section>

<!-- TAB 5: RAG STUDIO -->
<section id="tab-rag" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">📥 إضافة وثيقة لقاعدة المعرفة (Local RAG)</div>
      <input id="ragFilename" type="text" dir="ltr" placeholder="project_spec.md">
      <textarea id="ragContent" rows="8" placeholder="الصق الوثائق التقنية أو المراجع هنا..."></textarea>
      <button class="btn" onclick="saveRagDoc()">📚 حفظ في `/data/genio-os/rag_docs`</button>
    </div>
    <div class="panel">
      <div class="panel-title">🗂️ الوثائق المدمجة حالياً</div>
      <div id="ragDocsList" style="display:flex;flex-direction:column;gap:8px;"></div>
    </div>
  </div>
</section>

<!-- TAB 6: ADMIN & MODELS -->
<section id="tab-admin" class="studio-section">
  <div class="grid-3">
    <div class="panel">
      <div class="panel-title">⚙️ إعدادات عقدة Legion</div>
      <input id="cfgOllamaHost" type="text" dir="ltr">
      <select id="cfgModelSelect" dir="ltr"></select>
      <label style="font-size:0.8rem;color:var(--muted);">Temperature: <span id="tempVal">0.2</span></label>
      <input id="cfgTemp" type="range" min="0" max="1" step="0.05" value="0.2" oninput="document.getElementById('tempVal').innerText=this.value">
      <select id="cfgCtx" dir="ltr">
        <option value="4096">4096 tokens</option>
        <option value="8192" selected>8192 tokens</option>
        <option value="16384">16384 tokens</option>
      </select>
      <button class="btn" onclick="saveAdminConfig()">💾 حفظ الإعدادات</button>
    </div>

    <div class="panel">
      <div class="panel-title">📦 سحب نماذج جديدة على Legion</div>
      <div class="btn-row">
        <input id="pullModelInput" type="text" dir="ltr" placeholder="qwen2.5-coder:14b">
        <button class="btn purple" onclick="pullOllamaModel()">⬇️ Pull</button>
      </div>
      <div id="pullStatus" style="font-size:0.8rem;color:var(--amber);"></div>
      <div id="modelsDetailList" style="display:flex;flex-direction:column;gap:6px;max-height:260px;overflow-y:auto;"></div>
    </div>

    <div class="panel">
      <div class="panel-title">🔄 التحديث الذكي (GitHub Sync)</div>
      <button class="btn secondary" onclick="checkGitHubUpdates()">🔍 فحص التحديثات</button>
      <button class="btn" onclick="applyGitHubUpdate()">⚡ تطبيق التحديث الآن</button>
      <div id="updateBox" style="font-size:0.78rem;background:rgba(0,0,0,0.35);padding:10px;border-radius:8px;direction:ltr;text-align:left;">جاهز...</div>
    </div>
  </div>
</section>

<script>
let selectedAgent = "Genio-Rayes";
let activeFilePath = "";

function openTab(tabId, btn) {
  document.querySelectorAll(".studio-section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(tabId).classList.add("active");
  btn.classList.add("active");
  if (tabId === "tab-memory") loadMemoryTab();
}

function logKawaliss(htmlLine, cls = "kawaliss-line") {
  const box = document.getElementById("kawalissBox");
  const d = document.createElement("div");
  d.className = cls;
  d.innerHTML = `[${new Date().toLocaleTimeString()}] ${htmlLine}`;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

function cleanPromptText(txt) {
  return (txt || "").replace(/\[span_\d+\]\((start|end)_span\)/g, "").trim();
}

async function streamAgentTask(agentId, rawPrompt) {
  const prompt = cleanPromptText(rawPrompt);
  if (!prompt) return;

  // Create live message bubble in chatStream
  const stream = document.getElementById("chatStream");
  const msgDiv = document.createElement("div");
  msgDiv.className = "msg";
  msgDiv.innerHTML = `<div><b>🤖 ${agentId}</b> <span class="badge" id="liveBadge">⏳ يبث مباشرة...</span></div><div class="live-body" style="margin-top:6px;white-space:pre-wrap;"></div><div class="live-actions" style="margin-top:6px;"></div>`;
  stream.appendChild(msgDiv);
  const bodyEl = msgDiv.querySelector(".live-body");
  const actEl = msgDiv.querySelector(".live-actions");
  const badgeEl = msgDiv.querySelector("#liveBadge");

  logKawaliss(`🚀 Starting live stream for <b>${agentId}</b>...`);

  try {
    const response = await fetch("/api/task/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({agent_id: agentId, prompt})
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const parts = buffer.split("\n\n");
      buffer = parts.pop();

      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const ev = JSON.parse(part.slice(6));

        if (ev.event === "stage") {
          logKawaliss(ev.message);
          document.getElementById("liveTokenCounter").innerText = ev.message;
        } else if (ev.event === "token") {
          bodyEl.textContent += ev.token;
          if (ev.count % 8 === 0) {
            document.getElementById("liveTokenCounter").innerText = `⚡ [${agentId}] يكتب الكود حياً (${ev.count} tokens)...`;
            stream.scrollTop = stream.scrollHeight;
          }
        } else if (ev.event === "action") {
          const a = ev.action;
          if (a.type === "write_file") {
            const isErr = a.status === "syntax_error";
            logKawaliss(`💾 Wrote file: <b>${a.path}</b> (${a.bytes} B) — Status: ${a.status}`, isErr ? "kawaliss-heal" : "kawaliss-action");
            actEl.innerHTML += `<span class="action-chip ${isErr?'err':''}">💾 ${a.path} (${a.status})</span>`;
          } else if (a.type === "run_cmd") {
            const isErr = a.status === "error";
            logKawaliss(`⚙️ Ran cmd: <code>${a.cmd}</code> (exit ${a.returncode})`, isErr ? "kawaliss-heal" : "kawaliss-action");
            actEl.innerHTML += `<span class="action-chip ${isErr?'err':''}">⚙️ ${a.cmd} (exit ${a.returncode})</span>`;
          } else if (a.type === "learn_rule") {
            logKawaliss(`🧠 Memorized new Playbook rule: <b>${a.title}</b>`, "kawaliss-action");
            actEl.innerHTML += `<span class="action-chip">🧠 Learned: ${a.title}</span>`;
          }
        } else if (ev.event === "heal") {
          logKawaliss(ev.message, "kawaliss-heal");
          bodyEl.textContent += `\n\n🩹 [إصلاح ذاتي تلقائي - المحاولة ${ev.attempt}]: جاري تصحيح الخطأ وتوثيقه...\n`;
        } else if (ev.event === "done") {
          badgeEl.innerText = `✅ ${ev.elapsed_sec}s | ⚡ ${ev.tokens_per_sec} tok/s`;
          logKawaliss(ev.message, "kawaliss-action");
          document.getElementById("liveTokenCounter").innerText = ev.message;
          refreshAll();
        } else if (ev.event === "error") {
          badgeEl.innerText = "❌ خطأ";
          bodyEl.textContent += "\n❌ " + ev.error;
          logKawaliss("❌ " + ev.error, "kawaliss-heal");
        }
      }
    }
  } catch (e) {
    logKawaliss(`⚠️ Stream interrupted: ${e}`, "kawaliss-heal");
  }
}

async function streamSingleAgentTask() {
  const box = document.getElementById("promptBox");
  const raw = box.value.trim();
  if (!raw) return;
  box.value = "";
  const s = document.getElementById("chatStream");
  s.innerHTML += `<div class="msg user"><b>🧑‍💻 عزمي (الريس):</b><br>${cleanPromptText(raw).replace(/</g,'&lt;')}</div>`;
  await streamAgentTask(selectedAgent, raw);
}

async function runSwarmLive() {
  const box = document.getElementById("promptBox");
  const mission = cleanPromptText(box.value.trim()) || "Build a complete modular Python FastAPI project inside `hitech_service/` with `app.py`, `test_app.py`, and `ROADMAP.md`, then verify syntax.";
  box.value = "";
  const s = document.getElementById("chatStream");
  s.innerHTML += `<div class="msg user"><b>🐝 مهمة سرب كاملة (Rayes ➔ Dev-Lead ➔ QA-Sec):</b><br>${mission.replace(/</g,'&lt;')}</div>`;

  await streamAgentTask("Genio-Rayes", `SWARM STEP 1 (Architecture & Playbook Check): Design the architecture and write ROADMAP.md via <write_file path="ROADMAP.md"> for:\n${mission}`);
  await streamAgentTask("Dev-Lead", `SWARM STEP 2 (Full Code Implementation): Write all complete production files using <write_file path="..."> and record any reusable playbook rule via <learn_rule title="..."> for:\n${mission}`);
  await streamAgentTask("QA-Sec", `SWARM STEP 3 (Audit & Self-Healing): Test all generated files in the workspace using <run_cmd>python3 -m py_compile ...</run_cmd>, fix any issues, and save lessons learned via <learn_rule title="...">.`);
}

async function loadMemoryTab() {
  const r = await fetch("/api/memory");
  const d = await r.json();
  document.getElementById("pbCountLabel").innerText = d.stats.playbooks_count;
  document.getElementById("fixCountLabel").innerText = d.stats.error_fixes_count;

  document.getElementById("playbooksList").innerHTML = d.playbooks.map(p => `
    <div class="msg" style="padding:9px;">
      <div><b>📘 ${p.title}</b> <span class="badge">${p.agent} (${p.uses}x)</span></div>
      <div style="font-size:0.8rem;color:#cbd5e1;margin-top:4px;">${p.pattern.replace(/</g,'&lt;')}</div>
    </div>
  `).join("");

  document.getElementById("resolutionsList").innerHTML = d.error_resolutions.length ? d.error_resolutions.map(e => `
    <div class="msg" style="padding:9px;border-right-color:var(--amber);">
      <div><b>🩹 ${e.target}</b> <span class="badge">${e.fixed_by}</span></div>
      <div style="font-size:0.76rem;color:var(--red);margin-top:3px;">Error: ${e.error_signature.replace(/</g,'&lt;')}</div>
      <div style="font-size:0.78rem;color:var(--green);margin-top:3px;">Fix: ${e.resolution.replace(/</g,'&lt;')}</div>
    </div>
  `).join("") : `<div style="color:var(--muted);font-size:0.8rem;">لا توجد أخطاء مسجلة بعد</div>`;

  document.getElementById("ledgerViewer").textContent = d.ledger.map(x => JSON.stringify(x)).join("\n\n");
}

async function addManualPlaybook() {
  const title = document.getElementById("pbTitle").value.trim();
  const pattern = document.getElementById("pbPattern").value.trim();
  if (!title || !pattern) return;
  await fetch("/api/memory/playbook", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title, pattern, agent: "Azmi (Master Rule)"})
  });
  document.getElementById("pbTitle").value = "";
  document.getElementById("pbPattern").value = "";
  loadMemoryTab();
}

async function addManualResolution() {
  const error_signature = document.getElementById("errSig").value.trim();
  const target = document.getElementById("errTarget").value.trim();
  const resolution = document.getElementById("errRes").value.trim();
  if (!error_signature || !resolution) return;
  await fetch("/api/memory/resolution", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({error_signature, target, resolution})
  });
  document.getElementById("errSig").value = "";
  document.getElementById("errTarget").value = "";
  document.getElementById("errRes").value = "";
  loadMemoryTab();
}

async function refreshAll() {
  try {
    const r = await fetch("/api/status");
    const data = await r.json();
    const tel = data.telemetry;
    const ol = data.ollama;

    document.getElementById("ramLabel").innerText = `${tel.ram_used_gb}/${tel.ram_total_gb} GB`;
    document.getElementById("diskLabel").innerText = `${tel.disk_free_gb} GB Free`;
    if (tel.memory_stats) {
      document.getElementById("pbCountLabel").innerText = tel.memory_stats.playbooks_count;
      document.getElementById("fixCountLabel").innerText = tel.memory_stats.error_fixes_count;
    }
    document.getElementById("cfgOllamaHost").value = tel.ollama_host;

    const dot = document.getElementById("ollamaDot");
    const olLabel = document.getElementById("ollamaLabel");
    if (ol.online) {
      dot.className = "dot";
      olLabel.innerText = `Legion (${ol.models.length} موديل)`;
    } else {
      dot.className = "dot off";
      olLabel.innerText = `Ollama غير متصل`;
    }

    document.getElementById("agentsContainer").innerHTML = Object.entries(data.agents).map(([id, a]) => `
      <div class="agent-card ${id === selectedAgent ? 'active' : ''}" onclick="selectAgent('${id}')">
        <div><b>${a.icon} ${a.title}</b></div>
        <span class="badge">${a.badge}</span>
      </div>
    `).join("");

    const sel = document.getElementById("cfgModelSelect");
    const mList = ol.models.length ? ol.models : [tel.active_model];
    sel.innerHTML = mList.map(m => `<option value="${m}" ${m === tel.active_model ? 'selected' : ''}>${m}</option>`).join("");

    document.getElementById("ideFilesList").innerHTML = data.files.length ? data.files.map(f => `
      <div class="file-item" onclick="loadFileInIde('${f.path}')">
        <span>📄 ${f.path}</span>
        <span style="color:var(--muted);">${f.size_kb} KB</span>
      </div>
    `).join("") : `<div style="color:var(--muted);font-size:0.8rem;">المجلد فارغ</div>`;

    document.getElementById("ragDocsList").innerHTML = data.rag_docs.map(d => `
      <div class="msg" style="padding:9px;"><b>📘 ${d.name}</b> (${d.size_kb} KB)</div>
    `).join("");
  } catch (e) { console.error(e); }
}

function selectAgent(id) {
  selectedAgent = id;
  document.getElementById("curAgentName").innerText = id;
  refreshAll();
}

async function loadFileInIde(path) {
  const r = await fetch("/api/file/read", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({path})
  });
  const d = await r.json();
  if (d.ok) {
    activeFilePath = d.path;
    document.getElementById("currentEditPath").innerText = d.path;
    document.getElementById("codeEditor").value = d.content;
  }
}

function createNewFile() {
  const p = document.getElementById("newFilePath").value.trim();
  if (!p) return;
  activeFilePath = p;
  document.getElementById("currentEditPath").innerText = p;
  document.getElementById("codeEditor").value = "# " + p + "\n";
}

async function saveCurrentFile() {
  if (!activeFilePath) return;
  const content = document.getElementById("codeEditor").value;
  await fetch("/api/file/save", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({path: activeFilePath, content})
  });
  refreshAll();
}

async function runCurrentPythonFile() {
  if (!activeFilePath) return;
  await saveCurrentFile();
  const outBox = document.getElementById("ideRunOutput");
  outBox.style.display = "block";
  outBox.innerText = "⏳ Running...";
  const r = await fetch("/api/shell", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({cmd: `python3 "${activeFilePath}"`})
  });
  const d = await r.json();
  outBox.innerText = d.output || "(Exit 0)";
}

async function deleteCurrentFile() {
  if (!activeFilePath || !confirm("حذف " + activeFilePath + "؟")) return;
  await fetch("/api/file/delete", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({path: activeFilePath})
  });
  activeFilePath = "";
  refreshAll();
}

async function executeShell() {
  const inp = document.getElementById("shellInput");
  const cmd = inp.value.trim();
  if (!cmd) return;
  inp.value = "";
  await quickCmd(cmd);
}

async function quickCmd(cmd) {
  const out = document.getElementById("termOutput");
  out.innerText += `\n\nhitech@tn:/data/genio-os/workspace$ ${cmd}\n⏳...`;
  const r = await fetch("/api/shell", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({cmd})
  });
  const d = await r.json();
  out.innerText = out.innerText.replace("⏳...", d.output || "(Done)");
  out.scrollTop = out.scrollHeight;
}

async function saveRagDoc() {
  const filename = document.getElementById("ragFilename").value.trim();
  const content = document.getElementById("ragContent").value.trim();
  if (!filename || !content) return;
  await fetch("/api/rag/add", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({filename, content})
  });
  refreshAll();
}

async function saveAdminConfig() {
  await fetch("/api/config", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      ollama_host: document.getElementById("cfgOllamaHost").value,
      primary_model: document.getElementById("cfgModelSelect").value,
      temperature: parseFloat(document.getElementById("cfgTemp").value),
      num_ctx: parseInt(document.getElementById("cfgCtx").value)
    })
  });
  refreshAll();
}

async function pullOllamaModel() {
  const name = document.getElementById("pullModelInput").value.trim();
  if (!name) return;
  document.getElementById("pullStatus").innerText = "⏳ Pulling " + name + "...";
  const r = await fetch("/api/models/pull", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({model_name: name})
  });
  const d = await r.json();
  document.getElementById("pullStatus").innerText = d.ok ? "✅ Done!" : "❌ " + d.error;
  refreshAll();
}

async function checkGitHubUpdates() {
  const r = await fetch("/api/update/check");
  const d = await r.json();
  document.getElementById("updateBox").innerText = JSON.stringify(d, null, 2);
}

async function applyGitHubUpdate() {
  const r = await fetch("/api/update/apply", {method: "POST"});
  const d = await r.json();
  document.getElementById("updateBox").innerText = d.output || d.error;
}

refreshAll();
setInterval(refreshAll, 10000);
</script>
</body>
</html>
EOF

# ==============================================================================
# STAGE 5: VERIFY SYNTAX, RESTART SERVICE & PUSH TO GITHUB
# ==============================================================================
step_header "[5/5] فحص الكود، تشغيل الخدمة، ومزامنة الإصدار v5.0 مع GitHub"

"${INSTALL_DIR}/venv/bin/python" -m py_compile "${INSTALL_DIR}/core/engine.py" "${INSTALL_DIR}/web/server.py"
cp "$0" "${INSTALL_DIR}/install_genio_os.sh" 2>/dev/null || true

sudo systemctl daemon-reload
sudo systemctl restart genio-os.service

cd "${INSTALL_DIR}"
git add .
git commit -m "feat(v5.0): real-time SSE behind-the-scenes streaming, self-healing loop, and JSONL experience/playbook memory" >/dev/null 2>&1 || true
git push origin main >/dev/null 2>&1 || true

ok_msg "تم إطلاق Genio OS v5.0 Singularity بنجاح على http://tn:${FINAL_PORT} !"

