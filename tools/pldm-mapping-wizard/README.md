# PLDM Mapping Wizard

Interactive tool for configuring PDR-to-Redfish mappings for the IoT Foundry PLDM Agent.

## Problem Statement

The IoT.2 specification requires mapping PLDM PDR (Platform Descriptor Records) data to Redfish resources. While the spec defines standard mappings, real-world deployments need customization for:
- OEM-specific sensor types and units
- Custom entity types and naming
- Vendor-specific FRU data structures
- Non-standard threshold mappings
- Device-specific aggregations

Manually editing JSON mapping configuration is error-prone and requires deep knowledge of both PLDM and Redfish schemas.

## Solution: Interactive Wizard

A separate command-line tool that guides users through the mapping configuration process:

1. **Discovers** PDRs and FRU data from connected endpoints
2. **Learns** target Redfish schema from mockups or live systems
3. **Suggests** mappings based on IoT.2 standard patterns
4. **Validates** mappings against both PLDM and Redfish schemas
5. **Generates** ready-to-use configuration files
6. **Documents** custom mappings with rationale

## Workflow

```
┌─────────────────┐
│ 1. Connection   │ → Load config.json, connect to endpoints
└────────┬────────┘
         │
┌────────▼────────┐
│ 2. Discovery    │ → Retrieve all PDRs and FRU records
└────────┬────────┘
         │
┌────────▼────────┐
│ 3. Redfish      │ → Load target Redfish schema/mockup
│    Context      │
└────────┬────────┘
         │
┌────────▼────────┐
│ 4. Interactive  │ → For each PDR:
│    Mapping      │    - Show PLDM data structure
│                 │    - Suggest Redfish resource
│                 │    - Map fields interactively
│                 │    - Handle transforms (units, enums)
└────────┬────────┘
         │
┌────────▼────────┐
│ 5. Validation   │ → Test mappings against schemas
└────────┬────────┘
         │
┌────────▼────────┐
│ 6. Output       │ → Generate:
│                 │    - pdr_redfish_mappings.json
│                 │    - mapping_documentation.md
│                 │    - validation_report.json
└─────────────────┘
```

## Technology Stack

- **Language**: Python 3.10+
  - Rich ecosystem for PLDM/MCTP/Redfish
  - jsonschema, jmespath libraries available
  - Easy prototyping

- **CLI Framework**: Click
  - Subcommands for discover, map, validate, export
  - Progress bars and rich output

- **UI**: Rich library
  - Tables for PDR display
  - Interactive prompts with validation
  - Syntax highlighting for JSON

- **Validation**: jsonschema
  - DMTF Redfish schemas
  - Custom PLDM schema rules

## Code Structure

```
tools/pldm-mapping-wizard/
├── README.md                    # This file
├── requirements.txt
├── pldm_mapping_wizard/
│   ├── __init__.py
│   ├── cli.py                   # Click commands
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── pdr_retriever.py    # GetPDRRepositoryInfo, GetPDR
│   │   ├── fru_reader.py       # FRU data parsing
│   │   └── endpoint_probe.py   # Endpoint enumeration
│   ├── mapping/
│   │   ├── __init__.py
│   │   ├── interactive.py      # Rich-based UI for field mapping
│   │   ├── suggestions.py      # IoT.2 standard mapping suggestions
│   │   ├── transforms.py       # Unit conversions, enum mappings
│   │   └── validators.py       # Mapping rule validation
│   ├── redfish/
│   │   ├── __init__.py
│   │   ├── schema_loader.py    # Load DMTF schemas
│   │   └── resource_builder.py # Generate Redfish JSON from mappings
│   └── output/
│       ├── __init__.py
│       ├── config_writer.py    # Write pdr_redfish_mappings.json
│       └── doc_generator.py    # Generate mapping documentation
└── tests/
    └── ...
```

## Example Usage

### Full Interactive Session

```bash
$ pldm-mapping-wizard --config /etc/iot-foundry/config.json

🔍 Discovering PLDM endpoints...
   ✓ Found 2 endpoints (EID 8, EID 9)

📥 Retrieving PDRs...
   ✓ EID 8: 47 PDRs (23 sensors, 12 effecters, 4 FRU records)
   ✓ EID 9: 31 PDRs (18 sensors, 8 effecters, 2 FRU records)

📚 Loading Redfish schemas...
   ✓ Loaded: Chassis, Sensor, Control, Assembly

═══════════════════════════════════════════════════════════
Mapping PDR: Numeric Sensor (ID 5)
───────────────────────────────────────────────────────────
Name: "CPU_TEMP"
Entity: Physical Processor (ID 3)
Unit: Degrees C
Range: 0-125
Thresholds: Warning=80, Critical=95, Fatal=105
───────────────────────────────────────────────────────────

Suggested Redfish Resource:
  Type: Sensor
  Collection: /redfish/v1/Chassis/Node_8/Sensors
  Id: SENSOR_ID_5

Map this sensor? [Y/n]: y
Redfish sensor Id [SENSOR_ID_5]: CPU_TEMP
Reading units [Cel]: 
Upper threshold warning [80.0]: 
Upper threshold critical [95.0]: 
Upper threshold fatal [105.0]: 

✓ Mapped: CPU_TEMP → /redfish/v1/Chassis/Node_8/Sensors/CPU_TEMP

═══════════════════════════════════════════════════════════
Mapping PDR: State Effecter (ID 1)
───────────────────────────────────────────────────────────
Name: "GLOBAL_INTERLOCK"
Entity: I/O Module (ID 12)
States: 0=Deasserted, 1=Asserted
───────────────────────────────────────────────────────────

Suggested Redfish Resource:
  Type: Control
  Collection: /redfish/v1/Chassis/Node_8/Controls
  Id: EFFECTER_ID_1

Map this effecter? [Y/n]: y
Redfish control Id [EFFECTER_ID_1]: GlobalInterlock
Control type [Percent|Frequency|Duty]: (custom binary control)

✓ Mapped: GlobalInterlock → /redfish/v1/Chassis/Node_8/Controls/GlobalInterlock

... (continue for all PDRs)

✅ Mapping complete! 54 PDRs mapped to Redfish resources.

📝 Generating output files...
   ✓ pdr_redfish_mappings.json (12.3 KB)
   ✓ mapping_documentation.md (8.7 KB)
   ✓ validation_report.json (2.1 KB)

Run validation:
  $ pldm-mapping-wizard validate --mappings pdr_redfish_mappings.json

Test with agent:
  $ iot-foundry-pldm-agent --config config.json --mappings pdr_redfish_mappings.json
```

