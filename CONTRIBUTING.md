# Guide de contribution – Talend Documentation Generator

Merci de contribuer à ce générateur de documentation Talend ! Ce document couvre
le fonctionnement de l'architecture, les bonnes pratiques de développement, la
création de plugins ainsi que la roadmap publique.

## Architecture applicative

```mermaid
flowchart LR
    A[CLI / Streamlit] --> B[Parser\n(.item/.properties/.context)]
    B --> C[Analyzer\n(JobAnalyzer)]
    C --> D[Generator\n(Markdown/PDF/Diagrams)]
    D --> E[Sorties\nMarkdown/PDF/Screenshots]
    C --> F[LLM\n(Ollama client)]
    A --> G[Cache Manager]
    C --> H[Profiler & Logs]
```

- **CLI (`main.py`)** : commandes `generate`, `batch`, `watch`, `compare`, etc.
- **Streamlit (`ui/streamlit_app.py`)** : interface interactive pour parcourir
  les jobs, déclencher la génération et télécharger les artefacts.
- **Parseurs (`parser/`)** : extraction des structures XML Talend, métadonnées
  `.properties` et contextes.
- **Analyseurs (`analyzer/`)** : assemble les informations métier, normalise les
  flux et prépare les données pour la génération.
- **Générateurs (`generator/`)** : produit Markdown, PDF, et diagrammes Mermaid
  ou Graphviz.
- **LLM (`llm/`)** : prompts et client Ollama pour enrichir les descriptions.
- **Utils (`utils/`)** : cache, logs, recherche des assets, profilage.

## Environnement de développement

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Activer le lint/test rapide :

```bash
python -m compileall src
pytest
```

## Guide de développement de plugin

Les plugins permettent d'ajouter des transformations ou sorties personnalisées
au pipeline de génération.

1. Créer un module dans `src/generator/plugins/<nom>.py` exposant une classe
   `Plugin` avec les méthodes :
   - `supports(job: AnalyzedJob) -> bool`
   - `apply(job: AnalyzedJob, context: dict) -> dict | None`
2. Enregistrer le plugin dans `generator/markdown_generator.py` via une liste
   `EXTRA_PLUGINS`.
3. Utiliser les données normalisées de `AnalyzedJob` et respecter le format
   des flux (`mermaid`, `graphviz`).
4. Ajouter un test unitaire ciblé dans `tests/` validant :
   - La détection par `supports`
   - L'effet sur le document Markdown ou les métadonnées

### Points d'extension recommandés

- **Enrichissement Markdown** : injection de sections additionnelles (SLA,
  conformité, data lineage).
- **Sorties additionnelles** : export Confluence, HTML statique, Notion.
- **Vérifications** : contrôle des règles de nommage ou des dépendances
  interdites.

## Bonnes pratiques de code

- Couverture minimale sur les nouveaux modules : tests unitaires ou snapshot
  Markdown/PDF.
- Logs : utiliser `utils.logger.get_logger` avec `job_name` dans l'extra.
- Profilage : `utils.profiler.run_with_profile` pour mesurer les traitements
  lourds (batch/merge).
- Imports : rester explicite, pas de `try/except` autour des imports.
- Performance : privilégier `pathlib.Path` et `rg` pour les recherches.

## Roadmap (prévisionnelle)

- **1.1.0** : export HTML statique + téléversement S3 automatisé.
- **1.2.0** : détecteurs de mauvaises pratiques Talend (job anti-patterns).
- **1.3.0** : assistant interactif Streamlit pour la résolution d'incidents.
- **1.4.0** : moteur de plugin officiellement stable + registre public.
- **2.0.0** : support natif des projets Talend Cloud et auto-onboarding OAuth.

## Hall of Fame

- **Amine Ben Y** — concepteur initial du parser Talend.
- **Lina M.** — première implémentation des diagrammes Mermaid.
- **Carlos R.** — amélioration du pipeline PDF et du cache.
- **Vous ?** Ouvrez une PR ! Les contributions significatives seront ajoutées.
