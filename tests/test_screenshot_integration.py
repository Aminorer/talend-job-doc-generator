from __future__ import annotations

from pathlib import Path

from analyzer.job_analyzer import AnalyzedJob
from generator.markdown_generator import MarkdownGenerator
from generator.pdf_exporter import PDFExporter


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _dummy_job(screenshot_path: Path | None) -> AnalyzedJob:
    return AnalyzedJob(
        raw_item={
            "name": "SampleJob",
            "version": "0.1",
            "job_type": "Standard",
            "contexts": {},
            "components": [],
            "connections": [],
        },
        properties=None,
        contexts=None,
        dependencies={},
        flows={"mermaid": "", "graphviz": ""},
        screenshot_path=str(screenshot_path) if screenshot_path else None,
    )


def test_markdown_includes_screenshot(tmp_path):
    screenshot = tmp_path / "image.png"
    screenshot.write_bytes(b"content")
    generator = MarkdownGenerator(str(TEMPLATES_DIR))

    markdown = generator.generate(_dummy_job(screenshot), "desc", "job_compact.md")

    assert f"![" in markdown
    assert screenshot.as_posix() in markdown


def test_pdf_exporter_embeds_screenshot(tmp_path):
    screenshot = tmp_path / "image.png"
    screenshot.write_bytes(b"binary")
    exporter = PDFExporter(str(tmp_path))

    html_cover = exporter._cover_html({"name": "Job", "version": "1.0", "author": "Ada"}, {}, str(screenshot))
    assert "data:image/png;base64" in html_cover
    assert "Job" in html_cover
