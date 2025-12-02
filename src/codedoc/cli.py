import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from rich.prompt import Prompt
import time
from huggingface_hub import hf_hub_download
from codedoc.agent import WorkflowAgent
from codedoc.config import (
    ensure_dirs, MODELS_DIR, DEFAULT_MODEL_KEY, 
    DEFAULT_HOST, DEFAULT_PORT, MODELS
)
from codedoc.server import start_server, stop_server, is_server_running, get_pid
from codedoc.agent import LocalCodeAgent
from codedoc.analysis import Issue
from codedoc.patch import create_diff, apply_fix


from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
from codedoc.analysis import StaticAnalyzer
from codedoc.quality import ExternalLinter

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


@model_app.command("list")
def list_models():
    """List supported models and downloads."""
    table = Table(title="Supported Models", border_style="blue")
    table.add_column("Key", style="cyan", width=12)
    table.add_column("Name", style="white")
    table.add_column("Status", justify="center")

    for key, info in MODELS.items():
        path = MODELS_DIR / info["filename"]
        status = "[green]Downloaded[/green]" if path.exists() else "[dim]Not Found[/dim]"
        table.add_row(key, info["name"], status)
    
    console.print(table)
    console.print("\nUsage: [bold]codedoc model download <key>[/bold]")

@model_app.command("download")
def download_model(
    key: str = typer.Argument(DEFAULT_MODEL_KEY, help="Model key (e.g. qwen-7b, deepseek-6b)"),
):
    """Download a model by key."""
    if key not in MODELS:
        console.print(f"[red]Unknown model key: {key}[/red]")
        console.print("Run 'codedoc model list' to see available models.")
        raise typer.Exit(1)
        
    info = MODELS[key]
    console.print(Panel(f"Downloading [bold cyan]{info['name']}[/bold cyan]", title="Model Manager"))
    
    try:
        path = hf_hub_download(
            repo_id=info["repo"],
            filename=info["filename"],
            local_dir=MODELS_DIR,
        )
        console.print(f"[bold green]✔ Download Complete![/bold green]")
        console.print(f"Location: {path}")
    except Exception as e:
        console.print(f"[bold red]Download failed:[/bold red] {e}")
        
# --- Server Commands ---

@app.command("serve")
def serve(
    model: Optional[str] = typer.Option(None, help="Name of GGUF file"),
    gpu_layers: int = typer.Option(-1, help="GPU layers to offload (-1 for all)"),
    ctx: int = typer.Option(32768, help="Context window size")
):
    """Start the local Inference Server."""
    if model in MODELS:
        filename = MODELS[model]["filename"]
        model_path = MODELS_DIR / filename
    else:
        model_path = MODELS_DIR / model # Try direct filename

    if not model_path.exists():
        console.print(f"[red]Model not found: {model_path}[/red]")
        console.print("[yellow]Run 'codedoc model list' to check availability.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Starting server with {model_path.name}...[/bold]")
    success = start_server(model_path, n_gpu=gpu_layers, ctx=ctx)
    if not success:
        raise typer.Exit(1)

@app.command("kill")
def kill():
    """Stop the background server."""
    stop_server()

# --- Analysis Commands ---

def create_issue_table(issues: list[Issue]) -> Table:
    table = Table(title="Static Code Analysis", border_style="blue", show_lines=True)
    table.add_column("Line", style="cyan", justify="right", width=6)
    table.add_column("Sev", justify="center", width=8)
    table.add_column("Issue", style="white")

    severity_colors = {"HIGH": "bold red", "MEDIUM": "yellow", "LOW": "green"}

    if not issues:
        table.add_row("-", "OK", "[green]No static issues found.[/green]")
    else:
        for issue in issues:
            sev_style = severity_colors.get(issue.severity, "white")
            table.add_row(
                str(issue.line), 
                f"[{sev_style}]{issue.severity}[/{sev_style}]", 
                issue.message
            )
    return table

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
    
    with console.status("[bold cyan]Scanning code structure & Reasoning...[/bold cyan]", spinner="dots8Bit"):
        start_time = time.time()
        result = agent.analyze_file(str(file))
        duration = time.time() - start_time

    if isinstance(result, str) and result.startswith("Error"):
        console.print(f"[bold red]{result}[/bold red]")
        raise typer.Exit(1)

    # 1. Show Static Issues Table
    static_issues = result.get("static_issues", [])
    table = create_issue_table(static_issues)
    console.print(table)
    console.print("")

    # 2. Show LLM Analysis
    console.print(Panel(
        Markdown(result.get("llm_response", "")), 
        title=f"🧠 AI Insights ({duration:.1f}s)", 
        border_style="magenta",
        padding=(1, 2)
    ))
    
    
