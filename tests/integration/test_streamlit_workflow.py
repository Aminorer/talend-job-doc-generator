from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, List

import pytest

from llm import llama_client
from ui import streamlit_app


class _NoOpContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Column(_NoOpContext):
    def __init__(self, tracker: List[str]):
        self.tracker = tracker

    def metric(self, *args, **kwargs):
        self.tracker.append(f"metric:{args}")


class FakeStreamlit(_NoOpContext):
    def __init__(self, item_path: Path, tracker: List[str]):
        self.item_path = str(item_path)
        self.tracker = tracker
        self.sidebar = self

    # Layout helpers -------------------------------------------------
    def tabs(self, labels: Iterable[str]):
        return [_NoOpContext() for _ in labels]

    def columns(self, number: int):
        return [_Column(self.tracker) for _ in range(number)]

    def expander(self, *args, **kwargs):
        return _NoOpContext()

    # Inputs ---------------------------------------------------------
    def selectbox(self, label: str, options: List[Any], index: int = 0):  # noqa: ARG002
        if "Niveau de détail" in label:
            return "standard"
        if "diagramme" in label:
            return "mermaid"
        if "Niveau minimum" in label:
            return "INFO"
        return options[index]

    def checkbox(self, label: str, value: bool = False):  # noqa: ARG002
        if "LLM" in label:
            return False
        if "Rafraîchissement automatique" in label:
            return False
        return value

    def slider(self, label: str, min_value: int, max_value: int, value: int, step: int):  # noqa: ARG002
        return value

    def text_input(self, label: str, value: str = ""):  # noqa: ARG002
        return self.item_path if value == "" else value

    def button(self, label: str, *args, **kwargs):  # noqa: ARG002
        return label == "Générer la documentation"

    # Outputs --------------------------------------------------------
    def set_page_config(self, *args, **kwargs):
        self.tracker.append("set_page_config")

    def title(self, *args, **kwargs):
        self.tracker.append("title")

    def write(self, *args, **kwargs):
        self.tracker.append("write")

    def header(self, *args, **kwargs):
        self.tracker.append("header")

    def markdown(self, *args, **kwargs):
        self.tracker.append("markdown")

    def code(self, *args, **kwargs):
        self.tracker.append("code")

    def download_button(self, *args, **kwargs):
        self.tracker.append("download")

    def success(self, *args, **kwargs):
        self.tracker.append("success")

    def error(self, *args, **kwargs):
        self.tracker.append("error")

    def caption(self, *args, **kwargs):
        self.tracker.append("caption")

    def json(self, *args, **kwargs):
        self.tracker.append("json")

    def info(self, *args, **kwargs):
        self.tracker.append("info")

    def experimental_rerun(self, *args, **kwargs):
        self.tracker.append("rerun")


@pytest.mark.integration
def test_streamlit_main_flow(tmp_path: Path, fixtures_path: Path, monkeypatch) -> None:
    tracker: List[str] = []
    item_path = fixtures_path / "jobs" / "job_multiple_contexts.item"
    fake_st = FakeStreamlit(item_path, tracker)

    monkeypatch.setattr(streamlit_app, "st", fake_st)
    monkeypatch.setattr(
        streamlit_app,
        "load_config",
        lambda: {
            "generator": {"output_dir": str(tmp_path / "streamlit_output")},
            "diagrams": {"style": "TD"},
            "logging": {"log_dir": str(tmp_path / "logs"), "filename": "app.log"},
            "ollama": {},
        },
    )
    monkeypatch.setattr(streamlit_app, "configure_logging", lambda *_: None)
    dummy_logger = logging.getLogger("streamlit-test")
    dummy_logger.handlers = [logging.NullHandler()]
    dummy_logger.propagate = False
    monkeypatch.setattr(streamlit_app, "get_logger", lambda *args, **kwargs: dummy_logger)
    monkeypatch.setattr(
        llama_client.LlamaClient,
        "generate",
        lambda self, prompt, temperature=0.2: "Résumé simulé",
    )
    monkeypatch.setattr(streamlit_app, "time", SimpleNamespace(sleep=lambda *_: None))

    streamlit_app.main()

    output_dir = Path(tmp_path / "streamlit_output")
    md_files = list(output_dir.glob("*.md"))
    assert md_files, "Aucun fichier Markdown généré par le workflow Streamlit"
    content = md_files[0].read_text(encoding="utf-8")
    assert "job_multiple_contexts" in content
    assert "Contextes" in content
    assert "flowchart TD" in content

    assert "success" in tracker
    assert "markdown" in tracker
