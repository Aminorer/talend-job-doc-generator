"""Prompts pour la génération de texte."""
from __future__ import annotations

from typing import Dict


def build_job_prompt(job_data: Dict, detail_level: str = "standard") -> str:
    components = job_data.get("components", [])
    connections = job_data.get("connections", [])
    connections_list = [f"{c.get('source')}->{c.get('target')}" for c in connections]
    return (
        "Tu es un expert Talend. Résume le job suivant en français en mettant l'accent sur les flux de données, "
        "les composants critiques et les variables de contexte. "
        f"Détail demandé: {detail_level}.\n"
        f"Nom: {job_data.get('name')}\n"
        f"Composants ({len(components)}): {[c.get('unique_name') for c in components]}\n"
        f"Connexions ({len(connections)}): {connections_list}\n"
    )


__all__ = ["build_job_prompt"]
