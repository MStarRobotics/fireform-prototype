from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from fireform.pipeline import run_pipeline
from fireform.pdf_filler import inspect_pdf_fields

app = typer.Typer(
    help="FireForm Advanced Prototype CLI",
    add_completion=False,
)
console = Console()

@app.command()
def inspect(
    template: str = typer.Argument(..., help="Path to PDF template"),
):
    """
    Inspect and print field names from a fillable PDF template.
    """
    try:
        fields = inspect_pdf_fields(template)
        console.print(f"[bold green]Fields found in {template}:[/bold green]")
        for f in fields:
            console.print(f"  - [yellow]{f}[/yellow]")
    except Exception as exc:
        console.print(f"[bold red]Failed to inspect template: {exc}[/bold red]")
        raise typer.Exit(1)

@app.command()
def process(
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Incident description text"),
    text_file: Optional[Path] = typer.Option(None, "--text-file", "-f", help="Path to text file"),
    audio: Optional[Path] = typer.Option(None, "--audio", "-a", help="Path to audio file"),
    schema_path: Path = typer.Option("schemas/incident_schema.json", "--schema", "-s", help="JSON schema path"),
    agencies: list[str] = typer.Option([], "--agency", "-A", help="Agency plugin names to generate PDFs for"),
    model: str = typer.Option("llama3.1", "--model", "-m", help="Ollama model name"),
    output_dir: Path = typer.Option("outputs", "--output-dir", "-o", help="Directory for outputs"),
    save_artifacts: bool = typer.Option(True, "--save-artifacts", help="Save run metadata and artifacts"),
    max_retries: int = typer.Option(2, "--max-retries", help="Max schema correction retries"),
):
    """
    Process an incident and generate agency-specific PDFs.
    """
    if not (text or text_file or audio):
        console.print("[bold red]Must provide --text, --text-file, or --audio[/bold red]")
        raise typer.Exit(1)

    input_text = text
    if text_file:
        input_text = text_file.read_text(encoding="utf-8")
    elif not input_text:
        input_text = None  # means we rely on audio

    template_specs = []
    for ag in agencies:
        base = Path("schemas/template_maps")
        if not base.exists():
             base = Path("agencies") / ag
        elif (base / f"{ag}.json").exists():
             spec = {
                "template_path": f"templates/{ag}_report_template.pdf",
                "mapping_path": str(base / f"{ag}.json"),
                "output_name": f"{ag}_report.pdf",
             }
             template_specs.append(spec)
             continue

        spec = {
            "template_path": f"templates/{ag}_report_template.pdf" if Path(f"templates/{ag}_report_template.pdf").exists() else str(Path("agencies") / ag / "template.pdf"),
            "mapping_path": str(Path("agencies") / ag / "field_mapping.json"),
            "output_name": f"{ag}_report.pdf",
        }
        template_specs.append(spec)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Running FireForm Pipeline...", total=None)
        try:
            artifacts = run_pipeline(
                text_input=input_text,
                audio_path=str(audio) if audio else None,
                schema_path=str(schema_path),
                template_specs=template_specs,
                output_dir=str(output_dir),
                model=model,
                max_retries=max_retries,
                save_artifacts=save_artifacts,
            )
        except Exception as exc:
            console.print(f"[bold red]Pipeline failed:[/bold red] {exc}")
            raise typer.Exit(1)

    table = Table(title="Pipeline Profiling", show_header=True, header_style="bold magenta")
    table.add_column("Stage")
    table.add_column("Duration (seconds)")
    for stage, dur in artifacts.stage_durations.items():
        table.add_row(stage, f"{dur:.3f}")
    console.print(table)
    
    console.print(f"Run ID: [blue]{artifacts.run_id}[/blue]")
    console.print(f"Extraction Model: [blue]{artifacts.model}[/blue]")
    console.print(f"Retries Used: [blue]{artifacts.retries_used}[/blue]")
    
    if artifacts.template_results:
        console.print("[bold cyan]Agency Outputs:[/bold cyan]")
        for res in artifacts.template_results:
            status_color = "green" if res.status == "success" else "red"
            console.print(f"  - {res.output_name}: [{status_color}]{res.status}[/{status_color}] (mapped {res.fields_mapped} fields)")
    
    # Check for privacy audit file 
    run_dir = Path(output_dir) / artifacts.run_id
    audit_file = run_dir / "privacy_audit.json"
    if audit_file.exists():
        console.print("[green]✓ Privacy Audit Log Written.[/green]")

def main():
    app()

if __name__ == "__main__":
    main()
