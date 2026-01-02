"""CLI avancé pour générer et analyser la documentation de jobs Talend."""
from __future__ import annotations

import json
import logging
import os
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import click
import yaml
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.traceback import Traceback

from analyzer.job_analyzer import AnalyzedJob, JobAnalyzer
from generator.markdown_generator import MarkdownGenerator
from generator.pdf_exporter import PDFExporter
from llm.llama_client import LlamaClient
from llm.prompts import build_job_prompt
from parser.context_parser import ContextParser
from parser.item_parser import TalendItemParser
from parser.properties_parser import PropertiesParser
from utils.file_finder import FileFinder
from utils.logger import configure_logging, get_logger


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


class CliError(RuntimeError):
    """Erreur contrôlée avec suggestion utilisateur."""

    def __init__(self, message: str, suggestion: Optional[str] = None, exit_code: int = 1):
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.exit_code = exit_code


@dataclass
class CLIContext:
    """Contexte partagé entre les commandes CLI."""

    config: Dict[str, Any]
    console: Console
    verbose: bool
    quiet: bool
    workers: int
    output_format: str


@dataclass
class ParsedJob:
    """Résultat d'un parsing complet du job."""

    analyzed: AnalyzedJob
    item_data: Dict[str, Any]
    properties: Optional[Dict[str, Any]]
    contexts: Optional[Dict[str, Dict[str, str]]]
    files: Dict[str, Path]
    analyzer: JobAnalyzer


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
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


def _configure_logging(config: Dict[str, Any], verbose: bool, quiet: bool) -> None:
    configure_logging(config.get("logging"))
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    logging.getLogger().setLevel(level)


def _progress(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}"),
        BarColumn(bar_width=None),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
    )


def _render_error(console: Console, error: CliError) -> None:
    body = f"[bold red]{error.message}[/bold red]"
    if error.suggestion:
        body += f"\n[green]Suggestion : {error.suggestion}[/green]"
    console.print(Panel(body, title="Erreur", border_style="red", expand=False))


def _render_unexpected_error(console: Console, exc: BaseException) -> None:
    console.print(Panel("Une erreur inattendue est survenue", style="bold red"))
    console.print(Traceback.from_exception(type(exc), exc, exc.__traceback__), crop=False)


def _ensure_item_path(path: Path) -> None:
    if not path.exists():
        raise CliError(f"Chemin introuvable : {path}", suggestion="Vérifiez que le fichier ou dossier existe.")
    if path.is_dir():
        items = list(path.rglob("*.item"))
        if not items:
            raise CliError("Aucun fichier .item trouvé dans le dossier.", suggestion="Indiquez un fichier .item ou un dossier contenant un .item.")
    elif path.suffix.lower() != ".item":
        raise CliError("Le chemin fourni n'est pas un fichier .item.", suggestion="Utilisez un fichier .item ou un dossier contenant un .item.")


