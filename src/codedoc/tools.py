from smolagents import tool
from pathlib import Path
import os
from typing import List
from codedoc.analysis import StaticAnalyzer, Issue

# Initialize analyzer globally or per run
analyzer = StaticAnalyzer()

@tool
def list_files(directory: str) -> str:
    """
    Lists all files in the given directory recursively, ignoring hidden files (like .git).
    Args:
        directory: The path to the directory to list (use "." for current dir).
    """
    result = []
    path = Path(directory)
    if not path.exists():
        return f"Error: Directory {directory} does not exist."
    
    # Folders to explicitly ignore to save tokens
    IGNORE_DIRS = {
        '__pycache__', '.git', '.idea', '.vscode', 'venv', 'env', 
        'node_modules', 'dist', 'build', '.pytest_cache', 'site-packages', 'target', 'CodeDoc.egg-info'
    }
    
    for root, dirs, files in os.walk(path):
       
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in IGNORE_DIRS]
        
        for name in files:
            if not name.startswith('.') and not name.endswith(('.pyc', '.exe', '.dll', '.so', '.dylib', '.pyo')):
               
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, start=directory)
                result.append(rel_path)
                

    if len(result) > 500:
        return "\n".join(result[:500]) + f"\n... (and {len(result)-500} more files)"
        
    return "\n".join(result)

@tool
def read_file(file_path: str) -> str:
    """
    Reads the content of a specific file.
    Args:
        file_path: The path to the file to read.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        
        MAX_CHARS = 40000 
        
        if len(content) > MAX_CHARS:
            return (
                f"--- START OF FILE: {file_path} ---\n"
                f"{content[:MAX_CHARS]}\n"
                f"\n... [TRUNCATED: File too large. Use specific line reading or grep] ...\n"
                f"--- END OF FILE ---"
            )
            
        return f"{content}"
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(file_path: str, content: str) -> str:
    """
    Writes content to a file. Overwrites existing content.
    Args:
        file_path: The path to the file to write.
        content: The full content to write to the file.
    """
    try:
        path = Path(file_path.replace('\\', '/'))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return f"✓ Successfully wrote to {path}"
    except Exception as e:
        return f"✗ Error writing {file_path}: {e}"

@tool
def search_in_files(pattern: str, directory: str = ".") -> str:
    """
    Searches for a regex pattern in all files in the directory (like grep).
    Use this to find where functions or variables are defined without reading every file.
    Args:
        pattern: The regex pattern to search for (e.g. 'def process_data').
        directory: The directory to search in.
    """
    results = []
    file_list = list_files(directory).split('\n')
    
    try:
        regex = re.compile(pattern)
        for file_path in file_list:
            if not file_path.strip() or "..." in file_path: continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{file_path}:{i}: {line.strip()}")
            except:
                continue
    except re.error as e:
        return f"Invalid Regex: {e}"

    if not results: return "No matches found."
    return "\n".join(results[:50])

@tool
def inspect_code_structure(file_path: str) -> str:
    """
    Returns only function/class definitions. Useful for large files.
    Args:
        file_path: The file to inspect.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        structure = [f"{i+1}: {line.strip()}" for i, line in enumerate(lines) 
                     if line.strip().startswith(("def ", "class ", "@", "export "))]
        return "\n".join(structure) if structure else "No definitions found."
    except Exception as e:
        return f"Error: {e}"