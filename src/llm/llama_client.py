"""Client simple pour Ollama."""
from __future__ import annotations

from typing import Dict

import requests


class LlamaClient:
    def __init__(self, base_url: str, model: str = "llama3", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "temperature": temperature}
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")


__all__ = ["LlamaClient"]
