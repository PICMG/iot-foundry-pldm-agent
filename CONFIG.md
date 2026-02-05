# PLDM Agent Configuration Guide

This document describes the configuration options for the IoT-Foundry PLDM Agent.

## Configuration File

The agent uses a JSON configuration file (default: `config.json`) to control its behavior. The configuration file location can be specified via:
- Command line: `--config=/path/to/config.json`
- Environment variable: `PLDM_AGENT_CONFIG=/path/to/config.json`
- Default location: `./config.json`

## Configuration Sections

### Downstream Transport

Configuration for downstream PLDM communication over MCTP serial interface. By default, uses a PTY (pseudo-terminal) for communication, but can be configured to use a physical serial device.

**Transport Configuration:**
- **mctp_interface** (string, required): MCTP serial interface name assigned by Linux (e.g., `mctpserial0`)
- **local_eid** (integer, required, 8-255): Local MCTP Endpoint ID for this agent
- **peer_eids** (array, required): List of remote endpoint IDs to communicate with
  - Each value must be an integer between 8-255
  - Must specify at least one peer EID
- **serial_device** (string or null, optional, default: null): Physical serial device path
  - Examples: `/dev/ttyUSB0`, `/dev/ttyS1`, `/dev/pts/1`
  - If `null`, the transport uses a PTY (pseudo-terminal)
  - PTY is recommended for development and testing
- **baud_rate** (integer or null, optional, default: null): Serial baud rate
  - Valid values: 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600
  - Only used when `serial_device` is specified
  - Ignored for PTY-based connections
- **enable_diagnostics** (boolean, optional, default: false): Enable libsermctp diagnostic output
  - Useful for debugging MCTP communication issues
  - Prints detailed transport layer information to stderr

**Messaging Configuration:**
- **timeout_ms** (integer, optional, default: 5000): Request timeout in milliseconds
  - Minimum: 100ms
- **retries** (integer, optional, default: 3): Number of retry attempts on request failure
  - Range: 0-10
- **retry_delay_ms** (integer, optional, default: 1000): Delay between retry attempts in milliseconds
- **max_concurrent** (integer, optional, default: 10): Maximum concurrent PLDM requests
  - Minimum: 1
- **supported_types** (array, optional): Supported PLDM message types
  - Default: `["base", "platform"]`
  - Available types:
    - `base`: Base messages (discovery, capabilities)
    - `platform`: Platform monitoring (sensors, effecters)
    - `bios`: BIOS configuration
    - `fru`: Field Replaceable Unit data
    - `firmware-update`: Firmware update protocol
    - `redfish-device-enablement`: Redfish integration
    - `oem`: OEM-specific extensions

**Example - PTY (default):**
```json
"downstream_transport": {
  "mctp_interface": "mctpserial0",
  "local_eid": 8,
  "peer_eids": [9, 10, 11],
  "timeout_ms": 5000,
  "retries": 3,
  "supported_types": ["base", "platform"]
}
```

**Example - Physical serial device:**
```json
"downstream_transport": {
  "mctp_interface": "mctpserial0",
  "local_eid": 8,
  "peer_eids": [9, 10],
  "serial_device": "/dev/ttyUSB0",
  "baud_rate": 115200,
  "enable_diagnostics": true,
  "timeout_ms": 5000,
  "retries": 3,
  "max_concurrent": 5
}
```

### Messaging

PLDM message handling parameters:

- **timeout** (integer, ms): Request timeout duration
- **retries** (integer): Number of retry attempts on failure
- **retryDelay** (integer, ms): Delay between retry attempts
- **maxConcurrent** (integer): Maximum concurrent PLDM requests
- **supportedTypes** (array): Enabled PLDM message types
  - `base`: Base messages (discovery, capabilities)
  - `platform`: Platform monitoring (sensors, effecters)
  - `bios`: BIOS configuration
  - `fru`: Field Replaceable Unit data
  - `firmware-update`: Firmware update protocol
  - `redfish-device-enablement`: Redfish integration
  - `oem`: OEM-specific extensions

### Endpoints

PLDM endpoints to communicate with. Each endpoint can either be initialized by the agent or pre-initialized by the system.

**Common Properties:**
- **eid** (integer, required, 8-255): MCTP Endpoint ID
- **name** (string, optional): Friendly name for the endpoint
- **enabled** (boolean, required): Whether to communicate with this endpoint
- **initialize** (boolean, required): Whether the agent should initialize this endpoint
  - `true`: Agent sets up the MCTP serial connection for this endpoint
  - `false`: Endpoint is pre-initialized by the system (e.g., by systemd or another service)
