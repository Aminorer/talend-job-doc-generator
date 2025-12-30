"""Gestion basique des screenshots Talend."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


class ScreenshotHandler:
    def __init__(self, screenshot_path: Optional[str]):
        self.screenshot_path = Path(screenshot_path) if screenshot_path else None

    def exists(self) -> bool:
        return self.screenshot_path.exists() if self.screenshot_path else False


__all__ = ["ScreenshotHandler"]
