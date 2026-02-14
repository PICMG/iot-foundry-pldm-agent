# IoT Foundry PLDM Agent - Demo Control System

A three-part demo system for the IoT Foundry PLDM Agent, consisting of:

1. **Redfish Mockup Server** - Serves Redfish resources from a generated mockup
2. **Configurator** - Detects PLDM devices and generates Redfish mockup
3. **Runtime Agent** - Monitors and manages the automation system

## Quick Start

### 1. Initial Setup (one-time)

```bash
cd demo
./setup.sh
```

This creates a Python virtual environment and installs all dependencies.

### 2. Run the Demo

```bash
./start.sh
```

This launches an interactive menu where you can:
- Start the Redfish Mockup Server
- Run the Configurator to scan devices and generate mockup
- Start the Runtime Agent
- View logs from any component
- Stop all running parts

## Architecture

```
demo/
├── venv/                    # Python virtualenv (created by setup.sh)
├── parts/
│   ├── __init__.py
│   ├── shared.py            # Shared utilities (config, logging, process mgmt)
│   ├── redfish_server.py    # Part 1: Mockup server
│   ├── configurator.py      # Part 2: Device scanner & mockup generator
│   └── runtime_agent.py     # Part 3: Runtime monitor/manager
├── configs/
│   └── demo.ini             # Central configuration
├── logs/                    # Log files (created automatically)
├── requirements.txt         # Python dependencies
├── setup.sh                 # Initialization script
└── start.sh                 # Main control script (interactive menu)
```

## Configuration

All configuration is managed in `configs/demo.ini`:

```ini
[server]
host = 127.0.0.1
port = 8000
mockup_dir = /tmp/generated_mockup

[configurator]
pdr_output = /tmp/pdr_and_fru_records.json
auto_select = true

[agent]
poll_interval = 5

[logging]
log_level = INFO
```

Edit this file to customize port numbers, device timeout, logging levels, etc.

## Usage Workflow

### Step 1: Run Configurator
First time you use the demo, or when devices change:

```
./start.sh
→ Select "2) Run Configurator"
→ System scans for PLDM devices and generates mockup
→ Mockup saved to /tmp/generated_mockup
```

### Step 2: Start Redfish Server
```
./start.sh
→ Select "1) Start Redfish Mockup Server"
→ Server listens on http://127.0.0.1:8000
```

### Step 3: Start Runtime Agent (optional, in another terminal)
```
./start.sh
→ Select "3) Start Runtime Agent"
→ Agent polls system state every 5 seconds
```

### Step 4: View Logs
At any time:
```
./start.sh
→ Select "4) View Logs"
→ Choose which component to monitor
```

## Unit Management

Each part (server, agent, configurator) is independent:

- **Server**: Long-running background process
- **Agent**: Long-running background process  
- **Configurator**: One-shot operation (blocks until complete)

From the menu you can:
- Start/stop individual components
- View their logs in real-time
- Check status of all running parts

## Logging

Logs are written to `logs/` directory:

- `redfish_server.log` - Mockup server events
- `configurator.log` - Device scanning and generation
- `runtime_agent.log` - Agent activity

Combined console + file logging for debugging.

## Troubleshooting

### venv not found
```bash
./setup.sh
```

### Port 8000 already in use
Edit `configs/demo.ini` and change:
```ini
[server]
port = 8001
```

### Configurator can't find devices
- Ensure PLDM device is connected
- Check `/tmp/pdr_and_fru_records.json` exists
- View `logs/configurator.log` for details

### To restart everything cleanly
```bash
./start.sh → "5) Stop All" → Ctrl+C menu → Run again
```

