#!/usr/bin/env python3
"""Attempt to read PDR repository info and first few PDRs"""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def read_pdr_info():
    """Read PDR repository info and first few PDRs"""
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    print("=" * 100)
    print("PDR REPOSITORY INFO")
    print("=" * 100)
    print()
    
    # Get repository info
    cmd = PDLMCommandEncoder.encode_get_pdr_repository_info(instance_id=0)
    frame = MCTPFramer.build_frame(pldm_msg=cmd, dest=0, src=16, msg_type=0x01)
    
    port.write(frame)
    response_frame = port.read_until_idle()
    
    frames = MCTPFramer.extract_frames(response_frame)
    if frames:
        parsed = MCTPFramer.parse_frame(frames[0])
        pldm_response = parsed.get("extra", b"")
        result = PDLMCommandEncoder.decode_get_pdr_repository_info_response(pldm_response)
        
        if "error" not in result:
            print(f"Repository Info:")
            print(f"  Total PDRs: {result.get('total_pdr_records', 0)}")
            print(f"  Repository State: {result.get('repository_state', 0)}")
            print()
    
    # Try reading handles 0, 1, 2
    print("=" * 100)
    print("FIRST FEW PDRs")
    print("=" * 100)
    print()
    
    for handle_val in [0, 1, 2]:
        print(f"\n--- Requesting Handle 0x{handle_val:08x} ---")
        
        cmd = PDLMCommandEncoder.encode_get_pdr(
            instance_id=0,
            record_handle=handle_val,
            data_transfer_handle=0,
            transfer_operation_flag=0x01,
            request_count=255,
            record_change_number=0,
        )
        
        frame = MCTPFramer.build_frame(pldm_msg=cmd, dest=0, src=16, msg_type=0x01)
        port.write(frame)
        
        response_frame = port.read_until_idle()
        if not response_frame:
            print(f"  ✗ No response")
            continue
        
        frames = MCTPFramer.extract_frames(response_frame)
        if not frames:
            print(f"  ✗ No frames")
            continue
            
        parsed = MCTPFramer.parse_frame(frames[0])
        pldm_response = parsed.get("extra", b"")
        
        if len(pldm_response) < 12:
            print(f"  ✗ Response too short: {len(pldm_response)} bytes")
            continue
        
        cc = pldm_response[0]
        next_record_handle = struct.unpack('<I', pldm_response[1:5])[0]
        next_xfer_handle = struct.unpack('<I', pldm_response[5:9])[0]
        transfer_flag = pldm_response[9]
        response_count = struct.unpack('<H', pldm_response[10:12])[0]
        record_data = pldm_response[12:12 + response_count]
        
        print(f"  Completion Code: 0x{cc:02x}")
        if cc != 0:
            print(f"  ✗ Failed with CC={cc}")
            continue
        
        print(f"  Next Record Handle: 0x{next_record_handle:08x}")
        print(f"  Response Count: {response_count} bytes")
        print(f"  recordData: {record_data.hex()}")
        
        # Compare with expected_pdrs.md
        if handle_val == 1 and response_count == 9:
            expected_body = bytes([0x01, 0x00, 0x01, 0x01, 0x01, 0x00, 0x01, 0x01, 0x01])
            if record_data == expected_body:
                print(f"  ✓ Matches expected Terminus Locator PDR body from expected_pdrs.md")
            else:
                print(f"  ✗ Does NOT match expected body")
                print(f"    Expected: {expected_body.hex()}")
                print(f"    Got:      {record_data.hex()}")
        
        print()
    
    port.close()

if __name__ == '__main__':
    read_pdr_info()
