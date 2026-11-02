#!/usr/bin/env bash
# ==============================================================================
# 🚀 GENIO OS v4.0 (ULTIMATE EDITION) — Smart Diagnostic Wizard & Full Platform
# ==============================================================================
# Author: Mohamed Azmi Kaaniche (HiTech Lab TN)
# Repository: https://github.com/HiTechLabTN/hitech-genio-os
# Target Path: /data/genio-os
# ==============================================================================

# Self-heal Windows CRLF (\r) and UTF-8 BOM if present
if grep -q $'\r' "$0" 2>/dev/null; then
    sed -i 's/\r$//' "$0"
    sed -i '1s/^\xEF\xBB\xBF//' "$0"
    exec bash "$0" "$@"
fi

set -u

# --- Styling & Colors ---
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

# --- Smart Assistant Helper Functions ---
step_header() {
    echo -e "\n${C_PURPLE}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${C_RESET}"
    echo -e "${C_PURPLE}┃${C_RESET} 🤖 ${C_CYAN}${C_BOLD}$1${C_RESET}"
    echo -e "${C_PURPLE}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${C_RESET}"
}

info_msg() { echo -e "  ${C_BLUE}ℹ️  $1${C_RESET}"; }
ok_msg()   { echo -e "  ${C_GREEN}✅ $1${C_RESET}"; }
warn_msg() { echo -e "  ${C_YELLOW}⚠️  $1${C_RESET}"; }

fail_guard() {
    local step_name="$1"
    local fix_hint="$2"
    echo -e "\n  ${C_RED}${C_BOLD}❌ [مشكل تقني تم رصده في: ${step_name}]${C_RESET}"
    echo -e "  ${C_YELLOW}🔍 تفاصيل الخطأ من سجل الفحص (${DIAG_LOG}):${C_RESET}"
    tail -n 12 "$DIAG_LOG" | sed 's/^/     | /'
    echo -e "  ${C_CYAN}💡 نصيحة المساعد الذكي للإصلاح:${C_RESET} ${fix_hint}\n"
    read -p "  👉 هل تريد محاولة الإصلاح التلقائي والمتابعة؟ (Y/n): " RETRY_ANS
    if [[ "${RETRY_ANS:-Y}" =~ ^[Nn]$ ]]; then
        echo -e "  ${C_RED}تم إيقاف التثبيت بناءً على طلبك. راجع ${DIAG_LOG}${C_RESET}"
        exit 1
    fi
}

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
   ______           _          ____  _____             __ __   ____ 
  / ____/__  ____  (_)___     / __ \/ ___/   _   __   / // /  / __ \
 / / __/ _ \/ __ \/ / __ \   / / / /\__ \   | | / /  / // /_ / / / /
/ /_/ /  __/ / / / / /_/ /  / /_/ /___/ /   | |/ /  /__  __// /_/ / 
\____/\___/_/ /_/_/\____/   \____//____/    |___/     /_/   \____/  
                                                                    
  ⚡ HiTech Autonomous AI Enterprise Studio v4.0 (Ultimate Edition) ⚡
  All-in-One: Multi-Agent Swarm • Live Web IDE • Terminal • Admin • RAG
BANNER
echo -e "${C_RESET}"

# ==============================================================================
# STAGE 1: HARDWARE, STORAGE & PERMISSIONS DIAGNOSTIC
# ==============================================================================
step_header "[1/8] الفحص الذكي للعتاد، الذاكرة، ومساحة التخزين (/data)"

CPU_MODEL=$(grep -m1 "model name" /proc/cpuinfo | cut -d':' -f2 | xargs || echo "Generic CPU")
CPU_CORES=$(nproc 2>/dev/null || echo 2)
RAM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')
RAM_AVAIL=$(free -h | awk '/^Mem:/ {print $7}')

if [ ! -d "/data" ]; then
    warn_msg "المجلد /data غير موجود. جاري إنشاؤه وضبط صلاحياته..."
    sudo mkdir -p /data >>"$DIAG_LOG" 2>&1 || fail_guard "إنشاء /data" "تأكد من صلاحيات sudo: sudo mkdir -p /data"
fi
sudo chown -R "$USER":"$USER" /data >>"$DIAG_LOG" 2>&1 || true
DISK_FREE=$(df -h /data | awk 'NR==2 {print $4}')

ok_msg "المعالج (CPU): ${CPU_MODEL} (${CPU_CORES} أنوية)"
ok_msg "الذاكرة العشوائية (RAM): ${RAM_AVAIL} حرة من أصل ${RAM_TOTAL}"
ok_msg "مساحة التخزين (/data): ${DISK_FREE} متاحة للمشاريع والنماذج"

# ==============================================================================
# STAGE 2: SMART UPDATE DETECTOR OR FRESH INSTALL MODE
# ==============================================================================
step_header "[2/8] فحص حالة المنصة (تثبيت جديد أو تحديث ذكي Smart Update)"

IS_UPDATE=0
EXISTING_PORT=""
if [ -f "${INSTALL_DIR}/config.json" ]; then
    IS_UPDATE=1
    EXISTING_PORT=$(grep -oP '"port":\s*\K[0-9]+' "${INSTALL_DIR}/config.json" 2>/dev/null || echo "")
    info_msg "تم رصد نسخة سابقة من Genio OS في ${INSTALL_DIR}!"
    info_msg "سيقوم المساعد الذكي بترقيتها إلى الإصدار v4.0 Ultimate مع الحفاظ على ملفات workspace/..."
else
    info_msg "لم يتم رصد نسخة سابقة. جاري التأسيس الكامل من الصفر في ${INSTALL_DIR}..."
fi

# ==============================================================================
# STAGE 3: OPERATING SYSTEM DEPENDENCIES & SELF-HEALING
# ==============================================================================
step_header "[3/8] فحص وتثبيت المتطلبات التشغيلية للنظام (System Packages)"

PKGS=(python3 python3-venv python3-pip git curl jq whiptail lsof gh tmux iproute2)
MISSING=()
for p in "${PKGS[@]}"; do
    if ! dpkg -s "$p" >/dev/null 2>&1; then
        MISSING+=("$p")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    warn_msg "الحزم التالية ناقصة وسيتم تثبيتها الآن: ${MISSING[*]}"
    if ! (sudo apt-get update -qq >>"$DIAG_LOG" 2>&1 && sudo apt-get install -y -qq "${MISSING[@]}" >>"$DIAG_LOG" 2>&1); then
        fail_guard "تثبيت حزم النظام apt" "جرب تشغيل: sudo dpkg --configure -a && sudo apt-get update"
        sudo dpkg --configure -a >>"$DIAG_LOG" 2>&1 || true
        sudo apt-get install -y "${MISSING[@]}" >>"$DIAG_LOG" 2>&1
    fi
    ok_msg "تم تثبيت جميع الحزم النظامية بنجاح!"
else
    ok_msg "جميع الحزم الأساسية (Python3, Git, Curl, JQ, GH, Tmux, Lsof) مثبتة وسليمة!"