@app.command("fix")
def fix(
    file: Path = typer.Argument(..., help="File to fix"),
    interactive: bool = typer.Option(True, "--interactive/--auto", help="Ask confirmation before applying patch")
):
    """Analyze, fix, and patch a file automatically."""
    if not file.exists():
        console.print(f"[red]File {file} does not exist.[/red]")
        raise typer.Exit(1)
        
    if not is_server_running():
        console.print("[red]Server is not running. Execute 'codedoc serve' first.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]🔧 Attempting to fix {file.name}...[/bold blue]")
    agent = LocalCodeAgent()

    # 1. Get Fixes
    with console.status("[bold cyan]Agent is fixing code...[/bold cyan]", spinner="dots8Bit"):
        original_content = file.read_text(encoding="utf-8")
        fixed_content = agent.fix_file(str(file))

    if not fixed_content or fixed_content == original_content:
        console.print("[yellow]No changes suggested by the agent.[/yellow]")
        return

    # 2. Generate Diff
    diff = create_diff(original_content, fixed_content, file.name)
    
    if not diff:
        console.print("[yellow]No differences found between original and fixed code.[/yellow]")
        return
    
    # 3. Show Diff
    console.print(Panel(
        Syntax(diff, "diff", theme="monokai", word_wrap=True),
        title=f"Proposed Patch for {file.name}",
        border_style="yellow"
    ))
    
    
    # Show explanation
    console.print("\n[bold cyan]📝 What changed:[/bold cyan]")
    console.print("The patch above shows suggested improvements based on static analysis and best practices.")
    console.print("")

    # 4. Apply Logic
    if interactive:
        confirm = typer.confirm("Do you want to apply this patch?")
        if not confirm:
            console.print("[yellow]Patch discarded.[/yellow]")
            raise typer.Abort()
    
    if apply_fix(file, fixed_content):
        console.print(f"[bold green]✔ Successfully patched {file.name}[/bold green]")
    else:
        console.print(f"[bold red]❌ Failed to write to {file.name}[/bold red]")
        raise typer.Exit(1)
    
    
@app.command("task")
def task(
    prompt: str = typer.Argument(..., help="Describe what you want the agent to do"),
):
    """
    Run a multi-step agent workflow (Plan -> Analyze -> Fix).
    Example: codedoc task "Add a new 'delete' command to cli.py and update utils"
    """
    if not is_server_running():
        console.print("[red]Server is not running. Execute 'codedoc serve' first.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]🤖 Received Task:[/bold blue] {prompt}")
    
    agent = WorkflowAgent()
    agent.run_workflow(prompt)
    
@app.command("chat")
def chat():
    """
    Start an interactive chat session with the CodeDoc Orchestrator.
    """
    if not is_server_running():
        console.print("[red]Server is not running. Execute 'codedoc serve' first.[/red]")
        raise typer.Exit(1)

    from codedoc.agent import ChatOrchestrator
    
    console.print(Panel(
        "[bold green]CodeDoc Interactive Orchestrator[/bold green]\n"
        "Type 'exit', 'quit', or 'bye' to leave.\n"
        "commands: 'analyze <file>', 'fix <file>', or natural language.", 
        border_style="green"
    ))

    orchestrator = ChatOrchestrator()
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
                
            if not user_input.strip():
                continue

            # Show thinking spinner
            with console.status("[bold magenta]CodeDoc is thinking...[/bold magenta]", spinner="dots"):
                response = orchestrator.chat_turn(user_input)

            # Print Agent Response
            console.print(Panel(Markdown(response), title="CodeDoc", border_style="blue"))

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            
            
