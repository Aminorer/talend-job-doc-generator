"""Analyse et enrichissement des données d'un job Talend."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dependency_finder import DependencyFinder
from .flow_analyzer import FlowAnalyzer


@dataclass
class AnalyzedJob:
    raw_item: Dict[str, Any]
    properties: Optional[Dict[str, str]]
    contexts: Optional[Dict[str, Dict[str, str]]]
    dependencies: Dict[str, List[str]]
    flows: Dict[str, Any]


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

        return AnalyzedJob(
            raw_item=self.item_data,
            properties=self.properties_data,
            contexts=self.context_data,
            dependencies=dependencies,
            flows=flows,
        )

    @property
    def job_name(self) -> str:
        return self.item_data.get("name") or "Job Talend"

    def output_dir(self, base_dir: str) -> Path:
        return Path(base_dir) / self.job_name


__all__ = ["JobAnalyzer", "AnalyzedJob"]
