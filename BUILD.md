# Building and Running the PLDM Agent

## Build Requirements

- CMake 3.15 or later
- C++17 compatible compiler (GCC 7+, Clang 5+)
- Meson build system (>= 1.4.0) if building libpldm from source
- Ninja build tool
- Python 3.6+
- Linux kernel with MCTP support (optional, for production use)

## Installing Build Dependencies

Meson must be version 1.4.0 or later (required by libpldm). We recommend using `pipx` to install Meson in an isolated environment:

### Recommended: Using pipx

**Debian/Ubuntu:**
```bash
# Install system build tools and pipx
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config ninja-build pipx python3-full

# Ensure pipx is in PATH
pipx ensurepath

# Install Meson in isolated environment
pipx install "meson>=1.4.0"

# Add to PATH (if not already done)
export PATH="$HOME/.local/bin:$PATH"
```

**Fedora:**
```bash
sudo dnf install -y cmake gcc-c++ make pkg-config ninja-build pipx
pipx ensurepath
pipx install "meson>=1.4.0"
export PATH="$HOME/.local/bin:$PATH"
```

**RHEL/CentOS:**
```bash
sudo yum install -y cmake gcc-c++ make pkgconfig ninja-build pipx
pipx ensurepath
pipx install "meson>=1.4.0"
export PATH="$HOME/.local/bin:$PATH"
```

### Alternative: Automated Setup Script

An automated setup script is provided (note: uses pip3 directly, may have environment restrictions):

```bash
./setup-deps.sh
```

## Building

### Integrated Subprojects

The build includes and links against:
- **mctp-serial-linux** (CMake) - Provides `libsermctp` for MCTP serial transport
- **libpldm** (Meson-based) - Builds locally without system-wide installation
  - Installs to: `build/third_party/libpldm/`
  - Tests are disabled for faster builds

### Development Build

**First time setup:**

```bash
# 1. Install build dependencies (see section above)
# 2. Ensure Meson is in PATH
export PATH="$HOME/.local/bin:$PATH"

# 3. Verify Meson version
meson --version  # Should be >= 1.4.0

# 4. Create and configure build
mkdir -p build
cd build
cmake -DPLDM_USE_SYSTEM_LIBPLDM=OFF \
      -DMESON_EXECUTABLE=$HOME/.local/bin/meson \
      -DCMAKE_BUILD_TYPE=Debug ..
```

**Building:**

```bash
cd build

# Full build (configures and compiles everything)
cmake --build .

# Incremental build (after code changes)
cmake --build .

# Clean and rebuild (clears local libpldm build)
rm -rf subprojects/libpldm third_party
cmake --build .
```

**Running from build directory:**

```bash
./pldm-agent
./pldm-agent --log-level debug
```

## Running the Agent

### Development/Foreground Mode

Run the agent in the foreground with output to console (from build directory):

```bash
cd build
./pldm-agent
```

With custom configuration:
```bash
./pldm-agent --config ../config.json
```

With debug logging:
```bash
./pldm-agent --log-level debug
```

### Daemon Mode

Run as a background daemon:

```bash
./pldm-agent --daemon --config ../config.json
```

### Command Line Options

```
-d, --daemon          Run as a daemon (default: foreground)
-c, --config FILE     Configuration file (default: ./config.json)
-l, --log-level LEVEL Log level: debug, info, warn, error, fatal
-h, --help            Show help message
-v, --version         Show version information
```

## Installation

### System-wide Installation

```bash
cd build
sudo cmake --install . --prefix /usr/local

# Install systemd service
sudo cp systemd/pldm-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Enable as systemd Service

```bash
# Copy configuration
sudo mkdir -p /etc/pldm-agent
sudo cp config.json /etc/pldm-agent/config.json

# Enable and start service
sudo systemctl enable pldm-agent
sudo systemctl start pldm-agent

# Check status
sudo systemctl status pldm-agent

# View logs
sudo journalctl -u pldm-agent -f
```

## Development Workflow

### Quick Development Cycle

```bash
cd build
cmake --build .
./pldm-agent --log-level debug
```

### Clean Build

```bash
rm -rf build
mkdir -p build
cd build

# Configure for debug build with local libpldm
cmake -DPLDM_USE_SYSTEM_LIBPLDM=OFF \
      -DMESON_EXECUTABLE=$HOME/.local/bin/meson \
      -DCMAKE_BUILD_TYPE=Debug ..

cmake --build .
```

### Running with Custom Config

Create a test configuration file:

```bash
cp config.json config.dev.json
# Edit config.dev.json with development settings
./pldm-agent --config config.dev.json --log-level debug
```

## Debugging

### Enable Debug Build

```bash
cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS="-fsanitize=address" ..
```

### Run with GDB

```bash
gdb ./pldm-agent
(gdb) run
(gdb) break main
(gdb) run --log-level debug
```

### Enable PLDM Message Logging

Set in config.json:
```json
{
  "logging": {
    "pldmMessages": true
  }
}
```

## Logs

### Foreground Mode
Logs are printed to the console.

### Daemon Mode
Logs are written to:
- syslog (default)
- `/var/log/pldm-agent.log` (if configured)

View daemon logs:
```bash
# Using journalctl
sudo journalctl -u pldm-agent

# Using tail
sudo tail -f /var/log/pldm-agent.log
```

## Troubleshooting

### Build Fails with CMake Version Error

Update CMake to 3.15 or later:
```bash
sudo apt-get install cmake
```

### Permission Denied Errors

The daemon needs access to MCTP devices:

```bash
# Add user to mctp group
sudo usermod -a -G mctp $USER

# Or run with sudo
sudo ./pldm-agent --daemon
```

### Service Won't Start

Check logs:
```bash
sudo systemctl status pldm-agent
sudo journalctl -u pldm-agent -n 50
```

Check configuration file:
```bash
sudo cat /etc/pldm-agent/config.json
```

## Development Tips

1. **Hot Reload Not Available**: Restart the daemon to apply config changes:
   ```bash
   sudo systemctl restart pldm-agent
   ```

2. **Isolate Testing**: Use `--config` with a test configuration file to avoid affecting production.

3. **Signal Handling**: The agent handles SIGINT, SIGTERM, and SIGHUP for graceful shutdown.

4. **Syslog Integration**: In daemon mode, all logs go to syslog with identifier `pldm-agent`.
