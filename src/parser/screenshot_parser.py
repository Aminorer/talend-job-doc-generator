"""Extraction des screenshots Talend (.screenshot -> PNG)."""
from __future__ import annotations

import base64
import binascii
import logging
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree


LOGGER = logging.getLogger(__name__)


class ScreenshotParser:
    """Parses a Talend .screenshot XML file and writes the embedded PNG."""

    def __init__(self, screenshot_path: str, output_dir: Optional[str] = None):
        self.screenshot_path = Path(screenshot_path)
        self.output_dir = Path(output_dir) if output_dir else Path("docs/output/screenshots")

    def parse(self) -> Optional[Path]:
        """Extract the first screenshot to PNG and return its path."""
        if not self.screenshot_path.exists():
            raise FileNotFoundError(f"Le fichier {self.screenshot_path} est introuvable")

        try:
            tree = ElementTree.parse(self.screenshot_path)
        except ElementTree.ParseError as exc:  # pragma: no cover - parsing error is unlikely but explicit
            raise ValueError(f"Screenshot XML invalide: {exc}") from exc

        root = tree.getroot()
        screenshots = []
        for node in root.iter():
            if node.tag.split("}")[-1] != "screenshots":
                continue
            encoded = node.get("value") or (node.text or "").strip()
            if not encoded:
                continue
            key = node.get("key") or "screenshot"
            target_name = f"{self.screenshot_path.stem}_{key}.png"
            target_path = self.output_dir / target_name
            try:
                data = base64.b64decode(encoded)
            except binascii.Error as exc:
                raise ValueError("Contenu base64 du screenshot invalide") from exc

            self.output_dir.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(data)
            screenshots.append(target_path)
            LOGGER.info(
                "Screenshot extrait",
                extra={"source": str(self.screenshot_path), "output": str(target_path)},
            )

        return screenshots[0] if screenshots else None


__all__ = ["ScreenshotParser"]
