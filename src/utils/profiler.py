from __future__ import annotations

import cProfile
from datetime import datetime
import shutil
from pathlib import Path
from typing import Any, Callable, Optional, Tuple
from pstats import Stats

import tornado.template
from snakeviz.main import settings as snakeviz_settings
from snakeviz.stats import json_stats, table_rows


def run_with_profile(name: str, cache_dir: Path, func: Callable[[], Any]) -> Tuple[Any, Path]:
    """Exécute ``func`` avec cProfile et génère un rapport HTML SnakeViz.

    Le rapport et le fichier ``.prof`` sont stockés dans ``cache_dir / profiles``.
    """
    profile_dir = cache_dir / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prof_path = profile_dir / f"{name}_{timestamp}.prof"
    html_path = profile_dir / f"{name}_{timestamp}.html"

    profiler = cProfile.Profile()
    result = profiler.runcall(func)
    profiler.dump_stats(prof_path)

    _render_html_report(prof_path, html_path)
    return result, html_path


def _render_html_report(profile_path: Path, output_path: Path) -> None:
    stats = Stats(str(profile_path))
    loader = tornado.template.Loader(snakeviz_settings["template_path"])
    template = loader.load("viz.html")
    html_bytes = template.generate(
        profile_name=str(profile_path),
        table_rows=table_rows(stats),
        callees=json_stats(stats),
    )
    html_content = html_bytes.decode("utf-8").replace("/static/", "static/")
    output_path.write_text(html_content, encoding="utf-8")
    _copy_static_assets(output_path.parent)


def _copy_static_assets(destination_dir: Path) -> None:
    static_src = Path(snakeviz_settings["static_path"])
    static_dst = destination_dir / "static"
    if static_dst.exists():
        return
    shutil.copytree(static_src, static_dst)


__all__ = ["run_with_profile"]
