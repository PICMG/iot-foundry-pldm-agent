#!/usr/bin/env python3
"""Retrieve and decode all PDRs from DUT."""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder
from pldm_mapping_wizard.discovery.pdr_parser import PDRParser

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
        return None, f"No frames extracted"
    
    # Parse first frame
    frame = MCTPFramer.parse_frame(frames[0])
    if not frame:
        return None, f"Failed to parse frame"
    
    # Extract PLDM payload
    pldm_data = frame.get('extra')
    if not pldm_data or len(pldm_data) < 12:
        return None, f"Invalid PLDM payload"
    
    # Parse GetPDR response
    completion_code = pldm_data[0]
    if completion_code != 0:
        return None, f"Completion code: 0x{completion_code:02x}"
    
    next_handle = struct.unpack('<I', pldm_data[1:5])[0]
    response_count = struct.unpack('<H', pldm_data[10:12])[0]
    pdr_data = pldm_data[12:12+response_count]
    
    return {
        'handle': handle,
        'next_handle': next_handle,
        'pdr_data': bytes(pdr_data),
    }, None

def main():
    print("=" * 100)
    print("PDR DECODING - All PDRs")
    print("=" * 100)
    print()
    
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    # Start from handle 0
    handle = 0
    pdr_count = 0
    max_pdrs = 50
    
    for i in range(max_pdrs):
        result, error = get_pdr(port, handle)
        
        if error:
            print(f"Handle 0x{handle:08x}: Failed - {error}")
            break
        
        pdr_count += 1
        pdr_data = result['pdr_data']
        next_handle = result['next_handle']
        
        # Parse the PDR
        try:
            parsed_pdr = PDRParser.parse(pdr_data)
            
            print("=" * 100)
            print(f"Requested Handle: 0x{handle:08x} | PDR #{pdr_count} | Next Handle: 0x{next_handle:08x}")
            print("=" * 100)
            
            # Show parsed structure
            for key, value in parsed_pdr.items():
                if isinstance(value, bytes):
                    print(f"  {key}: {value.hex()}")
                elif isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        if isinstance(v, bytes):
                            print(f"    {k}: {v.hex()}")
                        else:
                            print(f"    {k}: {v}")
                elif isinstance(value, list):
                    print(f"  {key}:")
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            print(f"    [{idx}]:")
                            for k, v in item.items():
                                if isinstance(v, bytes):
                                    print(f"      {k}: {v.hex()}")
                                else:
                                    print(f"      {k}: {v}")
                        else:
                            print(f"    [{idx}]: {item}")
                else:
                    print(f"  {key}: {value}")
            
            print()
            
        except Exception as e:
            print("=" * 100)
            print(f"Requested Handle: 0x{handle:08x} | PDR #{pdr_count} | Next Handle: 0x{next_handle:08x}")
            print("=" * 100)
            print(f"  Parse error: {e}")
            print(f"  Raw data ({len(pdr_data)} bytes): {pdr_data.hex()}")
            print()
        
        # Check for loop completion
        if next_handle == 0 or next_handle == handle:
            print("=" * 100)
            print(f"Chain complete - Retrieved and decoded {pdr_count} PDRs")
            print("=" * 100)
            break
        
        handle = next_handle
    
    port.close()

if __name__ == '__main__':
    main()
