# Changelog

Toutes les modifications notables du projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/)
et ce projet adhère au principe de versioning sémantique.

## [1.0.0] - 2024-12-30
### Added
- Packaging PyPI complet avec entrypoints CLI `talend-doc-gen` et `talend-doc-gen-ui`.
- Documentation API Sphinx publiée pour GitHub Pages.
- Tutoriels Quick Start, Guide utilisateur, Guide développeur, FAQ et Troubleshooting dans le README.
### Changed
- Résolution automatique des templates et de `config.yaml` via un module `resource_finder`.
- Configuration Streamlit et CLI pour utiliser les assets embarqués.
### Fixed
- Chemin des ressources embarquées pour les installations pip.
### Removed
- Limitation de dépendances pour la génération de documentation HTML.

## [0.9.0] - 2024-12-15
### Added
- Profilage SnakeViz optionnel sur les commandes `generate` et `batch`.
- Cache de parsing `.item` contrôlé par l’option `--no-cache`.
### Changed
- Amélioration des messages d’erreur CLI avec suggestions contextualisées.
### Fixed
- Gestion des jobs sans fichier `.properties` associé.
### Removed
- Suppression des logs verbeux par défaut en mode production.

## [0.8.0] - 2024-12-01
### Added
- Mode `watch` pour regénérer automatiquement la documentation d’un dossier.
- Extraction des diagrammes Graphviz en plus de Mermaid.
### Changed
- Refonte des templates Markdown (compact, standard, exhaustif).
### Fixed
- Correction du mapping des types Talend vers des types lisibles.
### Removed
- Anciennes commandes expérimentales de génération partielle.

## [0.7.0] - 2024-11-15
### Added
- Intégration du client Ollama pour générer des descriptions LLM.
- Export PDF enrichi avec métadonnées et captures d’écran.
### Changed
- Consolidation des prompts LLM dans `llm/prompts.py`.
### Fixed
- Encodage UTF-8 systématique sur les exports Markdown/PDF.
### Removed
- Fallbacks d’encodage ISO obsolètes.

## [0.6.0] - 2024-11-01
### Added
- Analyseur de flux (`JobAnalyzer`) avec statistiques détaillées.
- Tableaux de bord Rich pour la CLI.
### Changed
- Refactoring des parseurs pour mutualiser la conversion des types.
### Fixed
- Correction des chemins relatifs lors de l’analyse en batch.
### Removed
- Dépendance implicite aux chemins hardcodés dans les tests.

## [0.5.0] - 2024-10-15
### Added
- Détection automatique des fichiers `.properties` et `.screenshot`.
- Gestion des contextes et variables via `ContextParser`.
### Changed
- Simplification du schéma de données retourné par `TalendItemParser`.
### Fixed
- Nettoyage des guillemets échappés dans les paramètres Talend.
### Removed
- Ancien mapping incomplet des catégories de composants.

## [0.4.0] - 2024-09-15
### Added
- Support des statistiques de composants/connexions dans les exports.
- Commande `compare` pour identifier les différences entre deux jobs.
### Changed
- Regroupement des résultats d’analyse dans la structure `AnalyzedJob`.
### Fixed
- Calcul des sous-jobs avec titres personnalisés.
### Removed
- Duplication des générateurs de diagrammes.

## [0.3.0] - 2024-08-15
### Added
- Templates Markdown multi-niveaux (compact, standard, exhaustif).
- Génération des diagrammes Mermaid basiques.
### Changed
- Interface CLI initiale avec options de diagramme et de template.
### Fixed
- Conversion booléenne fiable pour les paramètres CHECK.
### Removed
- Code expérimental de visualisation non maintenu.

## [0.2.0] - 2024-07-15
### Added
- Parser `.properties` dédié avec extraction des métadonnées (auteur, dates).
- Structure initiale de tests unitaires.
### Changed
- Séparation des modules en packages `parser`, `generator`, `analyzer`.
### Fixed
- Gestion des namespaces XML Talend dans le parser.
### Removed
- Dépendances transitoires inutilisées dans la phase d’exploration.

## [0.1.0] - 2024-07-01
### Added
- Version initiale du parser `.item` avec extraction des composants et connexions.
- Génération Markdown minimale pour un job Talend.
### Changed
- N/A
### Fixed
- N/A
### Removed
- N/A
