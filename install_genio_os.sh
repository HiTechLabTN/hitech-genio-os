#!/usr/bin/env bash
# ==============================================================================
# 🚀 Genio OS — Installateur (لا يولّد كود، ينسخ من الريبو)
# ==============================================================================
# القاعدة (خطة v1 §3.1): **المصدر الوحيد للحقيقة هو الريبو**.
# هذا السكريبت ما يكتبش `engine.py` ولا `server.py` ولا `index.html`:
# ينسخهم من نفس المجلّد اللي فيه السكريبت (clone الريبو).
#
# الاستعمال:
#   bash install_genio_os.sh                 # تثبيت في /data/genio-os
#   GENIO_INSTALL_DIR=/opt/genio-os bash …   # مسار آخر
#   GENIO_DRY_RUN=1 bash …                   # تجربة بلا خدمة وبلا venv
#   bash install_genio_os.sh --check         # قارن المنصّب مع الريبو
# ==============================================================================

# Self-heal Windows CRLF (\r) and UTF-8 BOM if present
if grep -q $'\r' "$0" 2>/dev/null; then
    sed -i 's/\r$//' "$0"
    sed -i '1s/^\(\xEF\xBB\xBF\)//' "$0"
    exec bash "$0" "$@"
fi

set -euo pipefail

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_CYAN='\033[38;5;51m'
C_BLUE='\033[38;5;39m'
C_GREEN='\033[38;5;46m'
C_YELLOW='\033[38;5;226m'
C_RED='\033[38;5;196m'
C_PURPLE='\033[38;5;141m'

MODE="install"
SKIP_SYSTEMD="${GENIO_SKIP_SYSTEMD:-0}"
for arg in "$@"; do
    case "${arg}" in
        --check) MODE="check" ;;
        --no-service) SKIP_SYSTEMD=1 ;;
        *) echo "خيار غير معروف: ${arg}" >&2; exit 2 ;;
    esac
done

INSTALL_DIR="${GENIO_INSTALL_DIR:-/data/genio-os}"
DRY_RUN="${GENIO_DRY_RUN:-0}"
PORT="${GENIO_PORT:-8099}"
OLLAMA_HOST="${GENIO_OLLAMA_HOST:-http://pop-os:11434}"
PRIMARY_MODEL="${GENIO_PRIMARY_MODEL:-ornith-1.5:9b}"
SERVICE_NAME="genio-os.service"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# الكود اللي لازم ينسخ — ما فمّاش نسخة داخل السكريبت
RUNTIME_PATHS=(core web requirements.txt config.json)
OPTIONAL_PATHS=(scripts docs deployment pytest.ini requirements-dev.txt README.md Makefile)

step_header() {
    echo -e "\n${C_PURPLE}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${C_RESET}"
    echo -e "${C_PURPLE}┃${C_RESET} 🧠 ${C_CYAN}${C_BOLD}$1${C_RESET}"
    echo -e "${C_PURPLE}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${C_RESET}"
}
info_msg() { echo -e "  ${C_BLUE}ℹ️  $1${C_RESET}"; }
ok_msg()   { echo -e "  ${C_GREEN}✅ $1${C_RESET}"; }
warn_msg() { echo -e "  ${C_YELLOW}⚠️  $1${C_RESET}"; }
die()      { echo -e "  ${C_RED}❌ $1${C_RESET}" >&2; exit 1; }

# --- الصلاحيات: جذر ولا sudo، وفي DRY_RUN بلا حتى واحد ------------------------
SUDO=""
if [ "${DRY_RUN}" != "1" ] && [ "$(id -u)" != "0" ]; then
    SUDO="sudo"
fi

# --- 0. الفحص المسبق: الكود موجود في الريبو؟ ---------------------------------
require_source() {
    local missing=()
    for path in "${RUNTIME_PATHS[@]}"; do
        [ -e "${SRC_DIR}/${path}" ] || missing+=("${path}")
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        die "الريبو ناقص: ${missing[*]} — شغّل السكريبت من داخل clone متاع الريبو."
    fi
    for path in core/engine.py web/server.py web/static/index.html; do
        [ -s "${SRC_DIR}/${path}" ] || die "ملف فارغ ولا ما موجودش: ${path}"
    done
    ok_msg "الكود موجود في الريبو: core/, web/, config.json"
}

