"""هوك `commit-msg` داخل الريبو: حماية هوية الكوميتات على أي clone جديد.

الهوك كان موجود غير على قرص هالجهاز (`~/.local/share/genio-os/hooks`)، فـ
clone جديد كان يبدا بلا حماية. هنا نتحقّقو من النسخة اللي في الريبو: توجد،
تنقّي الإسناد، ما تمسّش نص الرسالة، والسكريبت يربط `core.hooksPath`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".githooks" / "commit-msg"
SETUP = ROOT / "scripts" / "setup_githooks.sh"


def _sh(args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)


def _hook(tmp_path, message: str) -> str:
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(message, encoding="utf-8")
    result = _sh(["sh", str(HOOK), str(msg)])
    assert result.returncode == 0, result.stderr
    return msg.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# الملفات
# ---------------------------------------------------------------------------
def test_hook_lives_in_the_repo_and_is_a_script():
    assert HOOK.is_file(), "ما فمّاش .githooks/commit-msg"
    first = HOOK.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("#!") and "sh" in first
    assert SETUP.is_file(), "ما فمّاش scripts/setup_githooks.sh"


def test_makefile_exposes_a_hooks_target():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "setup_githooks.sh" in makefile
    assert "\nhooks:" in makefile


# ---------------------------------------------------------------------------
# السلوك
# ---------------------------------------------------------------------------
def test_hook_strips_every_attribution_trailer(tmp_path):
    out = _hook(
        tmp_path,
        "feat(i18n): drive the workspace from the catalogue\n"
        "\n"
        "The parked threads now read the shared catalogue.\n"
        "\n"
        "Co-authored-by: Codebuff <noreply@codebuff.com>\n"
        "Signed-off-by: Someone Else <else@example.com>\n"
        "Reviewed-by: Another Person <another@example.com>\n"
        "🤖 Generated with Codebuff\n",
    )
    lowered = out.lower()
    assert "co-authored-by" not in lowered
    assert "signed-off-by" not in lowered
    assert "reviewed-by" not in lowered
    assert "generated with" not in lowered
    assert "codebuff" not in lowered
    assert "someone else" not in lowered


def test_hook_keeps_the_actual_message_intact(tmp_path):
    body = (
        "fix(installer): survive a Python without ensurepip\n"
        "\n"
        "On this machine python3 ships no ensurepip, so the bootstrap was\n"
        "`python3 -m venv --without-pip` plus a system pip.\n"
        "\n"
        "Co-authored-by: Codebuff <noreply@codebuff.com>\n"
    )
    out = _hook(tmp_path, body)
    assert out.startswith("fix(installer): survive a Python without ensurepip")
    assert "`python3 -m venv --without-pip` plus a system pip." in out
    assert out.rstrip().endswith("a system pip."), "الفراغات الزايدة ما تنظّفوش"


def test_hook_leaves_a_clean_message_untouched(tmp_path):
    body = "feat(phase-1): add accounts, sessions and per-user workspaces\n\nThe platform now keeps one session per device.\n"
    assert _hook(tmp_path, body) == body


def test_hook_warns_but_allows_tool_names(tmp_path):
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text("docs: stop shipping Codebuff trailers\n", encoding="utf-8")
    result = _sh(["sh", str(HOOK), str(msg)])
    assert result.returncode == 0
    assert "تنبيه" in result.stderr


# ---------------------------------------------------------------------------
# الربط
# ---------------------------------------------------------------------------
def test_setup_script_points_hooks_path_at_a_working_hook():
    git = ["git", "-c", f"safe.directory={ROOT}"]
    previous = _sh(git + ["config", "--get", "core.hooksPath"], cwd=ROOT).stdout.strip()
    try:
        result = _sh(["sh", str(SETUP)], cwd=ROOT)
        assert result.returncode == 0, result.stderr
        hooks_path = _sh(git + ["config", "--get", "core.hooksPath"], cwd=ROOT).stdout.strip()
        assert hooks_path, "core.hooksPath ما تربطش"
        resolved = Path(hooks_path) if Path(hooks_path).is_absolute() else ROOT / hooks_path
        # عادي: .githooks   |   noexec: نسخة برّا الريبو
        assert (resolved / "commit-msg").is_file(), f"ما فمّاش commit-msg في {resolved}"
        # نفس الهوك متاع الريبو (نسخة ولا ملف مباشر)
        installed = (resolved / "commit-msg").read_text(encoding="utf-8")
        assert installed == HOOK.read_text(encoding="utf-8")
    finally:
        if previous:
            _sh(git + ["config", "core.hooksPath", previous], cwd=ROOT)
        else:
            _sh(git + ["config", "--unset", "core.hooksPath"], cwd=ROOT)


@pytest.mark.skipif(
    not (HOOK.is_file() and (ROOT / ".githooks").is_dir()),
    reason="ما فمّاش .githooks",
)
def test_a_real_commit_gets_the_trailer_removed(tmp_path):
    """end-to-end: git يشغّل الهوك فعليًا و الرسالة تنزل بلا إسناد."""
    repo = tmp_path / "clone"
    repo.mkdir()
    hooks = repo / ".githooks"
    hooks.mkdir()
    hook = hooks / "commit-msg"
    hook.write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
    hook.chmod(0o755)
    if not _sh(["sh", "-c", f"test -x '{hook}'"]).returncode == 0:
        pytest.skip("نظام ملفات بلا exec — الهوك ما ينجّمش يتشغّل هنا")

    git = ["git", "-c", f"safe.directory={tmp_path}"]
    assert _sh(git + ["init", "-q"], cwd=repo).returncode == 0
    _sh(git + ["config", "user.name", "@ZMi HiTech"], cwd=repo)
    _sh(git + ["config", "user.email", "azmi.hitech@gmail.com"], cwd=repo)
    _sh(git + ["config", "core.hooksPath", ".githooks"], cwd=repo)
    (repo / "file.txt").write_text("x\n", encoding="utf-8")
    _sh(git + ["add", "file.txt"], cwd=repo)

    message = "feat: keep the history clean\n\nCo-authored-by: Codebuff <noreply@codebuff.com>\n"
    commit = _sh(git + ["commit", "-q", "-m", message], cwd=repo)
    assert commit.returncode == 0, commit.stderr

    body = _sh(git + ["log", "-1", "--format=%B"], cwd=repo).stdout
    assert "feat: keep the history clean" in body
    assert "co-authored-by" not in body.lower()
    assert "codebuff" not in body.lower()
