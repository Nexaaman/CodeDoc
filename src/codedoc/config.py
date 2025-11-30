import os
from pathlib import Path

# Application directories
APP_NAME = "codedoc"
CODEDOC_DIR = Path.home() / ".codedoc"
MODELS_DIR = CODEDOC_DIR / "models"
LOGS_DIR = CODEDOC_DIR / "logs"
SERVER_PID_FILE = CODEDOC_DIR / "server.pid"

# Default Model (A good balance of speed/quality for coding)
# Using Qwen2.5-Coder-3B-Instruct as it's state-of-the-art for small coding models
DEFAULT_REPO = "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF"
DEFAULT_FILENAME = "qwen2.5-coder-3b-instruct-q4_k_m.gguf"

# Server Settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

def ensure_dirs():
    """Create necessary directories if they don't exist."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)