# --- mode --check: قارن المنصّب مع الريبو ------------------------------------
check_install() {
    step_header "فحص التثبيت مقابل الريبو"
    [ -d "${INSTALL_DIR}" ] || die "ما فمّاش تثبيت في ${INSTALL_DIR}"
    local drift=0
    for path in core web requirements.txt; do
        if ! diff -rq -x '__pycache__' -x '*.pyc' "${SRC_DIR}/${path}" "${INSTALL_DIR}/${path}" >/dev/null 2>&1; then
            warn_msg "يختلف: ${path}"
            diff -rq -x '__pycache__' -x '*.pyc' "${SRC_DIR}/${path}" "${INSTALL_DIR}/${path}" 2>/dev/null | head -10 || true
            drift=1
        fi
    done
    if [ "${drift}" -eq 0 ]; then
        ok_msg "التثبيت مطابق للريبو"
        exit 0
    fi
    die "التثبيت يختلف على الريبو — عاود شغّل السكريبت (بلا --check) باش ينسخ النسخة الجديدة"
}

echo -e "${C_CYAN}${C_BOLD}"
cat << "BANNER"
   ______           _          ____  _____
  / ____/__  ____  (_)___     / __ \/ ___/
 / / __/ _ \/ __ \/ / __ \   / / / /\__ \
/ /_/ /  __/ / / / / /_/ /  / /_/ /___/ /
\____/\___/_/ /_/_/\____/   \____//____/

  ⚡ Genio OS — Local-first AI Studio ⚡
  المصدر الوحيد للحقيقة = الريبو (بلا توليد كود)
BANNER
echo -e "${C_RESET}"

[ "${MODE}" = "check" ] && check_install

# ما نبداوش حتى نتأكدو إلي الكود موجود في الريبو (بلا كود = بلا توليد v5)
require_source

# --- 1. البنية -----------------------------------------------------------------
step_header "[1/5] تجهيز المسارات في ${INSTALL_DIR}"

if [ "${DRY_RUN}" = "1" ]; then
    mkdir -p "${INSTALL_DIR}"/{workspace,rag_docs,logs,memory/playbooks,memory/tools_}
