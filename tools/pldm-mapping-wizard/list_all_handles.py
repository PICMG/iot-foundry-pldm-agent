#!/usr/bin/env python3
"""List all available PDR handles from the repository."""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def main():
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    print("=" * 80)
    print("Retrieving all PDR handles via chain traversal")
    print("=" * 80)
    print()
    
    handle = 0
    retrieved_handles = []
    max_iterations = 20
    
    for i in range(max_iterations):
        print(f"Requesting handle 0x{handle:08x}...", end=" ")
        
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
        
        response_frame = port.read_until_idle()
        if not response_frame:
            print("✗ No response")
            break
        
        print(f"Raw response: {response_frame.hex()[:80]}...")
        
        frames = MCTPFramer.extract_frames(response_frame)
        if not frames:
            print("✗ No frames")
            break
        
        print(f"Frame count: {len(frames)}")
        for idx, f in enumerate(frames):
            print(f"  Frame {idx}: {len(f)} bytes - {f.hex()[:60]}...")
            
        parsed = MCTPFramer.parse_frame(frames[0])
        if not parsed:
            print(f"✗ Parse failed. Frame hex: {frames[0].hex()}")
            # Try the second frame if available
            if len(frames) > 1:
                print(f"Trying frame 1...")
                parsed = MCTPFramer.parse_frame(frames[1])
                if not parsed:
                    print(f"✗ Frame 1 also failed")
                    break
            else:
                break
        
        # Check FCS
        if not parsed.get("fcs_ok", False):
            print(f"⚠ FCS mismatch: calc=0x{parsed.get('fcs_calc', 0):04x}, recv=0x{parsed.get('raw_fcs', 0):04x}")
            
        pldm_response = parsed.get("extra", b"")
        
        if len(pldm_response) < 12:
            print(f"✗ Response too short: {len(pldm_response)} bytes")
            break
        
        completion_code = pldm_response[0]
        if completion_code != 0:
            print(f"✗ Completion code: 0x{completion_code:02x}")
            break
        
        next_handle = struct.unpack('<I', pldm_response[1:5])[0]
        response_count = struct.unpack('<H', pldm_response[10:12])[0]
        
        retrieved_handles.append(handle)
        print(f"✓ Got {response_count} bytes, next=0x{next_handle:08x}")
        
        if next_handle == 0 or next_handle == handle:
            print(f"\nChain complete (next handle is 0x{next_handle:08x})")
            break
        
        handle = next_handle
    
    print()
    print("=" * 80)
    print(f"Summary: Retrieved {len(retrieved_handles)} PDRs")
    print("=" * 80)
    for h in retrieved_handles:
        print(f"  0x{h:08x}")
    
    port.close()

if __name__ == '__main__':
    main()
