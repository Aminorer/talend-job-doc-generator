import json
import time
from pathlib import Path

from utils.cache_manager import CacheManager


def test_cache_manager_persists_with_gzip(tmp_path):
    cache_dir = tmp_path / ".cache"
    manager = CacheManager(cache_dir=cache_dir)

    manager.set("demo", {"foo": "bar"}, duration_ms=12.3)

    assert manager.cache_file.suffix == ".gz"
    assert manager.cache_file.exists()

    reloaded = CacheManager(cache_dir=cache_dir)
    assert reloaded.get("demo") == {"foo": "bar"}


def test_cache_manager_migrates_legacy_cache(tmp_path):
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    legacy_file = cache_dir / "item_cache.json"
    legacy_file.write_text(json.dumps({"old": {"data": {"value": 1}, "timestamp": time.time()}}), encoding="utf-8")

    manager = CacheManager(cache_dir=cache_dir)

    assert manager.get("old") == {"value": 1}
    assert manager.cache_file.exists()
    assert not legacy_file.exists()