else
    if [ ! -d "${INSTALL_DIR}" ]; then
        if ! mkdir -p "${INSTALL_DIR}" 2>/dev/null; then
            case "${INSTALL_DIR}" in
                /data/*|/opt/*|/srv/*)
                    ${SUDO} mkdir -p "${INSTALL_DIR}" && ${SUDO} chown -R "$(id -un):$(id -gn)" "${INSTALL_DIR}"
                    ;;
                *) die "ما قدرناش نخلقو ${INSTALL_DIR} — استعمل مسار تكتب فيه (GENIO_INSTALL_DIR)" ;;
            esac
        fi
    fi
    mkdir -p "${INSTALL_DIR}"/{workspace,rag_docs,logs,memory/playbooks,memory/tools_}
fi
ok_msg "المسارات واجدة (المساحة القابلة للكتابة في ${INSTALL_DIR})"

# --- 2. نسخ الكود من الريبو ----------------------------------------------------
step_header "[2/5] نسخ الكود من الريبو (بلا توليد)"

copy_path() {
    local rel="$1"
    local src="${SRC_DIR}/${rel}"
    local dst="${INSTALL_DIR}/${rel}"
    [ -e "${src}" ] || return 0
    mkdir -p "$(dirname "${dst}")"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --exclude '__pycache__' --exclude '*.pyc' "${src}" "${INSTALL_DIR}/"
    else
        cp -a "${src}" "${dst}"
        # ما ننسخوش الـ bytecode: يتولّد من جديد ويتضارب مع الـ check
        find "${dst}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    fi
}

# نصحّحو مسارات config.json باش تمشي مع مسار التثبيت (ماشي /data/genio-os دايمًا)
rewrite_config() {
    local cfg="$1"
    if command -v python3 >/dev/null 2>&1; then
        python3 - "${cfg}" "${INSTALL_DIR}" "${GENIO_PORT:-}" <<'PY'
import json, sys

path, install_dir, port = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
data["workspace_dir"] = f"{install_dir}/workspace"
data["rag_dir"] = f"{install_dir}/rag_docs"
data["memory_dir"] = f"{install_dir}/memory"
if port:
    data["port"] = int(port)
security = data.setdefault("security", {})
security.setdefault("host", "127.0.0.1")
security.setdefault("api_token", "")
security.setdefault("enable_shell", False)
security.setdefault("enable_update", False)
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
PY
    else
        warn_msg "python3 ما موجودش — config.json تنسخ كيما هو"
    fi
}

copy_path "core"
copy_path "web"
copy_path "requirements.txt"
copy_path "requirements-dev.txt"
copy_path "pytest.ini"
copy_path "scripts"
copy_path "docs"
copy_path "deployment"
copy_path "Makefile"
copy_path "README.md"

# config.json: ما نكتبوهش إذا موجود (إعدادات المستعمل ما تتحذفش)
if [ -f "${SRC_DIR}/config.json" ] && [ ! -f "${INSTALL_DIR}/config.json" ]; then
    cp "${SRC_DIR}/config.json" "${INSTALL_DIR}/config.json"
    rewrite_config "${INSTALL_DIR}/config.json"
    ok_msg "config.json تنسخ من الريبو (مسارات ${INSTALL_DIR})"
elif [ -f "${INSTALL_DIR}/config.json" ]; then
    info_msg "config.json موجود — نخلّيوه كيما هو (الإعدادات متاعك)"
fi

# إذا ما فمّاش config (تثبيت من مجلّد بلا config) نكتبو إعداد آمن أدنى
if [ ! -f "${INSTALL_DIR}/config.json" ]; then
    cat > "${INSTALL_DIR}/config.json" << EOF
{
  "version": "9.0.0",
  "enterprise_name": "Genio OS — Local-first AI Studio",
  "node_name": "$(hostname)",
  "ollama_host": "${OLLAMA_HOST}",
  "primary_model": "${PRIMARY_MODEL}",
  "vision_model": "minicpm-v:latest",
  "workspace_dir": "${INSTALL_DIR}/workspace",
  "rag_dir": "${INSTALL_DIR}/rag_docs",
  "memory_dir": "${INSTALL_DIR}/memory",
  "port": ${PORT},
  "temperature": 0.2,
  "num_ctx": 8192,
  "auto_self_heal_retries": 2,
  "security": {
    "host": "127.0.0.1",
    "api_token": "",
    "enable_shell": false,
    "enable_update": false
  }
}
EOF
    warn_msg "config.json ما كانش — كتبنا واحد آمن (host=127.0.0.1، shell مقفول)"
fi

ok_msg "الكود تنسخ من الريبو: $(ls "${INSTALL_DIR}/core" | tr '\n' ' ')"

# --- 3. venv + المتطلّبات ------------------------------------------------------
step_header "[3/5] بيئة Python والمتطلّبات"
if [ "${DRY_RUN}" = "1" ]; then
    warn_msg "DRY_RUN=1 → ما نعملوش venv ولا pip install"
else
    PYTHON_BIN="$(command -v python3 || true)"
    [ -n "${PYTHON_BIN}" ] || die "python3 ما موجودش"
    if [ ! -x "${INSTALL_DIR}/venv/bin/python" ]; then
        VENV_ERR="$(mktemp)"
        if "${PYTHON_BIN}" -m venv "${INSTALL_DIR}/venv" 2>"${VENV_ERR}"; then
            ok_msg "venv تخلق"
        else
            # Debian/Ubuntu بلا python3-venv: ensurepip ناقص، أما pip متاع النظام موجود
            warn_msg "python3 -m venv فشل (ensurepip ناقص؟) — نجرّبو --without-pip + pip متاع النظام"
            rm -rf "${INSTALL_DIR}/venv"
            if "${PYTHON_BIN}" -m venv --without-pip "${INSTALL_DIR}/venv"; then
                if "${PYTHON_BIN}" -m pip --python "${INSTALL_DIR}/venv/bin/python" install --quiet --upgrade pip; then
                    ok_msg "venv تخلق (بلا ensurepip) وpip تثبّت من النظام"
                else
                    cat "${VENV_ERR}" >&2
                    die "pip ما تثبّتش — ثبّت python3-venv ولا python3-pip"
                fi
            else
                cat "${VENV_ERR}" >&2
                die "ما قدرناش نعملو venv — ثبّت python3-venv (apt install python3.14-venv)"
            fi
        fi
        rm -f "${VENV_ERR}"
    else
        info_msg "venv موجود"
    fi
    "${INSTALL_DIR}/venv/bin/python" -m pip install --quiet --upgrade pip
    "${INSTALL_DIR}/venv/bin/python" -m pip install --quiet -r "${INSTALL_DIR}/requirements.txt"
    ok_msg "المتطلّبات مثبّتة"
fi

# --- 4. الخدمة (systemd) -------------------------------------------------------
step_header "[4/5] وحدة الخدمة"
UNIT_SRC="${INSTALL_DIR}/deployment/genio-os.service"
# المنفذ الفعلي: GENIO_PORT، وإلا اللي في config.json، وإلا 8099
EFFECTIVE_PORT="${GENIO_PORT:-}"
if [ -z "${EFFECTIVE_PORT}" ]; then
    EFFECTIVE_PORT="$(grep -oE '"port"[[:space:]]*:[[:space:]]*[0-9]+' "${INSTALL_DIR}/config.json" 2>/dev/null | head -1 | grep -oE '[0-9]+' || true)"
fi
EFFECTIVE_PORT="${EFFECTIVE_PORT:-8099}"

if [ -f "${UNIT_SRC}" ]; then
    UNIT_RENDERED="${INSTALL_DIR}/.${SERVICE_NAME}.rendered"
    sed -e "s#/opt/genio-os#${INSTALL_DIR}#g" \
        -e "s#/data/genio-os#${INSTALL_DIR}#g" \
        -e "s#^User=.*#User=$(id -un)#" \
        -e "s#^Group=.*#Group=$(id -gn)#" \
        -e "s#--port [0-9]\+#--port ${EFFECTIVE_PORT}#" \
        "${UNIT_SRC}" > "${UNIT_RENDERED}"
    if [ "${DRY_RUN}" = "1" ]; then
        info_msg "DRY_RUN: الوحدة موجودة في ${UNIT_RENDERED}"
    elif [ "${SKIP_SYSTEMD}" = "1" ]; then
        warn_msg "--no-service: الوحدة ما تسجّلتش في systemd (موجودة في ${UNIT_RENDERED})"
        info_msg "باش تسجّلها: systemctl copy من ${UNIT_RENDERED} لـ /etc/systemd/system/${SERVICE_NAME}"
    else
        ${SUDO} cp "${UNIT_RENDERED}" "/etc/systemd/system/${SERVICE_NAME}"
        ${SUDO} systemctl daemon-reload
        ok_msg "الوحدة مثبّتة في /etc/systemd/system/${SERVICE_NAME}"
    fi
else
    warn_msg "deployment/genio-os.service ما موجودش — ما نكتبوش وحدة من راسنا"
fi

# --- 5. فحص + تشغيل ------------------------------------------------------------
step_header "[5/5] الفحص والتشغيل"
"${INSTALL_DIR}/venv/bin/python" -m compileall -q "${INSTALL_DIR}/core" "${INSTALL_DIR}/web" 2>/dev/null \
    || "${SRC_DIR}/venv/bin/python" -m compileall -q "${INSTALL_DIR}/core" "${INSTALL_DIR}/web" 2>/dev/null \
    || warn_msg "compileall ما تمّاش (بلا venv) — الفحص يتمّ في CI"

if [ "${DRY_RUN}" = "1" ]; then
    ok_msg "DRY_RUN سالي — ${INSTALL_DIR} واجد للمعاينة"
    info_msg "الملفات المنسوخة: $(find "${INSTALL_DIR}/core" "${INSTALL_DIR}/web" -type f | wc -l) ملف"
    exit 0
fi

if [ "${SKIP_SYSTEMD}" = "1" ]; then
    info_msg "--no-service: ما نبداوش الخدمة. للتشغيل يدويًا:"
    info_msg "${INSTALL_DIR}/venv/bin/python -m uvicorn web.server:app --host 127.0.0.1 --port ${EFFECTIVE_PORT} (من داخل ${INSTALL_DIR})"
    exit 0
fi

${SUDO} systemctl enable --now "${SERVICE_NAME}" >/dev/null 2>&1 || ${SUDO} systemctl restart "${SERVICE_NAME}"

READY=0
for _ in $(seq 1 30); do
    if "${INSTALL_DIR}/venv/bin/python" - "${PORT}" << 'PY' >/dev/null 2>&1
import sys, urllib.request
port = sys.argv[1]
urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2)
PY
    then READY=1; break; fi
    sleep 1
done

if [ "${READY}" = "1" ]; then
    ok_msg "المنصّة تخدم على http://127.0.0.1:${PORT} (محلي فقط)"
    info_msg "أوّل حساب: POST /api/auth/bootstrap — وبعدها token ولا Cloudflare Access"
else
    warn_msg "الخدمة ما جاوبتش — شوف: journalctl -u ${SERVICE_NAME} -n 50"
fi
