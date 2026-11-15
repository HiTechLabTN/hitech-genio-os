#!/usr/bin/env bash
# ==============================================================================
# 💾 Genio OS — backup محلي للذاكرة والـ workspace والإعدادات (المرحلة 0)
#
# الاستعمال:  bash scripts/backup.sh
# المتغيرات:  GENIO_BACKUP_DIR (افتراضي: <repo>/backups)
#             GENIO_BACKUP_KEEP (افتراضي: 7 نسخ)
# ==============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${GENIO_BACKUP_DIR:-${ROOT}/backups}"
KEEP="${GENIO_BACKUP_KEEP:-7}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="${DEST}/genio-${STAMP}.tar.gz"

mkdir -p "${DEST}"

# ناخدو غير الموجود: memory + workspace + logs + config.json
TARGETS=()
for item in config.json memory workspace logs; do
    [ -e "${ROOT}/${item}" ] && TARGETS+=("${item}")
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
    echo "❌ ما فمّاش حتى شي يتعملو backup في ${ROOT}" >&2
    exit 1
fi

tar -czf "${ARCHIVE}" -C "${ROOT}" "${TARGETS[@]}"

SIZE="$(du -h "${ARCHIVE}" | cut -f1)"
echo "✅ Backup: ${ARCHIVE} (${SIZE})"

# نخلّيو غير آخر KEEP نسخ
if [ "${KEEP}" -gt 0 ]; then
    ls -1t "${DEST}"/genio-*.tar.gz 2>/dev/null \
        | tail -n +$((KEEP + 1)) \
        | while read -r old; do
              rm -f "${old}"
              echo "🗑️  حذف النسخة القديمة: $(basename "${old}")"
          done
fi
