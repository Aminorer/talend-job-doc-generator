"""Analyse des flux de données basés sur les connexions."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from generator.diagram_generator import DiagramGenerator

LOGGER = logging.getLogger(__name__)


class FlowAnalyzer:
    def __init__(
        self,
        item_data: Dict[str, Any],
        diagram_type: str = "mermaid",
        orientation: str = "TD",
        output_dir: str = "docs/output",
        graphviz_format: str = "png",
    ):
        self.item_data = item_data
        self.diagram_type = diagram_type
        self.orientation = orientation
        self.output_dir = output_dir
        self.graphviz_format = graphviz_format

    def analyze_flows(self) -> Dict[str, Any]:
        LOGGER.info(
            "Analyse des flux",
            extra={"job_name": self.item_data.get("name"), "connections": len(self.item_data.get("connections", []))},
        )
        flows: List[Dict[str, str]] = []
        for connection in self.item_data.get("connections", []):
            flows.append(
                {
                    "from": connection.get("source", ""),
                    "to": connection.get("target", ""),
                    "label": connection.get("label"),
                    "type": connection.get("connector_name"),
                }
            )
        flow_data = {
            "flows": flows,
            "components": self.item_data.get("components", []),
            "subjobs": self.item_data.get("subjobs", []),
            "job_name": self.item_data.get("name"),
        }
        diagrams = DiagramGenerator(
            flow_data,
            orientation=self.orientation,
            output_dir=self.output_dir,
            graphviz_format=self.graphviz_format,
        ).generate(self.diagram_type)
        flow_data.update(diagrams)
        return flow_data


__all__ = ["FlowAnalyzer"]
