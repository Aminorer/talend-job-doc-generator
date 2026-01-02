from pathlib import Path

from analyzer.job_analyzer import JobAnalyzer
from generator.markdown_generator import MarkdownGenerator
from parser.item_parser import TalendItemParser

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PROJECT_ROOT / "templates"


def test_job_analyzer_includes_joblets(tmp_path, fixtures_path):
    project_root = tmp_path / "talend_project"
    job_dir = project_root / "process"
    joblets_dir = job_dir / "Joblets"
    job_dir.mkdir(parents=True, exist_ok=True)
    joblets_dir.mkdir(parents=True, exist_ok=True)

    job_src = fixtures_path / "jobs" / "job_with_joblet.item"
    job_dst = job_dir / job_src.name
    job_dst.write_text(job_src.read_text(encoding="utf-8"), encoding="utf-8")

    joblet_src = fixtures_path / "joblets" / "EmailSender.item"
    joblet_dst = joblets_dir / joblet_src.name
    joblet_dst.write_text(joblet_src.read_text(encoding="utf-8"), encoding="utf-8")

    parsed_job = TalendItemParser(str(job_dst)).parse()
    parsed_job["project_root"] = str(project_root)

    analyzer = JobAnalyzer(
        parsed_job,
        properties_data=None,
        context_data=None,
        screenshot_path=None,
        diagram_type="mermaid",
        diagram_orientation="LR",
        diagram_output_dir=str(tmp_path / "diagrams"),
    )
    analyzed = analyzer.analyze()

    assert analyzed.joblets
    joblet = analyzed.joblets[0]
    assert joblet["name"] == "EmailSender"
    assert joblet["joblet_parameters"]["inputs"] == ["IncomingEmail"]
    assert joblet["joblet_parameters"]["outputs"] == ["OutgoingStatus"]
    assert joblet["flows"]["mermaid"].startswith("flowchart")

    markdown = MarkdownGenerator(str(TEMPLATES)).generate(analyzed, "Description courte", "job_standard.md")
    assert "Joblets utilisés" in markdown
    assert "IncomingEmail" in markdown
