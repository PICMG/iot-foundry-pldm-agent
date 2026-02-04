# Build System Overview

## CMakeLists.txt Structure

The main [CMakeLists.txt](CMakeLists.txt) orchestrates the build of the PLDM Agent and its subproject dependencies.

### Subproject Integration

#### 1. mctp-serial-linux (CMake)
- **Location:** `subprojects/mctp-serial-linux`
- **Build System:** CMake
- **Integration:** `add_subdirectory()`
- **Produces:** 
  - `libsermctp` - MCTP Serial transport library
  - `mctp-bridge` - Reference application
- **Used by:** pldm-agent links against `sermctp`

#### 2. libpldm (Meson)
- **Location:** `subprojects/libpldm`
- **Build System:** Meson
- **Integration:** `ExternalProject_Add()` (Meson wrapper)
- **Produces:** 
  - `libpldm.a/.so` - PLDM protocol library
  - Headers in `include/libpldm/`
- **Used by:** pldm-agent links against `pldm`

### Dependency Flow

```
pldm-agent (main executable)
├── Threads::Threads (system)
├── sermctp (from mctp-serial-linux)
│   └── linux-mctp/libsermctp/CMakeLists.txt
└── pldm (from libpldm)
    └── subprojects/libpldm/meson.build
```

## Build Configuration

### CMake Presets

Build type options:
- **Debug:** `-DCMAKE_BUILD_TYPE=Debug` - With debugging symbols, assertions enabled
- **Release:** `-DCMAKE_BUILD_TYPE=Release` - Optimized, NDEBUG defined

### Compiler Flags

**Debug:**
```
-g -O0 -DDEBUG
```

**Release:**
```
-O2 -DNDEBUG
```

## Build Artifacts

After successful build, the following artifacts are created:

```
build/
├── pldm-agent                          # Main executable
├── subprojects/
│   ├── mctp-serial-linux/              # libsermctp build directory
│   │   └── linux-mctp/
│   │       ├── libsermctp/
│   │       │   └── libsermctp.a
│   │       └── mctp-bridge/
│   └── libpldm/                        # libpldm build directory (Meson)
│       ├── libpldm.a
│       └── libpldm.so
├── pldm-agent.service                 # Generated systemd service
└── CMakeFiles/
```

## External Project Handling

### libpldm with Meson

The CMake build wraps Meson using `ExternalProject_Add`:

1. **Meson Setup:** Configures libpldm with custom options
2. **Meson Compile:** Builds libpldm library
3. **Meson Install:** Installs to build directory (not system)

Key CMake variables:
- `LIBPLDM_SOURCE_DIR` - Points to `subprojects/libpldm`
- `LIBPLDM_BINARY_DIR` - Build directory for libpldm
- `MESON_EXECUTABLE` - Meson binary location

### mctp-serial-linux with CMake

Direct CMake subdirectory integration:
- Uses standard CMake targets: `sermctp` library
- Options controlled via `option()` directives:
  - `BUILD_LIB` (default: ON) - Build libsermctp
  - `BUILD_APP` (default: ON) - Build mctp-bridge
  - `USE_SYSTEM_SERMCTP` (default: OFF) - Use system library

## Linking Strategy

The pldm-agent executable links to:

1. **System Libraries:**
   - `Threads::Threads` - For POSIX threading

2. **Subproject Libraries:**
   - `sermctp` - From `mctp-serial-linux`
   - `pldm` - From `libpldm`

**Link Directories:**
```cmake
target_link_directories(pldm-agent PRIVATE
    ${LIBPLDM_BINARY_DIR}
    ${CMAKE_BINARY_DIR}/subprojects/mctp-serial-linux
)
```

## Include Paths

The build configures header search paths for:
- `src/` - Agent source code
- `include/` - Agent headers
- `subprojects/libpldm/include/` - PLDM protocol headers
- `${LIBPLDM_BINARY_DIR}` - Generated PLDM headers

## Installation

The CMakeLists.txt configures installation of:
- Binary: `pldm-agent` → `/usr/local/bin/`
- Systemd service: → `/lib/systemd/system/`
- Configuration: `config.json` → `/etc/pldm-agent/config.json.default`

## Clean Build

To completely clean the build:
```bash
rm -rf build/
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
cmake --build .
```

This will rebuild all subprojects from scratch.

## Troubleshooting

### Meson not found
```
Error: Meson not found
Solution: pip install meson
```

### libpldm compilation fails
```
Check libpldm build directory:
  tail -f build/subprojects/libpldm/meson-logs/meson-log.txt
```

### Linking errors
```
Ensure subprojects built successfully:
  cmake --build . --verbose
```

## Build System Philosophy

- **Minimal vendoring:** Subprojects included as git submodules, not vendored code
- **Mixed build systems:** CMake orchestrates both CMake and Meson subprojects
- **Reproducible builds:** Fixed dependency versions from git submodule pinning
- **Development friendly:** Debug symbols and assertions enabled by default in Debug mode
