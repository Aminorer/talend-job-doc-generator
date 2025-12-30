"""Détection des dépendances (routines, joblets, connexions)."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional


LOGGER = logging.getLogger(__name__)
ROUTINE_PATTERN = re.compile(r"(Talend\w+|[A-Z][A-Za-z0-9_]*Routine)\.", re.IGNORECASE)


class DependencyFinder:
    """Identifie les dépendances clés d'un job Talend."""

    def __init__(self, item_data: Dict[str, Any]):
        self.item_data = item_data

    def find_dependencies(self) -> Dict[str, Any]:
        """Retourne les routines, joblets, subjobs et connexions DB détectées."""
        components = self.item_data.get("components", [])
        dependencies: Dict[str, Any] = {
            "routines": self._find_routines(components),
            "joblets": self._find_joblets(components),
            "subjobs": self._find_subjobs(),
            "db_connections": self._find_db_connections(components),
            "connectors": [conn.get("connector_name") for conn in self.item_data.get("connections", []) if conn.get("connector_name")],
        }
        return dependencies

    def _find_routines(self, components: List[Dict[str, Any]]) -> List[str]:
        routines: List[str] = []
        for comp in components:
            params = comp.get("parameters", {})
            for value in params.values():
                if isinstance(value, str) and ROUTINE_PATTERN.search(value):
                    routine_name = ROUTINE_PATTERN.search(value)
                    if routine_name:
                        routines.append(routine_name.group(1))
                if isinstance(value, list):
                    for entry in value:
                        if not isinstance(entry, dict):
                            continue
                        for sub_value in entry.values():
                            if isinstance(sub_value, str) and ROUTINE_PATTERN.search(sub_value):
                                routines.append(ROUTINE_PATTERN.search(sub_value).group(1))  # type: ignore[arg-type]
        return sorted(set(routines))

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
