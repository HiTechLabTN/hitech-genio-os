"""النسخ الاحتياطي و الاسترجاع: الأرشيف، الاحتفاظ، و التحقّق بالعدد.

النسخة لازم تحتوي قاعدة البيانات (memory/genio.db) + workspace + rag_docs،
و الاسترجاع لازم يثبت إن عدد الملفات و عدد الحسابات مطابقين للـ manifest.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "scripts" / "backup.sh"
RESTORE = ROOT / "scripts" / "restore.sh"


def _sh(script: Path, *args, env=None):
    return subprocess.run(
        ["bash", str(script), *args], capture_output=True, text=True, env=env
    )


def _data_dir(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    (data / "memory").mkdir(parents=True)
    (data / "workspace" / "proj").mkdir(parents=True)
    (data / "rag_docs").mkdir(parents=True)
    (data / "config.json").write_text('{"version": "9.0.0"}\n', encoding="utf-8")
    for i in range(3):
        (data / "workspace" / "proj" / f"file{i}.txt").write_text(f"x{i}\n", encoding="utf-8")
    (data / "rag_docs" / "doc.md").write_text("# doc\n", encoding="utf-8")
    (data / "memory" / "playbook.jsonl").write_text("{}\n", encoding="utf-8")

    db = data / "memory" / "genio.db"
    conn = sqlite3.connect(db)
    conn.execute("create table users (id integer primary key, email text)")
    conn.executemany(
        "insert into users (email) values (?)",
        [("owner@hitech.tn",), ("member@hitech.tn",), ("viewer@hitech.tn",)],
    )
    conn.commit()
    conn.close()
    return data


def _env(data: Path, **extra) -> dict:
    env = dict(os.environ)
    env.update({"GENIO_DATA_DIR": str(data)})
    env.update({k: str(v) for k, v in extra.items()})
    return env


def test_backup_contains_database_workspace_and_rag(tmp_path):
    data = _data_dir(tmp_path)
    result = _sh(BACKUP, env=_env(data))
    assert result.returncode == 0, result.stderr
    archives = sorted((data / "backups").glob("genio-*.tar.gz"))
    assert len(archives) == 1
    assert Path(str(archives[0]) + ".sha256").exists()

    with tarfile.open(archives[0]) as tar:
        names = tar.getnames()
    assert any(n.endswith("memory/genio.db") for n in names)
    assert any(n.endswith("workspace/proj/file1.txt") for n in names)
    assert any(n.endswith("rag_docs/doc.md") for n in names)
    assert any(n.endswith("config.json") for n in names)

    with tarfile.open(archives[0]) as tar:
        member = next(n for n in tar.getnames() if n.endswith("manifest.json"))
        manifest = json.load(tar.extractfile(member))
    assert manifest["users"] == 3
    # 3 workspace + 1 rag + 1 memory/playbook.jsonl (القاعدة محسوبة بالحسابات)


def test_backup_snapshot_is_a_working_sqlite_file(tmp_path):
    data = _data_dir(tmp_path)
    assert _sh(BACKUP, env=_env(data)).returncode == 0
    archive = sorted((data / "backups").glob("genio-*.tar.gz"))[-1]

    out = tmp_path / "peek"
    out.mkdir()
    with tarfile.open(archive) as tar:
        member = next(n for n in tar.getnames() if n.endswith("memory/genio.db"))
        tar.extract(member, out)

    db = next(out.rglob("genio.db"))
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    assert conn.execute("select count(*) from users").fetchone()[0] == 3
    conn.close()


def test_retention_keeps_only_the_requested_number(tmp_path):
    data = _data_dir(tmp_path)
    for _ in range(3):
        assert _sh(BACKUP, env=_env(data, GENIO_BACKUP_KEEP=2)).returncode == 0
        # نضمنو اسم مختلف لكل نسخة
        subprocess.run(["sleep", "1.05"], check=False)
    archives = sorted((data / "backups").glob("genio-*.tar.gz"))
    assert len(archives) == 2


def test_restore_verifies_file_and_account_counts(tmp_path):
    data = _data_dir(tmp_path)
    assert _sh(BACKUP, env=_env(data)).returncode == 0
    target = tmp_path / "restored"

    result = _sh(RESTORE, "--from", "latest", "--into", str(target), env=_env(data))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "عدد الملفات مطابق" in result.stdout
    assert "عدد الحسابات مطابق" in result.stdout

    assert (target / "workspace" / "proj" / "file2.txt").read_text(encoding="utf-8") == "x2\n"
    conn = sqlite3.connect(f"file:{target / 'memory' / 'genio.db'}?mode=ro", uri=True)
    assert conn.execute("select count(*) from users").fetchone()[0] == 3
    conn.close()


def test_restore_refuses_a_non_empty_target_without_force(tmp_path):
    data = _data_dir(tmp_path)
    assert _sh(BACKUP, env=_env(data)).returncode == 0
    target = tmp_path / "busy"
    target.mkdir()
    (target / "keep.txt").write_text("do not touch\n", encoding="utf-8")

    blocked = _sh(RESTORE, "--from", "latest", "--into", str(target), env=_env(data))
    assert blocked.returncode == 2
    assert (target / "keep.txt").exists()

    forced = _sh(RESTORE, "--from", "latest", "--into", str(target), "--force", env=_env(data))
    assert forced.returncode == 0, forced.stdout + forced.stderr


def test_restore_rejects_a_corrupt_archive(tmp_path):
    data = _data_dir(tmp_path)
    assert _sh(BACKUP, env=_env(data)).returncode == 0
    archive = sorted((data / "backups").glob("genio-*.tar.gz"))[-1]
    archive.write_bytes(b"not a tarball")

    result = _sh(RESTORE, "--from", str(archive), "--into", str(tmp_path / "x"), env=_env(data))
    assert result.returncode == 1
    assert "ما يتقراش" in result.stdout + result.stderr or "sha256" in result.stdout + result.stderr


def test_dry_run_writes_nothing(tmp_path):
    data = _data_dir(tmp_path)
    assert _sh(BACKUP, env=_env(data)).returncode == 0
    target = tmp_path / "dry"

    result = _sh(RESTORE, "--from", "latest", "--into", str(target), "--dry-run", env=_env(data))
    assert result.returncode == 0, result.stdout + result.stderr
    assert not target.exists()


def test_units_exist_and_point_at_the_production_directory():
    service = (ROOT / "deployment" / "genio-backup.service").read_text(encoding="utf-8")
    timer = (ROOT / "deployment" / "genio-backup.timer").read_text(encoding="utf-8")
    assert "GENIO_DATA_DIR=/data/genio-os" in service
    assert "scripts/backup.sh" in service
    assert "OnCalendar=*-*-* 03:30:00" in timer
    assert "Persistent=true" in timer
