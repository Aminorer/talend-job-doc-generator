"""Détection des dépendances (routines, joblets, connexions)."""
from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

from parser.routine_parser import RoutineParser

LOGGER = logging.getLogger(__name__)
ROUTINE_PATTERN = re.compile(
    r"(?P<class>(Talend\w+|[A-Z][A-Za-z0-9_]*Routine))\.(?P<method>[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


class DependencyFinder:
    """Identifie les dépendances clés d'un job Talend."""

    def __init__(self, item_data: Dict[str, Any]):
        self.item_data = item_data

    def find_dependencies(self) -> Dict[str, Any]:
        """Retourne les routines, joblets, subjobs et connexions DB détectées."""
        LOGGER.debug(
            "Analyse des dépendances démarrée",
            extra={"job_name": self.item_data.get("name"), "nb_components": len(self.item_data.get("components", []))},
        )
        components = self.item_data.get("components", [])
        project_root = self.item_data.get("project_root")
        routine_usages = self._find_routines(components)
        routine_definitions = self._parse_routine_files(project_root) if routine_usages else {}
        dependencies: Dict[str, Any] = {
            "routines": self._enrich_routines(routine_usages, routine_definitions, project_root),
            "joblets": self._find_joblets(components),
            "subjobs": self._find_subjobs(),
            "db_connections": self._find_db_connections(components),
            "connectors": [conn.get("connector_name") for conn in self.item_data.get("connections", []) if conn.get("connector_name")],
        }
        LOGGER.info(
            "Dépendances trouvées",
            extra={
                "job_name": self.item_data.get("name"),
                "routines": len(dependencies["routines"]),
                "joblets": len(dependencies["joblets"]),
                "db_connections": len(dependencies["db_connections"]),
            },
        )
        return dependencies

    def _find_routines(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        routines: Dict[str, Set[str]] = {}
        for comp in components:
            params = comp.get("parameters", {})
            for value in params.values():
                self._scan_value_for_routines(value, routines)
        return [
            {"name": name, "methods": sorted(methods)}
            for name, methods in sorted(routines.items(), key=lambda item: item[0].lower())
        ]

    def _scan_value_for_routines(self, value: Any, routines: Dict[str, Set[str]]) -> None:
        if isinstance(value, str):
            for match in ROUTINE_PATTERN.finditer(value):
                routine_name = match.group("class")
                method_name = match.group("method")
                routines.setdefault(routine_name, set()).add(method_name)
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    for sub_value in entry.values():
                        self._scan_value_for_routines(sub_value, routines)

    def _parse_routine_files(self, project_root: Optional[str]) -> Dict[str, Dict[str, Any]]:
        if not project_root:
            return {}
        routines_dir = Path(project_root) / "code" / "routines"
        if not routines_dir.exists():
            LOGGER.info("Dossier routines introuvable", extra={"project_root": project_root})
            return {}

        parsed: Dict[str, Dict[str, Any]] = {}
        for java_file in routines_dir.rglob("*.java"):
            try:
                info = RoutineParser(str(java_file)).extract_class_info()
                info["path"] = str(java_file)
                parsed[info["name"]] = info
            except Exception:  # pylint: disable=broad-except
                LOGGER.warning("Impossible de parser la routine", extra={"path": str(java_file)}, exc_info=True)
        return parsed

    def _enrich_routines(
        self,
        routine_usages: List[Dict[str, Any]],
        routine_definitions: Dict[str, Dict[str, Any]],
        project_root: Optional[str],
    ) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
        for routine in routine_usages:
            details = routine_definitions.get(routine["name"])
            methods: List[Dict[str, str]] = []
            for method in routine.get("methods", []):
                method_info = next((m for m in details.get("methods", []) if m.get("name") == method), None) if details else None
                methods.append(
                    {
                        "name": method,
                        "signature": method_info.get("signature") if method_info else method,
                        "javadoc": method_info.get("javadoc", "") if method_info else "",
                    }
                )
            enriched.append(
                {
                    "name": routine["name"],
                    "package": details.get("package") if details else None,
                    "path": self._relative_path(details.get("path"), project_root) if details else None,
                    "methods": methods,
                }
            )
        return enriched

    def _relative_path(self, path: Optional[str], project_root: Optional[str]) -> Optional[str]:
        if not path:
            return None
        path_obj = Path(path)
        if project_root:
            try:
                return str(path_obj.resolve().relative_to(Path(project_root).resolve()))
            except ValueError:
                return str(path_obj)
        return str(path_obj)

    def _find_joblets(self, components: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        joblets: List[Dict[str, str]] = []
        for comp in components:
            name = comp.get("name", "")
            if name and not name.lower().startswith("t"):
                joblets.append({"name": name, "unique_name": comp.get("unique_name", ""), "version": comp.get("version", "")})
        return joblets

    def _find_subjobs(self) -> List[Dict[str, Any]]:
        subjobs = self.item_data.get("subjobs", []) or []
        grouped: List[Dict[str, Any]] = []
        connections = self.item_data.get("connections", [])
        for subjob in subjobs:
            start_node = subjob.get("start")
            related = [c for c in connections if c.get("source") == start_node or c.get("target") == start_node]
            grouped.append({"title": subjob.get("title"), "start": start_node, "connections": related})
        return grouped

    def _find_db_connections(self, components: List[Dict[str, Any]]) -> List[Dict[str, Optional[str]]]:
        db_components: List[Dict[str, Optional[str]]] = []
        for comp in components:
            name = comp.get("name", "").lower()
            if not name.startswith("t") or ("input" not in name and "output" not in name and "rowgenerator" not in name):
                continue
            if "db" not in name and not any(db in name for db in ["oracle", "mysql", "postgres", "mssql", "jdbc", "snowflake"]):
                continue
            params = comp.get("parameters", {})
            db_components.append(
                {
                    "component": comp.get("unique_name", ""),
                    "type": comp.get("name", ""),
                    "host": self._get_param(params, ["HOST", "HOSTNAME", "SERVER"]),
                    "port": self._get_param(params, ["PORT", "DB_PORT"]),
                    "database": self._get_param(params, ["DBNAME", "DATABASE", "DBNAME_DEFAULT"]),
                    "schema": self._get_param(params, ["SCHEMA", "DBSCHEMA"]),
                    "user": self._get_param(params, ["USER", "USERNAME"]),
                }
            )
        return db_components

    def _get_param(self, params: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            value = params.get(key)
            if isinstance(value, str):
                return value
        return None


__all__ = ["DependencyFinder"]
