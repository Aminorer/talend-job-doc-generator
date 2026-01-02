from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

import main
from main import CliError, _render_description
from parser.item_parser import TalendItemParser


@pytest.mark.integration
def test_invalid_item_raises_value_error(fixtures_path: Path) -> None:
    invalid_item = fixtures_path / "jobs" / "job_invalid.item"
    parser = TalendItemParser(str(invalid_item), use_cache=False)
    with pytest.raises(ValueError):
        parser.parse()


@pytest.mark.integration
def test_cli_error_rendering(monkeypatch) -> None:
    console = Console(record=True)
    error = CliError("Problème", suggestion="Utilisez un .item valide.", exit_code=3)
    main._render_error(console, error)
    output = console.export_text()
    assert "Problème" in output
    assert "Suggestion" in output


@pytest.mark.integration
def test_llm_failure_is_handled(monkeypatch) -> None:
    console = Console(record=True)
    monkeypatch.setattr(
        "main.LlamaClient.generate",
        lambda self, prompt, temperature=0.2: (_ for _ in ()).throw(RuntimeError("llm down")),
    )
    description = _render_description({"name": "job_simple"}, "standard", use_llm=True, config={"ollama": {}}, console=console)
    assert "LLM indisponible" in description or "LLM" in console.export_text()


@pytest.mark.integration
def test_ensure_item_path_errors(tmp_path: Path) -> None:
    missing_path = tmp_path / "absent.item"
    with pytest.raises(CliError):
        main._ensure_item_path(missing_path)

    not_item = tmp_path / "file.txt"
    not_item.write_text("content", encoding="utf-8")
    with pytest.raises(CliError):
        main._ensure_item_path(not_item)
