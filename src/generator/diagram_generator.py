"""Génération de diagrammes Mermaid ou Graphviz à partir des flux."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from graphviz import Digraph
except Exception:  # pragma: no cover
    Digraph = None


LOGGER = logging.getLogger(__name__)

CATEGORY_COLORS = {
    "input": "#3498db",
    "output": "#2ecc71",
    "transform": "#f39c12",
    "log": "#9b59b6",
    "other": "#7f8c8d",
}

CONNECTOR_SYMBOL = {
    "FLOW": "-->",
    "ITERATE": "-.->",
    "REJECT": "-.x->",
}


class DiagramGenerator:
    def __init__(
        self,
        flow_data: Dict[str, Any],
        orientation: str = "TD",
        output_dir: str = "docs/output",
        graphviz_format: str = "png",
    ):
        self.flow_data = flow_data
        self.orientation = orientation
        self.output_dir = Path(output_dir)
        self.graphviz_format = graphviz_format
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, diagram_type: str = "mermaid") -> Dict[str, str]:
        """Génère les diagrammes demandés.

        Args:
            diagram_type: "mermaid", "graphviz" ou "both"
        """
        result: Dict[str, str] = {}
        if diagram_type in ("mermaid", "both"):
            result["mermaid"] = self.generate_mermaid()
        if diagram_type in ("graphviz", "both"):
            result["graphviz"] = self.generate_graphviz()
        return result

    def generate_mermaid(self) -> str:
        lines: List[str] = [f"flowchart {self.orientation}"]
        components = {c.get("unique_name", c.get("name")): c for c in self.flow_data.get("components", [])}
        for comp_id, comp in components.items():
            label = comp.get("name", comp_id)
            node_id = self._normalize_id(comp_id)
            category = (comp.get("category") or "other").lower()
            lines.append(f"  {node_id}[{label}]:::cat_{category}")

        for subjob in self.flow_data.get("subjobs", []):
            title = subjob.get("title") or "Subjob"
            start = self._normalize_id(subjob.get("start") or "")
            lines.append(f"  subgraph {self._normalize_id(title)}[{title}]")
            lines.append(f"    {start}")
            lines.append("  end")

        for flow in self.flow_data.get("flows", []):
            source = self._normalize_id(flow.get("from", ""))
            target = self._normalize_id(flow.get("to", ""))
            label = flow.get("label") or ""
            symbol = CONNECTOR_SYMBOL.get(flow.get("type", ""), "-->")
            connector = f" --|{label}|{symbol} " if label else f" {symbol} "
            lines.append(f"  {source}{connector}{target}")

        for key, color in CATEGORY_COLORS.items():
            lines.append(f"classDef cat_{key} fill:{color},stroke:#2c3e50,stroke-width:1px;")
        return "\n".join(lines)

    def generate_graphviz(self) -> str:
        """Génère une image Graphviz et retourne le chemin ou le DOT."""
        job_name = self.flow_data.get("job_name") or "talend_job"
        if Digraph is None:  # pragma: no cover
            LOGGER.warning("Graphviz indisponible, retour DOT brut")
            return self._fallback_dot()

        graph = Digraph(name="TalendJob", format=self.graphviz_format)
        graph.attr(rankdir="TB" if self.orientation == "TD" else "LR")
        components = {c.get("unique_name", c.get("name")): c for c in self.flow_data.get("components", [])}

        for comp_id, comp in components.items():
            label = comp.get("name", comp_id)
            category = (comp.get("category") or "other").lower()
            color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["other"])
            graph.node(self._normalize_id(comp_id), label=label, style="filled", fillcolor=color, color="#2c3e50")

        for flow in self.flow_data.get("flows", []):
            source = self._normalize_id(flow.get("from", ""))
            target = self._normalize_id(flow.get("to", ""))
            label = flow.get("label") or flow.get("type") or ""
            graph.edge(source, target, label=label)

        output_path = self.output_dir / f"{job_name}_flow"
        saved_path = graph.render(str(output_path), cleanup=True)
        return saved_path

    def _fallback_dot(self) -> str:
        lines: List[str] = ["digraph TalendJob {", '  rankdir="LR";']
        components = {c.get("unique_name", c.get("name")): c for c in self.flow_data.get("components", [])}
        for comp_id, comp in components.items():
            label = comp.get("name", comp_id)
            lines.append(f'  "{self._normalize_id(comp_id)}" [label="{label}"];')

        for flow in self.flow_data.get("flows", []):
            source = self._normalize_id(flow.get("from", ""))
            target = self._normalize_id(flow.get("to", ""))
            label = flow.get("label") or flow.get("type") or ""
            connector = f' [label="{label}"]' if label else ""
            lines.append(f'  "{source}" -> "{target}"{connector};')
        lines.append("}")
        return "\n".join(lines)

    def _normalize_id(self, value: Optional[str]) -> str:
        safe_value = value or "unknown"
        sanitized = safe_value.replace("-", "_").replace(" ", "_")
        return sanitized or "unknown"


__all__ = ["DiagramGenerator"]