fi

# ==============================================================================
# STAGE 4: TAILSCALE & OLLAMA GPU NODE AUTO-DISCOVERY
# ==============================================================================
step_header "[4/8] الاستكشاف الذكي لعقدة الذكاء الاصطناعي (Ollama / Legion)"

DETECTED_OLLAMA=""
if [ -f "${INSTALL_DIR}/config.json" ]; then
    SAVED_HOST=$(jq -r '.ollama_host // empty' "${INSTALL_DIR}/config.json" 2>/dev/null || true)
    if [ -n "$SAVED_HOST" ] && curl -s -m 2 "${SAVED_HOST}/api/tags" >/dev/null 2>&1; then
        DETECTED_OLLAMA="$SAVED_HOST"
    fi
fi

if [ -z "$DETECTED_OLLAMA" ]; then
    CANDIDATES=("pop-os" "legion" "100.85.172.4" "localhost" "127.0.0.1")
    if command -v tailscale >/dev/null 2>&1; then
        TS_PEERS=$(tailscale status --json 2>/dev/null | jq -r '.Peer[]? | select(.Online==true) | .HostName, .TailscaleIPs[0]' 2>/dev/null || true)
        for peer in $TS_PEERS; do CANDIDATES+=("$peer"); done
    fi

    for host in "${CANDIDATES[@]}"; do
        [ -z "$host" ] && continue
        if curl -s -m 2 "http://${host}:11434/api/tags" >/dev/null 2>&1; then
            DETECTED_OLLAMA="http://${host}:11434"
            break
        fi
    done
fi

if [ -z "$DETECTED_OLLAMA" ]; then
    warn_msg "لم يتم العثور على Ollama نشط تلقائياً. سيتم اعتماد http://pop-os:11434 افتراضياً (يمكنك تغييره من لوحة الإدارة)."
    DETECTED_OLLAMA="http://pop-os:11434"
else
    ok_msg "تم الاتصال بنجاح بعقدة Ollama على: ${DETECTED_OLLAMA}"
fi

DEFAULT_MODEL="qwen2.5-coder:14b"
MODELS_JSON=$(curl -s -m 3 "${DETECTED_OLLAMA}/api/tags" 2>/dev/null || echo "{}")
MODELS_COUNT=$(echo "$MODELS_JSON" | jq -r '.models | length' 2>/dev/null || echo "0")
if [ "$MODELS_COUNT" -gt 0 ] 2>/dev/null; then
    ok_msg "تم رصد ${MODELS_COUNT} نموذج ذكاء اصطناعي جاهز على العقدة!"
    if echo "$MODELS_JSON" | jq -r '.models[].name' | grep -q "^qwen2.5-coder:14b"; then
        DEFAULT_MODEL="qwen2.5-coder:14b"
    else
        DEFAULT_MODEL=$(echo "$MODELS_JSON" | jq -r '.models[0].name')
    fi
    ok_msg "النموذج القيادي الافتراضي: ${DEFAULT_MODEL}"
fi

# ==============================================================================
# STAGE 5: SMART PORT ALLOCATION (CONFLICT-FREE)
# ==============================================================================
step_header "[5/8] الفحص الذكي للبورتات لتفادي أي تضارب (Zero Port Conflict)"

# Stop existing genio-os service temporarily so its own port isn't seen as foreign conflict
sudo systemctl stop genio-os.service 2>/dev/null || true

TARGET_PORT="${EXISTING_PORT:-8099}"
if [ "$TARGET_PORT" = "8090" ]; then
    warn_msg "المنفذ 8090 مخصص لـ Open WebUI، جاري اختيار منفذ مستقل لـ Genio OS..."
    TARGET_PORT=8099
fi

FINAL_PORT=$(find_free_port "$TARGET_PORT")
ok_msg "تم تخصيص المنفذ الحصري والآمن لـ Genio OS v4.0: Port ${FINAL_PORT}"

# ==============================================================================
# STAGE 6: DEPLOYING GENIO OS v4.0 ULTIMATE ENGINE & 5-STUDIO WEB CONSOLE
# ==============================================================================
step_header "[6/8] بناء محرك Genio OS v4.0 Ultimate (5-in-1 Enterprise Studio)"

mkdir -p "${INSTALL_DIR}"/{core,web/static,workspace,rag_docs,logs,scripts}

cat << EOF > "${INSTALL_DIR}/config.json"
{
  "version": "4.0.0-Ultimate",
  "enterprise_name": "Genio OS v4.0 — HiTech Autonomous Studio",
  "node_name": "$(hostname)",
  "ollama_host": "${DETECTED_OLLAMA}",
  "primary_model": "${DEFAULT_MODEL}",
  "vision_model": "minicpm-v:latest",
  "workspace_dir": "${INSTALL_DIR}/workspace",
  "rag_dir": "${INSTALL_DIR}/rag_docs",
  "port": ${FINAL_PORT},
  "temperature": 0.2,
  "num_ctx": 8192,
  "auto_update_check": true
}
EOF

cat << 'EOF' > "${INSTALL_DIR}/requirements.txt"
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
requests>=2.31.0
pydantic>=2.7.0
rich>=13.7.0
psutil>=5.9.0
websockets>=12.0
python-multipart>=0.0.9
EOF

# --- 6.1 Core Engine (Multi-Agent Swarm + IDE + Shell + RAG + Model Manager) ---
cat << 'EOF' > "${INSTALL_DIR}/core/engine.py"
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
EOF

# --- 6.2 FastAPI Backend Server (All Studio Endpoints) ---
cat << 'EOF' > "${INSTALL_DIR}/web/server.py"
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
EOF

