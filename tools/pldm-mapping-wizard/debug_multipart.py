#!/usr/bin/env python3
"""Debug multipart transfer frame parsing."""

from pldm_mapping_wizard.serial_transport import MCTPFramer

# The problematic RX buffer from the trace
rx_hex = "7e010501100058989835ce7e00060000000000000004300000640000020201656e0000540072006900676700670065007200440065006100630074006900760061007400650064000020cf7e"

rx_data = bytes.fromhex(rx_hex)

print("=" * 100)
print("DEBUGGING MULTIPART RX BUFFER")
print("=" * 100)
print(f"\nRaw RX hex: {rx_hex}")
print(f"Raw RX bytes: {len(rx_data)} bytes")
print()

# Extract frames
frames = MCTPFramer.extract_frames(rx_data)
print(f"Extracted {len(frames)} frame(s):")
for i, frame in enumerate(frames):
    print(f"\nFrame {i}:")
    print(f"  Hex: {frame.hex()}")
    print(f"  Length: {len(frame)} bytes")
    
    # Parse the frame
    parsed = MCTPFramer.parse_frame(frame)
    if parsed:
        print(f"  Protocol: {parsed.get('protocol')}")
        print(f"  Byte count: {parsed.get('byte_count')}")
        print(f"  Header ver: {parsed.get('header_version')}")
        print(f"  Dest: {parsed.get('dest')}")
        print(f"  Src: {parsed.get('src')}")
        print(f"  Flags: 0x{parsed.get('flags'):02x}")
        print(f"  SOM: {parsed.get('som')}, EOM: {parsed.get('eom')}")
        print(f"  Msg type: {parsed.get('msg_type')}")
        print(f"  FCS OK: {parsed.get('fcs_ok')}")
        print(f"  Extra: {parsed.get('extra', b'').hex()}")
    else:
        print("  Failed to parse!")
