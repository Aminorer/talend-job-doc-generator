import io
import shutil
from pathlib import Path

from rich.console import Console

from main import CLIContext, load_config, run_batch


def _build_context(tmp_path: Path, workers: int = 12) -> CLIContext:
    config = load_config()
    generator_cfg = config.setdefault("generator", {})
    generator_cfg["output_dir"] = str(tmp_path / "output")
    return CLIContext(
        config=config,
        console=Console(file=io.StringIO(), color_system=None, force_terminal=False),
        verbose=False,
        quiet=True,
        workers=workers,
        output_format="json",
    )


def _copy_job(index: int, target_dir: Path, fixtures_dir: Path) -> None:
    job_dir = target_dir / f"job_{index}"
    job_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixtures_dir / "sample_job.item", job_dir / f"job_{index}.item")
    shutil.copy(fixtures_dir / "sample_job.context", job_dir / f"job_{index}.context")


def _prepare_many_jobs(tmp_path: Path, fixtures_dir: Path, count: int = 50) -> Path:
    for idx in range(count):
        _copy_job(idx, tmp_path, fixtures_dir)
    return tmp_path


def test_batch_processing_stays_under_threshold(tmp_path, fixtures_path, isolate_cache):
    jobs_dir = _prepare_many_jobs(tmp_path, fixtures_path)
    ctx = _build_context(tmp_path)

    result = run_batch(jobs_dir, ctx, incremental=False, profile=False)

    assert result.duration_s < 30, f"Traitement trop long ({result.duration_s}s)"
    assert len(result.results) == 50


def test_incremental_batch_skips_unchanged_jobs(tmp_path, fixtures_path, isolate_cache):
    jobs_dir = _prepare_many_jobs(tmp_path, fixtures_path)
    ctx = _build_context(tmp_path)

    first = run_batch(jobs_dir, ctx, incremental=True, profile=False)
    second = run_batch(jobs_dir, ctx, incremental=True, profile=False)

    assert len(first.skipped) == 0
    assert len(second.skipped) == 50
    assert second.duration_s <= first.duration_s