# --- 6.3 Ultimate 3D Enterprise Web Studio (5 Tabs: Operations, IDE, Terminal, RAG, Admin) ---
cat << 'EOF' > "${INSTALL_DIR}/web/static/index.html"
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#050811">
<title>Genio OS v4.0 Ultimate — HiTech 3D AI Enterprise Studio</title>
<style>
  :root {
    --bg-deep: #040710;
    --bg-glass: rgba(14, 22, 40, 0.78);
    --bg-card: rgba(22, 33, 58, 0.65);
    --cyan: #00f2fe;
    --blue: #4facfe;
    --purple: #a855f7;
    --green: #00e676;
    --amber: #ffd740;
    --red: #ff5252;
    --text: #f8fafc;
    --muted: #94a3b8;
    --border: rgba(0, 242, 254, 0.24);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background:
      radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.12), transparent 35%),
      radial-gradient(circle at 85% 20%, rgba(168, 85, 247, 0.12), transparent 35%),
      linear-gradient(180deg, #040710 0%, #091022 100%);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }

  /* 3D Top Command Bar */
  header {
    background: rgba(6, 10, 22, 0.88);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid var(--border);
    padding: 12px 18px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    box-shadow: 0 10px 35px rgba(0, 0, 0, 0.65);
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .brand-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .brand-logo {
    width: 38px;
    height: 38px;
    border-radius: 11px;
    background: linear-gradient(135deg, var(--cyan), var(--purple));
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 0 20px rgba(0, 242, 254, 0.5);
  }
  .brand-title {
    font-size: 1.15rem;
    font-weight: 900;
    background: linear-gradient(90deg, var(--cyan), #fff, var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .brand-sub {
    font-size: 0.72rem;
    color: var(--muted);
  }
  .telemetry-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }
  .pill {
    background: var(--bg-card);
    border: 1px solid var(--border);
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 0.78rem;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1);
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 10px var(--green); }
  .dot.off { background: var(--red); box-shadow: 0 0 10px var(--red); }

  /* Studio Navigation Tabs */
  .nav-tabs {
    display: flex;
    overflow-x: auto;
    gap: 8px;
    padding: 10px 18px;
    background: rgba(8, 13, 26, 0.75);
    border-bottom: 1px solid rgba(255,255,255,0.07);
  }
  .tab-btn {
    background: var(--bg-card);
    color: var(--muted);
    border: 1px solid transparent;
    padding: 9px 16px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 0.86rem;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .tab-btn:hover, .tab-btn.active {
    color: #040710;
    background: linear-gradient(135deg, var(--cyan), var(--blue));
    box-shadow: 0 6px 20px rgba(0, 242, 254, 0.35);
    transform: translateY(-2px);
  }

  /* Main Container */
  .studio-section {
    display: none;
    padding: 16px;
    flex: 1;
  }
  .studio-section.active {
    display: block;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 310px 1fr;
    gap: 16px;
  }
  .grid-3 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
  }
  @media (max-width: 960px) {
    .grid-2 { grid-template-columns: 1fr; }
  }

  /* 3D Glass Panels */
  .panel {
    background: var(--bg-glass);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 15px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: 0 14px 35px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.12);
  }
  .panel-title {
    font-size: 0.95rem;
    font-weight: 800;
    color: var(--cyan);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* Agent Cards */
  .agent-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 10px 12px;
    cursor: pointer;
    transition: all 0.25s;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .agent-card:hover, .agent-card.active {
    border-color: var(--cyan);
    background: rgba(0, 242, 254, 0.11);
    transform: translateX(-4px);
    box-shadow: 0 6px 20px rgba(0, 242, 254, 0.2);
  }
  .badge {
    font-size: 0.68rem;
    padding: 2px 8px;
    border-radius: 99px;
    background: rgba(168, 85, 247, 0.2);
    color: #e9d5ff;
    border: 1px solid rgba(168, 85, 247, 0.4);
  }

  /* Chat Stream */
  .chat-stream {
    min-height: 360px;
    max-height: 58vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 6px;
  }
  .msg {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.07);
    border-right: 4px solid var(--cyan);
    border-radius: 12px;
    padding: 12px;
    font-size: 0.9rem;
    line-height: 1.65;
  }
  .msg.user {
    border-right-color: var(--amber);
    background: rgba(255, 215, 64, 0.05);
  }
  .action-chip {
    display: inline-block;
    background: rgba(0, 230, 118, 0.14);
    color: var(--green);
    border: 1px solid var(--green);
    padding: 3px 9px;
    border-radius: 7px;
    font-size: 0.75rem;
    margin: 5px 4px 0 0;
    direction: ltr;
  }

  /* Inputs & Buttons */
  textarea, input, select {
    width: 100%;
    background: rgba(8, 13, 26, 0.9);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    font-family: inherit;
    font-size: 0.9rem;
    outline: none;
  }
  .code-editor {
    font-family: 'Fira Code', monospace;
    font-size: 0.84rem;
    line-height: 1.5;
    min-height: 420px;
    direction: ltr;
    text-align: left;
    color: #a5f3fc;
    background: #03060c;
  }
  .btn-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .btn {
    background: linear-gradient(135deg, var(--cyan), var(--blue));
    color: #040710;
    font-weight: 800;
    border: none;
    border-radius: 10px;
    padding: 10px 15px;
    cursor: pointer;
    font-size: 0.86rem;
    transition: all 0.2s;
  }
  .btn:hover { opacity: 0.92; transform: translateY(-1px); }
  .btn.purple {
    background: linear-gradient(135deg, #a855f7, #ec4899);
    color: #fff;
  }
  .btn.secondary {
    background: rgba(255,255,255,0.07);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .btn.danger {
    background: rgba(255, 82, 82, 0.2);
    color: var(--red);
    border: 1px solid var(--red);
  }
  .file-item {
    font-family: monospace;
    font-size: 0.8rem;
    padding: 8px 10px;
    background: rgba(255,255,255,0.03);
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    direction: ltr;
  }
  .file-item:hover { background: rgba(0, 242, 254, 0.14); }
  .terminal-out {
    background: #020409;
    color: #4ade80;
    font-family: monospace;
    font-size: 0.82rem;
    padding: 14px;
    border-radius: 12px;
    min-height: 330px;
    max-height: 55vh;
    overflow-y: auto;
    direction: ltr;
    text-align: left;
    white-space: pre-wrap;
    border: 1px solid rgba(74, 222, 128, 0.3);
  }
</style>
</head>
<body>

<header>
  <div class="brand-wrap">
    <div class="brand-logo">⚡</div>
    <div>
      <div class="brand-title">GENIO OS v4.0 ULTIMATE</div>
      <div class="brand-sub">HiTech Lab TN — Autonomous AI Studio (OpenWebUI + OpenCode + Swarm)</div>
    </div>
  </div>

  <div class="telemetry-bar">
    <select id="langSelect" style="width:auto;padding:5px 10px;font-size:0.78rem;" onchange="switchLang()">
      <option value="tn">🇹🇳 التونسية التقنية</option>
      <option value="en">🇬🇧 English</option>
      <option value="fr">🇫🇷 Français</option>
    </select>
    <div class="pill"><span id="ollamaDot" class="dot"></span> <span id="ollamaLabel">Ollama...</span></div>
    <div class="pill">🧠 RAM: <span id="ramLabel">--</span></div>
    <div class="pill">💾 /data: <span id="diskLabel">--</span></div>
    <div class="pill">🤖 <span id="activeModelBadge">--</span></div>
  </div>
</header>

<!-- 5-in-1 Enterprise Studio Navigation -->
<nav class="nav-tabs">
  <button class="tab-btn active" onclick="openTab('tab-ops', this)">👑 غرفة العمليات & Swarm</button>
  <button class="tab-btn" onclick="openTab('tab-ide', this)">💻 استوديو الكود الحي (Live Web IDE)</button>
  <button class="tab-btn" onclick="openTab('tab-term', this)">🖥️ طرفية السيرفر (Web Terminal)</button>
  <button class="tab-btn" onclick="openTab('tab-rag', this)">📚 قاعدة المعرفة (RAG Studio)</button>
  <button class="tab-btn" onclick="openTab('tab-admin', this)">⚙️ لوحة الإدارة والنماذج (Admin & Models)</button>
</nav>

<!-- TAB 1: OPERATIONS & SWARM -->
<section id="tab-ops" class="studio-section active">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">👥 الوكلاء المستقلون (Agents)</div>
      <div id="agentsContainer" style="display:flex;flex-direction:column;gap:8px;"></div>

      <div class="panel-title" style="margin-top:8px;">🚀 مهام ذاتية فورية (1-Click Autopilot)</div>
      <button class="btn" onclick="runAutopilotTrainer()">⚡ بناء مشروع HITECH AI Trainer v2.0</button>
      <button class="btn purple" onclick="runSwarmMission()">🐝 تشغيل السرب الكامل (Swarm: Rayes ➔ Dev ➔ QA)</button>
    </div>

    <div class="panel">
      <div class="panel-title">
        <span>💬 مركز القيادة والكتابة الفعلية في `/data/genio-os/workspace` (<span id="curAgentName">Genio-Rayes</span>)</span>
        <span id="taskSpinner" style="display:none;color:var(--amber);font-size:0.82rem;">⏳ جاري التنفيذ وكتابة الملفات...</span>
      </div>

      <div id="chatStream" class="chat-stream">
        <div class="msg">
          👋 <b>مرحباً يا ريس عزمي في النسخة الخارقة Genio OS v4.0 Ultimate!</b><br>
          جمعنالك في المنصة هذي أقوى مميزات <b>Open WebUI</b> (إدارة النماذج والـ RAG) + <b>OpenCode/Cursor</b> (محرر كود حي وتيرمينال مدمج) + <b>CrewAI/OpenBot</b> (سرب وكلاء يكتب الكود فعلياً على `/data/` ويفحصه برمجياً).<br>
          اختار وكيل، أو اضغط على <b>🐝 تشغيل السرب الكامل</b> باش يتعاونوا الوكلاء الكل بالتوازي والتسلسل!
        </div>
      </div>

      <textarea id="promptBox" rows="3" placeholder="اكتب مهمتك للوكيل أو للسرب... (مثال: اصنع تطبيق ويب متكامل مع قاعدة بيانات SQLite واختبره)"></textarea>
      <div class="btn-row">
        <button class="btn" style="flex:2;" onclick="dispatchSingleTask()">🚀 تنفيذ عبر الوكيل المختار</button>
        <button class="btn purple" style="flex:1;" onclick="runSwarmMission()">🐝 تنفيذ جماعي (Swarm Mode)</button>
      </div>
    </div>
  </div>
</section>

<!-- TAB 2: LIVE WEB IDE -->
<section id="tab-ide" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">
        <span>📂 شجرة ملفات `/data/genio-os/workspace`</span>
        <button class="btn secondary" style="padding:4px 9px;font-size:0.75rem;" onclick="refreshAll()">🔄</button>
      </div>
      <input id="newFilePath" type="text" dir="ltr" placeholder="folder/new_file.py">
      <button class="btn secondary" onclick="createNewFile()">➕ إنشاء / فتح ملف جديد</button>
      <div id="ideFilesList" style="display:flex;flex-direction:column;gap:6px;max-height:420px;overflow-y:auto;"></div>
    </div>

    <div class="panel">
      <div class="panel-title">
        <span>📝 المحرر البرمجي المباشر: <code id="currentEditPath" style="color:var(--amber);">لم يتم اختيار ملف</code></span>
        <div class="btn-row">
          <button class="btn" onclick="saveCurrentFile()">💾 حفظ على القرص (/data)</button>
          <button class="btn secondary" onclick="runCurrentPythonFile()">▶️ تشغيل وفحص</button>
          <button class="btn danger" onclick="deleteCurrentFile()">🗑️ حذف</button>
        </div>
      </div>
      <textarea id="codeEditor" class="code-editor" placeholder="اختر ملفاً من القائمة اليسرى لتحريره مباشرة أو أنشئ ملفاً جديداً..."></textarea>
      <pre id="ideRunOutput" dir="ltr" style="background:#020409;color:#38bdf8;padding:10px;border-radius:8px;font-size:0.78rem;max-height:150px;overflow:auto;display:none;"></pre>
    </div>
  </div>
</section>

<!-- TAB 3: WEB TERMINAL -->
<section id="tab-term" class="studio-section">
  <div class="panel">
    <div class="panel-title">
      <span>🖥️ طرفية السيرفر المباشرة (`tn` — `/data/genio-os/workspace`)</span>
      <div class="btn-row">
        <button class="btn secondary" onclick="quickCmd('ls -la')">ls -la</button>
        <button class="btn secondary" onclick="quickCmd('df -h /data && free -h')">فحص الذاكرة والقرص</button>
        <button class="btn secondary" onclick="quickCmd('git status')">git status</button>
        <button class="btn secondary" onclick="quickCmd('tailscale status')">tailscale status</button>
      </div>
    </div>
    <div id="termOutput" class="terminal-out">hitech@tn:/data/genio-os/workspace$ # جاهز لتنفيذ أوامر اللينكس مباشرة...</div>
    <div class="btn-row">
      <input id="shellInput" type="text" dir="ltr" placeholder="اكتب أي أمر Bash هنا (مثال: pytest أو python3 script.py)..." onkeydown="if(event.key==='Enter') executeShell()">
      <button class="btn" onclick="executeShell()">⚡ تنفيذ الأمر</button>
    </div>
  </div>
</section>

<!-- TAB 4: RAG KNOWLEDGE BASE -->
<section id="tab-rag" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">📥 إضافة وثيقة أو كود مرجعي لقاعدة المعرفة (Local RAG)</div>
      <input id="ragFilename" type="text" dir="ltr" placeholder="architecture_notes.md">
      <textarea id="ragContent" rows="8" placeholder="الصق هنا أي وثائق تقنية، قوانين مشروع، أو أكواد مرجعية لكي يقرأها الوكلاء تلقائياً قبل الإجابة..."></textarea>
      <button class="btn" onclick="saveRagDoc()">📚 حفظ في الذاكرة الدائمة (/data/genio-os/rag_docs)</button>
    </div>
    <div class="panel">
      <div class="panel-title">🗂️ الوثائق المدمجة حالياً في ذاكرة الوكلاء</div>
      <div id="ragDocsList" style="display:flex;flex-direction:column;gap:8px;"></div>
    </div>
  </div>
</section>

<!-- TAB 5: ADMIN & MODELS -->
<section id="tab-admin" class="studio-section">
  <div class="grid-3">
    <!-- Node & Hyperparameters -->
    <div class="panel">
      <div class="panel-title">⚙️ إعدادات عقدة Legion والمعاملات</div>
      <label style="font-size:0.8rem;color:var(--muted);">رابط Ollama عبر Tailscale:</label>
      <input id="cfgOllamaHost" type="text" dir="ltr">
      <label style="font-size:0.8rem;color:var(--muted);">النموذج القيادي الافتراضي:</label>
      <select id="cfgModelSelect" dir="ltr"></select>
      <label style="font-size:0.8rem;color:var(--muted);">درجة الإبداع (Temperature): <span id="tempVal">0.2</span></label>
      <input id="cfgTemp" type="range" min="0" max="1" step="0.05" value="0.2" oninput="document.getElementById('tempVal').innerText=this.value">
      <label style="font-size:0.8rem;color:var(--muted);">نافذة السياق (Context Window num_ctx):</label>
      <select id="cfgCtx" dir="ltr">
        <option value="4096">4096 tokens (Fast VRAM)</option>
        <option value="8192" selected>8192 tokens (Balanced)</option>
        <option value="16384">16384 tokens (Deep Architect)</option>
        <option value="32768">32768 tokens (Max Context)</option>
      </select>
      <button class="btn" onclick="saveAdminConfig()">💾 حفظ وتطبيق الإعدادات</button>
    </div>

    <!-- Ollama Model Manager -->
    <div class="panel">
      <div class="panel-title">📦 إدارة وتحميل النماذج على Legion</div>
      <div class="btn-row">
        <input id="pullModelInput" type="text" dir="ltr" placeholder="مثال: deepseek-coder-v2:16b">
        <button class="btn purple" onclick="pullOllamaModel()">⬇️ سحب النموذج (Pull)</button>
      </div>
      <div id="pullStatus" style="font-size:0.8rem;color:var(--amber);"></div>
      <div id="modelsDetailList" style="display:flex;flex-direction:column;gap:6px;max-height:280px;overflow-y:auto;"></div>
    </div>

    <!-- Smart Updater & GitHub Sync -->
    <div class="panel">
      <div class="panel-title">🔄 مركز التحديث الذكي (Smart GitHub Updater)</div>
      <p style="font-size:0.82rem;color:var(--muted);">يفحص مستودع <code>HiTechLabTN/hitech-genio-os</code> ويعلمك بأي ميزات جديدة مع تقرير Changelog كامل.</p>
      <button class="btn secondary" onclick="checkGitHubUpdates()">🔍 فحص التحديثات الآن</button>
      <button class="btn" onclick="applyGitHubUpdate()">⚡ سحب التحديثات وتطبيقها (Live Update)</button>
      <div id="updateBox" style="font-size:0.8rem;background:rgba(0,0,0,0.35);padding:10px;border-radius:8px;direction:ltr;text-align:left;">اضغط "فحص التحديثات" لعرض آخر سجل تغييرات...</div>
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
}

async function refreshAll() {
  try {
    const r = await fetch("/api/status");
    const data = await r.json();
    const tel = data.telemetry;
    const ol = data.ollama;

    document.getElementById("ramLabel").innerText = `${tel.ram_used_gb}/${tel.ram_total_gb} GB`;
    document.getElementById("diskLabel").innerText = `${tel.disk_free_gb} GB Free`;
    document.getElementById("activeModelBadge").innerText = tel.active_model;
    document.getElementById("cfgOllamaHost").value = tel.ollama_host;

    const dot = document.getElementById("ollamaDot");
    const olLabel = document.getElementById("ollamaLabel");
    if (ol.online) {
      dot.className = "dot";
      olLabel.innerText = `Legion متصل (${ol.models.length} موديل)`;
    } else {
      dot.className = "dot off";
      olLabel.innerText = `Ollama غير متصل`;
    }

    // Agents list
    const agDiv = document.getElementById("agentsContainer");
    agDiv.innerHTML = Object.entries(data.agents).map(([id, a]) => `
      <div class="agent-card ${id === selectedAgent ? 'active' : ''}" onclick="selectAgent('${id}')">
        <div><b>${a.icon} ${a.title}</b></div>
        <span class="badge">${a.badge}</span>
      </div>
    `).join("");

    // Models Select & Details
    const sel = document.getElementById("cfgModelSelect");
    const mList = ol.models.length ? ol.models : [tel.active_model];
    sel.innerHTML = mList.map(m => `<option value="${m}" ${m === tel.active_model ? 'selected' : ''}>${m}</option>`).join("");

    const mDetail = document.getElementById("modelsDetailList");
    mDetail.innerHTML = (ol.details || []).map(d => `
      <div class="file-item">
        <span>🤖 <b>${d.name}</b> (${d.quant})</span>
        <span style="color:var(--cyan);">${d.size_gb} GB</span>
      </div>
    `).join("");

    // IDE Files List
    const fDiv = document.getElementById("ideFilesList");
    fDiv.innerHTML = data.files.length ? data.files.map(f => `
      <div class="file-item" onclick="loadFileInIde('${f.path}')">
        <span>📄 ${f.path}</span>
        <span style="color:var(--muted);">${f.size_kb} KB</span>
      </div>
    `).join("") : `<div style="color:var(--muted);font-size:0.82rem;">لا توجد ملفات بعد في workspace</div>`;

    // RAG Docs List
    const rDiv = document.getElementById("ragDocsList");
    rDiv.innerHTML = data.rag_docs.length ? data.rag_docs.map(d => `
      <div class="msg" style="padding:10px;">
        <b>📘 ${d.name}</b> <span style="color:var(--muted);font-size:0.75rem;">(${d.size_kb} KB)</span>
        <div style="font-size:0.78rem;color:var(--muted);margin-top:4px;">${d.preview.replace(/</g,'&lt;')}...</div>
      </div>
    `).join("") : `<div style="color:var(--muted);font-size:0.82rem;">لا توجد وثائق مضافة بعد</div>`;
  } catch (e) { console.error(e); }
}

function selectAgent(id) {
  selectedAgent = id;
  document.getElementById("curAgentName").innerText = id;
  refreshAll();
}

function appendChat(role, title, text, actions = [], tps = 0) {
  const s = document.getElementById("chatStream");
  const d = document.createElement("div");
  d.className = "msg " + (role === "user" ? "user" : "");
  let chips = (actions || []).map(a => {
    if (a.type === "write_file") return `<span class="action-chip">💾 Saved: ${a.path} (${a.bytes} B)</span>`;
    if (a.type === "run_cmd") return `<span class="action-chip">⚙️ Cmd: ${a.cmd} (exit ${a.returncode})</span>`;
    return "";
  }).join("");
  const speedBadge = tps > 0 ? `<span class="badge" style="margin-right:8px;">⚡ ${tps} tok/s</span>` : "";
  const safe = (text || "").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
  d.innerHTML = `<div><b>${title}</b> ${speedBadge}</div><div style="margin-top:6px;">${safe}</div><div>${chips}</div>`;
  s.appendChild(d);
  s.scrollTop = s.scrollHeight;
}

async function dispatchSingleTask() {
  const box = document.getElementById("promptBox");
  const prompt = box.value.trim();
  if (!prompt) return;
  box.value = "";
  appendChat("user", "🧑‍💻 عزمي (الريس)", prompt);
  document.getElementById("taskSpinner").style.display = "inline";
  try {
    const r = await fetch("/api/task", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({agent_id: selectedAgent, prompt})
    });
    const res = await r.json();
    if (res.ok) {
      appendChat("agent", `${res.agent} (${res.elapsed_sec}s)`, res.reply, res.actions, res.tokens_per_sec);
    } else {
      appendChat("agent", "❌ تنبيه", res.error);
    }
  } catch (e) {
    appendChat("agent", "❌ خطأ اتصال", String(e));
  }
  document.getElementById("taskSpinner").style.display = "none";
  refreshAll();
}

