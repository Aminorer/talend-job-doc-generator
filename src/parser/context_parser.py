"""Extraction des variables de contexte Talend."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from lxml import etree


class ContextParser:
    def __init__(self, context_path: str):
        self.context_path = Path(context_path)
        if not self.context_path.exists():
            raise FileNotFoundError(f"Le fichier {context_path} n'existe pas")

    def parse(self) -> Dict[str, Dict[str, str]]:
        tree = etree.parse(str(self.context_path))
        root = tree.getroot()
        contexts: Dict[str, Dict[str, str]] = {}
        namespaces = root.nsmap or {}
        for context in root.findall(".//context", namespaces=namespaces):
            name = context.get("name", "Default")
            contexts[name] = {}
            for param in context.findall("contextParameter", namespaces=namespaces):
                contexts[name][param.get("name", "")] = param.get("value")
        return contexts


__all__ = ["ContextParser"]
