"""الـ venv ما يبقاش مربوط بـ ./venv — يتبع الـ mount (sshfs/noexec) — 2026-11-16.

`./venv/bin/python` على sshfs يعطي:
    failed to map segment from shared object
خاطر nosuid/nodev/noexec. الحل: مسار الـ venv يختارو سكريبت، والـ Makefile يتبعو.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "venv_path.sh"
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _path(env=None):
    merged = dict(os.environ)
    merged.pop("GENIO_VENV", None)
    merged.update(env or {})
    result = subprocess.run(
        ["sh", str(SCRIPT)], capture_output=True, text=True, timeout=30, env=merged
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_override_wins():
    assert _path({"GENIO_VENV": "/tmp/genio-custom-venv"}) == "/tmp/genio-custom-venv"


def test_path_is_absolute_and_outside_or_inside_the_repo():
    chosen = Path(_path())
    assert chosen.is_absolute()
    if chosen.parent != ROOT:  # برّا الريبو = noexec
        assert "genio-os" in str(chosen)


def test_makefile_uses_the_script_for_every_target():
    assert "sh scripts/venv_path.sh" in MAKEFILE
    assert "scripts/make_venv.sh" in MAKEFILE
    assert "$(VENV)/bin/$(PY) -m pytest" in MAKEFILE
    # ما عادش خلقة venv مباشرة في الـ target
    assert "$(PY) -m venv $(VENV)" not in MAKEFILE


def test_venv_fallback_script_handles_missing_ensurepip():
    script = (ROOT / "scripts" / "make_venv.sh").read_text(encoding="utf-8")
    assert "--without-pip" in script
    assert "pip --python" in script


def test_readme_documents_the_venue_and_the_count():
    assert "134" in README
    assert "noexec" in README
    assert "make venv" in README
