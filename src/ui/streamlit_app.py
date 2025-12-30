"""Application Streamlit pour générer la documentation Talend."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from analyzer.job_analyzer import JobAnalyzer
from generator.markdown_generator import MarkdownGenerator
from generator.pdf_exporter import PDFExporter
from llm.llama_client import LlamaClient
from llm.prompts import build_job_prompt
from parser.context_parser import ContextParser
from parser.item_parser import TalendItemParser
from parser.properties_parser import PropertiesParser
from utils.file_finder import FileFinder
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main():
    st.set_page_config(page_title="Talend Doc Generator", layout="wide")
    st.title("📚 Talend Documentation Generator")
    st.write("Générez automatiquement une documentation complète pour vos jobs Talend (.item).")

    config = load_config()
    template_map = {
        "compact": "job_compact.md",
        "standard": "job_standard.md",
        "exhaustif": "job_exhaustif.md",
    }

    with st.sidebar:
        st.header("Paramètres")
        detail_level = st.selectbox("Niveau de détail", options=["compact", "standard", "exhaustif"], index=1)
        diagram_type = st.selectbox("Type de diagramme", options=["mermaid", "graphviz", "both"], index=0)
        export_pdf = st.checkbox("Exporter en PDF", value=False)
        use_llm = st.checkbox("Activer la génération LLM", value=True)
        item_path_input = st.text_input("Chemin vers le fichier .item", value="")
        launch = st.button("Générer la documentation")

    if launch:
        if not item_path_input:
            st.error("Veuillez fournir un chemin vers un fichier .item")
            return

        try:
            finder = FileFinder(item_path_input)
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

            orientation = config.get("diagrams", {}).get("style", "TD")
            analyzer = JobAnalyzer(
                item_data,
                properties_data,
                context_data,
                screenshot_path=files.get("screenshot"),
                diagram_type=diagram_type,
                diagram_orientation=orientation,
            )
            analyzed_job = analyzer.analyze()

            # LLM
            llm_description = "Génération désactivée."
            if use_llm:
                llm_cfg = config.get("ollama", {})
                client = LlamaClient(
                    llm_cfg.get("base_url", "http://localhost:11434"),
                    llm_cfg.get("model", "llama3"),
                    llm_cfg.get("timeout", 120),
                )
                prompt = build_job_prompt(item_data, detail_level=detail_level)
                llm_description = client.generate(prompt)

            # Markdown
            md_generator = MarkdownGenerator(str(TEMPLATES_DIR))
            template_name = template_map.get(detail_level, "job_standard.md")
            markdown_content = md_generator.generate(analyzed_job, llm_description, template_name)

            output_dir = Path(config.get("generator", {}).get("output_dir", "docs/output"))
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / f"{analyzer.job_name}.md"
            md_path.write_text(markdown_content, encoding="utf-8")

            st.success("Documentation générée !")
            st.download_button("Télécharger Markdown", data=markdown_content, file_name=md_path.name)
            st.markdown("### Aperçu Markdown")
            st.markdown(markdown_content)

            st.markdown("### Diagramme Mermaid")
            st.code(analyzed_job.flows.get("mermaid", ""), language="mermaid")
            if diagram_type in ("graphviz", "both"):
                st.markdown("### Diagramme Graphviz")
                st.code(analyzed_job.flows.get("graphviz", ""), language="dot")

            # PDF optionnel
            if export_pdf:
                pdf_exporter = PDFExporter(str(output_dir))
                pdf_path = pdf_exporter.export(markdown_content, md_path.name)
                st.download_button("Télécharger PDF", data=pdf_path.read_bytes(), file_name=pdf_path.name)

            with st.expander("Données brutes (.json)"):
                st.code(json.dumps(item_data, ensure_ascii=False, indent=2), language="json")

        except Exception as exc:  # pylint: disable=broad-except
            st.error(f"Erreur lors de la génération : {exc}")


if __name__ == "__main__":
    main()
