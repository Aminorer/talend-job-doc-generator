from pathlib import Path

import pytest
from lxml import etree

from parser.tmap_parser import TMapParser, TMapParsingError


FIXTURES = Path(__file__).parent / "fixtures"


def _parse_node(xml: str) -> etree._Element:
    return etree.fromstring(xml.encode("utf-8"))


def test_parses_complete_structure_from_fixture():
    item_file = FIXTURES / "sample_job.item"
    tree = etree.parse(str(item_file))
    root = tree.getroot()
    tmap_node = next(root.iter("node"))

    result = TMapParser(tmap_node, namespaces=root.nsmap).parse()
    details = result.to_dict()

    assert len(details["input_tables"]) == 2
    assert details["input_tables"][0]["lookup"]["mode"] == "LOAD_ONCE"
    assert any(join["type"] in {"INNER", "Inner Join"} for join in details["joins"])
    assert {"table": "row1", "mode": "LOAD_ONCE", "join_model": "Inner Join", "inner_join": False} in details["lookups"]
    assert "row1.active == true" in details["filters"]
    assert any(table["is_reject"] is True for table in details["output_tables"])


def test_mapper_entries_capture_sources_and_targets():
    xml = """
    <node componentName="tMap">
      <elementParameter name="MAP">
        <baseTable>
          <inputTables>
            <table name="main">
              <mapperTableEntries>
                <mapperTableEntry name="id" expression="main.id"/>
              </mapperTableEntries>
            </table>
          </inputTables>
          <outputTables>
            <table name="outMain" isReject="false" rejectInnerJoin="false">
              <mapperTableEntry name="id_out" expression="main.id" input="main" inputColumn="id"/>
            </table>
          </outputTables>
        </baseTable>
      </elementParameter>
    </node>
    """
    result = TMapParser(_parse_node(xml)).parse().to_dict()

    input_mapping = next(m for m in result["mappings"] if m["target_table"] == "main")
    assert input_mapping["source_table"] == "main"
    assert input_mapping["target_column"] == "id"

    output_mapping = next(m for m in result["mappings"] if m["target_table"] == "outMain")
    assert output_mapping["source_table"] == "main"
    assert output_mapping["source_column"] == "id"
    assert output_mapping["target_column"] == "id_out"


def test_variables_with_nullable_and_types():
    xml = """
    <node componentName="tMap">
      <elementParameter name="MAP">
        <baseTable>
          <varTables>
            <varTable name="Var">
              <mapperTableEntries>
                <mapperTableEntry name="FLAG" expression="row1.id &gt; 0" type="id_Boolean" nullable="false"/>
              </mapperTableEntries>
            </varTable>
          </varTables>
        </baseTable>
      </elementParameter>
    </node>
    """
    result = TMapParser(_parse_node(xml)).parse()

    assert len(result.variables) == 1
    assert result.variables[0].name == "FLAG"
    assert result.variables[0].nullable is False
    assert result.variables[0].type == "id_Boolean"


def test_output_filters_and_rejects():
    xml = """
    <node componentName="tMap">
      <elementParameter name="MAP">
        <baseTable>
          <outputTables>
            <table name="clean" isReject="false" rejectInnerJoin="false">
              <filterCondition expression="row1.valid == true"/>
            </table>
            <table name="rejects" isReject="true" rejectInnerJoin="true">
              <filterCondition expression="row1.valid == false"/>
            </table>
          </outputTables>
        </baseTable>
      </elementParameter>
    </node>
    """
    details = TMapParser(_parse_node(xml)).parse().to_dict()

    assert "row1.valid == true" in details["filters"]
    assert "row1.valid == false" in details["filters"]
    assert details["rejects"] == ["rejects"]


def test_missing_map_parameter_raises_error():
    xml = "<node componentName='tMap'></node>"
    with pytest.raises(TMapParsingError):
        TMapParser(_parse_node(xml)).parse()