def _parse_job(
    item_path: Path,
    config: Dict[str, Any],
    *,
    diagram_type: str = "mermaid",
    detail: str = "standard",
    no_cache: bool = False,
    console: Optional[Console] = None,
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None,
    show_progress: bool = True,
) -> ParsedJob:
    _ensure_item_path(item_path)
    logger = get_logger(__name__)
    console = console or Console()
    diagram_orientation = config.get("diagrams", {}).get("style", "TD")

    try:
        files_task_description = f"Préparation {item_path.name}"
        internal_progress = progress or (_progress(console) if show_progress else None)
        managing_progress = progress is None and internal_progress is not None
        if internal_progress:
            if managing_progress:
                internal_progress.__enter__()
            task_id = task_id or internal_progress.add_task(files_task_description, total=4)

        finder = FileFinder(str(item_path))
        files = finder.find_related_files()
        if internal_progress:
            internal_progress.advance(task_id)

        item_data = TalendItemParser(str(files["item"]), use_cache=not no_cache).parse()
        if internal_progress:
            internal_progress.advance(task_id)

        properties_data = None
        if files.get("properties"):
            properties_data = PropertiesParser(str(files["properties"])).parse()
            item_data.update(
                {
                    "author": properties_data.get("author"),
                    "created_at": properties_data.get("created_at"),
                    "modified_at": properties_data.get("modified_at"),
                    "description": properties_data.get("description", item_data.get("description")),
                }
            )
        context_data = None
        if files.get("context"):
            context_data = ContextParser(str(files["context"])).parse()
        if internal_progress:
            internal_progress.advance(task_id)

        project_root = files.get("project_root") or files.get("item").parent  # type: ignore[union-attr]

        item_data["screenshot_path"] = str(files["screenshot"]) if files.get("screenshot") else None
        item_data["project_root"] = str(project_root) if project_root else None
        item_data["item_path"] = str(files.get("item")) if files.get("item") else None

        analyzer = JobAnalyzer(
            item_data,
            properties_data,
            context_data,
            screenshot_path=files.get("screenshot"),
            diagram_type=diagram_type,
            diagram_orientation=diagram_orientation,
        )
        logger.debug("Analyse du job %s", item_data.get("name"))
        analyzed_job = analyzer.analyze()
        if internal_progress:
            internal_progress.advance(task_id)
    finally:
        if managing_progress and internal_progress:
            internal_progress.stop()
            internal_progress.__exit__(None, None, None)

    return ParsedJob(
        analyzed=analyzed_job,
        item_data=item_data,
        properties=properties_data,
        contexts=context_data,
        files=files,
        analyzer=analyzer,
    )


def _render_description(item_data: Dict[str, Any], detail: str, use_llm: bool, config: Dict[str, Any], console: Console) -> str:
    if not use_llm:
        return "Génération désactivée."

    llm_cfg = config.get("ollama", {})
    client = LlamaClient(
        llm_cfg.get("base_url", "http://localhost:11434"),
        llm_cfg.get("model", "llama3"),
        llm_cfg.get("timeout", 120),
    )
    prompt = build_job_prompt(item_data, detail_level=detail)
    try:
        return client.generate(prompt)
    except Exception as exc:  # pylint: disable=broad-except
        console.print(Panel(f"LLM indisponible : {exc}", title="Avertissement", style="yellow"))
        return f"Description non générée (LLM indisponible: {exc})."


def _write_outputs(
    analyzer: JobAnalyzer,
    markdown_content: str,
    item_data: Dict[str, Any],
    *,
    output: Optional[str],
    export_pdf: bool,
    config: Dict[str, Any],
) -> Tuple[Dict[str, Path], Path]:
    output_dir = Path(config.get("generator", {}).get("output_dir", "docs/output"))
    md_path = Path(output) if output else output_dir / f"{analyzer.job_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_content, encoding="utf-8")

    result_paths: Dict[str, Path] = {"markdown": md_path}

    if export_pdf:
        pdf_exporter = PDFExporter(str(md_path.parent))
        metadata = {
            "name": analyzer.job_name,
            "version": item_data.get("version"),
            "author": item_data.get("author"),
        }
        pdf_path = pdf_exporter.export(
            markdown_content,
            md_path.name,
            metadata=metadata,
            screenshot_path=analyzer.screenshot_path,
            stats=item_data.get("stats"),
        )
        result_paths["pdf"] = pdf_path

    json_path = md_path.parent / f"{analyzer.job_name}.json"
    json_path.write_text(json.dumps(item_data, ensure_ascii=False, indent=2), encoding="utf-8")
    result_paths["raw_json"] = json_path

    return result_paths, md_path


