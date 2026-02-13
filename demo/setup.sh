#!/bin/bash
# Setup script: creates venv and installs dependencies
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$DEMO_DIR/venv"

echo "========================================"
echo "  IoT Foundry PLDM Demo - Setup"
echo "========================================"

if [ -d "$VENV_DIR" ]; then
    echo "[INFO] Virtual environment already exists at $VENV_DIR"
    echo "[INFO] Skipping venv creation"
else
    echo "[INFO] Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    echo "[OK] Virtual environment created"
fi

echo "[INFO] Upgrading pip..."
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel

echo "[INFO] Installing requirements..."
"$VENV_DIR/bin/pip" install -r "$DEMO_DIR/requirements.txt"

echo "[OK] Dependencies installed:"
"$VENV_DIR/bin/pip" list

echo ""
echo "========================================"
echo "  Setup Complete"
echo "========================================"
echo "Next steps:"
echo "  1. Run: ./start.sh"
echo "  2. Select 'Configure' to scan devices and generate mockup"
echo "  3. Select 'Server' to start the Redfish Mockup Server"
echo "  4. Select 'Agent' to run the runtime agent"
echo ""