async function runSwarmMission() {
  const box = document.getElementById("promptBox");
  const mission = box.value.trim() || "Build a complete modular Python FastAPI microservice inside `swarm_app/` with health check and unit test.";
  box.value = "";
  appendChat("user", "🐝 Swarm Mission (Rayes ➔ Dev-Lead ➔ QA-Sec)", mission);
  document.getElementById("taskSpinner").style.display = "inline";
  try {
    const r = await fetch("/api/swarm", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({mission})
    });
    const data = await r.json();
    if (data.ok) {
      for (const st of data.swarm_steps) {
        appendChat("agent", `🐝 ${st.agent} (${st.elapsed_sec || 0}s)`, st.reply || st.error, st.actions, st.tokens_per_sec);
      }
    }
  } catch (e) {
    appendChat("agent", "❌ خطأ في السرب", String(e));
  }
  document.getElementById("taskSpinner").style.display = "none";
  refreshAll();
}

async function runAutopilotTrainer() {
  appendChat("user", "⚡ 1-Click Autopilot", "بناء مشروع HITECH AI Trainer v2.0 الكامل في /data/genio-os/workspace/hitech-ai-trainer");
  document.getElementById("taskSpinner").style.display = "inline";
  const r = await fetch("/api/autopilot/hitech-trainer", {method: "POST"});
  const res = await r.json();
  document.getElementById("taskSpinner").style.display = "none";
  appendChat("agent", `Dev-Lead (${res.elapsed_sec || 0}s)`, res.reply || res.error, res.actions, res.tokens_per_sec);
  refreshAll();
}

