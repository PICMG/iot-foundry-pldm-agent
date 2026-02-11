#!/usr/bin/env python3
"""Capture complete TX/RX traces for DUT debugging."""

import sys
from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def format_hex(data: bytes) -> str:
    """Format bytes as continuous hex string."""
    return data.hex()

def main():
    """Capture traces for first few PDR retrievals."""
    print("=" * 120)
    print("COMPLETE TX/RX TRACE FOR DUT DEBUGGING")
    print("=" * 120)
    
    port = SerialPort("/dev/ttyUSB0", baudrate=115200)
    port.open()
    print("✓ Port opened\n")
    
    local_eid = 16
    remote_eid = 0
    instance_id = 0
    
    # ========== GetPDRRepositoryInfo ==========
    print("=" * 120)
    print("COMMAND 1: GetPDRRepositoryInfo (0x50)")
    print("=" * 120)
    
    pldm_msg = PDLMCommandEncoder.encode_get_pdr_repository_info(instance_id=instance_id)
    frame = MCTPFramer.build_frame(pldm_msg=pldm_msg, dest=remote_eid, src=local_eid, msg_type=0x01)
    
    print(f"TX: {format_hex(frame)}")
    print(f"    Length: {len(frame)} bytes\n")
    
    port.write(frame)
    rx_data = port.read_until_idle()
    
    print(f"RX: {format_hex(rx_data)}")
    print(f"    Length: {len(rx_data)} bytes")
    
    frames = MCTPFramer.extract_frames(rx_data)
    print(f"    Extracted {len(frames)} frame(s)")
    for i, f in enumerate(frames):
        parsed = MCTPFramer.parse_frame(f)
        if parsed:
            print(f"    Frame {i}: msg_type={parsed.get('msg_type')}, cmd={parsed.get('cmd_code')}, "
                  f"fcs_ok={parsed.get('fcs_ok')}, resp_code={parsed.get('resp_code')}")
    print()
    
    # ========== GetPDR for handles 0-5 ==========
    for handle in range(6):
        print("=" * 120)
        print(f"COMMAND {handle+2}: GetPDR (0x51) - Record Handle {handle}")
        print("=" * 120)
        
        pldm_msg = PDLMCommandEncoder.encode_get_pdr(
            instance_id=instance_id,
            record_handle=handle,
            data_transfer_handle=0,
            transfer_operation_flag=0x01,
            request_count=254,
            record_change_number=0,
        )
        frame = MCTPFramer.build_frame(pldm_msg=pldm_msg, dest=remote_eid, src=local_eid, msg_type=0x01)
        
        print(f"TX: {format_hex(frame)}")
        print(f"    Length: {len(frame)} bytes\n")
        
        port.write(frame)
        rx_data = port.read_until_idle()
        
        print(f"RX: {format_hex(rx_data)}")
        print(f"    Length: {len(rx_data)} bytes")
        
        frames = MCTPFramer.extract_frames(rx_data)
        print(f"    Extracted {len(frames)} frame(s)")
        for i, f in enumerate(frames):
            parsed = MCTPFramer.parse_frame(f)
            if parsed:
                print(f"    Frame {i}: msg_type={parsed.get('msg_type')}, cmd={parsed.get('cmd_code')}, "
                      f"fcs_ok={parsed.get('fcs_ok')}, som={parsed.get('som')}, eom={parsed.get('eom')}, "
                      f"resp_code={parsed.get('resp_code')}")
                if parsed.get('msg_type') == 0:
                    print(f"             ⚠️  CONTROL MESSAGE (should not appear during GetPDR)")
        print()
    
    port.close()
    print("=" * 120)
    print("TRACE COMPLETE")
    print("=" * 120)

if __name__ == "__main__":
    main()
