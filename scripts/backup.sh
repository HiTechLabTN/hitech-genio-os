#!/usr/bin/env bash
# ==============================================================================
# 💾 Genio OS — نسخة احتياطية كاملة (قاعدة البيانات + workspace + memory + rag_docs)
#
# الاستعمال:
#   bash scripts/backup.sh                    # مجلّد البيانات الافتراضي
#   GENIO_DATA_DIR=/data/genio-os bash scripts/backup.sh
#   make backup                               # نفس الشي
#
# المتغيرات:
#   GENIO_DATA_DIR      مجلّد البيانات (افتراضي: جذر الريبو)
#   GENIO_BACKUP_DIR    وين تتحفظ النسخ (افتراضي: <DATA>/backups)
#   GENIO_BACKUP_KEEP   عدد النسخ اللي نخلّيوها (افتراضي: 14؛ 0 = بلا حدّ)
#   GENIO_BACKUP_DAYS   نحذفو النسخ الأقدم من قدّاش يوم (افتراضي: 30؛ 0 = تعطيل)
#
# الخروج: 0 نجح | 1 خطأ | 3 نسخة أخرى تخدم توّا (lock)
# ==============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${GENIO_DATA_DIR:-$ROOT}"
DEST="${GENIO_BACKUP_DIR:-${DATA}/backups}"
KEEP="${GENIO_BACKUP_KEEP:-14}"
DAYS="${GENIO_BACKUP_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="${DEST}/genio-${STAMP}.tar.gz"

mkdir -p "${DEST}"

# ما نخلّيوش زوز نسخ يتشادّو في نفس الوقت
exec 9>"${DEST}/.backup.lock"
if ! flock -n 9; then
    echo "⏭️  نسخة أخرى تخدم توّا (${DEST}/.backup.lock) — تخطّينا." >&2
    exit 3
fi

TARGETS=()
for item in config.json memory workspace rag_docs logs; do
    [ -e "${DATA}/${item}" ] && TARGETS+=("${item}")
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
    echo "❌ ما فمّاش حتى شي يتعملو backup في ${DATA}" >&2
    exit 1
fi

STAGE="$(mktemp -d)"
cleanup() { rm -rf "${STAGE}"; }
trap cleanup EXIT

DB_SRC="${DATA}/memory/genio.db"
DB_OK=0
for item in "${TARGETS[@]}"; do
    cp -a "${DATA}/${item}" "${STAGE}/${item}"
done

# قاعدة SQLite تتنسخ بالـ backup API (نسخة متّسقة حتى لو المنصّة تخدم)
if [ -f "${DB_SRC}" ]; then
    PY=""
    [ -x "${ROOT}/venv/bin/python" ] && PY="${ROOT}/venv/bin/python"
    [ -z "${PY}" ] && command -v python3 >/dev/null 2>&1 && PY="python3"
    if [ -n "${PY}" ]; then
        if "${PY}" - "${DB_SRC}" "${STAGE}/memory/genio.db" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as source:
    with sqlite3.connect(dst) as target:
        source.backup(target)
PY
        then
            DB_OK=1
        fi
    fi
    if [ "${DB_OK}" -eq 0 ]; then
        echo "⚠️  ما قدرتش نعمل snapshot متّسق للقاعدة — خذيت نسخة عادية (cp)." >&2
    fi
fi

# عدّ الملفات و الحسابات: المرجع متاع التحقّق بعد الاسترجاع
PY_COUNT="${PY:-python3}"
USERS=$("${PY_COUNT}" - "${STAGE}/memory/genio.db" <<'PY' 2>/dev/null || echo 0
import sqlite3, sys
try:
    with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as conn:
        print(conn.execute("select count(*) from users").fetchone()[0])
except Exception:
    print(0)
PY
)
COMMIT="$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo "-")"

# ملفات WAL/SHM متاع القاعدة ما تتحسبش و ما تتحفظش (مؤقّتة)
rm -f "${STAGE}/memory/genio.db-wal" "${STAGE}/memory/genio.db-shm"

FILES=$({ find "${STAGE}/workspace" "${STAGE}/rag_docs" "${STAGE}/memory" \
    -type f ! -name 'genio.db*' 2>/dev/null || true; } | wc -l | tr -d ' ')

"${PY_COUNT}" - "${STAGE}/manifest.json" "${USERS}" "${FILES}" "${COMMIT}" "${STAMP}" <<'PY'
import json, sys
path, users, files, commit, stamp = sys.argv[1:6]
json.dump(
    {"created_at": stamp, "commit": commit, "users": int(users), "files": int(files),
     "includes": ["config.json", "memory/genio.db", "workspace", "rag_docs"]},
    open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2,
)
PY

tar -czf "${ARCHIVE}" -C "${STAGE}" .
( cd "${DEST}" && sha256sum "$(basename "${ARCHIVE}")" > "$(basename "${ARCHIVE}").sha256" )

SIZE="$(du -h "${ARCHIVE}" | cut -f1)"
echo "✅ نسخة احتياطية: ${ARCHIVE} (${SIZE}) — ${FILES} ملف، ${USERS} حساب، commit ${COMMIT}"

# الاحتفاظ: بالعدد و بالعمر
if [ "${KEEP}" -gt 0 ]; then
    ls -1t "${DEST}"/genio-*.tar.gz 2>/dev/null \
        | tail -n +$((KEEP + 1)) \
        | while read -r old; do
              rm -f "${old}" "${old}.sha256"
              echo "🗑️  حذف (تجاوز ${KEEP} نسخ): $(basename "${old}")"
          done
fi
if [ "${DAYS}" -gt 0 ]; then
    find "${DEST}" -name 'genio-*.tar.gz' -type f -mtime "+${DAYS}" -print -delete | while read -r old; do
        rm -f "${old}.sha256"
        echo "🗑️  حذف (أقدم من ${DAYS} يوم): $(basename "${old}")"
    done
fi
