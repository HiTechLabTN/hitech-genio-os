"""Vérification de update_genio.sh — Plan v1 المرحلة 0.

المطلوب: ما يبقاش مربوط في /data/genio-os، وياخو GENIO_INSTALL_DIR كيما
الإنسطالور، ويتأكّد إلي الوحدة موجودة قبل الـ restart.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "update_genio.sh"


def _run(install_dir: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GENIO_DRY_RUN": "1",
        "GENIO_INSTALL_DIR": str(install_dir),
        "GENIO_SERVICE": "genio-os-test.service",
    }
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60
    )


def test_script_uses_install_dir_not_a_hardcoded_path():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'INSTALL_DIR="${GENIO_INSTALL_DIR:-/data/genio-os}"' in text
    assert "cd /data/genio-os" not in text
    assert 'cd "${INSTALL_DIR}"' in text


def test_service_is_checked_before_restarting():
    text = SCRIPT.read_text(encoding="utf-8")
    check_at = text.index("systemctl cat")
    restart_at = text.index("systemctl restart")
    assert check_at < restart_at, "لازم فحص الوحدة قبل الـ restart"
    assert "SERVICE_FOUND" in text
    assert "is-active" in text


def test_script_does_not_generate_code_or_push():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "cat << 'EOF'" not in text
    assert "git push" not in text


def test_dry_run_honours_custom_install_dir(tmp_path):
    inst = tmp_path / "opt-genio"
    (inst / ".git").mkdir(parents=True)
    (inst / "config.json").write_text(json.dumps({"port": 9188}), encoding="utf-8")

    result = _run(inst)
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    assert str(inst) in out
    assert "DRY_RUN=1" in out
    assert "/data/genio-os" not in out
    assert "http://127.0.0.1:9188" in out


def test_dry_run_skips_restart_when_service_is_missing(tmp_path):
    inst = tmp_path / "copy"
    inst.mkdir()
    (inst / "config.json").write_text(json.dumps({"port": 8099}), encoding="utf-8")

    result = _run(inst)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ماشي git clone" in result.stdout
    assert "install_genio_os.sh" in result.stdout


def test_missing_install_dir_fails_clearly(tmp_path):
    missing = tmp_path / "nope"
    result = _run(missing)
    assert result.returncode != 0
    assert "ما فمّاش تثبيت" in (result.stdout + result.stderr)
    assert str(missing) in (result.stdout + result.stderr)


def test_port_is_read_from_config_without_jq(tmp_path):
    inst = tmp_path / "inst"
    (inst / ".git").mkdir(parents=True)
    (inst / "config.json").write_text('{\n  "port": 7333\n}\n', encoding="utf-8")

    result = _run(inst)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "7333" in result.stdout
