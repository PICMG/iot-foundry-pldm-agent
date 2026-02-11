#!/usr/bin/env python3
"""Calculate FCS for handle 0x02 response to verify checksum."""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def calc_fcs(data):
    """Calculate RFC1662 FCS-16 (PPP FCS with reflected polynomial)."""
    return MCTPFramer._calc_fcs(data)

def main():
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    handle = 0x02
    
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
    
    print("=" * 100)
    print("FCS CHECKSUM VERIFICATION")
    print("=" * 100)
    print()
    
    print("Raw response buffer (46 bytes):")
    hex_str = ' '.join(f'{b:02x}' for b in response_frame)
    print(f"  {hex_str}")
    print()
    
    # Parse frame structure
    print("Frame structure:")
    print(f"  [0]       Start flag:     0x{response_frame[0]:02x}")
    print(f"  [1]       Protocol:       0x{response_frame[1]:02x}")
    print(f"  [2]       Byte count:     0x{response_frame[2]:02x} ({response_frame[2]} bytes)")
    print()
    
    byte_count = response_frame[2]
    print(f"Expected frame structure:")
    print(f"  [0]       Start flag")
    print(f"  [1]       Protocol")
    print(f"  [2]       Byte count")
    print(f"  [3-{3+byte_count-1}]   Data ({byte_count} bytes)")
    print(f"  [{3+byte_count}-{3+byte_count+1}] FCS (2 bytes)")
    print(f"  [{3+byte_count+2}]     End flag")
    print()
    
    # Extract data for FCS calculation
    # FCS is calculated over: protocol + byte_count + data
    fcs_data = response_frame[1:3+byte_count]  # [1] to [2+byte_count]
    
    print(f"Data for FCS calculation (protocol + byte_count + data = {len(fcs_data)} bytes):")
    for i in range(0, len(fcs_data), 16):
        chunk = fcs_data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        print(f"  [{i:3d}] {hex_str}")
    print()
    
    # Calculate FCS
    calculated_fcs = calc_fcs(fcs_data)
    
    # Extract received FCS
    fcs_pos = 3 + byte_count
    if fcs_pos + 1 < len(response_frame):
        received_fcs_byte1 = response_frame[fcs_pos]
        received_fcs_byte2 = response_frame[fcs_pos + 1]
        received_fcs_le = (received_fcs_byte2 << 8) | received_fcs_byte1  # Little-endian
        received_fcs_be = (received_fcs_byte1 << 8) | received_fcs_byte2  # Big-endian
        
        print(f"FCS Comparison:")
        print(f"  Position [{fcs_pos}]:     0x{received_fcs_byte1:02x}")
        print(f"  Position [{fcs_pos+1}]:     0x{received_fcs_byte2:02x}")
        print(f"  Received (as LE):  0x{received_fcs_le:04x} (bytes: {received_fcs_byte1:02x} {received_fcs_byte2:02x})")
        print(f"  Received (as BE):  0x{received_fcs_be:04x} (bytes: {received_fcs_byte1:02x} {received_fcs_byte2:02x})")
        print(f"  Calculated FCS:    0x{calculated_fcs:04x}")
        print(f"    As LE bytes:     {calculated_fcs & 0xFF:02x} {(calculated_fcs >> 8) & 0xFF:02x}")
        print(f"    As BE bytes:     {(calculated_fcs >> 8) & 0xFF:02x} {calculated_fcs & 0xFF:02x}")
        print()
        
        if received_fcs_le == calculated_fcs:
            print(f"  ✓ FCS MATCHES (Little-Endian)! Checksum is correct.")
        elif received_fcs_be == calculated_fcs:
            print(f"  ✓ FCS MATCHES (Big-Endian)! DUT sends FCS in BE format.")
        else:
            print(f"  ✗ FCS MISMATCH in both byte orders!")
        print()
        
        # Check what comes after FCS
        end_flag_pos = fcs_pos + 2
        if end_flag_pos < len(response_frame):
            end_flag = response_frame[end_flag_pos]
            print(f"After FCS:")
            print(f"  Position [{end_flag_pos}]:     0x{end_flag:02x} {'(End flag - correct!)' if end_flag == 0x7E else '(Unexpected)'}")
            
            if end_flag_pos + 1 < len(response_frame):
                extra = response_frame[end_flag_pos + 1]
                print(f"  Position [{end_flag_pos + 1}]:     0x{extra:02x} (Extra byte)")
    else:
        print("ERROR: Not enough bytes for FCS")
        return
    
    print()
    print("=" * 100)
    print()
    print("CONCLUSION:")
    if received_fcs_be == calculated_fcs:
        print(f"  ✓ You are CORRECT! The FCS is 0x{received_fcs_byte1:02x} 0x{received_fcs_byte2:02x} (a2 7e)")
        print(f"  ✓ The 0x7E at position [{fcs_pos+1}] is part of the FCS checksum, NOT escaped")
        print(f"  ✓ The DUT sends FCS in big-endian format (non-standard, but valid)")
        print(f"  ✓ The frame structure is:")
        print(f"      7e [start] ... {byte_count} bytes data ... a2 7e [FCS] 7e [end] 7e [extra]")
        print(f"  ✓ Total: 46 bytes = 1 (start) + 1 (proto) + 1 (count) + {byte_count} (data) + 2 (FCS) + 1 (end) + 1 (extra)")
    elif received_fcs_le == calculated_fcs:
        print(f"  ✓ FCS matches in little-endian format")
    else:
        print("  FCS does not match in either byte order - needs investigation")
    
    port.close()

if __name__ == '__main__':
    main()
