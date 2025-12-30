"""Parser des fichiers .properties Talend."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from lxml import etree


class PropertiesParser:
    """Parser XML pour les fichiers .properties Talend."""

    def __init__(self, properties_path: str):
        self.properties_path = Path(properties_path)
        if not self.properties_path.exists():
            raise FileNotFoundError(f"Le fichier {properties_path} n'existe pas")
        if self.properties_path.suffix != ".properties":
            raise ValueError("Le fichier doit avoir l'extension .properties")

    def parse(self) -> Dict[str, Optional[str]]:
        tree = etree.parse(str(self.properties_path))
        root = tree.getroot()
        namespaces = {"tp": "http://www.talend.org/properties"}
        prop = root.find(".//tp:Property", namespaces=namespaces)
        if prop is None:
            raise ValueError("Élément Property introuvable dans le fichier .properties")

        metadata: Dict[str, Optional[str]] = {
            "author": prop.get("author"),
            "created_at": self._clean_date(prop.get("creationDate")),
            "modified_at": self._clean_date(prop.get("modificationDate")),
            "description": None,
            "status": prop.get("statusCode"),
            "label": prop.get("label"),
        }

        description_el = prop.find("description")
        if description_el is not None and description_el.text:
            metadata["description"] = description_el.text.strip()

        return metadata

    def _clean_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            trimmed = date_str[:19]
            parsed = datetime.fromisoformat(trimmed)
            return parsed.isoformat()
        except ValueError:
            return date_str


__all__ = ["PropertiesParser"]
