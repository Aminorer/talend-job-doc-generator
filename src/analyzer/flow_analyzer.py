"""Analyse des flux de données basés sur les connexions."""
from __future__ import annotations

from typing import Any, Dict, List

from generator.diagram_generator import DiagramGenerator


class FlowAnalyzer:
    def __init__(self, item_data: Dict[str, Any]):
        self.item_data = item_data

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
        diagram = DiagramGenerator(flow_data).generate_mermaid()
        flow_data["mermaid"] = diagram
        return flow_data


__all__ = ["FlowAnalyzer"]
