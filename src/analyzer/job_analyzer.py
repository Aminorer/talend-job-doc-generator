"""Analyse et enrichissement des données d'un job Talend."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dependency_finder import DependencyFinder
from .flow_analyzer import FlowAnalyzer
from parser.item_parser import TalendItemParser
from utils.file_finder import FileFinder
import logging

LOGGER = logging.getLogger(__name__)

@dataclass
class AnalyzedJob:
    raw_item: Dict[str, Any]
    properties: Optional[Dict[str, str]]
    contexts: Optional[Dict[str, Dict[str, str]]]
    dependencies: Dict[str, Any]
    flows: Dict[str, Any]
    joblets: List[Dict[str, Any]] = field(default_factory=list)
    screenshot_path: Optional[str] = None


class JobAnalyzer:
    """Agrège les différentes sources pour fournir un job enrichi."""

    def __init__(
        self,
        item_data: Dict[str, Any],
        properties_data: Optional[Dict[str, str]] = None,
        context_data: Optional[Dict[str, Dict[str, str]]] = None,
        screenshot_path: Optional[str] = None,
        diagram_type: str = "mermaid",
        diagram_orientation: str = "TD",
        diagram_output_dir: str = "docs/output",
        graphviz_format: str = "png",
    ):
        self.item_data = item_data
        self.properties_data = properties_data
        self.context_data = context_data
        self.screenshot_path = screenshot_path
        self.diagram_type = diagram_type
        self.diagram_orientation = diagram_orientation
        self.diagram_output_dir = diagram_output_dir
        self.graphviz_format = graphviz_format

    def analyze(self) -> AnalyzedJob:
        LOGGER.info("Analyse du job", extra={"job_name": self.item_data.get("name")})
        dependency_finder = DependencyFinder(self.item_data)
        dependencies = dependency_finder.find_dependencies()

        flow_analyzer = FlowAnalyzer(
            self.item_data,
            diagram_type=self.diagram_type,
            orientation=self.diagram_orientation,
            output_dir=self.diagram_output_dir,
            graphviz_format=self.graphviz_format,
        )
        flows = flow_analyzer.analyze_flows()
        joblets_data = self._load_joblets(dependencies)

        LOGGER.info(
            "Analyse terminée",
            extra={
                "job_name": self.item_data.get("name"),
                "nb_dependencies": sum(len(v) for v in dependencies.values() if isinstance(v, list)),
            },
        )
        return AnalyzedJob(
            raw_item=self.item_data,
            properties=self.properties_data,
            contexts=self.context_data,
            dependencies=dependencies,
            flows=flows,
            joblets=joblets_data,
            screenshot_path=self.screenshot_path,
        )

    @property
    def job_name(self) -> str:
        return self.item_data.get("name") or "Job Talend"

    def output_dir(self, base_dir: str) -> Path:
        return Path(base_dir) / self.job_name

    def _load_joblets(self, dependencies: Dict[str, Any]) -> List[Dict[str, Any]]:
        joblets_used = dependencies.get("joblets") or []
        project_root = self.item_data.get("project_root")
        if not project_root or not joblets_used:
            return []

        finder = FileFinder(str(project_root))
        joblet_files = finder.find_joblets()
        if not joblet_files:
            return []

        parsed_joblets: Dict[str, Dict[str, Any]] = {}
        for joblet_path in joblet_files:
            try:
                parsed = TalendItemParser(str(joblet_path), use_cache=True).parse()
            except Exception:  # pylint: disable=broad-except
                LOGGER.warning("Impossible de parser le joblet", extra={"path": str(joblet_path)}, exc_info=True)
                continue
            flow_data = FlowAnalyzer(
                parsed,
                diagram_type="mermaid",
                orientation=self.diagram_orientation,
                output_dir=self.diagram_output_dir,
                graphviz_format=self.graphviz_format,
            ).analyze_flows()
            details = {
                "name": parsed.get("name") or joblet_path.stem,
                "version": parsed.get("version"),
                "path": str(joblet_path),
                "joblet_parameters": parsed.get("joblet_parameters", {"inputs": [], "outputs": []}),
                "flows": flow_data,
                "components": parsed.get("components", []),
            }
            parsed_joblets[details["name"].lower()] = details
            parsed_joblets[joblet_path.stem.lower()] = details

        enriched: List[Dict[str, Any]] = []
        for joblet in joblets_used:
            lookup_keys = [joblet.get("name"), joblet.get("unique_name")]
            parsed = None
            for key in lookup_keys:
                if key and key.lower() in parsed_joblets:
                    parsed = parsed_joblets[key.lower()]
                    break
            enriched.append(
                {
                    "name": parsed.get("name") if parsed else joblet.get("name"),
                    "unique_name": joblet.get("unique_name"),
                    "version": joblet.get("version") or (parsed.get("version") if parsed else None),
                    "path": parsed.get("path") if parsed else None,
                    "joblet_parameters": parsed.get("joblet_parameters") if parsed else {"inputs": [], "outputs": []},
                    "flows": parsed.get("flows") if parsed else {"mermaid": "", "graphviz": ""},
                }
            )
        return enriched


__all__ = ["JobAnalyzer", "AnalyzedJob"]
