from __future__ import annotations

import time
from pathlib import Path

import pytest

from parser.item_parser import TalendItemParser
from utils.cache_manager import CacheManager


@pytest.mark.integration
def test_cache_hit_miss_and_invalidation(tmp_path: Path, fixtures_path: Path, monkeypatch) -> None:
    cache_dir = tmp_path / ".cache"
    cache_manager = CacheManager(cache_dir=cache_dir, ttl_seconds=60)
    monkeypatch.setattr("parser.item_parser.get_cache_manager", lambda: cache_manager)

    item = fixtures_path / "jobs" / "job_simple.item"
    parser = TalendItemParser(str(item), cache_manager=cache_manager, use_cache=True)

    cache_manager.clear()
    start = time.perf_counter()
    first_parse = parser.parse()
    first_duration = time.perf_counter() - start
    assert cache_manager.metrics["misses"] == 1
    assert first_parse["stats"]["nb_components"] == 3

    start = time.perf_counter()
    second_parse = parser.parse()
    second_duration = time.perf_counter() - start
    assert cache_manager.metrics["hits"] == 1
    assert second_parse == first_parse
    assert second_duration <= first_duration

    mutated = tmp_path / "job_simple_mutated.item"
    mutated.write_text(item.read_text(encoding="utf-8") + "\n<!-- mutation -->", encoding="utf-8")
    mutated_parser = TalendItemParser(str(mutated), cache_manager=cache_manager, use_cache=True)
    mutated_parser.parse()
    assert cache_manager.metrics["misses"] == 2

    cache_manager.clear()
    assert cache_manager.metrics["hits"] == 0
    assert cache_manager.metrics["misses"] == 0
