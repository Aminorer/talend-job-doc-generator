"""Détection automatique des fichiers liés à un job Talend."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from parser.screenshot_parser import ScreenshotParser


class FileFinder:
    def __init__(self, base_path: str, screenshot_output_dir: Optional[str] = None):
        self.base_path = Path(base_path)
        self.screenshot_output_dir = Path(screenshot_output_dir) if screenshot_output_dir else Path(
            "docs/output/screenshots"
        )

    def find_related_files(self) -> Dict[str, Optional[Path]]:
        item_path = Path(self.base_path)
        if item_path.is_dir():
            items = list(item_path.glob("*.item"))
            if not items:
                raise FileNotFoundError("Aucun fichier .item trouvé")
            item_path = items[0]
        if not item_path.exists():
            raise FileNotFoundError("Fichier .item introuvable")

        context_file = item_path.with_suffix(".context")
        if not context_file.exists():
            context_dir = item_path.parent / "context"
            if context_dir.exists():
                context_file = self._find_context_in_directory(context_dir, item_path.stem)

        related = {
            "item": item_path,
            "properties": item_path.with_suffix(".properties"),
            "screenshot": item_path.with_suffix(".screenshot"),
            "context": context_file if context_file and context_file.exists() else None,
        }
        for key, path in related.items():
            if not path or not path.exists():
                related[key] = None
            elif key == "screenshot":
                parser = ScreenshotParser(str(path), output_dir=str(self.screenshot_output_dir))
                try:
                    extracted = parser.parse()
                    related[key] = extracted
                except Exception:
                    related[key] = None
        return related

    def _find_context_in_directory(self, context_dir: Path, stem: str) -> Optional[Path]:
        """Sélectionne le fichier .context le plus pertinent dans un dossier context/."""
        candidates = list(context_dir.glob("*.context"))
        if not candidates:
            return None

        normalized_stem = stem.split("_")[0]
        for candidate in candidates:
            candidate_stem = candidate.stem.split("_")[0]
            if candidate_stem == stem or candidate_stem == normalized_stem:
                return candidate

        return candidates[0]


__all__ = ["FileFinder"]
