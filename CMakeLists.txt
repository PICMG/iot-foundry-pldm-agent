cmake_minimum_required(VERSION 3.15)
project(pldm-agent 
    VERSION 1.0.0
    DESCRIPTION "PLDM Agent for IoT-Foundry"
    LANGUAGES CXX C
)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Set build type to Release by default
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Compiler flags
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG")

# Find required packages
find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)

# Include subprojects
# Build mctp-serial-linux with CMake
add_subdirectory(subprojects/mctp-serial-linux EXCLUDE_FROM_ALL)

# Add nlohmann/json (header-only library)
add_subdirectory(subprojects/nlohmann-json EXCLUDE_FROM_ALL)

# libpldm integration
option(PLDM_USE_SYSTEM_LIBPLDM "Use system-installed libpldm via pkg-config" ON)

if(PLDM_USE_SYSTEM_LIBPLDM)
    pkg_check_modules(LIBPLDM REQUIRED IMPORTED_TARGET libpldm)
else()
    # Build libpldm with Meson (using ExternalProject)
    include(ExternalProject)

    # Check for Meson
    if(NOT MESON_EXECUTABLE)
        find_program(MESON_EXECUTABLE meson
            HINTS $ENV{HOME}/.local/bin
        )
    endif()
    if(NOT MESON_EXECUTABLE)
        message(FATAL_ERROR "Meson not found. Install Meson or set PLDM_USE_SYSTEM_LIBPLDM=ON.")
    endif()

    # Configure libpldm with Meson as an external project
    set(LIBPLDM_SOURCE_DIR ${CMAKE_SOURCE_DIR}/subprojects/libpldm)
    set(LIBPLDM_BINARY_DIR ${CMAKE_BINARY_DIR}/subprojects/libpldm)
    set(LIBPLDM_INSTALL_PREFIX ${CMAKE_BINARY_DIR}/third_party/libpldm)

    ExternalProject_Add(libpldm
        SOURCE_DIR ${LIBPLDM_SOURCE_DIR}
        BINARY_DIR ${LIBPLDM_BINARY_DIR}
        CONFIGURE_COMMAND ${MESON_EXECUTABLE} setup --prefix=${LIBPLDM_INSTALL_PREFIX} --libdir=lib -Dwerror=false -Dtests=false ${LIBPLDM_BINARY_DIR} ${LIBPLDM_SOURCE_DIR}
        BUILD_COMMAND ${MESON_EXECUTABLE} compile -C ${LIBPLDM_BINARY_DIR}
        INSTALL_COMMAND ${MESON_EXECUTABLE} install -C ${LIBPLDM_BINARY_DIR}
        EXCLUDE_FROM_ALL OFF
    )
endif()

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/src
    ${CMAKE_SOURCE_DIR}/include
)

if(NOT PLDM_USE_SYSTEM_LIBPLDM)
    include_directories(
        ${LIBPLDM_INSTALL_PREFIX}/include
    )
endif()

# Source files
set(PLDM_AGENT_SOURCES
    src/main.cpp
)

# Create executable
add_executable(pldm-agent ${PLDM_AGENT_SOURCES})

# Add dependency on libpldm external project
if(NOT PLDM_USE_SYSTEM_LIBPLDM)
    add_dependencies(pldm-agent libpldm)
endif()

# Link libraries
target_link_libraries(pldm-agent
    PRIVATE
    Threads::Threads
    sermctp
    nlohmann_json::nlohmann_json
)

if(PLDM_USE_SYSTEM_LIBPLDM)
    target_link_libraries(pldm-agent PRIVATE PkgConfig::LIBPLDM)
else()
    target_link_libraries(pldm-agent PRIVATE pldm)
endif()

# Set library search path for external projects
target_link_directories(pldm-agent PRIVATE
    ${CMAKE_BINARY_DIR}/subprojects/mctp-serial-linux
)

if(NOT PLDM_USE_SYSTEM_LIBPLDM)
    target_link_directories(pldm-agent PRIVATE
        ${LIBPLDM_INSTALL_PREFIX}/lib
    )
endif()

# Installation
install(TARGETS pldm-agent
    RUNTIME DESTINATION bin
)

# Create systemd service file
configure_file(
    ${CMAKE_SOURCE_DIR}/systemd/pldm-agent.service.in
    ${CMAKE_BINARY_DIR}/pldm-agent.service
    @ONLY
)

install(FILES ${CMAKE_BINARY_DIR}/pldm-agent.service
    DESTINATION /lib/systemd/system
    OPTIONAL
)

# Create default config file
install(FILES config.json
    DESTINATION /etc/pldm-agent
    RENAME config.json.default
    OPTIONAL
)

# Print build information
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Installation prefix: ${CMAKE_INSTALL_PREFIX}")
