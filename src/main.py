"""Point d'entrée principal pour générer la documentation Talend."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import yaml

from analyzer.job_analyzer import JobAnalyzer
from generator.markdown_generator import MarkdownGenerator
from generator.pdf_exporter import PDFExporter
from llm.llama_client import LlamaClient
from llm.prompts import build_job_prompt
from parser.context_parser import ContextParser
from parser.item_parser import TalendItemParser
from parser.properties_parser import PropertiesParser
from utils.file_finder import FileFinder


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_config(config_path: Optional[Path] = None) -> Dict:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _template_from_detail(detail: str) -> str:
    mapping = {
        "compact": "job_compact.md",
        "standard": "job_standard.md",
        "exhaustif": "job_exhaustif.md",
    }
    return mapping.get(detail.lower(), "job_standard.md")


def generate_documentation(
    item_path: str,
    template: Optional[str] = None,
    export_pdf: bool = False,
    detail: str = "standard",
    diagram_type: str = "mermaid",
    use_llm: bool = True,
    output: Optional[str] = None,
) -> Dict[str, Path]:
    config = load_config()
    finder = FileFinder(item_path)
    files = finder.find_related_files()

    item_data = TalendItemParser(str(files["item"])).parse()

    properties_data = None
    if files.get("properties"):
        properties_data = PropertiesParser(str(files["properties"])).parse()
        item_data.update({
            "author": properties_data.get("author"),
            "created_at": properties_data.get("created_at"),
            "modified_at": properties_data.get("modified_at"),
            "description": properties_data.get("description", item_data.get("description")),
        })

    context_data = None
    if files.get("context"):
        context_data = ContextParser(str(files["context"])).parse()

    diagram_orientation = config.get("diagrams", {}).get("style", "TD")
    analyzer = JobAnalyzer(
        item_data,
        properties_data,
        context_data,
        screenshot_path=files.get("screenshot"),
        diagram_type=diagram_type,
        diagram_orientation=diagram_orientation,
    )
    analyzed_job = analyzer.analyze()

    # Générer la description via LLM
    llm_description = "Génération désactivée."
    if use_llm:
        llm_cfg = config.get("ollama", {})
        client = LlamaClient(llm_cfg.get("base_url", "http://localhost:11434"), llm_cfg.get("model", "llama3"), llm_cfg.get("timeout", 120))
        prompt = build_job_prompt(item_data, detail_level=detail)
        try:
            llm_description = client.generate(prompt)
        except Exception as exc:  # pylint: disable=broad-except
            llm_description = f"Description non générée (LLM indisponible: {exc})."

    # Générer Markdown
    md_generator = MarkdownGenerator(str(TEMPLATES_DIR))
    template_name = template or _template_from_detail(detail)
    markdown_content = md_generator.generate(analyzed_job, llm_description, template_name)

    output_dir = Path(config.get("generator", {}).get("output_dir", "docs/output"))
    md_path = Path(output) if output else output_dir / f"{analyzer.job_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_content, encoding="utf-8")

    result_paths: Dict[str, Path] = {"markdown": md_path}

    if export_pdf:
        pdf_exporter = PDFExporter(str(md_path.parent))
        pdf_path = pdf_exporter.export(markdown_content, md_path.name)
        result_paths["pdf"] = pdf_path

    # Sauvegarder les données JSON pour debugging
    json_path = md_path.parent / f"{analyzer.job_name}.json"
    json_path.write_text(json.dumps(item_data, ensure_ascii=False, indent=2), encoding="utf-8")
    result_paths["raw_json"] = json_path

    return result_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère la documentation d'un job Talend (.item)")
    parser.add_argument("item_path", help="Chemin vers le fichier .item ou un dossier contenant un .item")
    parser.add_argument("--template", default=None, help="Nom du template Markdown à utiliser")
    parser.add_argument(
        "--detail",
        choices=["compact", "standard", "exhaustif"],
        default="standard",
        help="Niveau de détail souhaité",
    )
    parser.add_argument(
        "--diagram",
        choices=["mermaid", "graphviz", "both"],
        default="mermaid",
        help="Type de diagramme à générer",
    )
    parser.add_argument("--no-llm", action="store_true", help="Désactiver la génération via LLM")
    parser.add_argument("--output", "-o", default=None, help="Chemin de sortie du fichier Markdown")
    parser.add_argument("--pdf", action="store_true", help="Exporter également en PDF")
    args = parser.parse_args()

    outputs = generate_documentation(
        args.item_path,
        template=args.template,
        export_pdf=args.pdf,
        detail=args.detail,
        diagram_type=args.diagram,
        use_llm=not args.no_llm,
        output=args.output,
    )
    print("Documentation générée :")
    for kind, path in outputs.items():
        print(f"- {kind}: {path}")


if __name__ == "__main__":
    main()