def generate_documentation(
    item_path: Path,
    *,
    template: Optional[str],
    export_pdf: bool,
    detail: str,
    diagram_type: str,
    use_llm: bool,
    output: Optional[str],
    no_cache: bool,
    console: Console,
    config: Dict[str, Any],
    show_progress: bool = True,
) -> Dict[str, Path]:
    managing_progress = show_progress
    progress = _progress(console) if show_progress else None
    task_id: Optional[int] = None
    try:
        if progress:
            progress.__enter__()
            task_id = progress.add_task(f"Génération {item_path.name}", total=6 + (1 if export_pdf else 0))

        parsed = _parse_job(
            item_path,
            config,
            diagram_type=diagram_type,
            detail=detail,
            no_cache=no_cache,
            console=console,
            progress=progress,
            task_id=task_id,
        )
        if progress:
            progress.advance(task_id)

        llm_description = _render_description(parsed.item_data, detail, use_llm, config, console)
        if progress:
            progress.advance(task_id)

        md_generator = MarkdownGenerator(str(TEMPLATES_DIR))
        template_name = template or _template_from_detail(detail)
        markdown_content = md_generator.generate(parsed.analyzed, llm_description, template_name)
        if progress:
            progress.advance(task_id)

        outputs, _ = _write_outputs(parsed.analyzer, markdown_content, parsed.item_data, output=output, export_pdf=export_pdf, config=config)
        if progress:
            progress.advance(task_id, advance=2 if export_pdf else 1)

        return outputs
    finally:
        if managing_progress and progress:
            progress.stop()
            progress.__exit__(None, None, None)


