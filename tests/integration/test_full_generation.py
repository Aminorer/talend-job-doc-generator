from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from rich.console import Console

from main import generate_documentation


@pytest.mark.integration
def test_full_generation_pipeline(tmp_path: Path, fixtures_path: Path) -> None:
    config = {
        "generator": {"output_dir": str(tmp_path / "output")},
        "diagrams": {"style": "LR"},
        "pdf": {},
        "logging": {},
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3", "timeout": 2},
    }
    item_path = fixtures_path / "jobs" / "job_tmap_complex.item"

    start = time.perf_counter()
    outputs = generate_documentation(
        item_path,
        template="job_standard.md",
        export_pdf=True,
        detail="exhaustif",
        diagram_type="both",
        use_llm=False,
        output=None,
        no_cache=True,
        console=Console(record=True),
        config=config,
        show_progress=False,
    )
    duration = time.perf_counter() - start

    assert duration < 5, "La génération complète dépasse 5 secondes"

    md_path = outputs["markdown"]
    pdf_path = outputs["pdf"]
    json_path = outputs["raw_json"]

    assert md_path.exists()
    assert pdf_path.exists() and pdf_path.stat().st_size > 0
    assert json_path.exists()

    markdown_content = md_path.read_text(encoding="utf-8")
    assert markdown_content.startswith("# Documentation détaillée - job_tmap_complex")
    assert "Tables d'entrée : row1, lookup1" in markdown_content
    assert "Tables de sortie : out_joined, out_reject" in markdown_content
    assert "Diagramme Mermaid" in markdown_content
    assert "flowchart LR" in markdown_content

    data = json.loads(json_path.read_text(encoding="utf-8"))
    stats = data.get("stats", {})
    assert stats["nb_components"] == 4
    assert stats["nb_connections"] == 3
    assert stats["component_types"].get("tMap") == 1
    assert stats["connection_types"].get("FLOW") == 3