// Live Web IDE functions
async function loadFileInIde(path) {
  const r = await fetch("/api/file/read", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path})
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
  document.getElementById("codeEditor").value = "# New file: " + p + "\n";
}

async function saveCurrentFile() {
  if (!activeFilePath) return alert("اختر ملفاً أو اكتب اسم ملف جديد أولاً");
  const content = document.getElementById("codeEditor").value;
  await fetch("/api/file/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path: activeFilePath, content})
  });
  refreshAll();
}

async function runCurrentPythonFile() {
  if (!activeFilePath) return;
  await saveCurrentFile();
  const outBox = document.getElementById("ideRunOutput");
  outBox.style.display = "block";
  outBox.innerText = "⏳ Running " + activeFilePath + "...";
  const r = await fetch("/api/shell", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({cmd: `python3 "${activeFilePath}"`})
  });
  const d = await r.json();
  outBox.innerText = d.output || "(Exit 0 — No stdout)";
}

async function deleteCurrentFile() {
  if (!activeFilePath || !confirm("حذف الملف " + activeFilePath + "؟")) return;
  await fetch("/api/file/delete", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path: activeFilePath})
  });
  activeFilePath = "";
  document.getElementById("currentEditPath").innerText = "لم يتم اختيار ملف";
  document.getElementById("codeEditor").value = "";
  refreshAll();
}

