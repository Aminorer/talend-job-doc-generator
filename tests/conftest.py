import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"

for path in (PROJECT_ROOT, SRC_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from utils import cache_manager  # noqa: E402


def pytest_configure(config):  # noqa: D401
    """Enregistre des marqueurs personnalisés pour les tests d'intégration."""
    config.addinivalue_line("markers", "integration: tests d'intégration end-to-end")


@pytest.fixture(autouse=True)
def isolate_cache(tmp_path, monkeypatch):
    """Réinitialise le cache entre chaque test pour éviter les effets de bord."""
    cache_dir = tmp_path / ".cache"
    manager = cache_manager.CacheManager(cache_dir=cache_dir)
    monkeypatch.setattr(cache_manager, "_DEFAULT_CACHE_MANAGER", manager)
    yield manager
    manager.clear()


@pytest.fixture
def fixtures_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures"
