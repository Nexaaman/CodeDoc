import subprocess
import shutil
from typing import Dict, Optional

class ExternalLinter:
    """Interface for running external CLI tools like Ruff, Black, etc."""
    
    @staticmethod
    def _run_tool(command: list) -> Dict[str, str]:
        if not shutil.which(command[0]):
            return {"status": "missing", "output": f"{command[0]} not installed"}
        
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return {
                "status": "ok" if result.returncode == 0 else "issue",
                "output": result.stdout + result.stderr
            }
        except Exception as e:
            return {"status": "error", "output": str(e)}

    @classmethod
    def run_ruff(cls, file_path: str) -> Dict[str, str]:
        # ruff check --output-format=text <file>
        return cls._run_tool(["ruff", "check", "--output-format=text", file_path])

    @classmethod
    def run_black_check(cls, file_path: str) -> Dict[str, str]:
        # black --check --diff <file>
        return cls._run_tool(["black", "--check", "--diff", file_path])
    
    @classmethod
    def run_flake8(cls, file_path: str) -> Dict[str, str]:
        return cls._run_tool(["flake8", file_path])