#!/bin/bash
# Setup script for PLDM Agent build dependencies

set -e

echo "Installing PLDM Agent build dependencies..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Error: Unable to detect OS"
    exit 1
fi

case "$OS" in
    ubuntu|debian)
        echo "Detected Debian/Ubuntu"
        sudo apt-get update
        sudo apt-get install -y \
            build-essential \
            cmake \
            pkg-config \
            python3-pip \
            python3-dev \
            ninja-build
        
        # Install Meson (libpldm requires >= 1.4.0)
        sudo pip3 install "meson>=1.4.0"
        ;;
    fedora)
        echo "Detected Fedora"
        sudo dnf install -y \
            cmake \
            gcc-c++ \
            make \
            pkg-config \
            python3-pip \
            ninja-build
        
        # Install Meson (libpldm requires >= 1.4.0)
        sudo pip3 install "meson>=1.4.0"
        ;;
    rhel|centos)
        echo "Detected RHEL/CentOS"
        sudo yum install -y \
            cmake \
            gcc-c++ \
            make \
            pkgconfig \
            python3-pip \
            ninja-build
        
        # Install Meson (libpldm requires >= 1.4.0)
        sudo pip3 install "meson>=1.4.0"
        ;;
    *)
        echo "Warning: Unsupported OS: $OS"
        echo "Please install the following manually:"
        echo "  - CMake 3.15 or later"
        echo "  - C++ compiler (GCC 7+ or Clang 5+)"
        echo "  - Meson (pip install 'meson>=1.4.0')"
        echo "  - Ninja build system"
        exit 1
        ;;
esac

echo "Build dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "  mkdir -p build && cd build"
echo "  cmake -DCMAKE_BUILD_TYPE=Debug .."
echo "  cmake --build ."
