
# PLDM Agent for IoT-Foundry

This repository implements a pldm agent for the IoT-Foundry system archietcture. This repository is part of the IoTFoundry family of open source projects. For more information about IoTFoundry, please visit the main IoTFoundry site at: https://picmg.github.io/iot-foundry/

The PLDM agent is a continuously running application that interfaces between the MCTP protocol and serial drivers, and the Redfish server, as shown by the image below.  The role of the Agent is to handle device descovery, Plaftorm Descriptor Record (PDR) gathering, device recovery, and data translation between the Redfish and PLDM Domains as shown in the figure below.

![PLDM Agent](assets/pldm-agent.svg)

# Architecture Overview:
The **Redfish API** is a modern, standardized way to manage servers. It provides a clean, secure, web‑style interface for controlling and monitoring systems. Redfish uses familiar RESTful APIs and JSON, the same technologies used by modern web services. This makes it easier for both humans and automation tools to interact with hardware.  More on the Redfish API can be found here:  https://redfish.dmtf.org/

**Platform Level Data Model (PLDM)** is a standardized set of binary data models and message formats defined by the DMTF to support platform management in modern computing systems. Its purpose is to provide a uniform, vendor‑neutral way for components within a platform—such as sensors, power devices, firmware modules, and FRUs—to describe themselves and exchange management information.

**Management Component Transport Protocol
Management Component Transport Protocol (MCTP)** is a DMTF‑defined communication protocol designed to transport management messages between components within a platform. It focuses on the movement of messages rather than their meaning.

More on PLDM and MCTP can be found here: https://www.dmtf.org/standards/pmci

**PICMG’s IoT.1 and IoT.2 specifications** together establish a standardized framework for building interoperable Industrial IoT systems. IoT.1 defines a common data model and control structure that devices use to describe their capabilities, measurements, configuration parameters, and control functions. By standardizing the semantics of device information, IoT.1 enables consistent discovery, interpretation, and management of IIoT components across vendors and deployment environments.   

IoT.2 complements this by defining the communication architecture that transports IoT.1‑compliant data across industrial networks. It specifies how devices discover one another, exchange messages, and operate reliably over modern network technologies. While IoT.1 focuses on what the data means, IoT.2 focuses on how that data moves, creating a complete, scalable, and vendor‑neutral foundation for interoperable IIoT ecosystems. This specifications leverage DMTF's PLDM and MCTP standards.

More on PICMG IoT.1 and IoT.2 can be found here:
https://www.picmg.org/openstandards/hardware-platform-management/iotx/

# System Requirements
The following are system requirements for the PLDM agent:

- Linux Operating System.
- Python 3.x
- At least one USB port.
- At least one IoT-Foundry-compliant endpoint to be connected to the serial USB port.
- Cabling to connect the endpoint to the serial (USB over serial) port.

# Installation

## Clone the Repository

```bash
git clone --recurse-submodules https://github.com/PICMG/iot-foundry-pldm-agent.git
cd iot-foundry-pldm-agent
```

**Note:** The `--recurse-submodules` flag is required to pull in all necessary dependencies, including the PLDM mapping wizard tools.

## Quick Start Demo

The easiest way to get started is using the interactive demo system:

### 1. Initial Setup

```bash
cd demo
./setup.sh
```

This script will:
- Create a Python virtual environment in `demo/venv/`
- Install all required Python dependencies from `requirements.txt`
- Set up directory structure for logs and configuration

### 2. Launch the Demo Control Panel

```bash
./start.sh
```

This launches an interactive menu where you can:

1. **Start Redfish Mockup Server** - HTTP server serving Redfish resources
2. **Run Configurator** - Scan PLDM devices and generate Redfish mockup
3. **Start Runtime Agent** - Monitor USB topology and manage resource state
4. **View Logs** - Live log viewing (Ctrl+C to exit back to menu)
5. **Stop All Running Parts** - Clean shutdown of all components
6. **Show Status** - Display current state of all components

### 3. Typical Workflow

1. Connect your IoT-Foundry-compliant PLDM device to a USB serial port
2. Run the **Configurator** (option 2) to scan devices and generate mockup
3. Start the **Redfish Mockup Server** (option 1) to serve Redfish resources
4. Start the **Runtime Agent** (option 3) to begin monitoring
5. View logs (option 4) to observe device discovery and state changes

The Runtime Agent will:
- Continuously monitor USB topology for device connections/disconnections
- Verify device identity using FRU (Field Replaceable Unit) data
- Automatically disable Redfish resources when devices are unplugged
- Re-enable resources when the same device is reconnected


For more detailed information about the demo system, see [`demo/README.md`](demo/README.md).


