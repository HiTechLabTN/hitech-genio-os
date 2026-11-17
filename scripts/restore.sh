#!/usr/bin/env bash
# ==============================================================================
# ♻️  Genio OS — استرجاع نسخة احتياطية + تحقّق من المحتوى
#
# الاستعمال:
#   bash scripts/restore.sh --list                          # النسخ المتوفّرة
#   bash scripts/restore.sh --dry-run                       # فحص بلا كتابة
#   bash scripts/restore.sh --from latest --into /tmp/probe  # استرجاع مجرّب
#   GENIO_DATA_DIR=/data/genio-os bash scripts/restore.sh --from latest --into /data/genio-os --force
#
# يتحقّق بعد الاسترجاع: عدد الملفات و عدد الحسابات (جدول users) مقابل manifest.json
# اللي يتكتب وقت الـ backup. أي فرق = exit 1.
#
# الخروج: 0 نجح و مطابق | 1 فشل/فرق | 2 استعمال غالط
# ==============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${GENIO_DATA_DIR:-$ROOT}"
DEST="${GENIO_BACKUP_DIR:-${DATA}/backups}"
FROM=""
INTO=""
FORCE=0
DRY=0
LIST=0

while [ $# -gt 0 ]; do
    case "$1" in
        --from) FROM="${2:-}"; shift 2 ;;
        --into) INTO="${2:-}"; shift 2 ;;
        --force) FORCE=1; shift ;;
        --dry-run) DRY=1; shift ;;
        --list) LIST=1; shift ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "restore: خيار غير معروف: $1" >&2; exit 2 ;;
    esac
done

if [ "${LIST}" -eq 1 ]; then
    echo "📦 النسخ في ${DEST}:"
    ls -1t "${DEST}"/genio-*.tar.gz 2>/dev/null | while read -r f; do
        printf '  %s  (%s)\n' "$(basename "$f")" "$(du -h "$f" | cut -f1)"
    done
    [ -z "$(ls -1 "${DEST}"/genio-*.tar.gz 2>/dev/null)" ] && echo "  (ما فمّاش)"
    exit 0
fi

if [ -z "${FROM}" ] || [ -z "${INTO}" ]; then
    echo "restore: لازم --from <archive|latest> و --into <dir>" >&2
    exit 2
fi

if [ "${FROM}" = "latest" ]; then
    FROM="$(ls -1t "${DEST}"/genio-*.tar.gz 2>/dev/null | head -1 || true)"
fi
[ -f "${FROM}" ] || { echo "restore: ما لقيتش الأرشيف: ${FROM}" >&2; exit 2; }

echo "📦 الأرشيف: ${FROM}"

# 1) التحقّق من الـ checksum إذا موجود
if [ -f "${FROM}.sha256" ]; then
    if ( cd "$(dirname "${FROM}")" && sha256sum -c --quiet "$(basename "${FROM}").sha256" ); then
        echo "  ✅ sha256 مطابق"
    else
        echo "  ❌ sha256 ما يطابقش — الأرشيف تالف ولا تبدّل" >&2
        exit 1
    fi
else
    echo "  ⚠️  ما فمّاش .sha256 — نكملو بلا تحقّق سلامة"
fi

if ! tar -tzf "${FROM}" >/dev/null 2>&1; then
    echo "  ❌ الأرشيف ما يتقراش (tar فشل)" >&2
    exit 1
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
tar -xzf "${FROM}" -C "${STAGE}"

MANIFEST="${STAGE}/manifest.json"
PY=""
[ -x "${ROOT}/venv/bin/python" ] && PY="${ROOT}/venv/bin/python"
[ -z "${PY}" ] && command -v python3 >/dev/null 2>&1 && PY="python3"

if [ -z "${PY}" ]; then
    echo "restore: python3 مطلوب للتحقّق" >&2
    exit 2
fi

WANT=$("${PY}" - "${MANIFEST}" <<'PY'
import json, sys
try:
    m = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("-1 -1")
    raise SystemExit
print(m.get("users", -1), m.get("files", -1))
PY
)
WANT_USERS=$(printf '%s' "${WANT}" | awk '{print $1}')
WANT_FILES=$(printf '%s' "${WANT}" | awk '{print $2}')
echo "  📋 manifest: ${WANT_FILES} ملف، ${WANT_USERS} حساب"

count_files() {
    { find "$1/workspace" "$1/rag_docs" "$1/memory" -type f ! -name 'genio.db*' 2>/dev/null || true; } | wc -l | tr -d ' '
}
count_users() {
    "${PY}" - "$1/memory/genio.db" <<'PY' 2>/dev/null || echo -1
import sqlite3, sys
try:
    with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as conn:
        print(conn.execute("select count(*) from users").fetchone()[0])
except Exception:
    print(-1)
PY
}

GOT_FILES="$(count_files "${STAGE}")"
GOT_USERS="$(count_users "${STAGE}")"
echo "  🔎 داخل الأرشيف: ${GOT_FILES} ملف، ${GOT_USERS} حساب"

STATUS=0
if [ "${GOT_FILES}" != "${WANT_FILES}" ]; then
    echo "  ❌ عدد الملفات ما يطابقش (متوقّع ${WANT_FILES}، لقينا ${GOT_FILES})" >&2
    STATUS=1
else
    echo "  ✅ عدد الملفات مطابق (${GOT_FILES})"
fi
if [ "${GOT_USERS}" != "${WANT_USERS}" ]; then
    echo "  ❌ عدد الحسابات ما يطابقش (متوقّع ${WANT_USERS}، لقينا ${GOT_USERS})" >&2
    STATUS=1
else
    echo "  ✅ عدد الحسابات مطابق (${GOT_USERS})"
fi

if [ "${DRY}" -eq 1 ]; then
    echo "🧪 dry-run: ما كتبناش حتى شي."
    exit "${STATUS}"
fi

# 2) الوجهة: ما نطيحوش داتا موجودة بلا --force
if [ -d "${INTO}" ] && [ -n "$(ls -A "${INTO}" 2>/dev/null)" ] && [ "${FORCE}" -eq 0 ]; then
    echo "restore: ${INTO} ماشي فارغ — زيد --force كان تحب تدهسو" >&2
    exit 2
fi

mkdir -p "${INTO}"
for item in config.json memory workspace rag_docs logs manifest.json; do
    [ -e "${STAGE}/${item}" ] || continue
    rm -rf "${INTO:?}/${item}"
    cp -a "${STAGE}/${item}" "${INTO}/${item}"
done

# 3) تحقّق بعد الكتابة الفعلية
FINAL_FILES="$(count_files "${INTO}")"
FINAL_USERS="$(count_users "${INTO}")"
echo "  📂 بعد الاسترجاع في ${INTO}: ${FINAL_FILES} ملف، ${FINAL_USERS} حساب"

if [ "${FINAL_FILES}" != "${WANT_FILES}" ] || [ "${FINAL_USERS}" != "${WANT_USERS}" ]; then
    echo "❌ الاسترجاع كمّل أما التحقّق فشل." >&2
    exit 1
fi
[ "${STATUS}" -ne 0 ] && { echo "❌ الأرشيف نفسه فيه فرق — ما تعاودش تستعملو." >&2; exit 1; }

echo "✅ الاسترجاع نجح: ${FINAL_FILES} ملف و ${FINAL_USERS} حساب مطابقين للـ manifest."
exit 0
