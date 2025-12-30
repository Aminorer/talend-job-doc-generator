"""Détection des dépendances (routines, joblets, connexions)."""
from __future__ import annotations

from typing import Any, Dict, List


class DependencyFinder:
    def __init__(self, item_data: Dict[str, Any]):
        self.item_data = item_data

    def find_dependencies(self) -> Dict[str, List[str]]:
        components = self.item_data.get("components", [])
        routines = [c["unique_name"] for c in components if c.get("name", "").startswith("tLibraryLoad")]
        joblets = [c["unique_name"] for c in components if "joblet" in c.get("name", "").lower()]
        connections = [conn.get("connector_name") for conn in self.item_data.get("connections", []) if conn.get("connector_name")]
        return {
            "routines": routines,
            "joblets": joblets,
            "connectors": connections,
        }


__all__ = ["DependencyFinder"]
