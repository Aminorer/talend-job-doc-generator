"""Génération de diagrammes Mermaid à partir des flux."""
from __future__ import annotations

from typing import Any, Dict, List


class DiagramGenerator:
    def __init__(self, flow_data: Dict[str, Any], orientation: str = "TD"):
        self.flow_data = flow_data
        self.orientation = orientation

    def generate_mermaid(self) -> str:
        lines: List[str] = [f"flowchart {self.orientation}"]
        components = {c.get("unique_name", c.get("name")): c for c in self.flow_data.get("components", [])}
        for comp_id, comp in components.items():
            label = comp.get("name", comp_id)
            lines.append(f"  {self._normalize_id(comp_id)}[{label}]")

        for flow in self.flow_data.get("flows", []):
            source = self._normalize_id(flow.get("from", ""))
            target = self._normalize_id(flow.get("to", ""))
            label = flow.get("label") or flow.get("type") or ""
            connector = f" --|{label}|--> " if label else " --> "
            lines.append(f"  {source}{connector}{target}")
        return "\n".join(lines)

    def _normalize_id(self, value: str) -> str:
        sanitized = value.replace("-", "_").replace(" ", "_")
        return sanitized or "unknown"


__all__ = ["DiagramGenerator"]
