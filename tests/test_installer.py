"""Vérification du contrat d'installation — Plan v1 §3.1 / §6 المرحلة 0.

الحاجة اللي نحميوها: `clone + install` ما يرجّعش v5.
يعني السكريبت ما يولّدش كود، وما يعملش git push، وينسخ الملفات كيما هي.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "install_genio_os.sh"


def _run_dry(install_dir: Path) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GENIO_DRY_RUN": "1",
        "GENIO_INSTALL_DIR": str(install_dir),
        "GENIO_PORT": "8123",
    }
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_installer_contains_no_code_generation():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "cat << 'EOF' >" not in text
    assert "\"${INSTALL_DIR}/core/engine.py\"\n" not in text.replace("cp ", "")
    # لا يوجد أي heredoc للكود القديم
    assert text.count("cat <<") <= 1  # فقط heredoc الخاص بـ config.json المحتمل
    assert "git push" not in text
    assert "git add" not in text


def test_installer_does_not_embed_the_old_engine():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "AGENTS_REGISTRY = {" not in text
    assert "class GenioEngine" not in text
    assert "Singularity" not in text


def test_installer_has_a_fallback_for_missing_ensurepip():
    """Debian بلا python3-venv: لازم fallback بلا ensurepip."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--without-pip" in text
    assert "pip --python" in text
    assert "python3-venv" in text


def test_unknown_flag_is_rejected():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--nope"], capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0
    assert "خيار غير معروف" in (result.stdout + result.stderr)


def test_no_service_flag_is_supported():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--no-service" in text
    assert "GENIO_SKIP_SYSTEMD" in text


def test_dry_run_copies_repo_code_verbatim(tmp_path):
    result = _run_dry(tmp_path / "inst")
    assert result.returncode == 0, result.stdout + result.stderr

    inst = tmp_path / "inst"
    for relative in ("core/engine.py", "web/server.py", "web/static/index.html"):
        assert (inst / relative).read_text(encoding="utf-8") == (
            ROOT / relative
        ).read_text(encoding="utf-8"), relative

    # الكود المنسوخ هو النسخة الحالية، ماشي v5
    engine = (inst / "core/engine.py").read_text(encoding="utf-8")
    assert "workspace_override" in engine          # ميزة المرحلة 1
    assert "Singularity" not in engine             # ماركر v5 القديم
    assert "self_evolving_ledger" not in engine


def test_dry_run_writes_safe_config(tmp_path):
    result = _run_dry(tmp_path / "inst")
    assert result.returncode == 0, result.stdout + result.stderr

    inst = tmp_path / "inst"
    config = json.loads((inst / "config.json").read_text(encoding="utf-8"))
    assert config["security"]["host"] == "127.0.0.1"
    assert config["security"]["enable_shell"] is False
    assert config["security"]["enable_update"] is False
    assert config["port"] == 8123
    # المسارات تتبع INSTALL_DIR ماشي /data/genio-os
    assert config["workspace_dir"] == str(inst / "workspace")
    assert config["rag_dir"] == str(inst / "rag_docs")
    assert config["memory_dir"] == str(inst / "memory")


def test_dry_run_keeps_existing_config(tmp_path):
    inst = tmp_path / "inst"
    inst.mkdir()
    custom = {"port": 9099, "security": {"host": "0.0.0.0", "enable_shell": True}}
    (inst / "config.json").write_text(json.dumps(custom), encoding="utf-8")

    result = _run_dry(inst)
    assert result.returncode == 0, result.stdout + result.stderr

    kept = json.loads((inst / "config.json").read_text(encoding="utf-8"))
    assert kept["port"] == 9099
    assert kept["security"]["host"] == "0.0.0.0"


def test_dry_run_renders_the_service_unit(tmp_path):
    result = _run_dry(tmp_path / "inst")
    assert result.returncode == 0, result.stdout + result.stderr

    unit = tmp_path / "inst" / ".genio-os.service.rendered"
    assert unit.is_file()
    text = unit.read_text(encoding="utf-8")
    assert str(tmp_path / "inst") in text
    assert "/opt/genio-os" not in text
    # المنفذ يتبع GENIO_PORT (8123 هنا) ماشي 8099 متاع الـ template
    assert "--port 8123" in text
    assert "--port 8099" not in text


def test_installer_fails_without_a_repo(tmp_path):
    """كان السكريبت يتشغّل من مجلّد بلا كود، لازم يفشل بوضوح ماشي يولّد v5."""
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    copy = lonely / "install_genio_os.sh"
    copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

    env = {
        **os.environ,
        "GENIO_DRY_RUN": "1",
        "GENIO_INSTALL_DIR": str(tmp_path / "inst"),
    }
    result = subprocess.run(
        ["bash", str(copy)], env=env, capture_output=True, text=True, timeout=60
    )
    assert result.returncode != 0
    assert "الريبو ناقص" in (result.stdout + result.stderr)


def test_check_mode_detects_drift(tmp_path):
    inst = tmp_path / "inst"
    assert _run_dry(inst).returncode == 0

    check = subprocess.run(
        ["bash", str(SCRIPT), "--check"],
        env={**os.environ, "GENIO_INSTALL_DIR": str(inst)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert check.returncode == 0, check.stdout + check.stderr

    (inst / "web" / "server.py").write_text("# drifted\n", encoding="utf-8")
    drifted = subprocess.run(
        ["bash", str(SCRIPT), "--check"],
        env={**os.environ, "GENIO_INSTALL_DIR": str(inst)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert drifted.returncode != 0
    assert "يختلف" in drifted.stdout
