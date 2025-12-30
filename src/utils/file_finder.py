"""Détection automatique des fichiers liés à un job Talend."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


class FileFinder:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def find_related_files(self) -> Dict[str, Optional[Path]]:
        item_path = Path(self.base_path)
        if item_path.is_dir():
            items = list(item_path.glob("*.item"))
            if not items:
                raise FileNotFoundError("Aucun fichier .item trouvé")
            item_path = items[0]
        if not item_path.exists():
            raise FileNotFoundError("Fichier .item introuvable")

        related = {
            "item": item_path,
            "properties": item_path.with_suffix(".properties"),
            "screenshot": item_path.with_suffix(".screenshot"),
            "context": item_path.with_suffix(".context"),
        }
        for key, path in related.items():
            if not path.exists():
                related[key] = None
        return related


__all__ = ["FileFinder"]
