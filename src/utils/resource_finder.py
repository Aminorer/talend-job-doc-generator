"""Gestion centralisée des fichiers de ressources embarqués."""
from __future__ import annotations

from importlib import resources
from pathlib import Path


def find_assets_root() -> Path:
    """Retourne le dossier où se trouvent les templates et la config.

    L'ordre de recherche est le suivant :
    1. Répertoire du projet (utilisation en développement).
    2. Paquet embarqué ``talend_doc_gen_assets`` installé via pip.
    3. Dossier parent du fichier courant (repli).

    Returns:
        Path: chemin vers le dossier contenant ``templates`` et ``config.yaml``.
    """

    repository_root = Path(__file__).resolve().parents[2]
    if (repository_root / "templates").exists() and (repository_root / "config.yaml").exists():
        return repository_root

    try:
        package_root = resources.files("talend_doc_gen_assets")  # type: ignore[attr-defined]
        return Path(str(package_root))
    except ModuleNotFoundError:
        return repository_root
