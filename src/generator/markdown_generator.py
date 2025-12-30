"""Génération de la documentation Markdown."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from analyzer.job_analyzer import AnalyzedJob


class MarkdownGenerator:
    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)

    def generate(self, job: AnalyzedJob, llm_description: str, template_name: str) -> str:
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template introuvable: {template_path}")
        template = template_path.read_text(encoding="utf-8")
        contexts = self._format_contexts(job.raw_item.get("contexts", {}), job.contexts)
        components_table = self._format_components(job.raw_item.get("components", []))
        connections_list = self._format_connections(job.raw_item.get("connections", []))
        components_detailed = self._format_components(job.raw_item.get("components", []), detailed=True)
        notes_section = self._format_notes(job.raw_item.get("notes", []))
        stats_section = self._format_stats(job.raw_item.get("stats", {}))

        mermaid_diagram = job.flows.get("mermaid", "") or "Diagramme Mermaid indisponible"
        graphviz_diagram = job.flows.get("graphviz", "")

        return template.format(
            job_name=job.raw_item.get("name", "Job Talend"),
            overview=llm_description,
            llm_description=llm_description,
            version=job.raw_item.get("version", ""),
            job_type=job.raw_item.get("job_type", ""),
            author=job.raw_item.get("author", ""),
            default_context=job.raw_item.get("default_context", ""),
            created_at=job.raw_item.get("created_at", ""),
            modified_at=job.raw_item.get("modified_at", ""),
            contexts=contexts,
            components_table=components_table,
            components_detailed=components_detailed,
            connections_list=connections_list,
            notes_section=notes_section,
            stats_section=stats_section,
            mermaid_diagram=mermaid_diagram,
            graphviz_diagram=graphviz_diagram or "Diagramme Graphviz non généré",
        )

    def _format_contexts(self, contexts: Dict[str, Dict[str, Any]], parsed_contexts: Any) -> str:
        lines: List[str] = []
        combined = contexts or parsed_contexts or {}
        for context_name, params in combined.items():
            lines.append(f"### {context_name}")
            if not params:
                lines.append("(aucune variable)")
            else:
                for key, value in params.items():
                    if isinstance(value, dict):
                        display = value.get("value") or value
                    else:
                        display = value
                    lines.append(f"- **{key}**: {display}")
            lines.append("")
        return "\n".join(lines).strip() or "Aucun contexte détecté"

    def _format_components(self, components: List[Dict[str, Any]], detailed: bool = False) -> str:
        if not components:
            return "Aucun composant détecté"
        header = "| Unique Name | Composant | Version |" if not detailed else "| Unique Name | Composant | Version | Paramètres clés |"
        separator = "|---|---|---|" if not detailed else "|---|---|---|---|"
        rows = [header, separator]
        for comp in components:
            params = comp.get("parameters", {})
            top_params = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3]) if detailed else ""
            row = f"| {comp.get('unique_name')} | {comp.get('name')} | {comp.get('version', '')} |"
            if detailed:
                row += f" {top_params} |"
            rows.append(row)
        return "\n".join(rows)

    def _format_connections(self, connections: List[Dict[str, Any]]) -> str:
        if not connections:
            return "Aucune connexion"
        lines = []
        for conn in connections:
            label = conn.get("label") or conn.get("connector_name") or ""
            lines.append(f"- {conn.get('source')} -> {conn.get('target')} ({label})")
        return "\n".join(lines)

    def _format_notes(self, notes: List[Dict[str, Any]]) -> str:
        if not notes:
            return "Pas de notes"
        return "\n".join(f"- {note.get('label', '')}: {note.get('text', '')}" for note in notes)

    def _format_stats(self, stats: Dict[str, Any]) -> str:
        if not stats:
            return "Pas de statistiques"
        lines = []
        for key, value in stats.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)


__all__ = ["MarkdownGenerator"]
