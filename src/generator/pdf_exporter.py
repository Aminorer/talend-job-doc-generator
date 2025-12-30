"""Export Markdown en PDF."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import markdown2
from fpdf import FPDF, HTMLMixin

try:
    from weasyprint import HTML  # type: ignore
except Exception:  # pragma: no cover
    HTML = None

template_css = """
<style>
body { font-family: Helvetica, Arial, sans-serif; font-size: 12px; }
h1,h2,h3 { margin-top: 10px; }
code, pre { font-family: monospace; background: #f4f4f4; padding: 4px; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #ccc; padding: 4px; }
</style>
"""


class PDF(FPDF, HTMLMixin):
    pass


class PDFExporter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, markdown_content: str, filename: str) -> Path:
        """Convertit le Markdown en PDF.

        Utilise WeasyPrint si disponible (comme décrit dans le README), sinon
        effectue un fallback vers FPDF pour garantir la génération.
        """
        html_content = template_css + markdown2.markdown(markdown_content)
        output_path = self.output_dir / f"{Path(filename).stem}.pdf"
        if HTML:
            HTML(string=html_content).write_pdf(str(output_path))
        else:
            pdf = PDF()
            pdf.add_page()
            pdf.write_html(html_content)
            pdf.output(str(output_path))
        return output_path


__all__ = ["PDFExporter"]