def _render_stats_table(stats: Dict[str, Any]) -> Table:
    table = Table(title="Statistiques", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Clé", style="bold")
    table.add_column("Valeur", justify="right")
    for key, value in stats.items():
        if isinstance(value, dict):
            table.add_row(key, json.dumps(value, ensure_ascii=False))
        else:
            table.add_row(key, str(value))
    return table


def _display_outputs(console: Console, outputs: Dict[str, Path]) -> None:
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Type")
    table.add_column("Chemin")
    for kind, path in outputs.items():
        table.add_row(kind, str(path))
    console.print(Panel(table, title="Fichiers générés", border_style="green"))


def _export_stats(console: Console, stats: Dict[str, Any], output_format: str) -> None:
    if output_format == "yaml":
        dumped = yaml.safe_dump(stats, allow_unicode=True, sort_keys=False)
        console.print(Syntax(dumped, "yaml", theme="monokai", word_wrap=True))
    else:
        dumped = json.dumps(stats, ensure_ascii=False, indent=2)
        console.print(Syntax(dumped, "json", theme="monokai", word_wrap=True))


def _list_items(directory: Path) -> List[Path]:
    return sorted(directory.rglob("*.item"))


def _select_path_with_completion(message: str, default: str = ".") -> Path:
    try:
        import readline

        def complete(text: str, state: int) -> Optional[str]:
            base = Path(default)
            candidates = [
                str(p)
                for p in base.glob(f"{text}*")
                if p.is_dir() or p.suffix == ".item"
            ]
            try:
                return candidates[state]
            except IndexError:
                return None

        readline.set_completer_delims("\t\n")
        readline.set_completer(complete)
        readline.parse_and_bind("tab: complete")
    except Exception:  # pragma: no cover - fallback silencieux
        pass

    choice = Prompt.ask(message, default=default)
    return Path(choice).expanduser().resolve()


def _wizard(ctx: CLIContext) -> None:
    console = ctx.console
    console.print(Panel("Bienvenue dans l'assistant interactif Talend Doc", border_style="cyan"))
    actions = {
        "generate": "Générer la documentation",
        "validate": "Valider un .item",
        "batch": "Batch sur un dossier",
        "stats": "Afficher les stats",
        "compare": "Comparer deux versions",
        "watch": "Surveiller un dossier",
        "quit": "Quitter",
    }
    action = Prompt.ask("Que souhaitez-vous faire ?", choices=list(actions.keys()), default="generate")
    if action == "quit":
        return

    if action in {"generate", "validate", "stats"}:
        path = _select_path_with_completion("Chemin du fichier .item", default=str(Path.cwd()))
        if action == "generate":
            template = Prompt.ask("Template (laisser vide pour défaut)", default="") or None
            detail = Prompt.ask("Niveau de détail", choices=["compact", "standard", "exhaustif"], default="standard")
            diagram = Prompt.ask("Diagramme", choices=["mermaid", "graphviz", "both"], default="mermaid")
            use_llm = Confirm.ask("Utiliser le LLM ?", default=True)
            outputs = generate_documentation(
                path,
                template=template,
                export_pdf=False,
                detail=detail,
                diagram_type=diagram,
                use_llm=use_llm,
                output=None,
                no_cache=False,
                console=console,
                config=ctx.config,
            )
            _display_outputs(console, outputs)
        elif action == "validate":
            parsed = _parse_job(path, ctx.config, console=console)
            console.print(Panel(f"{parsed.analyzer.job_name} est valide", border_style="green", title="Validation"))
        elif action == "stats":
            parsed = _parse_job(path, ctx.config, console=console)
            _export_stats(console, parsed.item_data.get("stats", {}), ctx.output_format)
            console.print(_render_stats_table(parsed.item_data.get("stats", {})))
    elif action == "batch":
        folder = _select_path_with_completion("Dossier à traiter", default=str(Path.cwd()))
        run_batch(folder, ctx)
    elif action == "compare":
        first = _select_path_with_completion("Chemin version A", default=str(Path.cwd()))
        second = _select_path_with_completion("Chemin version B", default=str(Path.cwd()))
        compare_jobs(first, second, ctx)
    elif action == "watch":
        folder = _select_path_with_completion("Dossier à surveiller", default=str(Path.cwd()))
        watch_folder(folder, ctx)


def _stats_panel(title: str, stats: Dict[str, Any]) -> Panel:
    return Panel(_render_stats_table(stats), title=title, border_style="blue")


def run_batch(folder: Path, ctx: CLIContext) -> None:
    _ensure_item_path(folder)
    items = _list_items(folder if folder.is_dir() else folder.parent)
    if not items:
        raise CliError("Aucun .item à traiter dans le dossier", suggestion="Vérifiez l'arborescence fournie.")

    console = ctx.console
    console.print(Panel(f"Batch sur {len(items)} fichiers", border_style="cyan"))
    progress = _progress(console)
    task_id = progress.add_task("Batch", total=len(items))
    results: Dict[Path, str] = {}
    failures: Dict[Path, str] = {}

    with progress:
        with ThreadPoolExecutor(max_workers=ctx.workers) as executor:
            future_map = {
                executor.submit(
                    generate_documentation,
                    item,
                    template=None,
                    export_pdf=False,
                    detail="standard",
                    diagram_type="mermaid",
                    use_llm=False,
                    output=None,
                    no_cache=False,
                    console=console,
                    config=ctx.config,
                    show_progress=False,
                ): item
                for item in items
            }
            for future in as_completed(future_map):
                item = future_map[future]
                try:
                    output = future.result()
                    results[item] = str(output.get("markdown"))
                except Exception as exc:  # pylint: disable=broad-except
                    failures[item] = str(exc)
                progress.advance(task_id)

    table = Table(box=box.SIMPLE, header_style="bold")
    table.add_column("Job")
    table.add_column("Statut")
    table.add_column("Détail")
    for item, path in results.items():
        table.add_row(item.name, "✅", path)
    for item, err in failures.items():
        table.add_row(item.name, "❌", err)

    console.print(Panel(table, title="Résultats batch", border_style="green" if not failures else "red"))


def watch_folder(folder: Path, ctx: CLIContext) -> None:
    try:
        from watchfiles import watch
    except ImportError as exc:  # pragma: no cover - dépendance optionnelle
        raise CliError("watchfiles n'est pas installé", suggestion="Ajoutez watchfiles dans requirements.txt puis pip install -r requirements.txt.") from exc

    _ensure_item_path(folder)
    console = ctx.console
    console.print(Panel(f"Surveillance de {folder}", border_style="cyan"))
    try:
        for changes in watch(folder, recursive=True):
            changed_items = [Path(path) for _, path in changes if path.endswith(".item")]
            for item in changed_items:
                console.print(f"Changement détecté sur {item}", style="yellow")
                try:
                    outputs = generate_documentation(
                        item,
                        template=None,
                        export_pdf=False,
                        detail="standard",
                        diagram_type="mermaid",
                        use_llm=False,
                        output=None,
                        no_cache=True,
                        console=console,
                        config=ctx.config,
                    )
                    _display_outputs(console, outputs)
                except CliError as error:
                    _render_error(console, error)
    except KeyboardInterrupt:
        console.print("Arrêt de la surveillance", style="bold yellow")


def compare_jobs(first: Path, second: Path, ctx: CLIContext) -> None:
    parsed_a = _parse_job(first, ctx.config, console=ctx.console, show_progress=False)
    parsed_b = _parse_job(second, ctx.config, console=ctx.console, show_progress=False)

    stats_a = parsed_a.item_data.get("stats", {})
    stats_b = parsed_b.item_data.get("stats", {})

    table = Table(title="Comparaison", box=box.SIMPLE_HEAVY, header_style="bold magenta")
    table.add_column("Métrique")
    table.add_column(first.name, justify="right")
    table.add_column(second.name, justify="right")
    keys = sorted(set(stats_a.keys()) | set(stats_b.keys()))
    for key in keys:
        table.add_row(key, str(stats_a.get(key, "-")), str(stats_b.get(key, "-")))

    ctx.console.print(Panel(table, border_style="cyan"))


def _validate_job(item_path: Path, ctx: CLIContext) -> None:
    parsed = _parse_job(item_path, ctx.config, console=ctx.console)
    ctx.console.print(Panel(f"{parsed.analyzer.job_name} est valide", border_style="green", title="Validation"))


def _stats_command(item_path: Path, ctx: CLIContext) -> None:
    parsed = _parse_job(item_path, ctx.config, console=ctx.console)
    stats = parsed.item_data.get("stats", {})
    _export_stats(ctx.console, stats, ctx.output_format)
    ctx.console.print(_stats_panel("Détails", stats))


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.option("--verbose", "verbose", is_flag=True, help="Activer les logs détaillés")
@click.option("--quiet", "quiet", is_flag=True, help="Réduire la verbosité")
@click.option("--workers", default=4, show_default=True, help="Nombre de workers pour le batch")
@click.option("--format", "output_format", type=click.Choice(["json", "yaml"]), default="json", show_default=True, help="Format de sortie pour les stats")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool, workers: int, output_format: str) -> None:
    """CLI moderne pour Talend Job Doc Generator."""

    if verbose and quiet:
        raise click.UsageError("--verbose et --quiet sont mutuellement exclusifs")

    config = load_config()
    _configure_logging(config, verbose, quiet)
    console = Console()
    ctx.obj = CLIContext(config=config, console=console, verbose=verbose, quiet=quiet, workers=workers, output_format=output_format)

    if ctx.invoked_subcommand is None:
        _wizard(ctx.obj)


