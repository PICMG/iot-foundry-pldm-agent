# PLDM Mapping Wizard - Development Status

## Project Structure

```
tools/pldm-mapping-wizard/
├── README.md                    # User-facing documentation
├── DEVELOPMENT.md              # This file - development status
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Direct dependencies
├── .gitignore
├── pldm-mapping-wizard.py      # Entry point script
├── tests.py                    # Basic tests
├── pldm_mapping_wizard/
│   ├── __init__.py
│   ├── cli.py                  # Click CLI commands (setup, validate)
│   ├── discovery/
│   │   ├── __init__.py         # PortMonitor class ✓
│   │   ├── pdr_retriever.py   # PDRRetriever class (stub)
│   │   └── fru_reader.py       # FRUReader class (stub)
│   ├── mapping/
│   │   ├── __init__.py         # DeviceMapping, MappingAccumulator ✓
│   │   ├── interactive.py      # InteractiveMapper class (stub)
│   │   ├── suggestions.py      # SuggestionEngine class (stub)
│   │   ├── transforms.py       # TransformRegistry class (stub)
│   │   └── validators.py       # MappingValidator class (stub)
│   ├── redfish/
│   │   └── __init__.py         # SchemaLoader class ✓
│   └── output/
│       └── __init__.py         # DocumentationGenerator class (stub)
```

## Implementation Status

### ✅ Completed (Phase 0 - Project Setup)

1. **Project structure**
   - `pyproject.toml` with dependencies
   - Package initialization
   - Entry point script

2. **CLI Framework** (`cli.py`)
   - Click command group with `--version` flag
   - `setup` command with `--output` option
   - `validate` command with `--mappings` option
   - Device loop infrastructure with retry handling

3. **Schema Loading** (`redfish/__init__.py`)
   - `SchemaLoader` class with caching
   - `load_schemas()` method (hardcoded list, placeholder)
   - `get_schema()` retrieval method

4. **Port Monitoring** (`discovery/__init__.py`)
   - `PortMonitor` class
   - `wait_for_device()` - user prompt and device detection
   - `_detect_port()` - find first available USB/ACM device
   - `_get_usb_address()` - extract USB hardware address from symlink

5. **Mapping Accumulation** (`mapping/__init__.py`)
   - `DeviceMapping` dataclass
   - `MappingAccumulator` class
   - `add_device()` and `save()` methods
   - Support for loading existing mappings

6. **Tests**
   - Schema loading test
   - Mapping accumulation test
   - Both passing ✓

### ✅ Completed (Phase 1A - Serial Communication)

1. **Serial Port I/O** (`serial_transport.py`)
   - `SerialPort` class with open/close/read/write
   - Configurable baudrate (default 115200)
   - Timeout handling
   - Error reporting

2. **MCTP Frame Handling** (`serial_transport.py`)
   - `MCTPFramer` class with frame/unframe operations
   - MCTP header structure: [EID][Type|Flags][Length][Payload]
   - Support for up to 65KB payloads
   - Frame validation and error handling

3. **PLDM Command Encoding** (`discovery/pldm_commands.py`)
   - `PDLMCommandEncoder` class
   - `encode_get_pdr_repository_info()` - GetPDRRepositoryInfo command
   - `encode_get_pdr()` - GetPDR command with pagination support
   - `decode_get_pdr_repository_info_response()` - Parse repository metadata
   - `decode_get_pdr_response()` - Parse PDR data
   - Complete PLDM header structure handling

4. **PDR Retrieval** (`discovery/pdr_retriever.py`)
   - `PDRRetriever` class with MCTP/PLDM integration
   - `connect()` - open serial port
   - `get_repository_info()` - query PDR repository metadata
   - `get_pdrs()` - retrieve all PDRs with pagination and retry logic
   - `disconnect()` - clean up
   - Retry on timeout/failure
   - Error reporting

5. **CLI Integration** (`cli.py`)
   - Integrated `PDRRetriever` into `setup` command
   - Device connection with retry options
   - PDR retrieval with failure handling
   - User prompts for retry/skip/quit
   - Accumulates PDR count in output

6. **Tests**
   - MCTP frame encoding/decoding test
   - PLDM command encoding test
   - PLDM response decoding test
   - All passing ✓

### ✅ Completed (Phase 1B - PDR Parsing)

