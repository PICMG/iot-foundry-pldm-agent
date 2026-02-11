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

## Workflow: Sequential Device Configuration

```
┌──────────────────────────────┐
│ 1. Load Redfish Schemas      │ → Load DMTF schemas and cache in memory
│    (once, at startup)        │    Reused for all devices
└────────┬─────────────────────┘
         │
┌────────▼──────────────────────┐
│ 2. Port Scanning Loop and     │ → Scan selected /dev/ttyUSB* and /dev/ttyACM*
│    PDR Discovery              │ → Retrieve USB hardware address
│    (with retry on failure)    │ → Retrieve PDRs from devices  
└────────┬──────────────────────┘
         │
┌────────▼──────────────────────┐
│ 3. Select mockup              │ → Prompt user for mockup location (online?)
│                               │    
└────────┬──────────────────────┘
         │
┌────────▼──────────────────────┐
│ 4. Select Computer System     │ → Ask: Computer system and USB to connect to
│    And usb controller         │    If only one system - use that
└────────┬──────────────────────┘    If no USB Controller, create it
         │
┌────────▼──────────────────────┐
│ 6. Interactive Mapping        │ → For each PDR on this device:
│                               │    - Create missing chassis and system
│                               │    - Create Automation node and automationinstrumentation
│                               │    - Create cables
│                               │    - Interactively request input for mapping 
└────────┬──────────────────────┘
         │
┌────────▼──────────────────────┐
│ 7. Accumulate to Output       │ → Append mappings to json
│                               │   
└───────────────────────────────┘
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
│   │   ├── port_monitor.py     # Watch /dev/ttyUSB* and /dev/ttyACM*
│   │   ├── usb_info.py         # Extract USB hardware address (vid:pid:serial)
│   │   ├── pdr_retriever.py    # GetPDRRepositoryInfo, GetPDR with retry
│   │   ├── fru_reader.py       # FRU data parsing
│   │   └── endpoint_probe.py   # Connect to single port
│   ├── mapping/
│   │   ├── __init__.py
│   │   ├── interactive.py      # Rich-based UI for field mapping
│   │   ├── suggestions.py      # IoT.2 standard mapping suggestions
│   │   ├── transforms.py       # Unit conversions, enum mappings
│   │   ├── device_mapper.py    # Per-device mapping with accumulation
│   │   └── validators.py       # Mapping rule validation
│   ├── redfish/
│   │   ├── __init__.py
│   │   ├── schema_loader.py    # Load DMTF schemas (once, cached)
│   │   └── resource_builder.py # Generate Redfish JSON from mappings
│   └── output/
│       ├── __init__.py
│       ├── config_writer.py    # Append to pdr_redfish_mappings.json
│       └── doc_generator.py    # Generate mapping documentation
└── tests/
    └── ...
```

## Example Usage

### Full Interactive Session

```bash
$ pldm-mapping-wizard setup --output /etc/iot-foundry/pdr_redfish_mappings.json

� Loading Redfish schemas...
   ✓ Loaded: Chassis, Sensor, Control, Assembly (cached in memory)

🔍 Watching for USB/ACM devices...
Insert PLDM device #1 and press ENTER (or 'q' to quit): [ENTER]

  ✓ Device detected on /dev/ttyUSB0
  ✓ USB hardware address: usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_01A234B5-if00

Device identifier (connector/slot name) [Node_1]: Slot-A

📥 Retrieving PDRs from /dev/ttyUSB0...
   ✓ Found 47 PDRs (23 sensors, 12 effecters, 4 FRU records)

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
  Collection: /redfish/v1/Chassis/Slot_A/Sensors
  Id: SENSOR_ID_5

Map this sensor? [Y/n]: y
Redfish sensor Id [SENSOR_ID_5]: CPU_TEMP
Reading units [Cel]: 
Upper threshold warning [80.0]: 
Upper threshold critical [95.0]: 
Upper threshold fatal [105.0]: 

✓ Mapped: CPU_TEMP → /redfish/v1/Chassis/Slot_A/Sensors/CPU_TEMP

═══════════════════════════════════════════════════════════
... (continue for all PDRs on this device)

✅ Device "Slot-A" configured! 47 PDRs mapped to Redfish resources.
📝 Saved to pdr_redfish_mappings.json

────────────────────────────────────────────────────────────
Remove device and insert next one, then press ENTER
(or 'q' to finish): [ENTER]

🔍 Waiting for next device...
Insert PLDM device #2 and press ENTER (or 'q' to quit): [ENTER]

  ✓ Device detected on /dev/ttyUSB0
  ✓ USB hardware address: usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_02B345C6-if00

Device identifier (connector/slot name) [Node_2]: Slot-B

📥 Retrieving PDRs from /dev/ttyUSB0...
   ✓ Found 31 PDRs (18 sensors, 8 effecters, 2 FRU records)

═══════════════════════════════════════════════════════════
... (continue for all PDRs on this device)

✅ Device "Slot-B" configured! 31 PDRs mapped to Redfish resources.
📝 Appended to pdr_redfish_mappings.json

────────────────────────────────────────────────────────────
Remove device and insert next one, then press ENTER
(or 'q' to finish): q

✅ Configuration complete! 78 PDRs mapped across 2 devices.

📝 Generated output files:
   ✓ pdr_redfish_mappings.json (18.5 KB, 2 devices)
   ✓ mapping_documentation.md (11.2 KB)
   ✓ validation_report.json (3.4 KB)

Test with agent:
  $ iot-foundry-pldm-agent --config config.json --mappings pdr_redfish_mappings.json
```

