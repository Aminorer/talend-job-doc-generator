"""Export Markdown en PDF avec WeasyPrint (fallback FPDF)."""
from __future__ import annotations

import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import markdown2
from fpdf import FPDF, HTMLMixin

try:  # pragma: no cover
    from weasyprint import CSS, HTML
except Exception:  # pragma: no cover
    CSS = None
    HTML = None


LOGGER = logging.getLogger(__name__)

template_css = """
@page { size: A4; margin: 20mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; color: #2c3e50; }
h1, h2, h3 { color: #1a5276; }
code, pre { font-family: monospace; background: #f4f6f6; padding: 4px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
th, td { border: 1px solid #dfe6e9; padding: 6px; }
tr:nth-child(even) { background: #f9fbfc; }
.cover { text-align: center; padding: 60px 20px; }
.badge { display: inline-block; padding: 4px 8px; border-radius: 4px; background: #2ecc71; color: #fff; margin: 2px; }
.stats { display: flex; gap: 12px; justify-content: center; margin-top: 16px; }
.stat { background: #ecf0f1; padding: 8px 12px; border-radius: 6px; }
.footer { text-align: center; font-size: 9pt; color: #7f8c8d; margin-top: 24px; }
"""


class PDF(FPDF, HTMLMixin):
    """PDF Fallback basé sur FPDF."""


class PDFExporter:
    """Convertit du Markdown enrichi en PDF prêt à partager."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        markdown_content: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None,
        screenshot_path: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Convertit le Markdown en PDF en ajoutant page de garde, CSS et screenshot.

        Args:
            markdown_content: contenu Markdown brut.
            filename: nom de fichier cible.
            metadata: informations de job (nom, auteur, version, date).
            screenshot_path: chemin vers un PNG à embarquer.
            stats: statistiques calculées à mettre en avant sur la couverture.
        """
        LOGGER.info(
            "Export PDF démarré",
            extra={"job_name": metadata.get("name") if metadata else None, "output_dir": str(self.output_dir)},
        )
        html_content = markdown2.markdown(markdown_content)
        html = self._wrap_html(html_content, metadata=metadata or {}, screenshot_path=screenshot_path, stats=stats or {})
        output_path = self.output_dir / f"{Path(filename).stem}.pdf"
        if HTML:
            try:
                css = CSS(string=template_css) if CSS else None
                HTML(string=html).write_pdf(str(output_path), stylesheets=[css] if css else None)
                LOGGER.info("Export PDF terminé", extra={"job_name": metadata.get("name") if metadata else None, "path": str(output_path)})
                return output_path
            except Exception as exc:  # pragma: no cover
                LOGGER.error("WeasyPrint indisponible, fallback FPDF: %s", exc)
        pdf = PDF()
        pdf.add_page()
        pdf.write_html(template_css + html)
        pdf.output(str(output_path))
        LOGGER.info("Export PDF via FPDF", extra={"job_name": metadata.get("name") if metadata else None, "path": str(output_path)})
        return output_path

    def _wrap_html(self, body_html: str, metadata: Dict[str, Any], screenshot_path: Optional[str], stats: Dict[str, Any]) -> str:
        cover = self._cover_html(metadata, stats, screenshot_path)
        return f"""
        <html>
        <head><style>{template_css}</style></head>
        <body>
            {cover}
            <div class="content">
                {body_html}
            </div>
            <div class="footer">Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </body>
        </html>
        """

    def _cover_html(self, metadata: Dict[str, Any], stats: Dict[str, Any], screenshot_path: Optional[str]) -> str:
        screenshot_img = ""
        if screenshot_path:
            img_path = Path(screenshot_path)
            if img_path.exists():
                encoded = base64.b64encode(img_path.read_bytes()).decode("utf-8")
                screenshot_img = f'<img src="data:image/png;base64,{encoded}" alt="Screenshot" style="max-width: 100%; margin-top: 12px;"/>'
        stat_blocks = ""
        if stats:
            stat_items = []
            for key, value in stats.items():
                stat_items.append(f'<div class="stat"><strong>{key}</strong><br/>{value}</div>')
            stat_blocks = '<div class="stats">' + "".join(stat_items) + "</div>"
        return f"""
        <div class="cover">
            <h1>{metadata.get('name', 'Documentation Talend')}</h1>
            <div class="badge">Version {metadata.get('version', '?')}</div>
            <div class="badge">Auteur: {metadata.get('author', 'N/A')}</div>
            <p>Généré le {datetime.now().strftime('%Y-%m-%d')}</p>
            {stat_blocks}
            {screenshot_img}
        </div>
        """


__all__ = ["PDFExporter"]
