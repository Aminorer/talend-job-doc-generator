"""Analyse des flux de données basés sur les connexions."""
from __future__ import annotations

from typing import Any, Dict, List

from generator.diagram_generator import DiagramGenerator


class FlowAnalyzer:
    def __init__(self, item_data: Dict[str, Any], diagram_type: str = "mermaid", orientation: str = "TD"):
        self.item_data = item_data
        self.diagram_type = diagram_type
        self.orientation = orientation

    def analyze_flows(self) -> Dict[str, Any]:
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
        }
        diagrams = DiagramGenerator(flow_data, orientation=self.orientation).generate(self.diagram_type)
        flow_data.update(diagrams)
        return flow_data


__all__ = ["FlowAnalyzer"]
