"""Détection automatique des fichiers liés à un job Talend."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from parser.screenshot_parser import ScreenshotParser


class FileFinder:
    def __init__(self, base_path: str, screenshot_output_dir: Optional[str] = None):
        self.base_path = Path(base_path)
        self.screenshot_output_dir = Path(screenshot_output_dir) if screenshot_output_dir else Path(
            "docs/output/screenshots"
        )

    def find_related_files(self) -> Dict[str, Optional[Path]]:
        item_path = self._resolve_item_path()

        context_file = item_path.with_suffix(".context")
        if not context_file.exists():
            context_dir = item_path.parent / "context"
            if context_dir.exists():
                context_file = self._find_context_in_directory(context_dir, item_path.stem)

        project_root = self._infer_project_root(item_path)

        related = {
            "item": item_path,
            "properties": item_path.with_suffix(".properties"),
            "screenshot": item_path.with_suffix(".screenshot"),
            "context": context_file if context_file and context_file.exists() else None,
            "project_root": project_root,
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

    def find_joblets(self) -> List[Path]:
        """Retourne la liste des joblets présents dans process/Joblets/."""
        base = Path(self.base_path)
        if base.is_dir() and any((base / marker).exists() for marker in ("process", "context", "code")):
            project_root = base
        else:
            project_root = None
        try:
            item_path = self._resolve_item_path()
        except (FileNotFoundError, ValueError):
            item_path = base
        project_root = project_root or self._infer_project_root(item_path)
        joblets_dir = project_root / "process" / "Joblets"
        if not joblets_dir.exists():
            return []
        return sorted(joblets_dir.rglob("*.item"))

    def _infer_project_root(self, item_path: Path) -> Path:
        """Tente de retrouver la racine du projet Talend à partir du .item."""
        current = item_path.parent
        markers = ("process", "context", "code")
        while current.parent != current:
            if any((current / marker).exists() for marker in markers):
                return current
            current = current.parent
        return item_path.parent

    def _resolve_item_path(self) -> Path:
        item_path = Path(self.base_path)
        if item_path.is_dir():
            items = list(item_path.glob("*.item"))
            if not items:
                raise FileNotFoundError("Aucun fichier .item trouvé")
            item_path = items[0]
        if not item_path.exists():
            raise FileNotFoundError("Fichier .item introuvable")
        if item_path.suffix.lower() != ".item":
            raise ValueError("Le chemin fourni doit pointer vers un fichier .item")
        return item_path

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
