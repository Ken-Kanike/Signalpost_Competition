#!/usr/bin/env bash
# ==============================================================================
# 🏆 Signalpost: Autonomous Norwegian Corporate Intelligence Agent
# One-command execution wrapper conforming to Builderr Competition Guidelines
# Usage: ./run.sh <orgnr_or_jsonl_file> [output_dir]
# ==============================================================================

set -e

TARGET="${1:-923609016}"
OUTPUT_DIR="${2:-output}"

echo "=========================================================="
echo " 🏆 Signalpost Norwegian Company Research Agent"
echo " Target:     ${TARGET}"
echo " Output Dir: ${OUTPUT_DIR}"
echo "=========================================================="

# Resolve Python executable (works on Unix and Windows Git Bash)
PYTHON_CMD=""
has_required_modules() {
    "$1" -c "import rich, click, uvicorn, fastapi" 2>/dev/null
}

# 1. Try system python (works on PowerShell/CMD/Unix with proper Python)
if command -v python &>/dev/null && has_required_modules python; then
    PYTHON_CMD="python"
# 2. Try Windows Python paths on Git Bash (mount point is /mnt/c)
elif [ -x "/mnt/c/Program Files/Python312/python.exe" ] && has_required_modules "/mnt/c/Program Files/Python312/python.exe"; then
    PYTHON_CMD="/mnt/c/Program Files/Python312/python.exe"
elif [ -x "/mnt/c/Program Files/Python311/python.exe" ] && has_required_modules "/mnt/c/Program Files/Python311/python.exe"; then
    PYTHON_CMD="/mnt/c/Program Files/Python311/python.exe"
elif [ -x "/mnt/c/Program Files/Python310/python.exe" ] && has_required_modules "/mnt/c/Program Files/Python310/python.exe"; then
    PYTHON_CMD="/mnt/c/Program Files/Python310/python.exe"
# 3. Try python3 (MSYS2/Unix) only if it has required modules
elif command -v python3 &>/dev/null && has_required_modules python3; then
    PYTHON_CMD="python3"
# 4. Fallback: delegate to Windows cmd which has the correct Python on PATH
elif command -v cmd &>/dev/null; then
    cmd //c "run.bat \"${TARGET}\" \"${OUTPUT_DIR}\""
    exit $?
else
    echo "Error: Python 3.10+ with required modules not found in PATH."
    exit 1
fi

# Run the agent pipeline
"$PYTHON_CMD" main.py run "${TARGET}" --output-dir "${OUTPUT_DIR}"
