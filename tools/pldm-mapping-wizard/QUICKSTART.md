# Quick Start

## Installation

```bash
cd tools/pldm-mapping-wizard
python3 -m pip install --break-system-packages -e .
```

## Basic Usage

### Interactive Setup (Recommended)

```bash
pldm-mapping-wizard setup --output pdr_redfish_mappings.json
```

This will:
1. Load Redfish schemas (one-time)
2. Watch for USB/ACM device insertion
3. For each device:
   - Ask for connector/slot name
   - Retrieve PDRs
   - Interactively map each PDR to Redfish
4. Accumulate all mappings into output file

### Validate Existing Mappings

```bash
pldm-mapping-wizard validate --mappings pdr_redfish_mappings.json
```

## Current Limitations (Phase 1)

- PDR discovery not yet implemented (will fail to connect to real devices)
- Redfish schemas are placeholder stubs (not actual DMTF schemas)
- Port detection uses simple glob matching (no hot-plug monitoring)
- Interactive mapping prompts not yet implemented

## Project Status

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed implementation status and next steps.
