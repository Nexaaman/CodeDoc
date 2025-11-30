import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from huggingface_hub import hf_hub_download

from codedoc.config import (
    ensure_dirs, MODELS_DIR, DEFAULT_REPO, DEFAULT_FILENAME, 
    DEFAULT_HOST, DEFAULT_PORT
)
from codedoc.server import start_server, stop_server, is_server_running
from codedoc.agent import LocalCodeAgent

app = typer.Typer(
    help="CodeDoc: Your Local AI Coding Assistant",
    add_completion=False
)
console = Console()
model_app = typer.Typer(help="Manage local AI models")
app.add_typer(model_app, name="model")

@app.callback()
def main():
    """Initialize directories on every run."""
    ensure_dirs()

# --- Model Commands ---

@model_app.command("download")
def download_model(
    repo: str = typer.Option(DEFAULT_REPO, help="Hugging Face Repo ID"),
    filename: str = typer.Option(DEFAULT_FILENAME, help="GGUF Filename")
):
    """Download a GGUF model for local inference."""
    console.print(Panel(f"Downloading from [bold cyan]{repo}[/bold cyan]", title="Model Manager"))
    
    try:
        path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=MODELS_DIR,
        )
        console.print(f"[bold green]✔ Download Complete![/bold green]")
        console.print(f"Location: {path}")
    except Exception as e:
        console.print(f"[bold red]Download failed:[/bold red] {e}")

@model_app.command("list")
def list_models():
    """List available models."""
    files = list(MODELS_DIR.glob("*.gguf"))
    if not files:
        console.print("[yellow]No models found. Run 'codedoc model download' first.[/yellow]")
        return
    
    console.print(f"[bold]Found {len(files)} models:[/bold]")
    for f in files:
        size_gb = f.stat().st_size / (1024**3)
        console.print(f"• [cyan]{f.name}[/cyan] ({size_gb:.2f} GB)")

# --- Server Commands ---

@app.command("serve")
def serve(
    model: Optional[str] = typer.Option(None, help="Name of GGUF file"),
    gpu_layers: int = typer.Option(-1, help="GPU layers to offload (-1 for all)"),
    ctx: int = typer.Option(16384, help="Context window size")
):
    """Start the local Inference Server."""
    # Find model
    if not model:
        # auto-select first model if not specified
        files = list(MODELS_DIR.glob("*.gguf"))
        if not files:
            console.print("[red]No models found. Download one first![/red]")
            raise typer.Exit(1)
        model_path = files[0]
        console.print(f"[yellow]No model specified. Using: {model_path.name}[/yellow]")
    else:
        model_path = MODELS_DIR / model
        if not model_path.exists():
            console.print(f"[red]Model {model} not found in {MODELS_DIR}[/red]")
            raise typer.Exit(1)

    success = start_server(model_path, n_gpu=gpu_layers, ctx=ctx)
    if not success:
        raise typer.Exit(1)

@app.command("kill")
def kill():
    """Stop the background server."""
    stop_server()

# --- Analysis Commands (Phase 1 Goal) ---

@app.command("analyze")
def analyze(file: Path):
    """Analyze a source file for bugs and improvements."""
    if not file.exists():
        console.print(f"[red]File {file} does not exist.[/red]")
        raise typer.Exit(1)

    if not is_server_running():
        console.print("[red]Server is not running. Execute 'codedoc serve' first.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]🔍 Reading {file.name}...[/bold blue]")
    
    agent = LocalCodeAgent()
    
    with console.status("[bold green]Agent is thinking (this may take a moment)...[/bold green]", spinner="dots"):
        result = agent.analyze_file(str(file))
    
    console.print(Panel(Markdown(str(result)), title=f"Analysis: {file.name}", border_style="green"))

if __name__ == "__main__":
    app()