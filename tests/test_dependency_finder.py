from pathlib import Path

from analyzer.dependency_finder import DependencyFinder


def test_dependency_finder_enriches_routines(tmp_path, fixtures_path):
    project_root = tmp_path / "talend_project"
    routine_src = fixtures_path / "routines" / "StringRoutine.java"
    routine_dst = project_root / "code" / "routines" / routine_src.name
    routine_dst.parent.mkdir(parents=True, exist_ok=True)
    routine_dst.write_text(routine_src.read_text(encoding="utf-8"), encoding="utf-8")

    components = [
        {
            "name": "tJavaFlex",
            "unique_name": "tJavaFlex_1",
            "parameters": {
                "CODE": "StringRoutine.toUpper(row1.name);\nStringRoutine.formatName(\"A\", \"B\");",
            },
        }
    ]
    item_data = {
        "name": "job_with_routines",
        "components": components,
        "connections": [],
        "subjobs": [],
        "project_root": str(project_root),
    }

    dependencies = DependencyFinder(item_data).find_dependencies()

    routines = dependencies["routines"]
    assert len(routines) == 1
    routine = routines[0]
    assert routine["name"] == "StringRoutine"
    assert routine["path"].endswith(str(Path("code/routines") / "StringRoutine.java"))
    method_map = {m["name"]: m for m in routine["methods"]}
    assert set(method_map.keys()) == {"toUpper", "formatName"}
    assert method_map["toUpper"]["signature"] == "public static String toUpper(String input)"
    assert "Met en majuscule" in method_map["toUpper"]["javadoc"]