### Retry on Connection Failure

```bash
Insert PLDM device #1 and press ENTER (or 'q' to quit): [ENTER]

  ✓ Device detected on /dev/ttyUSB0

📥 Retrieving PDRs from /dev/ttyUSB0...
   ✗ Connection lost mid-transfer. Retrying...
   ✗ Failed to retrieve PDRs: Timeout

Options:
  [r] Retry (remove device, reinsert, and try again)
  [s] Skip this device
  [q] Quit
  
Choose: [r]: r

Remove device and press ENTER when ready: [ENTER]
Insert device and press ENTER when ready: [ENTER]

  ✓ Device detected on /dev/ttyUSB0
  
📥 Retrieving PDRs from /dev/ttyUSB0...
   ✓ Found 47 PDRs

(continue mapping...)
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
  "generated": "2026-02-06T14:23:01Z",
  "devices": [
    {
      "connector": "Slot-A",
      "usb_hardware_address": "usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_01A234B5-if00",
      "eid": 8,
      "chassis_resource": "/redfish/v1/Chassis/Slot_A",
      "sensors": [
        {
          "pdr_id": 5,
          "pdr_type": "numeric_sensor",
          "sensor_id": 5,
          "pldm_name": "CPU_TEMP",
          "entity_type": 3,
          "entity_instance": 0,
          "redfish_id": "CPU_TEMP",
          "redfish_uri": "/redfish/v1/Chassis/Slot_A/Sensors/CPU_TEMP",
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
          "redfish_uri": "/redfish/v1/Chassis/Slot_A/Controls/GlobalInterlock",
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
    },
    {
      "connector": "Slot-B",
      "usb_hardware_address": "usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_02B345C6-if00",
      "eid": 9,
      "chassis_resource": "/redfish/v1/Chassis/Slot_B",
      "sensors": [...],
      "controls": [...]
    }
  ]
}
```

**Key fields:**
- `connector`: User-provided identifier for documentation (not used by agent, but aids troubleshooting)
- `usb_hardware_address`: Extracted from device symlink; persists across reboots and `/dev/ttyUSB*` reassignments
- `eid`: Endpoint ID assigned during discovery (may differ from connector)
- All other fields: per-device PDR mappings (same structure as before)

## Integration with Main Agent

The wizard generates configuration consumed by the PLDM agent's mapping engine:

1. **Startup**: Agent loads `pdr_redfish_mappings.json` alongside `config.json`
2. **PDR Discovery**: Agent retrieves PDRs from endpoints (same as wizard)
3. **Mapping Engine**: Applies field transformations from mapping config
4. **Resource Generation**: Creates Redfish resources with mapped data
5. **Updates**: Sensor readings → Redfish sensor updates via field mappings

The wizard is **development/setup time** tool. The agent **runtime** uses its output.

## Implementation Phases

### Phase 1: Device Detection & PDR Discovery (Week 1)
- Load Redfish schemas at startup (before device loop)
- Watch `/dev/ttyUSB*` and `/dev/ttyACM*` for new devices
- Extract USB hardware address from device symlinks (vid:pid:serial)
- Connect to single port (vs. config.json discovery)
- Implement GetPDRRepositoryInfo command with retry logic
- Implement GetPDR command with pagination and error recovery
- Parse and display PDR contents (numeric sensor, state sensor, etc.)
- Read and parse FRU data
- Prompt user for connector/slot identification

### Phase 2: Interactive Mapping with Accumulation (Week 2)
- Rich UI for PDR display per device
- Field-by-field mapping prompts with IoT.2 default suggestions
- Basic transform support (unit conversions)
- Device mapper: append new device to pdr_redfish_mappings.json
- Prompt for next device (loop until user quits)
- Output pdr_redfish_mappings.json with accumulated devices

### Phase 3: Validation & Testing (Week 3)
- JSON schema validation for accumulated mappings
- Redfish schema compliance checks
- Test against live endpoints with retry logic
- Error reporting and diagnostics
- Validate USB hardware addresses don't collide

### Phase 4: Advanced Features (Week 4+)
- Templates for common configurations
- Diff/merge existing device mappings
- OEM extension support
- Batch mode for non-interactive setup (for factory automation)

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

