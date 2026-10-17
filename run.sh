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

# Check if Python is installed
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3.10+ is required but not found in PATH."
    exit 1
fi

# Run the agent pipeline
$PYTHON_CMD main.py run "${TARGET}" --output-dir "${OUTPUT_DIR}" "$@"