- **poll** (boolean, optional, default: false): Enable periodic polling
- **poll_interval** (integer, optional, default: 60): Polling interval in seconds

**Agent-Initialized Endpoints (initialize=true):**

When the agent initializes an endpoint, you must specify the serial connection details:

- **hw_address** (string, required if serial_device not specified): USB hardware address
  - Format: `"<bus>-<port>:<config>.<interface>"` (e.g., `"1-1.2:1.0"`)
  - Use `lsusb -t` to find USB hardware addresses
  - Ensures binding to a specific physical USB port regardless of enumeration order
  - **Mutually exclusive with serial_device** - use this for USB-serial adapters
- **serial_device** (string, required if hw_address not specified): Direct serial device path
  - Examples: `"/dev/ttyUSB0"`, `"/dev/ttyS1"`, `"/dev/ttyAMA0"`
  - Use for built-in serial ports or when USB hardware address is not applicable
  - **Mutually exclusive with hw_address**
- **baud_rate** (integer, required): Serial baud rate
  - Valid values: 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600
- **flow_control** (string, required): Flow control setting
  - `"none"`: No flow control
  - `"hardware"`: RTS/CTS hardware flow control
  - `"software"`: XON/XOFF software flow control
- **connector_id** (string, required): Physical connector identifier
  - Examples: `"J12"`, `"CON3"`, `"SERIAL_PORT_2"`
  - Used for physical hardware documentation and troubleshooting

**System-Initialized Endpoints (initialize=false):**

For endpoints managed by the system, only the common properties are needed. The agent will communicate with the endpoint but won't set up the MCTP connection.

**Examples:**

Agent-initialized USB-serial endpoint:
```json
{
  "eid": 9,
  "name": "sensor-hub",
  "enabled": true,
  "initialize": true,
  "hw_address": "1-1.2:1.0",
  "baud_rate": 115200,
  "flow_control": "hardware",
  "connector_id": "J12",
  "poll": true,
  "poll_interval": 60
}
```

Agent-initialized built-in serial port:
```json
{
  "eid": 10,
  "name": "legacy-controller",
  "enabled": true,
  "initialize": true,
  "serial_device": "/dev/ttyS1",
  "baud_rate": 9600,
  "flow_control": "none",
  "connector_id": "J8"
}
```

System-managed endpoint:
```json
{
  "eid": 11,
  "name": "system-bmc",
  "enabled": true,
  "initialize": false,
  "poll": false
}
```

### Discovery

Automatic endpoint discovery settings:

- **enabled** (boolean): Enable/disable discovery
- **interval** (integer, seconds): Discovery scan interval
- **eidRange**: EID range to scan
  - **start** (integer): Starting EID
  - **end** (integer): Ending EID

### Logging

Logging configuration:

- **level** (string, required): Minimum log level
  - `debug`: Verbose debugging information
  - `info`: General information
  - `warn`: Warning messages
  - `error`: Error messages
  - `fatal`: Fatal errors only
- **output** (string): Log destination
  - `console`: Standard output
  - `file`: Log file
  - `syslog`: System logger
  - `both`: Console and file
- **file** (string): Log file path
- **maxSize** (integer, MB): Log file size before rotation
- **maxFiles** (integer): Number of rotated logs to keep
- **pldmMessages** (boolean): Log raw PLDM message payloads (debugging)

### Security

Security and access control:

- **authentication** (boolean): Require message authentication
- **encryption** (boolean): Enable message encryption
- **allowedEids** (array): Whitelist of allowed EIDs (empty = allow all)

### Performance

Performance tuning parameters:

- **workerThreads** (integer): Number of worker threads
- **bufferSize** (integer, bytes): Message buffer size
- **queueSize** (integer): Maximum message queue size

### Event Service

Integration with IoT-Foundry Event Service:

- **enabled** (boolean): Enable event publishing
- **endpoint** (string): Event service URL
- **topics** (array): Event topics to publish

## Configuration Validation

The agent validates the configuration file against the JSON schema (`config.schema.json`) on startup. Invalid configurations will prevent the agent from starting and display detailed error messages.

To validate a configuration file manually:

```bash
# Using ajv-cli
ajv validate -s config.schema.json -d config.json

# Using jsonschema (Python)
jsonschema -i config.json config.schema.json
```