@cli.command(help="Générer la documentation pour un fichier .item")
@click.argument("item_path", type=click.Path(exists=True, path_type=Path))
@click.option("--template", default=None, help="Nom du template Markdown à utiliser")
@click.option("--detail", type=click.Choice(["compact", "standard", "exhaustif"]), default="standard", show_default=True)
@click.option("--diagram", type=click.Choice(["mermaid", "graphviz", "both"]), default="mermaid", show_default=True, help="Type de diagramme à générer")
@click.option("--no-llm", is_flag=True, help="Désactiver la génération via LLM")
@click.option("--output", "-o", default=None, help="Chemin de sortie du fichier Markdown")
@click.option("--pdf", is_flag=True, help="Exporter également en PDF")
@click.option("--no-cache", is_flag=True, help="Désactiver le cache du parser .item")
@click.pass_obj
def generate(ctx: CLIContext, item_path: Path, template: Optional[str], detail: str, diagram: str, no_llm: bool, output: Optional[str], pdf: bool, no_cache: bool) -> None:
    try:
        outputs = generate_documentation(
            item_path,
            template=template,
            export_pdf=pdf,
            detail=detail,
            diagram_type=diagram,
            use_llm=not no_llm,
            output=output,
            no_cache=no_cache,
            console=ctx.console,
            config=ctx.config,
        )
        _display_outputs(ctx.console, outputs)
    except CliError as error:
        _render_error(ctx.console, error)
        sys.exit(error.exit_code)
    except Exception as exc:  # pylint: disable=broad-except
        _render_unexpected_error(ctx.console, exc)
        sys.exit(1)


