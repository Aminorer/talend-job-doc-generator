"""Gestionnaire de cache pour le parsing des fichiers .item.

Deux niveaux de cache sont fournis :
- Un cache mémoire LRU pour la session courante.
- Un cache disque persistant (JSON) dans ``.cache/``.

Les entrées sont invalidées automatiquement via le hash MD5 du fichier
et un TTL configurable (24h par défaut).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_TTL_SECONDS = 24 * 60 * 60
DEFAULT_MEMORY_SIZE = 64


@dataclass
class CacheEntry:
    data: Dict[str, Any]
    timestamp: float
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CacheEntry":
        return cls(
            data=payload["data"],
            timestamp=payload.get("timestamp", time.time()),
            duration_ms=payload.get("duration_ms"),
        )


class CacheManager:
    """Gestionnaire centralisé pour le cache .item."""

    def __init__(
        self,
        cache_dir: Optional[Path | str] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_memory_entries: int = DEFAULT_MEMORY_SIZE,
    ) -> None:
        resolved_cache_dir = cache_dir or os.environ.get("TALEND_DOC_CACHE_DIR")
        self.cache_dir = Path(resolved_cache_dir) if resolved_cache_dir else Path(__file__).resolve().parents[2] / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "item_cache.json.gz"
        self.legacy_cache_file = self.cache_dir / "item_cache.json"
        self.ttl_seconds = ttl_seconds
        self.max_memory_entries = max_memory_entries

        self._memory_cache: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self._disk_cache: Dict[str, CacheEntry] = {}
        self.metrics = {"hits": 0, "misses": 0, "time_saved_ms": 0.0}

        self._load_disk_cache()

    # ------------------------------------------------------------------
    @staticmethod
    def compute_md5(file_path: Path) -> str:
        hash_md5 = hashlib.md5()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    # ------------------------------------------------------------------
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retourne une entrée de cache si valide."""

        self._purge_expired()
        entry = self._memory_cache.get(key)
        if entry:
            self.metrics["hits"] += 1
            self.metrics["time_saved_ms"] += entry.duration_ms or 0
            self._memory_cache.move_to_end(key)
            return entry.data

        entry = self._disk_cache.get(key)
        if entry:
            self.metrics["hits"] += 1
            self.metrics["time_saved_ms"] += entry.duration_ms or 0
            self._add_to_memory(key, entry)
            return entry.data

        self.metrics["misses"] += 1
        return None

    def set(self, key: str, value: Dict[str, Any], duration_ms: Optional[float] = None) -> None:
        entry = CacheEntry(data=value, timestamp=time.time(), duration_ms=duration_ms)
        self._add_to_memory(key, entry)
        self._disk_cache[key] = entry
        self._persist_disk()

    # ------------------------------------------------------------------
    def _add_to_memory(self, key: str, entry: CacheEntry) -> None:
        self._memory_cache[key] = entry
        self._memory_cache.move_to_end(key)
        while len(self._memory_cache) > self.max_memory_entries:
            self._memory_cache.popitem(last=False)

    def _load_disk_cache(self) -> None:
        source_file = self.cache_file if self.cache_file.exists() else self.legacy_cache_file
        if not source_file.exists():
            return
        try:
            payload = self._read_cache_file(source_file)
            for key, entry_payload in payload.items():
                self._disk_cache[key] = CacheEntry.from_dict(entry_payload)
            # Migration transparente de l'ancien cache non compressé
            if source_file == self.legacy_cache_file:
                self._persist_disk()
                self.legacy_cache_file.unlink(missing_ok=True)
        except (json.JSONDecodeError, OSError):
            # Cache corrompu, on repart sur un cache vide
            self._disk_cache = {}

    def _persist_disk(self) -> None:
        serializable = {key: entry.to_dict() for key, entry in self._disk_cache.items()}
        with gzip.open(self.cache_file, "wt", encoding="utf-8") as handle:
            json.dump(serializable, handle, ensure_ascii=False, indent=2)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [key for key, entry in self._disk_cache.items() if now - entry.timestamp > self.ttl_seconds]
        for key in expired:
            self._disk_cache.pop(key, None)
            self._memory_cache.pop(key, None)
        if expired:
            self._persist_disk()

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self._memory_cache.clear()
        self._disk_cache.clear()
        self._persist_disk()
        self.metrics = {"hits": 0, "misses": 0, "time_saved_ms": 0.0}

    def get_metrics(self) -> Dict[str, Any]:
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = (self.metrics["hits"] / total_requests * 100) if total_requests else 0.0
        cache_size = self.cache_file.stat().st_size if self.cache_file.exists() else 0
        return {
            "hits": self.metrics["hits"],
            "misses": self.metrics["misses"],
            "hit_rate": round(hit_rate, 2),
            "time_saved_ms": round(self.metrics["time_saved_ms"], 2),
            "entries": len(self._disk_cache),
            "size_bytes": cache_size,
        }

    def _read_cache_file(self, path: Path) -> Dict[str, Any]:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                return json.load(handle)
        return json.loads(path.read_text(encoding="utf-8"))


_DEFAULT_CACHE_MANAGER: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    global _DEFAULT_CACHE_MANAGER  # noqa: PLW0603
    if _DEFAULT_CACHE_MANAGER is None:
        _DEFAULT_CACHE_MANAGER = CacheManager()
    return _DEFAULT_CACHE_MANAGER


__all__ = ["CacheManager", "CacheEntry", "get_cache_manager"]
