#!/usr/bin/env python3
"""Diagnose if PDR header is being returned twice"""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def diagnose():
    """Retrieve first PDR and show raw response structure"""
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    print("=" * 100)
    print("PDR RESPONSE DIAGNOSTIC")
    print("=" * 100)
    print()
    
    # Request first PDR
    cmd = PDLMCommandEncoder.encode_get_pdr(
        instance_id=0,
        record_handle=0,
        data_transfer_handle=0,
        transfer_operation_flag=0x01,  # GetFirstPart
        request_count=255,
        record_change_number=0,
    )
    
    frame = MCTPFramer.build_frame(
        pldm_msg=cmd,
        dest=0,
        src=16,
        msg_type=0x01,
    )
    
    print(f"TX Command: {frame.hex()}")
    port.write(frame)
    
    response_frame = port.read_until_idle()
    print(f"\nRX Response: {response_frame.hex()}\n")
    
    # Parse the frame
    frames = MCTPFramer.extract_frames(response_frame)
    parsed_frames = [MCTPFramer.parse_frame(fr) for fr in frames]
    
    if not parsed_frames:
        print("No frames parsed")
        return
    
    pf = parsed_frames[0]
    print(f"Frame parsed:")
    print(f"  msg_type: 0x{pf.get('msg_type', 0):02x}")
    print(f"  cmd_code: 0x{pf.get('cmd_code', 0):02x}")
    print(f"  fcs_ok: {pf.get('fcs_ok')}")
    print()
    
    # Decode the response
    pldm_response = pf.get("extra", b"")
    print(f"PLDM Response payload ({len(pldm_response)} bytes):")
    print(f"  {pldm_response.hex()}\n")
    
    # Manually parse response structure
    if len(pldm_response) < 12:
        print("Response too short")
        return
    
    cc = pldm_response[0]
    next_record_handle = struct.unpack('<I', pldm_response[1:5])[0]
    next_xfer_handle = struct.unpack('<I', pldm_response[5:9])[0]
    transfer_flag = pldm_response[9]
    response_count = struct.unpack('<H', pldm_response[10:12])[0]
    
    print(f"Response Structure:")
    print(f"  [0] Completion Code: 0x{cc:02x}")
    print(f"  [1-4] Next Record Handle: 0x{next_record_handle:08x}")
    print(f"  [5-8] Next Xfer Handle: 0x{next_xfer_handle:08x}")
    print(f"  [9] Transfer Flag: 0x{transfer_flag:02x}")
    print(f"  [10-11] Response Count: {response_count}")
    print()
    
    # Extract recordData
    record_data = pldm_response[12:12 + response_count]
    print(f"recordData ({len(record_data)} bytes):")
    print(f"  {record_data.hex()}\n")
    
    # Check if recordData starts with what looks like a PDR header
    if len(record_data) >= 10:
        handle_from_data = struct.unpack('<I', record_data[0:4])[0]
        version_from_data = record_data[4]
        type_from_data = record_data[5]
        
        print(f"First 10 bytes of recordData interpreted as PDR header:")
        print(f"  [0-3] Record Handle: 0x{handle_from_data:08x}")
        print(f"  [4] PDR Version: 0x{version_from_data:02x}")
        print(f"  [5] PDR Type: 0x{type_from_data:02x}")
        print(f"  [6-7] Change Number: 0x{struct.unpack('<H', record_data[6:8])[0]:04x}")
        print(f"  [8-9] Data Length: {struct.unpack('<H', record_data[8:10])[0]}")
        print()
        
        if version_from_data == 0x01:
            print(f"✓ recordData INCLUDES 10-byte PDR header (version=0x01 indicates valid header)")
            print(f"✓ This is NON-STANDARD - DSP0248 says recordData = variable length record data only")
            print(f"✓ The DUT appears to include the complete PDR (header + body) in recordData")
        else:
            print(f"✗ recordData does NOT start with valid PDR header")
            print(f"✓ This is STANDARD - DSP0248 behavior (recordData = body only)")
    
    port.close()

if __name__ == '__main__':
    diagnose()