@app.command("score")
def score(
    file: Path = typer.Argument(..., help="Python file to score"),
):
    """
    Calculate a comprehensive Code Quality Score (0-100) and run linters.
    """
    if not file.exists():
        console.print(f"[red]File {file} does not exist.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]📊 Analyzing Health of {file.name}...[/bold blue]")

    # 1. Run Internal Analysis
    analyzer = StaticAnalyzer()
    try:
        content = file.read_text(encoding="utf-8")
        results = analyzer.scan(content, str(file))
        internal_score = results["score"]
        metrics = results["metrics"]
        issues = results["issues"]
    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")
        raise typer.Exit(1)

    # 2. Run External Linters (Parallel-ish via helper)
    with console.status("[bold magenta]Running external tools (Ruff/Black)...[/bold magenta]"):
        ruff_res = ExternalLinter.run_ruff(str(file))
        black_res = ExternalLinter.run_black_check(str(file))

    # --- VISUALIZATION DASHBOARD ---

    # 1. Score Panel
    score_color = "green" if internal_score >= 80 else "yellow" if internal_score >= 50 else "red"
    score_panel = Panel(
        f"[bold {score_color} try='center' size=50]{internal_score}/100[/bold {score_color}]\n\n"
        f"Issues Found: {len(issues)}\n"
        f"Functions: {len(metrics)}",
        title="Code Quality Score",
        border_style=score_color
    )

    # 2. Complexity Table
    c_table = Table(title="Cyclomatic Complexity", border_style="cyan", show_edge=False)
    c_table.add_column("Function", style="white")
    c_table.add_column("Complex", justify="right")
    c_table.add_column("Lines", justify="right")
    c_table.add_column("Args", justify="right")
    
    for m in metrics:
        c_color = "red" if m.complexity > 10 else "green"
        c_table.add_row(m.name, f"[{c_color}]{m.complexity}[/{c_color}]", str(m.length), str(m.args_count))
        
    if not metrics:
        c_table.add_row("No functions found", "-", "-", "-")

    # 3. Issues Panel
    if issues:
        issue_text = "\n".join([f"[{i.severity}] L{i.line}: {i.message}" for i in issues])
    else:
        issue_text = "[green]No static issues detected![/green]"
    
    issues_panel = Panel(issue_text, title="Static Analysis Issues", border_style="yellow")

    # 4. External Tools Panel
    ext_text = ""
    
    # Ruff
    if ruff_res["status"] == "missing":
        ext_text += "[dim]• Ruff not installed (pip install ruff)[/dim]\n"
    elif ruff_res["status"] == "ok":
        ext_text += "[green]• Ruff: Pass[/green]\n"
    else:
        ext_text += "[red]• Ruff: Failed[/red]\n"
        
    # Black
    if black_res["status"] == "missing":
        ext_text += "[dim]• Black not installed (pip install black)[/dim]\n"
    elif black_res["status"] == "ok":
        ext_text += "[green]• Black: Formatted[/green]\n"
    else:
        ext_text += "[yellow]• Black: Formatting needed[/yellow]\n"
        
    ext_panel = Panel(ext_text, title="External Tools", border_style="blue")

    # RENDER GRID
    console.print(Panel(
        Columns([score_panel, ext_panel]),
        title=f"Dashboard: {file.name}",
        subtitle="Run 'codedoc fix' to resolve issues automatically"
    ))
    console.print(Columns([c_table, issues_panel]))

    # Print External Details if failures
    if ruff_res["status"] == "issue":
        console.print(Panel(ruff_res["output"], title="Ruff Details", border_style="red", expand=False))
    
@app.command("status")
def status():
    """Check the health and status of the CodeDoc server."""
    from codedoc.config import DEFAULT_HOST, DEFAULT_PORT, MODELS_DIR, SERVER_PID_FILE
    import psutil
    from rich.table import Table
    
    console.print(Panel("CodeDoc System Status", style="bold cyan"))
    
    # 1. Check Server Status
    if is_server_running(DEFAULT_HOST, DEFAULT_PORT):
        server_status = "[bold green]✓ ONLINE[/bold green]"
        server_url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/v1"
    else:
        server_status = "[bold red]✗ OFFLINE[/bold red]"
        server_url = "[dim]N/A[/dim]"
    
    # 2. Check PID
    pid = get_pid()
    if pid:
        try:
            process = psutil.Process(pid)
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            pid_info = f"[cyan]{pid}[/cyan] (CPU: {cpu_percent:.1f}%, RAM: {memory_mb:.0f}MB)"
        except psutil.NoSuchProcess:
            pid_info = f"[red]{pid} (dead)[/red]"
    else:
        pid_info = "[dim]No PID file[/dim]"
    
    # 3. Check Models
    model_files = list(MODELS_DIR.glob("*.gguf"))
    if model_files:
        model_info = f"[green]{len(model_files)} model(s)[/green]"
        model_list = "\n".join([f"  • {f.name}" for f in model_files[:3]])
        if len(model_files) > 3:
            model_list += f"\n  ... and {len(model_files) - 3} more"
    else:
        model_info = "[yellow]No models found[/yellow]"
        model_list = "  [dim]Run 'codedoc model download' first[/dim]"
    
    # 4. Create Status Table
    table = Table(show_header=False, border_style="blue", padding=(0, 2))
    table.add_column("Component", style="bold white", width=20)
    table.add_column("Status", style="white")
    
    table.add_row("Server", server_status)
    table.add_row("Endpoint", server_url)
    table.add_row("Process", pid_info)
    table.add_row("Models", model_info)
    
    console.print(table)
    console.print()
    
    # 5. Show Model Details
    console.print("[bold]Available Models:[/bold]")
    console.print(model_list)
    
    # 6. Quick Actions
    console.print()
    if not is_server_running():
        console.print("[yellow]💡 Tip: Start the server with 'codedoc serve'[/yellow]")
    elif not model_files:
        console.print("[yellow]💡 Tip: Download a model with 'codedoc model download'[/yellow]")
    else:
        console.print("[green]✓ System ready! Try 'codedoc analyze <file>' or 'codedoc fix <file>' or 'codedoc task <prompt>' or 'codedoc chat' [/green]")


if __name__ == "__main__":
    app()
