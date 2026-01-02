"""Génération de la documentation Markdown."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from analyzer.job_analyzer import AnalyzedJob

LOGGER = logging.getLogger(__name__)


class MarkdownGenerator:
    """Construit un Markdown riche à partir d'un job analysé."""

    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)

    def generate(self, job: AnalyzedJob, llm_description: str, template_name: str) -> str:
        """Génère le Markdown final en injectant toutes les sections enrichies."""
        LOGGER.info(
            "Génération Markdown",
            extra={"job_name": job.raw_item.get("name"), "template": template_name},
        )
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template introuvable: {template_path}")
        template = template_path.read_text(encoding="utf-8")

        contexts = self._format_contexts(job.raw_item.get("contexts", {}), job.contexts)
        contexts_table = self._format_context_table(job.raw_item.get("contexts", {}))
        components_table = self._format_components(job.raw_item.get("components", []))
        components_detailed = self._format_components(job.raw_item.get("components", []), detailed=True)
        connections_list = self._format_connections(job.raw_item.get("connections", []))
        notes_section = self._format_notes(job.raw_item.get("notes", []))
        stats_section = self._format_stats(job.raw_item.get("stats", {}))
        tmap_section = self._format_tmap(job.raw_item.get("components", []))
        dependencies_section = self._format_dependencies(job.dependencies)
        db_connections = self._format_db_connections(job.dependencies.get("db_connections", []))
        screenshot_section = self._format_screenshot(job.screenshot_path)
        toc = self._build_toc(
            [
                "Description générée",
                "Métadonnées",
                "Screenshot",
                "Contextes",
                "Variables de contexte",
                "Composants",
                "Connexions",
                "Détails des composants",
                "tMap",
                "Dépendances",
                "Connexions DB",
                "Notes",
                "Statistiques",
            ]
        )

        mermaid_diagram = job.flows.get("mermaid", "") or "Diagramme Mermaid indisponible"
        graphviz_diagram = job.flows.get("graphviz", "")

        content = template.format(
            job_name=job.raw_item.get("name", "Job Talend"),
            overview=llm_description,
            llm_description=llm_description,
            version=job.raw_item.get("version", ""),
            job_type=job.raw_item.get("job_type", ""),
            author=job.raw_item.get("author", ""),
            default_context=job.raw_item.get("default_context", ""),
            created_at=job.raw_item.get("created_at", ""),
            modified_at=job.raw_item.get("modified_at", ""),
            screenshot_section=screenshot_section,
            contexts=contexts,
            contexts_table=contexts_table,
            components_table=components_table,
            components_detailed=components_detailed,
            connections_list=connections_list,
            notes_section=notes_section,
            stats_section=stats_section,
            tmap_section=tmap_section,
            dependencies_section=dependencies_section,
            db_connections=db_connections,
            toc=toc,
            mermaid_diagram=mermaid_diagram,
            graphviz_diagram=graphviz_diagram or "Diagramme Graphviz non généré",
        )
        LOGGER.info(
            "Markdown généré",
            extra={
                "job_name": job.raw_item.get("name"),
                "components": len(job.raw_item.get("components", [])),
                "connections": len(job.raw_item.get("connections", [])),
            },
        )
        return content

    def _build_toc(self, titles: List[str]) -> str:
        return "\n".join(f"- [{title}](#{self._anchor(title)})" for title in titles)

    def _anchor(self, title: str) -> str:
        return title.lower().replace(" ", "-")

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

    def _format_context_table(self, contexts: Dict[str, Dict[str, Any]]) -> str:
        if not contexts:
            return "Aucune variable de contexte"
        rows = ["| Contexte | Nom | Type | Valeur | Commentaire |", "|---|---|---|---|---|"]
        for ctx_name, params in contexts.items():
            for name, info in params.items():
                rows.append(
                    f"| {ctx_name} | {name} | {info.get('type')} | {info.get('value')} | {info.get('comment', '')} |"
                )
        return "\n".join(rows)

    def _format_components(self, components: List[Dict[str, Any]], detailed: bool = False) -> str:
        if not components:
            return "Aucun composant détecté"
        header = (
            "| Unique Name | Composant | Version | Catégorie |"
            if not detailed
            else "| Unique Name | Composant | Version | Paramètres clés | Schémas |"
        )
        separator = "|---|---|---|---|" if not detailed else "|---|---|---|---|---|"
        rows = [header, separator]
        for comp in components:
            params = comp.get("parameters", {})
            schema_desc = ", ".join(f"{col.get('name')}:{col.get('type')}" for col in comp.get("schema", [])[:3])
            top_params = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3]) if detailed else ""
            row = (
                f"| {comp.get('unique_name')} | {comp.get('name')} | {comp.get('version', '')} | {comp.get('category', '')} |"
            )
            if detailed:
                row = (
                    f"| {comp.get('unique_name')} | {comp.get('name')} | {comp.get('version', '')} | {top_params} | {schema_desc} |"
                )
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

    def _format_tmap(self, components: List[Dict[str, Any]]) -> str:
        tmap_comps = [c for c in components if c.get("parameters", {}).get("tmap_details")]
        if not tmap_comps:
            return "Aucun tMap détecté"
        lines: List[str] = []
        for comp in tmap_comps:
            details = comp["parameters"]["tmap_details"]
            if hasattr(details, "to_dict"):
                details = details.to_dict()
            lines.append(f"### {comp.get('unique_name')}")
            input_names = details.get("input_table_names") or [
                t.get("name", "") for t in details.get("input_tables", [])
            ]
            output_names = details.get("output_table_names") or [
                t.get("name", "") for t in details.get("output_tables", [])
            ]
            lines.append(f"- Tables d'entrée : {', '.join(filter(None, input_names))}")
            lines.append(f"- Tables de sortie : {', '.join(filter(None, output_names))}")
            if details.get("filters"):
                lines.append("#### Filtres")
                lines.extend(f"- {flt}" for flt in details["filters"])
            if details.get("mappings"):
                lines.append("#### Mappings")
                lines.append("| Entrée | Sortie | Expression |")
                lines.append("|---|---|---|")
                for mapping in details["mappings"]:
                    source = mapping.get("source_table") or ""
                    if mapping.get("source_column"):
                        source = f"{source}.{mapping['source_column']}" if source else mapping["source_column"]
                    target = mapping.get("target_table") or ""
                    if mapping.get("target_column"):
                        target = (
                            f"{target}.{mapping['target_column']}"
                            if target and mapping["target_column"]
                            else mapping.get("target_column", target)
                        )
                    lines.append(f"| {source} | {target} | `{mapping.get('expression','')}` |")
            lines.append("")
        return "\n".join(lines)

    def _format_dependencies(self, dependencies: Dict[str, Any]) -> str:
        lines: List[str] = []
        routines = dependencies.get("routines") or []
        joblets = dependencies.get("joblets") or []
        connectors = dependencies.get("connectors") or []
        if routines:
            lines.append("**Routines détectées :** " + ", ".join(sorted(set(routines))))
        if joblets:
            lines.append("**Joblets :** " + ", ".join(j.get("unique_name") or j.get("name") for j in joblets))
        if connectors:
            lines.append("**Connecteurs :** " + ", ".join(sorted(set(connectors))))
        return "\n".join(lines) or "Aucune dépendance détectée"

    def _format_db_connections(self, db_connections: List[Dict[str, Any]]) -> str:
        if not db_connections:
            return "Aucune connexion DB détectée"
        rows = ["| Composant | Type | Host | Port | Database | Schéma | Utilisateur |", "|---|---|---|---|---|---|---|"]
        for conn in db_connections:
            rows.append(
                f"| {conn.get('component')} | {conn.get('type')} | {conn.get('host')} | {conn.get('port')} | {conn.get('database')} | {conn.get('schema')} | {conn.get('user')} |"
            )
        return "\n".join(rows)

    def _format_screenshot(self, screenshot_path: Optional[str]) -> str:
        if not screenshot_path:
            return "Aucun screenshot disponible"
        path = Path(screenshot_path)
        if not path.exists():
            return "Screenshot introuvable"
        return f"![Screenshot]({path.as_posix()})"


__all__ = ["MarkdownGenerator"]
