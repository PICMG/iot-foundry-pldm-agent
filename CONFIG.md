# PLDM Agent Configuration Guide

This document describes the configuration options for the IoT-Foundry PLDM Agent.

## Configuration File

The agent uses a JSON configuration file (default: `config.json`) to control its behavior. The configuration file location can be specified via:
- Command line: `--config=/path/to/config.json`
- Environment variable: `PLDM_AGENT_CONFIG=/path/to/config.json`
- Default location: `./config.json`

## Configuration Sections

### Transport

- **eid** (integer, 8-254): Local MCTP Endpoint ID
- **mtu** (integer): Maximum transmission unit in bytes
- **socketPath** (string): Unix socket path for local MCTP

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

Pre-configured PLDM endpoints to communicate with:
- **name** (string): Friendly name
- **hwAddress** (string): if the device is a usb-connected serial port, hardware address may be used instead of interface name.
- **interface** (string): device path for the downstream serial interface - not used if hwAddress is specified.
- **connectorId** (string): identifying marking for the associated board connector for the
- **eid** (integer, required): MCTP Endpoint ID
- **enabled** (boolean): Enable communication with this endpoint
- **poll** (boolean): Enable periodic polling
- **pollInterval** (integer, seconds): Polling frequency

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
