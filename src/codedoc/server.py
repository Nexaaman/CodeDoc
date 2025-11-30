import sys
import subprocess
import time
import os
import signal
import requests
import psutil
from pathlib import Path
from rich.console import Console
from codedoc.config import LOGS_DIR, SERVER_PID_FILE, DEFAULT_HOST, DEFAULT_PORT

console = Console()

def is_server_running(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Check if the API is responsive."""
    try:
        response = requests.get(f"http://{host}:{port}/v1/models", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False

def get_pid():
    """Read the PID from file."""
    if SERVER_PID_FILE.exists():
        try:
            return int(SERVER_PID_FILE.read_text().strip())
        except ValueError:
            return None
    return None

def start_server(model_path: Path, host=DEFAULT_HOST, port=DEFAULT_PORT, n_gpu=-1, ctx=16384):
    """Start the llama.cpp server as a detached subprocess."""
    
    if is_server_running(host, port):
        console.print(f"[yellow]Server is already running on {host}:{port}[/yellow]")
        return True

    cmd = [
        sys.executable, "-m", "llama_cpp.server",
        "--model", str(model_path),
        "--host", host,
        "--port", str(port),
        "--n_gpu_layers", "999",  # Offload as many layers as fit
        "--n_ctx", str(ctx),
        "--chat_format", "chatml", # Crucial for Qwen/DeepSeek
        # "--type_k", "q8_0",  
        # "--type_v", "q8_0",  
    ]

    log_file_path = LOGS_DIR / "server.log"
    
    with open(log_file_path, "w") as log_file:
        # start_new_session=True creates a new process group, detaching it from the CLI
        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )

    # Save PID
    SERVER_PID_FILE.write_text(str(process.pid))
    
    # Wait for server to be ready
    with console.status(f"[bold green]Booting AI Server (PID: {process.pid})...[/bold green]"):
        for _ in range(30): # Wait up to 30 seconds
            if is_server_running(host, port):
                console.print(f"[green]Server online at http://{host}:{port}/v1[/green]")
                return True
            time.sleep(1)
            
            # Check if process died correctly
            if process.poll() is not None:
                console.print("[bold red]Server process died immediately. Check logs.[/bold red]")
                console.print(f"Logs: {log_file_path}")
                return False

    console.print("[red]Timeout waiting for server to start.[/red]")
    return False

def stop_server():
    """Kill the server process."""
    pid = get_pid()
    if not pid:
        console.print("[yellow]No server PID found.[/yellow]")
        return

    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        console.print(f"[green]Stopped server (PID {pid})[/green]")
    except psutil.NoSuchProcess:
        console.print("[yellow]Process already gone.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error stopping server: {e}[/red]")
    finally:
        if SERVER_PID_FILE.exists():
            SERVER_PID_FILE.unlink()