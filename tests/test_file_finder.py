from pathlib import Path

from utils.file_finder import FileFinder


FIXTURES = Path(__file__).parent / "fixtures"


def test_finder_picks_context_from_directory(tmp_path):
    job_dir = tmp_path / "job"
    context_dir = job_dir / "context"
    job_dir.mkdir()
    context_dir.mkdir()

    item_src = FIXTURES / "sample_job.item"
    context_src = FIXTURES / "sample_job.context"
    screenshot_src = FIXTURES / "sample_job.screenshot"
    item_dst = job_dir / item_src.name
    context_dst = context_dir / context_src.name
    screenshot_dst = job_dir / screenshot_src.name
    item_dst.write_text(item_src.read_text(encoding="utf-8"), encoding="utf-8")
    context_dst.write_text(context_src.read_text(encoding="utf-8"), encoding="utf-8")
    screenshot_dst.write_text(screenshot_src.read_text(encoding="utf-8"), encoding="utf-8")

    related = FileFinder(str(job_dir), screenshot_output_dir=str(tmp_path / "screens")).find_related_files()
    assert related["context"] == context_dst
    assert related["screenshot"] is not None
    assert related["screenshot"].exists()
    assert related["screenshot"].parent == tmp_path / "screens"


def test_find_joblets_from_project_root(tmp_path, fixtures_path):
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

    joblets = FileFinder(str(job_dst)).find_joblets()
    assert joblets == [joblet_dst]
