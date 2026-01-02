from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from click.testing import CliRunner

import main


@pytest.fixture
def cli_config(tmp_path: Path) -> dict:
    return {
        "generator": {"output_dir": str(tmp_path / "cli_output")},
        "diagrams": {"style": "TD"},
        "logging": {},
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3", "timeout": 2},
    }


@pytest.mark.integration
def test_cli_generate_validate_stats_compare_and_batch(fixtures_path: Path, cli_config: dict, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(main, "load_config", lambda config_path=None: cli_config)

    item_path = fixtures_path / "jobs" / "job_simple.item"
    output_path = cli_config["generator"]["output_dir"]

    generate_result = runner.invoke(
        main.cli,
        ["generate", str(item_path), "--no-llm", "--diagram", "mermaid", "--output", str(Path(output_path) / "cli.md")],
    )
    assert generate_result.exit_code == 0

    validate_result = runner.invoke(main.cli, ["validate", str(item_path)])
    assert validate_result.exit_code == 0

    stats_result = runner.invoke(main.cli, ["stats", str(item_path)])
    assert stats_result.exit_code == 0
    assert "nb_components" in stats_result.stdout

    compare_target = fixtures_path / "jobs" / "job_multiple_contexts.item"
    compare_result = runner.invoke(main.cli, ["compare", str(item_path), str(compare_target)])
    assert compare_result.exit_code == 0
    assert "Comparaison" in compare_result.stdout

    batch_result = runner.invoke(main.cli, ["batch", str(fixtures_path / "jobs")])
    assert batch_result.exit_code == 0
    assert "Résultats batch" in batch_result.stdout


@pytest.mark.integration
def test_cli_watch_uses_fake_watcher(fixtures_path: Path, cli_config: dict, monkeypatch) -> None:
    runner = CliRunner()
    calls = []
    monkeypatch.setattr(main, "load_config", lambda config_path=None: cli_config)

    def fake_generate(item_path: Path, **kwargs):
        calls.append(Path(item_path))
        return {"markdown": Path(cli_config["generator"]["output_dir"]) / "watch.md"}

    monkeypatch.setattr(main, "generate_documentation", fake_generate)

    item_path = fixtures_path / "jobs" / "job_simple.item"

    def fake_watch(path, recursive=True):  # noqa: ARG001
        yield {(1, str(item_path))}

    monkeypatch.setitem(
        sys.modules,
        "watchfiles",
        types.SimpleNamespace(watch=fake_watch),
    )

    watch_result = runner.invoke(main.cli, ["watch", str(item_path.parent)])
    assert watch_result.exit_code == 0
    assert item_path in calls