// Terminal functions
async function executeShell() {
  const inp = document.getElementById("shellInput");
  const cmd = inp.value.trim();
  if (!cmd) return;
  inp.value = "";
  await quickCmd(cmd);
}

async function quickCmd(cmd) {
  const out = document.getElementById("termOutput");
  out.innerText += `\n\nhitech@tn:/data/genio-os/workspace$ ${cmd}\n⏳ Running...`;
  const r = await fetch("/api/shell", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({cmd})
  });
  const d = await r.json();
  out.innerText = out.innerText.replace("⏳ Running...", d.output || "(Done)");
  out.scrollTop = out.scrollHeight;
}

// RAG functions
async function saveRagDoc() {
  const filename = document.getElementById("ragFilename").value.trim();
  const content = document.getElementById("ragContent").value.trim();
  if (!filename || !content) return;
  await fetch("/api/rag/add", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({filename, content})
  });
  document.getElementById("ragFilename").value = "";
  document.getElementById("ragContent").value = "";
  refreshAll();
}

// Admin functions
async function saveAdminConfig() {
  await fetch("/api/config", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
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
  document.getElementById("pullStatus").innerText = `⏳ جاري سحب النموذج ${name} على Legion...`;
  const r = await fetch("/api/models/pull", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({model_name: name})
  });
  const d = await r.json();
  document.getElementById("pullStatus").innerText = d.ok ? `✅ تم تحميل ${name} بنجاح!` : `❌ خطأ: ${d.error}`;
  refreshAll();
}

async function checkGitHubUpdates() {
  const box = document.getElementById("updateBox");
  box.innerText = "🔍 Checking GitHub origin/main...";
  const r = await fetch("/api/update/check");
  const d = await r.json();
  box.innerText = `Local: ${d.local_hash || 'N/A'} | Remote: ${d.remote_hash || 'N/A'}\nUpdate Available: ${d.update_available} (${d.commits_behind} commits behind)\n\nRecent Commits:\n` + (d.changelog || []).join("\n");
}

async function applyGitHubUpdate() {
  const box = document.getElementById("updateBox");
  box.innerText = "⚡ Pulling latest updates from GitHub...";
  const r = await fetch("/api/update/apply", {method: "POST"});
  const d = await r.json();
  box.innerText = d.ok ? `✅ Updated:\n${d.output}` : `❌ Error:\n${d.error}`;
}

refreshAll();
setInterval(refreshAll, 9000);
</script>
</body>
</html>
EOF

# --- 6.4 Clean Terminal TUI (core/tui.py) with Auto-Update Notifier ---
cat << 'EOF' > "${INSTALL_DIR}/core/tui.py"
#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.engine import GenioEngine, AGENTS_REGISTRY

console = Console()


