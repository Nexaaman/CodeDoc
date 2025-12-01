import difflib
from pathlib import Path
from rich.console import Console

console = Console()

def create_diff(original: str, fixed: str, filename: str) -> str:
    """
    Generate a unified diff between original and fixed strings.
    """
    original_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "".join(diff)

def apply_fix(file_path: Path, new_content: str) -> bool:
    """
    Overwrite the file with new content.
    Returns True if successful, False otherwise.
    """
    try:
        file_path.write_text(new_content, encoding="utf-8")
        return True
    except PermissionError as e:
        console.print(f"[red]Permission denied: {e}[/red]")
        return False
    except OSError as e:
        console.print(f"[red]OS error writing file: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return False