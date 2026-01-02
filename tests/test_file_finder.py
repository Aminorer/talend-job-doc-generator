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
    item_dst = job_dir / item_src.name
    context_dst = context_dir / context_src.name
    item_dst.write_text(item_src.read_text(encoding="utf-8"), encoding="utf-8")
    context_dst.write_text(context_src.read_text(encoding="utf-8"), encoding="utf-8")

    related = FileFinder(str(job_dir)).find_related_files()
    assert related["context"] == context_dst
