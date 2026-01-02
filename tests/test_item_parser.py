import time
from pathlib import Path

import pytest

from parser.item_parser import TalendItemParser
from utils.cache_manager import CacheManager


FIXTURES = Path(__file__).parent / "fixtures"


def test_tmap_parsing_with_variables_and_joins():
    item_file = FIXTURES / "sample_job.item"
    parsed = TalendItemParser(str(item_file)).parse()

    tmap = next(comp for comp in parsed["components"] if comp["name"] == "tMap")
    details = tmap["parameters"]["tmap_details"]

    assert len(details["input_tables"]) == 2
    assert details["input_tables"][0]["lookup"]["join_model"] == "Inner Join"
    assert any("lookup1.id" in join["expression"] for join in details["joins"])
    assert any(lookup["mode"] == "LOAD_ONCE" for lookup in details["lookups"])

    assert any(table["name"] == "outMain" for table in details["output_tables"])
    assert details["rejects"] == ["rejects"]

    variable = details["variables"][0]
    assert variable["name"] == "UP_NAME"
    assert "UPCASE" in variable["expression"]

    assert any(mapping["source_table"] == "row1" for mapping in details["mappings"])
    assert details["filters"] == ["row1.active == true"]


def test_basic_job_metadata_and_connections():
    item_file = FIXTURES / "sample_job.item"
    parsed = TalendItemParser(str(item_file)).parse()

    assert parsed["name"] == "sample_job"
    assert parsed["default_context"] == "Default"
    assert parsed["stats"]["nb_components"] == 2

    flow = parsed["connections"][0]
    assert flow["source"] == "tMap_1"
    assert flow["target"] == "tFileOutputDelimited_1"


def test_invalid_extension_raises(tmp_path):
    bad_file = tmp_path / "dummy.txt"
    bad_file.write_text("invalid", encoding="utf-8")
    with pytest.raises(ValueError):
        TalendItemParser(str(bad_file))


def test_cache_hit_and_miss(tmp_path):
    cache_manager = CacheManager(cache_dir=tmp_path, ttl_seconds=3600)
    item_file = FIXTURES / "sample_job.item"

    parser = TalendItemParser(str(item_file), cache_manager=cache_manager)
    parser.parse()

    metrics_after_first = cache_manager.get_metrics()
    assert metrics_after_first["misses"] == 1
    assert metrics_after_first["hits"] == 0

    parser.parse()
    metrics_after_second = cache_manager.get_metrics()
    assert metrics_after_second["hits"] == 1
    assert metrics_after_second["misses"] == 1
    assert metrics_after_second["time_saved_ms"] >= 0


def test_cache_invalidation_on_file_change(tmp_path):
    cache_manager = CacheManager(cache_dir=tmp_path, ttl_seconds=3600)
    tmp_item = tmp_path / "copy.item"
    tmp_item.write_text((FIXTURES / "sample_job.item").read_text(encoding="utf-8"), encoding="utf-8")

    parser = TalendItemParser(str(tmp_item), cache_manager=cache_manager)
    parser.parse()

    # modification du fichier -> nouveau hash -> miss attendu
    tmp_item.write_text(tmp_item.read_text(encoding="utf-8") + "\n<!-- change -->", encoding="utf-8")
    parser = TalendItemParser(str(tmp_item), cache_manager=cache_manager)
    parser.parse()

    metrics = cache_manager.get_metrics()
    assert metrics["misses"] == 2  # deux parse avec fichiers différents (hash modifié)


def test_cache_ttl_expiration(tmp_path, monkeypatch):
    cache_manager = CacheManager(cache_dir=tmp_path, ttl_seconds=1)
    item_file = FIXTURES / "sample_job.item"
    parser = TalendItemParser(str(item_file), cache_manager=cache_manager)
    parser.parse()

    key = cache_manager.compute_md5(item_file)
    # Simule une entrée ancienne pour forcer l'expiration
    old_timestamp = time.time() - 5
    cache_manager._disk_cache[key].timestamp = old_timestamp  # type: ignore[attr-defined]
    cache_manager._memory_cache[key].timestamp = old_timestamp  # type: ignore[attr-defined]

    # L'appel devrait purger et provoquer un miss
    parser.parse()
    metrics = cache_manager.get_metrics()
    assert metrics["misses"] >= 2
