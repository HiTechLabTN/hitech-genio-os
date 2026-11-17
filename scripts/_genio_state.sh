#!/usr/bin/env bash
# دوال مشتركة بين scripts/backup.sh و scripts/restore.sh — تتقرا بـ `source`،
# ماشي تنفيذ. الشرطين لازم يكونو معرّفين قبلها: ROOT (جذر الريبو) و PY.

# بايثون متاع الـ venv وإلا متاع النظام
pick_python() {
    if [ -x "${ROOT}/venv/bin/python" ]; then
        printf '%s' "${ROOT}/venv/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
        printf '%s' "python3"
    fi
}

# عدد الملفات (بلا قاعدة البيانات و ملفاتها المؤقّتة) في workspace/rag_docs/memory
count_files() {
    { find "$1/workspace" "$1/rag_docs" "$1/memory" -type f ! -name 'genio.db*' 2>/dev/null || true; } \
        | wc -l | tr -d ' '
}

# عدد الحسابات من جدول users، ولا -1 كان ما قدرناش نقراو القاعدة
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

# نسخة متّسقة من قاعدة SQLite حتى لو المنصّة تخدم توّا
snapshot_db() {
    [ -f "$1" ] || return 1
    "${PY}" - "$1" "$2" <<'PY'
import sqlite3, sys
with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as source:
    with sqlite3.connect(sys.argv[2]) as target:
        source.backup(target)
PY
}
