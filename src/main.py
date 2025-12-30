"""Point d'entrée principal pour générer la documentation Talend."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import yaml

from analyzer.job_analyzer import JobAnalyzer
from generator.diagram_generator import DiagramGenerator
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


def generate_documentation(item_path: str, template: Optional[str] = None, export_pdf: bool = False) -> Dict[str, Path]:
    config = load_config()
    finder = FileFinder(item_path)
    files = finder.find_related_files()

    item_data = TalendItemParser(str(files["item"])) .parse()

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

    analyzer = JobAnalyzer(item_data, properties_data, context_data, screenshot_path=files.get("screenshot"))
    analyzed_job = analyzer.analyze()

    # Générer le diagramme et l'injecter dans les flux
    diagram_gen = DiagramGenerator(analyzed_job.flows)
    analyzed_job.flows["mermaid"] = diagram_gen.generate_mermaid()

    # Générer la description via LLM
    llm_cfg = config.get("ollama", {})
    client = LlamaClient(llm_cfg.get("base_url", "http://localhost:11434"), llm_cfg.get("model", "llama3"), llm_cfg.get("timeout", 120))
    prompt = build_job_prompt(item_data)
    llm_description = client.generate(prompt)

    # Générer Markdown
    md_generator = MarkdownGenerator(str(TEMPLATES_DIR))
    template_name = template or config.get("generator", {}).get("default_template", "job_standard.md")
    markdown_content = md_generator.generate(analyzed_job, llm_description, template_name)

    output_dir = Path(config.get("generator", {}).get("output_dir", "docs/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{analyzer.job_name}.md"
    md_path.write_text(markdown_content, encoding="utf-8")

    result_paths: Dict[str, Path] = {"markdown": md_path}

    if export_pdf:
        pdf_exporter = PDFExporter(str(output_dir))
        pdf_path = pdf_exporter.export(markdown_content, md_path.name)
        result_paths["pdf"] = pdf_path

    # Sauvegarder les données JSON pour debugging
    json_path = output_dir / f"{analyzer.job_name}.json"
    json_path.write_text(json.dumps(item_data, ensure_ascii=False, indent=2), encoding="utf-8")
    result_paths["raw_json"] = json_path

    return result_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère la documentation d'un job Talend (.item)")
    parser.add_argument("item_path", help="Chemin vers le fichier .item ou un dossier contenant un .item")
    parser.add_argument("--template", default=None, help="Nom du template Markdown à utiliser")
    parser.add_argument("--pdf", action="store_true", help="Exporter également en PDF")
    args = parser.parse_args()

    outputs = generate_documentation(args.item_path, template=args.template, export_pdf=args.pdf)
    print("Documentation générée :")
    for kind, path in outputs.items():
        print(f"- {kind}: {path}")


if __name__ == "__main__":
    main()
