from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class BatchRecord:
    md5: str
    outputs: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.time())


class BatchState:
    """Stocke l'état d'exécution des batchs pour le mode incrémental."""

    def __init__(self, cache_dir: Path) -> None:
        self.state_file = cache_dir / "batch_state.json"
        self.records: Dict[str, BatchRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.state_file.exists():
            return
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for path, payload in raw.items():
            self.records[path] = BatchRecord(
                md5=payload.get("md5", ""),
                outputs=payload.get("outputs", {}),
                timestamp=payload.get("timestamp", time.time()),
            )

    def should_skip(self, item_path: Path, md5: str) -> bool:
        record = self.records.get(str(item_path))
        return record is not None and record.md5 == md5

    def get_outputs(self, item_path: Path) -> Optional[Dict[str, str]]:
        record = self.records.get(str(item_path))
        return record.outputs if record else None

    def update(self, item_path: Path, md5: str, outputs: Dict[str, str]) -> None:
        self.records[str(item_path)] = BatchRecord(md5=md5, outputs=outputs)

    def save(self) -> None:
        serializable = {
            path: {"md5": record.md5, "outputs": record.outputs, "timestamp": record.timestamp}
            for path, record in self.records.items()
        }
        self.state_file.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = ["BatchState"]
