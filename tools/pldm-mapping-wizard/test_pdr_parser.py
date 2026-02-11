#!/usr/bin/env python3
"""Test PDR parsing functionality."""

from pldm_mapping_wizard.discovery.pdr_parser import PDRParser, PDRType

def test_pdr_header_parsing():
    """Test PDR header parsing."""
    print("Testing PDR header parsing...")
    
    # Create a mock PDR header (8 bytes)
    # [0:2] Record handle = 0x0001
    # [2]   Header revision = 0x00
    # [3]   PDR type = NUMERIC_SENSOR (0x09)
    # [4:6] Record length = 0x0040 (64 bytes)
    # [6:8] Checksum/validity = 0x00
    
    pdr_data = bytes([
        0x01, 0x00,  # handle = 1
        0x00,         # revision
        0x09,         # type = NUMERIC_SENSOR
        0x40, 0x00,  # length = 64
        0x00, 0x00,  # checksum
    ])
    
    header = PDRParser.parse_header(pdr_data)
    assert header is not None, "Failed to parse header"
    assert header.pdr_record_handle == 1, "Handle mismatch"
    assert header.pdr_type == PDRType.NUMERIC_SENSOR, "Type mismatch"
    assert header.pdr_length == 64, "Length mismatch"
    print("  ✓ PDR header parsing works")


def test_pdr_generic_parsing():
    """Test generic PDR parsing."""
    print("\nTesting generic PDR parsing...")
    
    # Mock PDR with header
    pdr_data = bytes([
        0x01, 0x00,  # handle = 1
        0x00,         # revision
        0x09,         # type = NUMERIC_SENSOR
        0x40, 0x00,  # length = 64
        0x00, 0x00,  # checksum
        # Padding to 64 bytes
    ] + [0x00] * 56)
    
    pdr = PDRParser.parse_pdr(pdr_data)
    assert pdr is not None, "Failed to parse PDR"
    assert pdr["type"] == PDRType.NUMERIC_SENSOR, "Type mismatch"
    assert pdr["type_name"] == "NUMERIC_SENSOR", "Type name mismatch"
    assert pdr["handle"] == 1, "Handle mismatch"
    assert pdr["length"] == 64, "Length mismatch"
    print(f"  Parsed PDR: {pdr}")
    print("  ✓ Generic PDR parsing works")


def test_numeric_sensor_pdr_parsing():
    """Test numeric sensor PDR parsing."""
    print("\nTesting numeric sensor PDR parsing...")
    
    # Mock numeric sensor PDR
    pdr_data = bytes([
        0x02, 0x00,  # handle = 2
        0x00,         # revision
        0x09,         # type = NUMERIC_SENSOR (0x09)
        0x40, 0x00,  # length = 64
        0x00, 0x00,  # checksum
        # Sensor data
        0x10, 0x00,  # sensor_id = 16
        0x03,         # entity_type = 3 (Processor)
        0x01, 0x00,  # entity_instance = 1
        0x00,         # reserved
        0x7F,         # sensor_init
        0x00,         # sensor_aux_flags
        0x01,         # sensor_type
        0x40,         # event_msg_ctrl_type
        # Padding
    ] + [0x00] * 44)
    
    pdr = PDRParser.parse_pdr(pdr_data)
    assert pdr is not None, "Failed to parse numeric sensor PDR"
    assert pdr["type"] == PDRType.NUMERIC_SENSOR, "Type mismatch"
    assert "parsed" in pdr, "No parsed data"
    assert pdr["parsed"]["sensor_id"] == 16, "Sensor ID mismatch"
    assert pdr["parsed"]["entity_type"] == 3, "Entity type mismatch"
    print(f"  Parsed numeric sensor: {pdr['parsed']}")
    print("  ✓ Numeric sensor PDR parsing works")


def test_pdr_sequence_parsing():
    """Test parsing multiple PDRs in sequence."""
    print("\nTesting PDR sequence parsing...")
    
    # Create two sequential PDRs (32 bytes each for simplicity)
    pdr1 = bytes([
        0x01, 0x00,  # handle = 1
        0x00, 0x09,  # revision, type = NUMERIC_SENSOR
        0x20, 0x00,  # length = 32
        0x00, 0x00,  # checksum
    ] + [0xFF] * 24)  # padding
    
    pdr2 = bytes([
        0x02, 0x00,  # handle = 2
        0x00, 0x14,  # revision, type = STATE_SENSOR
        0x20, 0x00,  # length = 32
        0x00, 0x00,  # checksum
    ] + [0xAA] * 24)  # padding
    
    combined = pdr1 + pdr2
    
    # Parse first PDR
    pdr_obj1 = PDRParser.parse_pdr(combined, 0)
    assert pdr_obj1 is not None, "Failed to parse first PDR"
    assert pdr_obj1["handle"] == 1, "First handle mismatch"
    assert pdr_obj1["type"] == 0x09, "First type mismatch"
    
    # Parse second PDR
    offset = pdr_obj1["length"]
    pdr_obj2 = PDRParser.parse_pdr(combined, offset)
    assert pdr_obj2 is not None, "Failed to parse second PDR"
    assert pdr_obj2["handle"] == 2, "Second handle mismatch"
    assert pdr_obj2["type"] == 0x14, "Second type mismatch"
    
    print(f"  PDR 1: handle={pdr_obj1['handle']}, type={pdr_obj1['type_name']}")
    print(f"  PDR 2: handle={pdr_obj2['handle']}, type={pdr_obj2['type_name']}")
    print("  ✓ PDR sequence parsing works")


if __name__ == "__main__":
    test_pdr_header_parsing()
    test_pdr_generic_parsing()
    test_numeric_sensor_pdr_parsing()
    test_pdr_sequence_parsing()
    print("\n✅ All PDR parsing tests passed!")
