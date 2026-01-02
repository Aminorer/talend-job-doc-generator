from parser.routine_parser import RoutineParser


def test_routine_parser_extracts_methods(fixtures_path):
    routine_path = fixtures_path / "routines" / "StringRoutine.java"

    info = RoutineParser(str(routine_path)).extract_class_info()

    assert info["name"] == "StringRoutine"
    assert info["package"] == "routines"
    method_map = {m["name"]: m for m in info["methods"]}
    assert "toUpper" in method_map
    assert "formatName" in method_map
    assert method_map["toUpper"]["signature"] == "public static String toUpper(String input)"
    assert "Met en majuscule" in method_map["toUpper"]["javadoc"]
