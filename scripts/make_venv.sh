#!/bin/sh
# إنشاء الـ venv + المتطلّبات، مع fallback كيما الإنسطالور:
# Debian/Ubuntu بلا python3-venv ما عندوش ensurepip، أما pip متاع النظام موجود.
set -eu

venv="${1:?usage: make_venv.sh <venv-path>}"
python="${PYTHON:-python3}"

mkdir -p "$(dirname "$venv")"

if [ ! -x "$venv/bin/python" ]; then
    if "$python" -m venv "$venv" 2>/dev/null; then
        :
    else
        echo "⚠️  python3 -m venv فشل (ensurepip ناقص؟) — نجرّبو --without-pip + pip متاع النظام" >&2
        rm -rf "$venv"
        "$python" -m venv --without-pip "$venv"
        "$python" -m pip --python "$venv/bin/python" install --quiet --upgrade pip
    fi
fi

"$venv/bin/python" -m pip install --quiet --upgrade pip
"$venv/bin/python" -m pip install --quiet -r requirements.txt -r requirements-dev.txt

echo "✅ venv: $venv"
"$venv/bin/python" -V
