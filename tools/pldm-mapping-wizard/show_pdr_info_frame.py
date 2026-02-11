#!/usr/bin/env python3
"""Show the GetPDRRepositoryInfo request frame"""

import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def show_pdr_info_frame():
    """Show the GetPDRRepositoryInfo frame"""
    
    print("=" * 100)
    print("GetPDRRepositoryInfo REQUEST FRAME")
    print("=" * 100)
    print()
    
    # Build GetPDRRepositoryInfo command
    instance_id = 0
    cmd = PDLMCommandEncoder.encode_get_pdr_repository_info(instance_id=instance_id)
    
    print(f"PLDM Command (before MCTP framing):")
    print(f"  Bytes: {cmd.hex()}")
    print(f"  Length: {len(cmd)} bytes")
    print()
    
    print(f"PLDM Command Structure:")
    print(f"  [0] Instance ID + Type: 0x{cmd[0]:02x}")
    print(f"      Instance ID: {cmd[0] & 0x1F}")
    print(f"      Request bit: {(cmd[0] >> 7) & 1}")
    print(f"  [1] Command: 0x{cmd[1]:02x} (GetPDRRepositoryInfo)")
    print()
    
    # Frame it with MCTP
    frame = MCTPFramer.build_frame(
        pldm_msg=cmd,
        dest=0,
        src=16,
        msg_type=0x01,
    )
    
    print(f"MCTP Frame (complete packet on wire):")
    print(f"  Full hex: {frame.hex()}")
    print(f"  Length: {len(frame)} bytes")
    print()
    
    print(f"MCTP Frame Structure (byte-by-byte):")
    print(f"  [0]    0x{frame[0]:02x}  - Start flag")
    print(f"  [1]    0x{frame[1]:02x}  - Protocol (MCTP serial)")
    print(f"  [2]    0x{frame[2]:02x}  - Byte count ({frame[2]} bytes)")
    print(f"  [3]    0x{frame[3]:02x}  - Dest EID")
    print(f"  [4]    0x{frame[4]:02x}  - Src EID")
    print(f"  [5]    0x{frame[5]:02x}  - Msg Type (PLDM)")
    for i in range(6, len(frame) - 3):
        print(f"  [{i}]    0x{frame[i]:02x}  - PLDM payload byte {i-5}")
    print(f"  [{len(frame)-3}]    0x{frame[-3]:02x}  - FCS high")
    print(f"  [{len(frame)-2}]    0x{frame[-2]:02x}  - FCS low")
    print(f"  [{len(frame)-1}]    0x{frame[-1]:02x}  - End flag")
    print()
    
    # Format with spaces for readability
    hex_str = ' '.join([f'{b:02x}' for b in frame])
    print(f"Frame with spaces:")
    print(f"  {hex_str}")

if __name__ == '__main__':
    show_pdr_info_frame()
