"""Parser simplifié pour les routines Java Talend."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


class RoutineParser:
    """Extrait les informations clés d'une routine Java."""

    PACKAGE_REGEX = re.compile(r"package\s+([a-zA-Z_][\w\.]*);")
    CLASS_REGEX = re.compile(r"class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
    METHOD_REGEX = re.compile(
        r"(?P<javadoc>/\*\*.*?\*/)?\s*public\s+(?P<signature>[^\{;]+?\s+\w+\s*\([^;{]*\))",
        re.DOTALL,
    )

    def __init__(self, routine_path: str):
        self.routine_path = Path(routine_path)
        if not self.routine_path.exists():
            raise FileNotFoundError(f"Routine introuvable : {routine_path}")

    def extract_class_info(self) -> Dict[str, Any]:
        """Retourne le nom de classe, le package et les méthodes publiques."""
        content = self.routine_path.read_text(encoding="utf-8")
        package = self._extract_package(content)
        class_name = self._extract_class_name(content)
        methods = self._extract_methods(content)

        return {
            "name": class_name,
            "package": package,
            "methods": methods,
        }

    def _extract_package(self, content: str) -> str:
        match = self.PACKAGE_REGEX.search(content)
        return match.group(1) if match else ""

    def _extract_class_name(self, content: str) -> str:
        match = self.CLASS_REGEX.search(content)
        if not match:
            raise ValueError(f"Impossible de trouver le nom de classe dans {self.routine_path}")
        return match.group("name")

    def _extract_methods(self, content: str) -> List[Dict[str, str]]:
        methods: List[Dict[str, str]] = []
        for match in self.METHOD_REGEX.finditer(content):
            javadoc_raw = match.group("javadoc") or ""
            signature_raw = match.group("signature")
            signature = self._normalize_whitespace(signature_raw)
            name = self._extract_method_name(signature)
            methods.append(
                {
                    "name": name,
                    "signature": f"public {signature}",
                    "javadoc": self._clean_javadoc(javadoc_raw),
                }
            )
        return methods

    def _extract_method_name(self, signature: str) -> str:
        name_match = re.search(r"(\w+)\s*\(", signature)
        return name_match.group(1) if name_match else signature

    def _clean_javadoc(self, raw: str) -> str:
        if not raw:
            return ""
        cleaned_lines: List[str] = []
        for line in raw.splitlines():
            line = line.strip()
            line = re.sub(r"^/\*\*?", "", line)
            line = line.replace("*/", "")
            line = line.lstrip("*").strip()
            if line:
                cleaned_lines.append(line)
        return " ".join(cleaned_lines)

    def _normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


__all__ = ["RoutineParser"]
