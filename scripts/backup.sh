#!/usr/bin/env bash
# ==============================================================================
# 💾 Genio OS — نسخة احتياطية كاملة (قاعدة البيانات + workspace + memory + rag_docs)
#
#   bash scripts/backup.sh                        # مجلّد البيانات الافتراضي
#   GENIO_DATA_DIR=/data/genio-os make backup
#
# المتغيرات:
#   GENIO_DATA_DIR      مجلّد البيانات (افتراضي: جذر الريبو)
#   GENIO_BACKUP_DIR    وين تتحفظ النسخ (افتراضي: <DATA>/backups)
#   GENIO_BACKUP_KEEP   عدد النسخ (افتراضي: 14؛ 0 = بلا حدّ)
#   GENIO_BACKUP_DAYS   نحذفو الأقدم من N يوم (افتراضي: 30؛ 0 = تعطيل)
#
# الخروج: 0 نجح | 1 خطأ | 3 نسخة أخرى تخدم توّا
# ==============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${GENIO_DATA_DIR:-$ROOT}"
DEST="${GENIO_BACKUP_DIR:-${DATA}/backups}"
KEEP="${GENIO_BACKUP_KEEP:-14}"
DAYS="${GENIO_BACKUP_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="${DEST}/genio-${STAMP}.tar.gz"

source "${ROOT}/scripts/_genio_state.sh"
PY="$(pick_python || true)"

mkdir -p "${DEST}"
exec 9>"${DEST}/.backup.lock"
flock -n 9 || { echo "⏭️  نسخة أخرى تخدم توّا — تخطّينا." >&2; exit 3; }

ITEMS=()
for item in config.json memory workspace rag_docs logs; do
    [ -e "${DATA}/${item}" ] && ITEMS+=("${item}")
done
[ "${#ITEMS[@]}" -gt 0 ] || { echo "❌ ما فمّاش حتى شي يتعملو backup في ${DATA}" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
for item in "${ITEMS[@]}"; do
    cp -a "${DATA}/${item}" "${STAGE}/${item}"
done
# ملفات WAL/SHM مؤقّتة: ما تتحفظش
rm -f "${STAGE}/memory/genio.db-wal" "${STAGE}/memory/genio.db-shm"

if [ -n "${PY}" ]; then
    snapshot_db "${DATA}/memory/genio.db" "${STAGE}/memory/genio.db" \
        || echo "⚠️  snapshot القاعدة فشل — النسخة عادية (cp)." >&2
else
    echo "⚠️  ما فمّاش python — القاعدة تنسخ عادي (cp)." >&2
fi

USERS="$(count_users "${STAGE}" 2>/dev/null || echo 0)"
FILES="$(count_files "${STAGE}")"
COMMIT="$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo '-')"

if [ -n "${PY}" ]; then
    "${PY}" - "${STAGE}/manifest.json" "${USERS}" "${FILES}" "${COMMIT}" "${STAMP}" <<'PY'
import json, sys
path, users, files, commit, stamp = sys.argv[1:6]
json.dump(
    {"created_at": stamp, "commit": commit, "users": int(users), "files": int(files)},
    open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2,
)
PY
fi

tar -czf "${ARCHIVE}" -C "${STAGE}" .
( cd "${DEST}" && sha256sum "$(basename "${ARCHIVE}")" > "$(basename "${ARCHIVE}").sha256" )
echo "✅ نسخة احتياطية: ${ARCHIVE} ($(du -h "${ARCHIVE}" | cut -f1)) — ${FILES} ملف، ${USERS} حساب، commit ${COMMIT}"

# --- الاحتفاظ: بالعدد ثم بالعمر ------------------------------------------------
drop() {
    rm -f "$1" "$1.sha256"
    echo "🗑️  حذف: $(basename "$1")"
}

if [ "${KEEP}" -gt 0 ]; then
    ls -1t "${DEST}"/genio-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
        drop "${old}"
    done
fi
if [ "${DAYS}" -gt 0 ]; then
    find "${DEST}" -maxdepth 1 -name 'genio-*.tar.gz' -type f -mtime "+${DAYS}" 2>/dev/null | while read -r old; do
        drop "${old}"
    done
fi
