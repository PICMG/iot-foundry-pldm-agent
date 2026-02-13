#!/usr/bin/env bash
set -euo pipefail

# Quick demo: scan devices -> generate mockup -> launch Redfish Mockup Server
# Usage: tools/run_demo.sh [DEST_DIR]

DEST=${1:-/tmp/generated_mockup}

ROOT=$(dirname "$0")
CLI="$ROOT/pldm-mapping-wizard/pldm_mapping_wizard/cli.py"
COLLECT_OUTPUT="/tmp/pdr_and_fru_records.json"
MOCKUP_SERVER_DIR="$ROOT/Redfish-Mockup-Server"
SERVER_PY="$MOCKUP_SERVER_DIR/redfishMockupServer.py"

echo "1) Scanning devices and generating mockup into: ${DEST}"
python3 "$CLI" scan-and-generate -c "$COLLECT_OUTPUT" -d "$DEST" --no-auto-select

echo "2) Checking server dependencies (grequests)"
if ! python3 - <<'PY' >/dev/null 2>&1
import importlib, sys
spec = importlib.util.find_spec('grequests')
sys.exit(0 if spec else 1)
PY
then
  echo "Missing dependency 'grequests'. Install with:" >&2
  echo "  python3 -m pip install -r $MOCKUP_SERVER_DIR/requirements.txt" >&2
  echo "Then run:" >&2
  echo "  python3 $SERVER_PY $DEST" >&2
  exit 1
fi

echo "3) Launching Redfish Mockup Server (foreground). Press Ctrl-C to stop." 
python3 "$SERVER_PY" "$DEST"
