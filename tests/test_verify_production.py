"""سكريبت تحقّق الإنتاج: لازم يفرّق بين المتزامن و الماشي، و يرجّع exit code صحيح."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_production.sh"


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", f"safe.directory={cwd}", *args], cwd=cwd, capture_output=True, text=True
    )


def _sh(args, cwd=ROOT, env=None):
    return subprocess.run(["sh", *args], cwd=cwd, env=env, capture_output=True, text=True)


def _repo(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "@ZMi HiTech")
    _git(path, "config", "user.email", "azmi.hitech@gmail.com")
    # الملفات الحرجة اللي السكريبت يتحقّق منها
    for rel in (
        "core/proxy.py",
        "web/server.py",
        "web/static/index.html",
        "scripts/setup_githooks.sh",
        ".githooks/commit-msg",
    ):
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# placeholder\n", encoding="utf-8")
    # علامات قاعدة الثقة بالـ Cloudflare headers (السكريبت يتحقّق منها)
    (path / "core" / "security.py").write_text(
        "INTERNAL_NETWORKS = ()\ndef cloudflare_evidence(request):\n    return False\n",
        encoding="utf-8",
    )
    (path / "file.txt").write_text("one\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "first")
    return path


def test_script_and_make_target_exist():
    assert SCRIPT.is_file()
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "\nverify-prod:" in makefile
    assert "verify_production.sh" in makefile


def test_script_covers_every_required_check():
    body = SCRIPT.read_text(encoding="utf-8")
    for needle in (
        "origin/main",
        "/api/status",
        "api/i18n",
        "x-accel-buffering",
        "no-cache",
        "Secure",
        "login_attempts",
        "cloudflareaccess",
        "CF-Connecting-IP",
        "X-Forwarded-Proto",
    ):
        assert needle in body, needle


def test_code_only_passes_when_head_matches_origin(tmp_path):
    repo = _repo(tmp_path / "clone")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    result = _sh([str(SCRIPT), "--code-only"], cwd=repo, env={"GENIO_INSTALL_DIR": str(repo), "PATH": "/usr/bin:/bin"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "HEAD = origin/main" in result.stdout


def test_code_only_fails_when_the_trust_rule_is_missing(tmp_path):
    """كود قديم في /data/genio-os = 403 على الدومين: لازم يتفشّ

    """
    repo = _repo(tmp_path / "clone")
    (repo / "core" / "security.py").write_text("# نسخة قديمة\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old security")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    result = _sh([str(SCRIPT), "--code-only"], cwd=repo, env={"GENIO_INSTALL_DIR": str(repo), "PATH": "/usr/bin:/bin"})
    assert result.returncode == 1
    assert "core/security.py قديم" in result.stdout


def test_code_only_fails_when_the_server_is_behind(tmp_path):
    repo = _repo(tmp_path / "clone")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    (repo / "file.txt").write_text("two\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "second")  # HEAD ولّى قدام origin/main

    result = _sh([str(SCRIPT), "--code-only"], cwd=repo, env={"GENIO_INSTALL_DIR": str(repo), "PATH": "/usr/bin:/bin"})
    assert result.returncode == 1, result.stdout
    assert "ماشي متزامن" in result.stdout
    assert "update_genio.sh" in result.stdout


def test_missing_installation_fails(tmp_path):
    result = _sh([str(SCRIPT), "--code-only"], env={"GENIO_INSTALL_DIR": str(tmp_path / "roh"), "PATH": "/usr/bin:/bin"})
    assert result.returncode == 1
    assert "ما فمّاش ريبو git" in result.stdout


def test_unknown_argument_exits_2():
    result = _sh([str(SCRIPT), "--nope"])
    assert result.returncode == 2
