@echo off
echo [INFO] Installing CodeDoc with NVIDIA GPU Support...

:: 1. Set Flags for CUDA compilation
set CMAKE_ARGS=-DGGML_CUDA=on
set FORCE_CMAKE=1

:: 2. Uninstall any existing CPU-only version to avoid conflicts
pip uninstall -y llama-cpp-python

:: 3. Install dependencies from pyproject.toml (this will pick up the flags)
pip install -e .

echo.
echo [SUCCESS] Installation complete. 
echo Run 'codedoc status' to verify dependencies.
pause