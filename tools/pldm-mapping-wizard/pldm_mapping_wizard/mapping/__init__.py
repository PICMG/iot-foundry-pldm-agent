"""Mapping data structures and accumulation."""

from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from rich.console import Console

console = Console()


@dataclass
class DeviceMapping:
    """Mapping data for a single device."""

    connector: str
    usb_hardware_address: str
    eid: int
    chassis_resource: str
    sensors: List[Dict[str, Any]]
    controls: List[Dict[str, Any]]
    fru_mappings: Dict[str, Any]


class MappingAccumulator:
    """Accumulate device mappings into a single output file."""

    def __init__(self, output_path: str):
        """
        Initialize the accumulator.
        
        Args:
            output_path: Path to pdr_redfish_mappings.json.
        """
        self.output_path = Path(output_path)
        self.devices: List[Dict[str, Any]] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing mappings from file if it exists."""
        if self.output_path.exists():
            try:
                with open(self.output_path, "r") as f:
                    data = json.load(f)
                    self.devices = data.get("devices", [])
                    console.print(
                        f"[cyan]ℹ️  Loaded {len(self.devices)} existing device(s)[/cyan]\n"
                    )
            except Exception as e:
                console.print(f"[yellow]⚠️  Warning: Could not load existing mappings: {e}[/yellow]\n")

    def add_device(self, device_mapping: DeviceMapping) -> None:
        """
        Add a device mapping to the accumulator.
        
        Args:
            device_mapping: DeviceMapping object for a device.
        """
        self.devices.append(asdict(device_mapping))

    def save(self, mapping_doc: str = "", validation_report: str = "") -> None:
        """
        Save accumulated mappings to output file.
        
        Args:
            mapping_doc: Optional documentation content.
            validation_report: Optional validation report content.
        """
        output = {
            "version": "1.0",
            "generated": self._iso_timestamp(),
            "devices": self.devices,
        }

        with open(self.output_path, "w") as f:
            json.dump(output, f, indent=2)

        console.print(f"📝 Saved to {self.output_path}")

    def _iso_timestamp(self) -> str:
        """Get ISO 8601 timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
