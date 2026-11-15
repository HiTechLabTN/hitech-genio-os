#!/usr/bin/env bash
# ==============================================================================
# 🔄 Genio OS — تحديث (يخدم مع GENIO_INSTALL_DIR كيما الإنسطالور)
# ==============================================================================
# الاستعمال:
#   bash update_genio.sh                        # /data/genio-os
#   GENIO_INSTALL_DIR=/opt/genio-os bash …      # مسار آخر
#   GENIO_DRY_RUN=1 bash …                      # تجربة: بلا git pull وبلا restart
#
# قاعدة المرحلة 0: المصدر الوحيد للحقيقة = الريبو. هذا السكريبت ما يولّدش كود.
# ==============================================================================

set -uo pipefail

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_CYAN='\033[38;5;51m'
C_GREEN='\033[38;5;46m'
C_YELLOW='\033[38;5;226m'
C_RED='\033[38;5;196m'
C_BLUE='\033[38;5;39m'

INSTALL_DIR="${GENIO_INSTALL_DIR:-/data/genio-os}"
DRY_RUN="${GENIO_DRY_RUN:-0}"
SERVICE_NAME="${GENIO_SERVICE:-genio-os.service}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ok_msg()   { echo -e "  ${C_GREEN}✅ $1${C_RESET}"; }
info_msg() { echo -e "  ${C_BLUE}ℹ️  $1${C_RESET}"; }
warn_msg() { echo -e "  ${C_YELLOW}⚠️  $1${C_RESET}"; }
die()      { echo -e "  ${C_RED}❌ $1${C_RESET}" >&2; exit 1; }

# الصلاحيات: بلا sudo في DRY_RUN ولا كي نكونو root
SUDO=""
if [ "${DRY_RUN}" != "1" ] && [ "$(id -u)" != "0" ]; then
    SUDO="sudo"
fi

echo -e "${C_CYAN}${C_BOLD}🔄 Genio OS — تحديث ${INSTALL_DIR}${C_RESET}"

[ -d "${INSTALL_DIR}" ] || die "ما فمّاش تثبيت في ${INSTALL_DIR} — استعمل install_genio_os.sh ولا حطّ GENIO_INSTALL_DIR"
cd "${INSTALL_DIR}" || die "ما قدرناش ندخلو ${INSTALL_DIR}"

# --- 1. الكود: من الريبو، ما نولّدوش -----------------------------------------
if [ -d "${INSTALL_DIR}/.git" ]; then
    BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    if [ "${DRY_RUN}" = "1" ]; then
        info_msg "DRY_RUN=1 → كان نعملو: git pull --ff-only origin ${BRANCH}"
    else
        echo -e "  ${C_BLUE}ℹ️  git pull --ff-only origin ${BRANCH}${C_RESET}"
        if git pull --ff-only origin "${BRANCH}"; then
            ok_msg "الكود تحدّث من الريبو"
        else
            warn_msg "git pull ما تمّاش — الكود بقى كيما هو، ما نكمّلوش بالنسخة القديمة"
        fi
    fi

    echo -e "\n${C_CYAN}📋 آخر التحديثات:${C_RESET}"
    git log -n 3 --pretty=format:"  - %s (%ar)" 2>/dev/null || true
    echo
else
    warn_msg "${INSTALL_DIR} ماشي git clone — نسخة منسوخة، ما فمّاش git pull."
    info_msg "حدّث الـ clone متاع الريبو، وبعدها: bash ${SRC_DIR}/install_genio_os.sh"
    info_msg "الإنسطالور ينسخ core/ و web/ من الريبو (بلا توليد كود)."
fi

# --- 2. الخدمة: موجودة قبل الـ restart؟ --------------------------------------
SERVICE_FOUND=0
if command -v systemctl >/dev/null 2>&1; then
    if ${SUDO} systemctl cat "${SERVICE_NAME}" >/dev/null 2>&1; then
        SERVICE_FOUND=1
    fi
fi

if [ "${SERVICE_FOUND}" = "1" ]; then
    if [ "${DRY_RUN}" = "1" ]; then
        info_msg "DRY_RUN=1 → كان نعملو: systemctl restart ${SERVICE_NAME}"
    else
        if ${SUDO} systemctl restart "${SERVICE_NAME}"; then
            ok_msg "الخدمة ${SERVICE_NAME} تعاودت"
        else
            warn_msg "restart فشل — شوف: journalctl -u ${SERVICE_NAME} -n 50"
        fi
        if ${SUDO} systemctl is-active --quiet "${SERVICE_NAME}"; then
            ok_msg "الحالة: active"
        else
            warn_msg "الحالة: ماشي active — journalctl -u ${SERVICE_NAME} -n 50"
        fi
    fi
else
    warn_msg "الوحدة ${SERVICE_NAME} ما موجوداش في systemd — ما نعملوش restart."
    info_msg "ثبّتها: bash ${SRC_DIR}/install_genio_os.sh (ينسخ deployment/genio-os.service)"
fi

# --- 3. المنفذ + فحص سريع ----------------------------------------------------
PORT="$(grep -oE '"port"[[:space:]]*:[[:space:]]*[0-9]+' config.json 2>/dev/null | head -1 | grep -oE '[0-9]+' || true)"
PORT="${PORT:-8099}"

if [ "${DRY_RUN}" != "1" ] && [ "${SERVICE_FOUND}" = "1" ] && command -v curl >/dev/null 2>&1; then
    if curl -sf -o /dev/null --max-time 5 "http://127.0.0.1:${PORT}/api/status"; then
        ok_msg "المنصّة تجاوب على http://127.0.0.1:${PORT}"
    else
        warn_msg "ما جاوبتش على http://127.0.0.1:${PORT} — شوف اللوجز"
    fi
fi

echo
echo -e "${C_GREEN}${C_BOLD}🎉 مريقل.${C_RESET}"
info_msg "محلي فقط: http://127.0.0.1:${PORT} (الربط على 127.0.0.1 من المرحلة 0)"
info_msg "للوصول من بعيد: Cloudflare Tunnel + Access، ولا حطّ GENIO_API_TOKEN"
info_msg "نسخة احتياطية قبل أي تحديث: bash scripts/backup.sh"