async def main():
    engine = GenioEngine()
    upd = engine.check_git_updates()

    while True:
        console.clear()
        tel = engine.get_system_telemetry()
        ollama = await engine.check_ollama_status()
        status_str = f"[bold green]ONLINE ({len(ollama['models'])} models)[/]" if ollama["online"] else "[bold red]OFFLINE[/]"

        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="right")
        header.add_row(
            f"[bold cyan]⚡ GENIO OS v{tel['version']} — Interactive SSH & Mobile TUI[/]",
            f"Node: [bold yellow]{tel['node']}[/] | Web Port: [bold green]{tel['port']}[/] | RAM: {tel['ram_used_gb']}/{tel['ram_total_gb']}GB"
        )
        header.add_row(
            f"Ollama ({tel['ollama_host']}): {status_str}",
            f"Active Model: [bold magenta]{tel['active_model']}[/] | /data Free: {tel['disk_free_gb']}GB"
        )
        console.print(Panel(header, border_style="cyan"))

        if upd.get("update_available"):
            console.print(Panel(
                f"[bold yellow]🔔 يتوفر تحديث جديد على GitHub ({upd['commits_behind']} تحديثات)! اكتب [cyan]u[/cyan] لتثبيته الآن.[/]",
                border_style="yellow"
            ))

        t = Table(title="👥 فريق الوكلاء المستقلين (Autonomous Swarm)", border_style="blue")
        t.add_column("#", style="cyan", justify="center")
        t.add_column("Agent ID", style="bold white")
        t.add_column("Specialty", style="green")
        agent_keys = list(AGENTS_REGISTRY.keys())
        for idx, k in enumerate(agent_keys, 1):
            t.add_row(str(idx), f"{AGENTS_REGISTRY[k]['icon']} {k}", AGENTS_REGISTRY[k]["title"])
        console.print(t)

        console.print(
            "\n[bold yellow]الأوامر:[/] [cyan]1-5[/] مهمة لوكيل | [cyan]s[/] تشغيل السرب الكامل (Swarm) | "
            "[cyan]f[/] ملفات /data | [cyan]c[/] الإعدادات | [cyan]u[/] فحص وتحديث المنصة | [cyan]q[/] خروج"
        )
        choice = Prompt.ask("👉 اختر رقم الوكيل أو الأمر", default="1")

        if choice.lower() == "q":
            break
        elif choice.lower() == "f":
            files = engine.list_workspace_files()
            console.print(Panel("\n".join([f"📄 {f['path']} ({f['size_kb']} KB)" for f in files]) or "المجلد فارغ", title="ملفات /data/genio-os/workspace"))
            Prompt.ask("اضغط Enter للمتابعة")
        elif choice.lower() == "c":
            new_host = Prompt.ask("رابط Ollama", default=tel["ollama_host"])
            new_model = Prompt.ask("اسم الموديل", default=tel["active_model"])
            engine.save_config({"ollama_host": new_host, "primary_model": new_model})
        elif choice.lower() == "u":
            import subprocess
            console.print("[bold cyan]🔄 جاري تحديث المنصة عبر genio-update...[/]")
            subprocess.run(["/usr/local/bin/genio-update"])
            Prompt.ask("اضغط Enter للمتابعة")
        elif choice.lower() == "s":
            mission = Prompt.ask("🐝 اكتب المهمة الكاملة للسرب (Rayes ➔ Dev-Lead ➔ QA-Sec)")
            if mission.strip():
                with console.status("[bold magenta]🐝 السرب يشتغل بالتسلسل ويكتب الملفات في /data/genio-os/workspace ...[/]"):
                    res = await engine.dispatch_swarm(mission)
                for st in res.get("swarm_steps", []):
                    console.print(Panel(st.get("reply", ""), title=f"🐝 {st.get('agent')} ({st.get('elapsed_sec')}s)", border_style="magenta"))
                Prompt.ask("اضغط Enter للمتابعة")
        elif choice.isdigit() and 1 <= int(choice) <= len(agent_keys):
            ag_id = agent_keys[int(choice) - 1]
            task = Prompt.ask(f"📝 اكتب مهمتك لـ [bold cyan]{ag_id}[/]")
            if task.strip():
                with console.status(f"[bold yellow]⏳ {ag_id} ينفذ المهمة ويكتب الكود الفعلي في /data ...[/]"):
                    res = await engine.dispatch_task(ag_id, task)
                if res.get("ok"):
                    console.print(Panel(res["reply"], title=f"✅ {ag_id} ({res['elapsed_sec']}s | {res.get('tokens_per_sec',0)} tok/s)", border_style="green"))
                    for act in res.get("actions", []):
                        console.print(f"  [bold green]✔ Action:[/] {act}")
                else:
                    console.print(f"[bold red]❌ {res.get('error')}[/]")
                Prompt.ask("\nاضغط Enter للمتابعة")


if __name__ == "__main__":
    asyncio.run(main())
EOF
chmod +x "${INSTALL_DIR}/core/tui.py"

# ==============================================================================
# STAGE 7: PYTHON VENV, GLOBAL BINARIES (`genio` & `genio-update`) & SYSTEMD
# ==============================================================================
step_header "[7/8] تجهيز بيئة Python، الأوامر العامة (genio / genio-update)، وخدمة 24/7"

if [ ! -d "${INSTALL_DIR}/venv" ]; then
    python3 -m venv "${INSTALL_DIR}/venv" >>"$DIAG_LOG" 2>&1 || fail_guard "إنشاء venv" "تأكد من تثبيت python3-venv"
fi
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip -q >>"$DIAG_LOG" 2>&1
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt" -q >>"$DIAG_LOG" 2>&1 || fail_guard "تثبيت مكتبات Python" "تحقق من اتصال الإنترنت ثم أعد المحاولة"

# Verify Python syntax of core modules so syntax errors NEVER happen
"${INSTALL_DIR}/venv/bin/python" -m py_compile "${INSTALL_DIR}/core/engine.py" "${INSTALL_DIR}/core/tui.py" "${INSTALL_DIR}/web/server.py" >>"$DIAG_LOG" 2>&1 || fail_guard "فحص سلامة الكود البرمجي" "حدث خطأ أثناء توليد ملفات البايثون"
ok_msg "تم فحص الكود البرمجي (engine.py, tui.py, server.py) والتأكد من خلوه من أي أخطاء Syntax!"

# Global command: /usr/local/bin/genio
sudo rm -f /usr/local/bin/genio
sudo tee /usr/local/bin/genio >/dev/null << EOF
#!/usr/bin/env bash
exec "${INSTALL_DIR}/venv/bin/python" "${INSTALL_DIR}/core/tui.py" "\$@"
EOF
sudo chmod +x /usr/local/bin/genio

# Global command: /usr/local/bin/genio-update
sudo rm -f /usr/local/bin/genio-update
sudo tee /usr/local/bin/genio-update >/dev/null << 'EOF'
#!/usr/bin/env bash
set -e
INSTALL_DIR="/data/genio-os"
cd "$INSTALL_DIR"
echo -e "\033[38;5;51m\033[1m🔄 [Genio Smart Updater] جاري فحص وسحب آخر التحديثات من GitHub...\033[0m"
git fetch origin main 2>/dev/null || true
LOCAL_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "local")
git pull origin main 2>/dev/null || true
NEW_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "local")

"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
sudo systemctl restart genio-os.service

echo -e "\n\033[38;5;46m┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\033[0m"
echo -e "\033[38;5;46m┃ 📋 تقرير التحديث والميزات الجديدة (Changelog: ${LOCAL_HASH} ➔ ${NEW_HASH})          ┃\033[0m"
echo -e "\033[38;5;46m┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\033[0m"
git log -n 5 --pretty=format:"  ✨ %h — %s (%cr)" 2>/dev/null || echo "  ✨ Genio OS v4.0 Ultimate Ready"
echo -e "\n"

