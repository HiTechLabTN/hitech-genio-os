"""Fixtures partagées — brique de vérification de la Phase 0 / Sprint 0."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Les tests pilotent la sécurité par variables d'environnement : on part propre.
for _var in ("GENIO_API_TOKEN", "GENIO_HOST", "GENIO_ENABLE_SHELL", "GENIO_ENABLE_UPDATE"):
    os.environ.pop(_var, None)


@pytest.fixture(scope="session")
def server():
    """Importe l'application FastAPI réelle (engine + routes)."""
    import web.server as server_module

    return server_module


@pytest.fixture()
def loopback(server):
    """Client dont l'IP source est 127.0.0.1."""
    from starlette.testclient import TestClient

    return TestClient(server.app, client=("127.0.0.1", 50000))


@pytest.fixture()
def remote(server):
    """Client dont l'IP source est publique (simule Internet)."""
    from starlette.testclient import TestClient

    return TestClient(server.app, client=("203.0.113.5", 50000))
