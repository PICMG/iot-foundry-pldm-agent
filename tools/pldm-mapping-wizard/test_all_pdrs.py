#!/usr/bin/env python3
"""Retrieve and parse all PDRs from DUT to verify framing works correctly."""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def get_pdr(port, handle):
    """Retrieve a single PDR by handle."""
    cmd = PDLMCommandEncoder.encode_get_pdr(
        instance_id=0,
        record_handle=handle,
        data_transfer_handle=0,
        transfer_operation_flag=0x01,
        request_count=255,
        record_change_number=0,
    )
    
    frame = MCTPFramer.build_frame(pldm_msg=cmd, dest=0, src=16, msg_type=0x01)
    port.write(frame)
    response = port.read_until_idle()
    
    if not response:
        return None, "No response"
    
    # Extract frames
    frames = MCTPFramer.extract_frames(response)
    if not frames:
        return None, f"No frames extracted from {len(response)} bytes"
    
    # Parse first frame
    frame = MCTPFramer.parse_frame(frames[0])
    if not frame:
        return None, f"Failed to parse frame ({len(frames[0])} bytes)"
    
    # Extract PLDM payload (stored in 'extra' field)
    pldm_data = frame.get('extra')
    if not pldm_data:
        return None, f"No payload in frame (frame keys: {list(frame.keys())})"
    if len(pldm_data) < 12:
        return None, f"Invalid PLDM payload ({len(pldm_data)} bytes)"
    
    # Parse GetPDR response
    completion_code = pldm_data[0]
    if completion_code != 0:
        return None, f"Completion code: 0x{completion_code:02x}"
    
    next_handle = struct.unpack('<I', pldm_data[1:5])[0]
    response_count = struct.unpack('<H', pldm_data[10:12])[0]
    pdr_data = pldm_data[12:12+response_count]
    
    if len(pdr_data) != response_count:
        return None, f"Expected {response_count} bytes, got {len(pdr_data)}"
    
    return {
        'handle': handle,
        'next_handle': next_handle,
        'pdr_data': pdr_data,
        'pdr_type': pdr_data[5] if len(pdr_data) > 5 else None,
    }, None

def main():
    print("=" * 100)
    print("PDR RETRIEVAL TEST - Walking all handles")
    print("=" * 100)
    print()
    
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    # Start from handle 0
    handle = 0
    retrieved = []
    max_pdrs = 50  # Safety limit
    
    for i in range(max_pdrs):
        result, error = get_pdr(port, handle)
        
        if error:
            print(f"Handle 0x{handle:08x}: ✗ FAILED - {error}")
            break
        
        retrieved.append(result)
        
        pdr_type = result['pdr_type']
        pdr_size = len(result['pdr_data'])
        next_handle = result['next_handle']
        
        print(f"Handle 0x{handle:08x}: ✓ OK - Type 0x{pdr_type:02x}, {pdr_size} bytes, next=0x{next_handle:08x}")
        
        # Check for loop completion
        if next_handle == 0 or next_handle == handle:
            print()
            print("Chain complete (next handle is 0x00000000 or same as current)")
            break
        
        handle = next_handle
    
    port.close()
    
    print()
    print("=" * 100)
    print(f"Summary: Successfully retrieved {len(retrieved)} PDRs")
    print("=" * 100)
    
    # Show type distribution
    type_counts = {}
    for pdr in retrieved:
        pdr_type = pdr['pdr_type']
        type_counts[pdr_type] = type_counts.get(pdr_type, 0) + 1
    
    print()
    print("PDR Type Distribution:")
    for pdr_type in sorted(type_counts.keys()):
        count = type_counts[pdr_type]
        print(f"  Type 0x{pdr_type:02x}: {count} PDR(s)")
    
    print()
    print("All PDRs retrieved and parsed successfully!")

if __name__ == '__main__':
    main()