PORT=$(jq -r '.port // 8099' "$INSTALL_DIR/config.json" 2>/dev/null || echo 8099)
TS_IP=$(tailscale ip -4 2>/dev/null | head -n 1 || hostname -I | awk '{print $1}')
echo -e "  🌐 \033[1mرابط الاستوديو على الويب والموبايل:\033[0m http://${TS_IP}:${PORT}  (أو http://$(hostname):${PORT})"
echo -e "  💻 \033[1mلتشغيل الكونسول التفاعلي في الطرفية:\033[0m \033[33mgenio\033[0m"
echo -e "  🔄 \033[1mلتحديث المنصة في أي وقت ومن أي مسار:\033[0m \033[33mgenio-update\033[0m\n"
EOF
sudo chmod +x /usr/local/bin/genio-update

# Remove old conflicting alias in ~/.bashrc if it points to dummy file
sed -i '/alias genio-update=/d' ~/.bashrc 2>/dev/null || true

# Systemd Service
sudo tee /etc/systemd/system/genio-os.service >/dev/null << EOF
[Unit]
Description=Genio OS v4.0 Ultimate Autonomous AI Enterprise Studio
After=network.target tailscaled.service

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn web.server:app --host 0.0.0.0 --port ${FINAL_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable genio-os.service >/dev/null 2>&1
sudo systemctl restart genio-os.service
sleep 1

if systemctl is-active --quiet genio-os.service; then
    ok_msg "خدمة الويب (genio-os.service) تشتغل بنجاح 24/7 على المنفذ ${FINAL_PORT}!"
else
    fail_guard "تشغيل خدمة systemd" "تحقق من السجل عبر: sudo journalctl -u genio-os.service -n 20"
fi

# ==============================================================================
# STAGE 8: GITHUB REPOSITORY SYNC & 1-LINER INSTALL DOCUMENTATION
# ==============================================================================
step_header "[8/8] توثيق المستودع ومزامنة التحديث مع GitHub (HiTechLabTN/hitech-genio-os)"

cp "$0" "${INSTALL_DIR}/install_genio_os.sh" 2>/dev/null || true
chmod +x "${INSTALL_DIR}/install_genio_os.sh"

cat << 'EOF' > "${INSTALL_DIR}/README.md"
# ⚡ Genio OS v4.0 Ultimate (`hitech-genio-os`)
**Autonomous Local AI Enterprise Studio** — مصممة في **HiTech Lab TN** لتجمع قوة `Open WebUI` + `OpenCode / Cursor` + `CrewAI / OpenBot` في منصة محلية واحدة بدون أي قيود (100% Local Authority).

## 🌟 الميزات الخارقة في الإصدار v4.0 Ultimate
1. **غرفة عمليات وسرب وكلاء (Multi-Agent Swarm):** تنفيذ متسلسل وتعاوني (`Genio-Rayes` ➔ `Dev-Lead` ➔ `QA-Sec`) يكتب الكود الفعلي مباشرة في `/data/genio-os/workspace`.
2. **استوديو كود حي مدمج (Live Web IDE):** تصفح، تحرير، حفظ، وتشغيل ملفات البايثون والمشاريع مباشرة من المتصفح أو الهاتف.
3. **طرفية ويب تفاعلية (Integrated Web Terminal):** تنفيذ أوامر اللينكس والـ Git وفحص العتاد مباشرة من الواجهة.
4. **قاعدة معرفة محلية (RAG Knowledge Studio):** رفع الوثائق والمراجع التقنية ليدمجها الوكلاء تلقائياً في سياق البرمجة.
5. **لوحة إدارة النماذج والتحديث الذكي (Admin & Model Manager):** التحكم في `Temperature`، `Context Window`، سحب نماذج جديدة على `Legion`، وتحديث المنصة بضغطة زر.

## 🚀 التثبيت أو التحديث السريع بأمر واحد (1-Command Smart Installer)
```bash
git clone https://github.com/HiTechLabTN/hitech-genio-os.git /tmp/genio-installer && bash /tmp/genio-installer/install_genio_os.sh
```
EOF

cd "${INSTALL_DIR}"
git init -b main >/dev/null 2>&1 || true
git add .
git commit -m "feat(v4.0): Ultimate 5-in-1 AI Studio (Swarm, Live Web IDE, Web Terminal, RAG, Admin & Smart Diagnostic Installer)" >/dev/null 2>&1 || true

if git remote get-url origin >/dev/null 2>&1; then
    info_msg "جاري رفع التحديث الجديد تلقائياً إلى GitHub (origin/main)..."
    if git push -u origin main >>"$DIAG_LOG" 2>&1; then
        ok_msg "تم تحديث مستودع GitHub بنجاح! أي جهاز آخر يمكنه الآن التثبيت أو التحديث بأمر واحد."
    else
        warn_msg "تعذر الرفع التلقائي لـ GitHub (ربما تحتاج git push يدوياً لاحقاً)."
    fi
fi

TS_MY_IP=$(tailscale ip -4 2>/dev/null | head -n 1 || hostname -I | awk '{print $1}')

echo -e "\n${C_CYAN}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${C_RESET}"
echo -e "${C_CYAN}┃${C_RESET} 🎉 ${C_GREEN}${C_BOLD}مريقل يا ريس عزمي! اكتمل تجهيز Genio OS v4.0 Ultimate بنجاح 100%${C_RESET}   ${C_CYAN}┃${C_RESET}"
echo -e "${C_CYAN}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${C_RESET}"
echo -e "  🌐 ${C_BOLD}استوديو الويب الخارق (5-in-1 Web & Mobile Studio):${C_RESET}"
echo -e "     👉 ${C_GREEN}http://${TS_MY_IP}:${FINAL_PORT}${C_RESET}"
echo -e "     👉 ${C_GREEN}http://$(hostname):${FINAL_PORT}${C_RESET}"
echo -e "\n  💻 ${C_BOLD}الأوامر الذكية المدمجة في النظام (تعمل من أي مكان في الـ Terminal):${C_RESET}"
echo -e "     👉 ${C_YELLOW}genio${C_RESET}         : فتح الكونسول التفاعلي الملون (Rich TUI + Swarm)"
echo -e "     👉 ${C_YELLOW}genio-update${C_RESET}  : سحب آخر التحديثات وعرض تقرير الـ Changelog"
echo -e "\n  📦 ${C_BOLD}أمر التثبيت الموحد لمشاركته أو تنصيبه على أي ماكينة جديدة:${C_RESET}"
echo -e "     ${C_GRAY}git clone https://github.com/HiTechLabTN/hitech-genio-os.git /tmp/genio && bash /tmp/genio/install_genio_os.sh${C_RESET}\n"

