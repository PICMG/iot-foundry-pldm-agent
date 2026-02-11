"""Basic tests for PLDM Mapping Wizard."""

import tempfile
import json
from pathlib import Path
from pldm_mapping_wizard.redfish import SchemaLoader
from pldm_mapping_wizard.mapping import MappingAccumulator, DeviceMapping


def test_schema_loader():
    """Test schema loading."""
    loader = SchemaLoader()
    schemas = loader.load_schemas()
    
    assert loader.loaded is True
    assert "Chassis" in schemas
    assert "Sensor" in schemas
    print("✓ Schema loader test passed")


def test_mapping_accumulator():
    """Test mapping accumulation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_mappings.json"
        
        accumulator = MappingAccumulator(str(output_path))
        
        # Create a test device mapping
        device = DeviceMapping(
            connector="Slot-A",
            usb_hardware_address="usb-test-123",
            eid=8,
            chassis_resource="/redfish/v1/Chassis/Slot_A",
            sensors=[],
            controls=[],
            fru_mappings={}
        )
        
        accumulator.add_device(device)
        accumulator.save()
        
        # Verify output file
        assert output_path.exists()
        
        with open(output_path, "r") as f:
            data = json.load(f)
        
        assert "version" in data
        assert data["version"] == "1.0"
        assert len(data["devices"]) == 1
        assert data["devices"][0]["connector"] == "Slot-A"
        
        print("✓ Mapping accumulator test passed")


if __name__ == "__main__":
    test_schema_loader()
    test_mapping_accumulator()
    print("\n✅ All tests passed!")
