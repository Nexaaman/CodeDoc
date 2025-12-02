import os
from pathlib import Path

# Application directories
APP_NAME = "codedoc"
CODEDOC_DIR = Path.home() / ".codedoc"
MODELS_DIR = CODEDOC_DIR / "models"
LOGS_DIR = CODEDOC_DIR / "logs"
SERVER_PID_FILE = CODEDOC_DIR / "server.pid"

# Server Settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# --- MODEL REGISTRY ---


MODELS = {
    "qwen-7b": {
        "name": "Qwen2.5-Coder-7B-Instruct",
        "repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "filename": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "description": "Best overall for coding. (Rec: 6GB+ VRAM)"
    },
    "qwen-3b": {
        "name": "Qwen2.5-Coder-3B-Instruct",
        "repo": "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
        "filename": "qwen2.5-coder-3b-instruct-q5_k_m.gguf",
        "description": "Fastest. Good for quick edits. (Rec: 4GB+ VRAM)"
    },
    "deepseek-6b": {
        "name": "DeepSeek-Coder-6.7B-Instruct",
        "repo": "TheBloke/deepseek-coder-6.7B-instruct-GGUF",
        "filename": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "description": "Very stable, industry standard. (Rec: 6GB+ VRAM)"
    },
    "deepseek-r1": {
        "name": "DeepSeek-R1-Distill-Llama-8B",
        "repo": "unsloth/DeepSeek-R1-Distill-Llama-8B-GGUF",
        "filename": "DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf",
        "description": "Reasoning model. Thinks before coding. (Rec: 6GB+ VRAM - tight)"
    },
    "mistral-7b": {
        "name": "Mistral-7B-Instruct-v0.3",
        "repo": "MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF",
        "filename": "Mistral-7B-Instruct-v0.3.Q4_K_M.gguf",
        "description": "Good generalist (Docs + Code). (Rec: 6GB+ VRAM)"
    }
}

# Default Selection
DEFAULT_MODEL_KEY = "qwen-3b"

def ensure_dirs():
    """Create necessary directories if they don't exist."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)