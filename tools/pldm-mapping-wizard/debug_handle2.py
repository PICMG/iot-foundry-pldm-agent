#!/usr/bin/env python3
"""Debug handle 0x02 response to see where extra 0x7E bytes appear."""

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
    
    handle = 0x02
    print(f"Requesting handle 0x{handle:08x}...")
    print()
    
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
    
    print(f"Raw response ({len(response_frame)} bytes):")
    print(f"  {response_frame.hex()}")
    print()
    
    # Find all 0x7E positions
    positions = [i for i, b in enumerate(response_frame) if b == 0x7E]
    print(f"0x7E (frame delimiter) positions: {positions}")
    print()
    
    # Show bytes around each 0x7E
    for pos in positions:
        start = max(0, pos - 3)
        end = min(len(response_frame), pos + 4)
        context = response_frame[start:end]
        print(f"  Position {pos}: ...{context.hex()}...")
    print()
    
    # Extract frames
    frames = MCTPFramer.extract_frames(response_frame)
    print(f"Extracted {len(frames)} frames:")
    for idx, f in enumerate(frames):
        print(f"  Frame {idx}: {len(f)} bytes")
        print(f"    Hex: {f.hex()}")
        print()
    
    port.close()

if __name__ == '__main__':
    main()
