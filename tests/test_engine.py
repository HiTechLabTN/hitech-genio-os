"""Vérification du moteur et du modèle de configuration (المرحلة 0)."""

from __future__ import annotations

from core.engine import AGENTS_REGISTRY, GenioEngine


def test_registry_has_six_agents():
    assert len(AGENTS_REGISTRY) == 6
    assert "Genio-Rayes" in AGENTS_REGISTRY
    for agent in AGENTS_REGISTRY.values():
        assert agent["role"].strip()


def test_engine_boots_with_writable_dirs():
    engine = GenioEngine()
    assert engine.workspace.is_dir()
    assert engine.rag_dir.is_dir()


def test_resolve_dir_falls_back_to_repo_local(tmp_path):
    fallback = tmp_path / "workspace"
    resolved = GenioEngine._resolve_dir(None, fallback, "workspace_dir")
    assert resolved == fallback
    assert resolved.is_dir()


def test_resolve_dir_creates_configured_path(tmp_path):
    configured = tmp_path / "custom-workspace"
    resolved = GenioEngine._resolve_dir(str(configured), tmp_path / "fallback", "workspace_dir")
    assert resolved == configured


def test_security_block_survives_reload():
    engine = GenioEngine()
    block = engine.config.get("security") or {}
    assert block.get("host") == "127.0.0.1"
    assert block.get("enable_shell") is False
    assert block.get("enable_update") is False


def test_playbooks_load():
    engine = GenioEngine()
    playbooks = engine.load_playbooks()
    assert isinstance(playbooks, list)
