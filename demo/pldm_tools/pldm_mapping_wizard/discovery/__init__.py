"""Port monitoring for /dev/ttyUSB* devices."""

import os
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path
from rich.console import Console

console = Console()


class PortMonitor:
    """Monitor for new USB serial device appearances."""

    def __init__(self):
        """Initialize port monitor."""
        self.tty_paths = ["/dev/ttyUSB*"]

    def wait_for_device(self) -> Optional[Dict[str, str]]:
        """
        Wait for user to insert a device and confirm readiness.
        
        Returns:
            Dictionary with 'port' and 'usb_address' keys, or None if user quit.
        """
        console.print("🔍 Watching for USB devices...")
        user_input = console.input(
            "Insert PLDM device and press ENTER (or 'q' to quit): "
        )

        if user_input.lower() == "q":
            return None

        # Detect currently available ports
        port = self._detect_port()
        if not port:
            console.print("[red]✗ No USB device detected. Please try again.[/red]\n")
            return self.wait_for_device()

        usb_address = self._get_usb_address(port)

        console.print(f"\n  ✓ Device detected on {port}")
        if usb_address:
            console.print(f"  ✓ USB hardware address: {usb_address}")
        console.print()

        return {
            "port": port,
            "usb_address": usb_address or "unknown",
        }

    def _detect_port(self) -> Optional[str]:
        """
        Detect the first available USB or ACM serial port.
        
        Returns:
            Path to the device (e.g., "/dev/ttyUSB0") or None.
        """
        for pattern in ["/dev/ttyUSB*"]:
            ports = sorted(Path("/").glob(pattern.lstrip("/")))
            if ports:
                return str(ports[0])
        return None

    def _get_usb_address(self, port: str) -> Optional[str]:
        """
        Extract USB hardware address from device symlink.
        
        Args:
            port: Device path (e.g., "/dev/ttyUSB0").
            
        Returns:
            USB hardware address (e.g., "usb-...-if00") or None.
        """
        try:
            # Follow symlink in /dev/serial/by-id/
            result = subprocess.run(
                ["ls", "-la", "/dev/serial/by-id/"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            
            for line in result.stdout.split("\n"):
                if port.split("/")[-1] in line:
                    # Extract symlink target name
                    parts = line.split()
                    if parts:
                        return parts[-1]
            
            return None
        except Exception:
            return None