### Non-Interactive Mode (Automation)

```bash
# Use defaults from IoT.2 spec
$ pldm-mapping-wizard generate --config config.json --defaults iot2 \
    --output mappings.json

# Apply custom template
$ pldm-mapping-wizard generate --config config.json --template oem_vendor.yaml \
    --output mappings.json
```

## Output Format: pdr_redfish_mappings.json

```json
{
  "version": "1.0",
  "generated": "2026-02-05T14:23:01Z",
  "endpoints": [
    {
      "eid": 8,
      "chassis_resource": "/redfish/v1/Chassis/Node_8",
      "sensors": [
        {
          "pdr_id": 5,
          "pdr_type": "numeric_sensor",
          "sensor_id": 5,
          "pldm_name": "CPU_TEMP",
          "entity_type": 3,
          "entity_instance": 0,
          "redfish_id": "CPU_TEMP",
          "redfish_uri": "/redfish/v1/Chassis/Node_8/Sensors/CPU_TEMP",
          "field_mappings": {
            "reading": {
              "source": "sensor_reading",
              "transform": "pldm_to_real",
              "scale": "pdr.resolution"
            },
            "readingUnits": {
              "source": "constant",
              "value": "Cel"
            },
            "thresholds.upperCaution.reading": {
              "source": "pdr.threshold_warning_high",
              "transform": "pldm_to_real",
              "scale": "pdr.resolution"
            }
          }
        }
      ],
      "controls": [
        {
          "pdr_id": 1,
          "pdr_type": "state_effecter",
          "effecter_id": 1,
          "pldm_name": "GLOBAL_INTERLOCK",
          "redfish_id": "GlobalInterlock",
          "redfish_uri": "/redfish/v1/Chassis/Node_8/Controls/GlobalInterlock",
          "control_type": "Duty",
          "field_mappings": {
            "controlPercent": {
              "source": "effecter_state",
              "transform": "state_to_percent",
              "map": {"0": 0.0, "1": 100.0}
            }
          }
        }
      ],
      "fru_mappings": {
        "chassis_fields": {
          "Manufacturer": {
            "source": "fru.chassis_part_number",
            "transform": "extract_manufacturer"
          },
          "SerialNumber": {
            "source": "fru.chassis_serial_number"
          },
          "PartNumber": {
            "source": "fru.chassis_part_number"
          }
        }
      }
    }
  ]
}
```

## Integration with Main Agent

The wizard generates configuration consumed by the PLDM agent's mapping engine:

1. **Startup**: Agent loads `pdr_redfish_mappings.json` alongside `config.json`
2. **PDR Discovery**: Agent retrieves PDRs from endpoints (same as wizard)
3. **Mapping Engine**: Applies field transformations from mapping config
4. **Resource Generation**: Creates Redfish resources with mapped data
5. **Updates**: Sensor readings → Redfish sensor updates via field mappings

The wizard is **development/setup time** tool. The agent **runtime** uses its output.

## Implementation Phases

### Phase 1: PDR Discovery (Week 1)
- Connect to endpoints via config.json
- Implement GetPDRRepositoryInfo command
- Implement GetPDR command with pagination
- Parse and display PDR contents (numeric sensor, state sensor, etc.)
- Read and parse FRU data

### Phase 2: Interactive Mapping (Week 2)
- Rich UI for PDR display
- Field-by-field mapping prompts
- IoT.2 default suggestions
- Basic transform support (unit conversions)
- Output pdr_redfish_mappings.json

### Phase 3: Validation & Testing (Week 3)
- JSON schema validation
- Redfish schema compliance checks
- Test against live endpoints
- Error reporting and diagnostics

### Phase 4: Advanced Features (Week 4+)
- Templates for common configurations
- Batch mode for automation
- Diff/merge existing mappings
- OEM extension support

## Benefits

✅ **Correctness**: Validates mappings against both schemas  
✅ **Speed**: Minutes vs hours of manual configuration  
✅ **Discoverability**: Shows what's actually available from devices  
✅ **Documentation**: Auto-generates mapping rationale  
✅ **Maintainability**: Easy to update when devices change  
✅ **Onboarding**: New users can configure without deep PLDM knowledge

## References

- [IoT.2 Specification](../../references/PICMG_IOT_2_R1_0.pdf) - Standard PLDM-to-Redfish mappings
- [CONFIG.md](../../CONFIG.md) - Endpoint configuration
- [TRANSPORT.md](../../TRANSPORT.md) - PLDM transport implementation
- [Declarative Mapping Design](../../docs/pdr_mapping_design.md) (if created)

## Status

**Current**: Design/planning phase  
**Next**: Implement Phase 1 (PDR Discovery module)