@cli.command(help="Valider un fichier .item sans générer de documentation")
@click.argument("item_path", type=click.Path(exists=True, path_type=Path))
@click.pass_obj
def validate(ctx: CLIContext, item_path: Path) -> None:
    try:
        _validate_job(item_path, ctx)
    except CliError as error:
        _render_error(ctx.console, error)
        sys.exit(error.exit_code)
    except Exception as exc:  # pylint: disable=broad-except
        _render_unexpected_error(ctx.console, exc)
        sys.exit(1)


@cli.command(help="Générer la documentation pour tous les .item d'un dossier")
@click.argument("folder", type=click.Path(exists=True, path_type=Path))
@click.pass_obj
def batch(ctx: CLIContext, folder: Path) -> None:
    try:
        run_batch(folder, ctx)
    except CliError as error:
        _render_error(ctx.console, error)
        sys.exit(error.exit_code)
    except Exception as exc:  # pylint: disable=broad-except
        _render_unexpected_error(ctx.console, exc)
        sys.exit(1)


@cli.command(help="Surveiller un dossier et régénérer automatiquement")
@click.argument("folder", type=click.Path(exists=True, path_type=Path))
@click.pass_obj
def watch(ctx: CLIContext, folder: Path) -> None:  # pylint: disable=redefined-builtin
    try:
        watch_folder(folder, ctx)
    except CliError as error:
        _render_error(ctx.console, error)
        sys.exit(error.exit_code)
    except Exception as exc:  # pylint: disable=broad-except
        _render_unexpected_error(ctx.console, exc)
        sys.exit(1)


@cli.command(help="Afficher les statistiques d'un job")
@click.argument("item_path", type=click.Path(exists=True, path_type=Path))
@click.pass_obj
def stats(ctx: CLIContext, item_path: Path) -> None:
    try:
        _stats_command(item_path, ctx)
    except CliError as error:
        _render_error(ctx.console, error)
        sys.exit(error.exit_code)
    except Exception as exc:  # pylint: disable=broad-except
        _render_unexpected_error(ctx.console, exc)
        sys.exit(1)


@cli.command(help="Comparer deux versions d'un job")
@click.argument("first", type=click.Path(exists=True, path_type=Path))
@click.argument("second", type=click.Path(exists=True, path_type=Path))
@click.pass_obj
def compare(ctx: CLIContext, first: Path, second: Path) -> None:
    try:
        compare_jobs(first, second, ctx)
    except CliError as error:
        _render_error(ctx.console, error)
        sys.exit(error.exit_code)
    except Exception as exc:  # pylint: disable=broad-except
        _render_unexpected_error(ctx.console, exc)
        sys.exit(1)


def main() -> None:
    cli(standalone_mode=False)


if __name__ == "__main__":
    main()