1. **PDR Data Structures** (`discovery/pdr_parser.py`)
   - `PDRType` enum with all PLDM PDR types
   - `PDRHeader` dataclass for common PDR header
   - `NumericSensorPDR` dataclass with full sensor metadata
   - `StateSensorPDR` dataclass with state set definitions
   - `EntityAssociationPDR` dataclass for entity relationships

2. **PDR Parsing** (`discovery/pdr_parser.py`)
   - `PDRParser` class with static parsing methods
   - `parse_header()` - Extract PDR header (8 bytes)
   - `parse_numeric_sensor()` - Parse numeric sensor PDR with thresholds
   - `parse_state_sensor()` - Parse state sensor PDR with state values
   - `parse_pdr()` - Generic PDR parser that auto-detects type
   - Support for sequential PDR parsing (iterate through buffer)

3. **PDR Parsing Integration** (`discovery/pdr_retriever.py`)
   - Updated `get_pdrs()` to parse retrieved binary data
   - Accumulate raw PDR data into buffer
   - Parse buffer into structured PDR objects
   - Return list of parsed PDR dictionaries

4. **CLI PDR Display** (`cli.py`)
   - Display PDR breakdown (sensors, effecters, entities, etc.)
   - Count by type
   - Show summary before saving

5. **Tests**
   - PDR header parsing test
   - Generic PDR parsing test
   - Numeric sensor PDR parsing test
   - Sequential PDR parsing test
   - All passing ✓

### 🚧 Phase 1C+ Stubs (Ready for Implementation)

These modules have basic class and method signatures:

1. **FRU Reading** (`discovery/fru_reader.py`)
   - `FRUReader` class
   - Method: `read_fru(fru_record_set_identifier)`
   - **TODO**: Implement GetFRURecordByOption command

2. **Interactive Mapping** (`mapping/interactive.py`)
   - `InteractiveMapper` class
   - Methods: `display_pdr()`, `prompt_mapping()`
   - **TODO**: Implement Rich table display for PDR details
   - **TODO**: Implement interactive prompts for field mapping

3. **Mapping Suggestions** (`mapping/suggestions.py`)
   - `SuggestionEngine` class
   - Method: `suggest_mapping(pdr)`
   - **TODO**: Implement IoT.2 standard mapping logic

4. **Data Transforms** (`mapping/transforms.py`)
   - `TransformRegistry` class
   - Methods: `_pldm_to_real()`, `_state_to_percent()`, `apply()`
   - Skeleton: transform registration framework complete
   - **TODO**: Add unit conversion transforms
   - **TODO**: Add enum/state mapping transforms

5. **Validation** (`mapping/validators.py`)
   - `MappingValidator` class
   - Method: `validate_mapping(mapping)`
   - **TODO**: Implement JSON schema validation
   - **TODO**: Implement Redfish schema compliance checks

6. **Documentation Generation** (`output/__init__.py`)
   - `DocumentationGenerator` class
   - Method: `generate(devices)`
   - **TODO**: Implement markdown doc generation

### 📋 Next Steps

**Phase 1B+: PDR Parsing**
- Parse retrieved PDR binary data into structured records
- Distinguish PDR types (numeric sensor, state sensor, FRU, entity, etc.)
- Extract sensor/effecter metadata
- Build list of discoverable resources

**Phase 2: Interactive Mapping UI**
- Wire `InteractiveMapper` into CLI
- Display each PDR with Rich tables
- Prompt user for Redfish resource mapping
- Wire suggestions and transforms

**Phase 3: Validation & Testing**
- Implement mapping validators
- Test end-to-end with real endpoints

## How to Run

### Install
```bash
cd tools/pldm-mapping-wizard
python3 -m pip install --break-system-packages -e .
```

### Run Tests
```bash
python3 tests.py
```

### Run CLI (will wait for device or 'q' to quit)
```bash
pldm-mapping-wizard setup --output my_mappings.json
```

## Dependencies

- `click>=8.0.0` - CLI framework
- `rich>=10.0.0` - Terminal UI (tables, prompts, colors)
- `pyserial>=3.5` - Serial port communication
- `jsonschema>=4.0.0` - JSON validation
- `pyyaml>=5.4.0` - YAML parsing (for schemas)
- `requests>=2.27.0` - HTTP (for downloading DMTF schemas)

## Notes

- Redfish schemas are currently hardcoded placeholders; Phase 2 will implement loading from DMTF
- Port detection uses simple glob matching; Phase 3 will add udev monitoring for hot-plug
- USB hardware address extraction currently parses `/dev/serial/by-id/` symlinks; robust fallback needed
