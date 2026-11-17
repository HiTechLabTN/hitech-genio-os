#!/usr/bin/env bash
# ==============================================================================
# ♻️  Genio OS — استرجاع نسخة احتياطية + تحقّق من المحتوى
#
#   bash scripts/restore.sh --list
#   bash scripts/restore.sh --dry-run                       # فحص بلا كتابة
#   bash scripts/restore.sh --from latest --into /tmp/probe
#   GENIO_DATA_DIR=/data/genio-os bash scripts/restore.sh --from latest --into /data/genio-os --force
#
# يتحقّق: sha256، ثم عدد الملفات و عدد الحسابات مقابل manifest.json
# (قبل الكتابة و بعدها). أي فرق = exit 1.
#
# الخروج: 0 مطابق | 1 فرق/فشل | 2 استعمال غالط
# ==============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${GENIO_DATA_DIR:-$ROOT}"
DEST="${GENIO_BACKUP_DIR:-${DATA}/backups}"
FROM=""
INTO=""
FORCE=0
DRY=0

while [ $# -gt 0 ]; do
    case "$1" in
        --from) FROM="${2:-}"; shift 2 ;;
        --into) INTO="${2:-}"; shift 2 ;;
        --force) FORCE=1; shift ;;
        --dry-run) DRY=1; shift ;;
        --list) shift
            echo "📦 النسخ في ${DEST}:"
            found=0
            for f in "${DEST}"/genio-*.tar.gz; do
                [ -e "$f" ] || continue
                found=1
                printf '  %s  (%s)\n' "$(basename "$f")" "$(du -h "$f" | cut -f1)"
            done
            [ "${found}" -eq 1 ] || echo "  (ما فمّاش)"
            exit 0 ;;
        -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
        *) echo "restore: خيار غير معروف: $1" >&2; exit 2 ;;
    esac
done

[ -n "${FROM}" ] && [ -n "${INTO}" ] \
    || { echo "restore: لازم --from <archive|latest> و --into <dir>" >&2; exit 2; }

if [ "${FROM}" = "latest" ]; then
    FROM="$(ls -1t "${DEST}"/genio-*.tar.gz 2>/dev/null | head -1 || true)"
fi
[ -f "${FROM}" ] || { echo "restore: ما لقيتش الأرشيف: ${FROM}" >&2; exit 2; }
echo "📦 الأرشيف: ${FROM}"

if [ -f "${FROM}.sha256" ]; then
    ( cd "$(dirname "${FROM}")" && sha256sum -c --quiet "$(basename "${FROM}").sha256" ) \
        || { echo "  ❌ sha256 ما يطابقش — الأرشيف تالف ولا تبدّل" >&2; exit 1; }
    echo "  ✅ sha256 مطابق"
else
    echo "  ⚠️  ما فمّاش .sha256 — نكملو بلا تحقّق سلامة"
fi
tar -tzf "${FROM}" >/dev/null 2>&1 \
    || { echo "  ❌ الأرشيف ما يتقراش (tar فشل)" >&2; exit 1; }

source "${ROOT}/scripts/_genio_state.sh"
PY="$(pick_python || true)"
[ -n "${PY}" ] || { echo "restore: python3 مطلوب للتحقّق" >&2; exit 2; }

STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
tar -xzf "${FROM}" -C "${STAGE}"

# المرجع من الـ manifest اللي كتبو backup.sh
read -r WANT_USERS WANT_FILES < <("${PY}" - "${STAGE}/manifest.json" <<'PY'
import json, sys
try:
    m = json.load(open(sys.argv[1], encoding="utf-8"))
    print(m.get("users", -1), m.get("files", -1))
except Exception:
    print(-1, -1)
PY
)
echo "  📋 manifest: ${WANT_FILES} ملف، ${WANT_USERS} حساب"

# يقارن مصدر مع المرجع، يطبع النتيجة، و يرجّع 1 كان فمّا فرق
verify_against_manifest() {
    local label="$1" dir="$2" files users bad=0
    files="$(count_files "${dir}")"
    users="$(count_users "${dir}")"
    echo "  🔎 ${label}: ${files} ملف، ${users} حساب"
    if [ "${files}" = "${WANT_FILES}" ]; then
        echo "  ✅ عدد الملفات مطابق (${files})"
    else
        echo "  ❌ عدد الملفات ما يطابقش (متوقّع ${WANT_FILES}، لقينا ${files})" >&2
        bad=1
    fi
    if [ "${users}" = "${WANT_USERS}" ]; then
        echo "  ✅ عدد الحسابات مطابق (${users})"
    else
        echo "  ❌ عدد الحسابات ما يطابقش (متوقّع ${WANT_USERS}، لقينا ${users})" >&2
        bad=1
    fi
    return "${bad}"
}

verify_against_manifest "داخل الأرشيف" "${STAGE}" || {
    [ "${DRY}" -eq 1 ] && exit 1
    echo "❌ الأرشيف نفسه فيه فرق — ما تعاودش تستعملو." >&2
    exit 1
}

if [ "${DRY}" -eq 1 ]; then
    echo "🧪 dry-run: ما كتبناش حتى شي."
    exit 0
fi

# ما نطيحوش داتا موجودة بلا --force
if [ "${FORCE}" -eq 0 ] && [ -d "${INTO}" ] && [ -n "$(ls -A "${INTO}" 2>/dev/null)" ]; then
    echo "restore: ${INTO} ماشي فارغ — زيد --force كان تحب تدهسو" >&2
    exit 2
fi

mkdir -p "${INTO}"
for item in config.json memory workspace rag_docs logs manifest.json; do
    [ -e "${STAGE}/${item}" ] || continue
    rm -rf "${INTO:?}/${item}"
    cp -a "${STAGE}/${item}" "${INTO}/${item}"
done

verify_against_manifest "بعد الاسترجاع في ${INTO}" "${INTO}" || {
    echo "❌ الاسترجاع كمّل أما التحقّق فشل." >&2
    exit 1
}
echo "✅ الاسترجاع نجح: ${WANT_FILES} ملف و ${WANT_USERS} حساب مطابقين للـ manifest."
exit 0
