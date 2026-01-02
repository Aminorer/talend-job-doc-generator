from pathlib import Path

import pytest

from parser.item_parser import TalendItemParser


FIXTURES = Path(__file__).parent / "fixtures"


def test_tmap_parsing_with_variables_and_joins():
    item_file = FIXTURES / "sample_job.item"
    parsed = TalendItemParser(str(item_file)).parse()

    tmap = next(comp for comp in parsed["components"] if comp["name"] == "tMap")
    details = tmap["parameters"]["tmap_details"]

    assert len(details["input_tables"]) == 2
    assert details["input_tables"][0]["join_model"] == "Inner Join"
    assert any("lookup1.id" in join["expression"] for join in details["joins"])
    assert {"table": "row1", "mode": "LOAD_ONCE"} in details["lookups"]

    assert {"name": "outMain", "is_reject": False, "reject_inner_join": False} in details["output_tables"]
    assert details["rejects"] == ["rejects"]

    variable = details["variables"][0]
    assert variable["name"] == "UP_NAME"
    assert "UPCASE" in variable["expression"]

    assert any(mapping["input"].startswith("row1.") for mapping in details["mappings"])
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
