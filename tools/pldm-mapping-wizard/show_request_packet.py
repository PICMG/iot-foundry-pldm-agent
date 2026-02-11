#!/usr/bin/env python3
"""Show the exact GetPDR request packet being sent"""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def show_request_packet():
    """Show the GetPDR request packet structure"""
    
    print("=" * 100)
    print("GetPDR REQUEST PACKET STRUCTURE")
    print("=" * 100)
    print()
    
    # Build GetPDR command for handle 0x00000001
    record_handle = 0x00000001
    instance_id = 0
    
    cmd = PDLMCommandEncoder.encode_get_pdr(
        instance_id=instance_id,
        record_handle=record_handle,
        data_transfer_handle=0,
        transfer_operation_flag=0x01,  # GetFirstPart
        request_count=255,
        record_change_number=0,
    )
    
    print(f"PLDM Command (before MCTP framing):")
    print(f"  Bytes: {cmd.hex()}")
    print(f"  Length: {len(cmd)} bytes")
    print()
    
    # Decode the command
    print(f"PLDM Command Structure:")
    print(f"  [0] Instance ID + Type: 0x{cmd[0]:02x}")
    print(f"      Instance ID: {cmd[0] & 0x1F}")
    print(f"      Request bit: {(cmd[0] >> 7) & 1}")
    print(f"  [1] Command: 0x{cmd[1]:02x} (GetPDR)")
    print(f"  [2-5] Record Handle: 0x{struct.unpack('<I', cmd[2:6])[0]:08x}")
    print(f"  [6-9] Data Transfer Handle: 0x{struct.unpack('<I', cmd[6:10])[0]:08x}")
    print(f"  [10] Transfer Operation Flag: 0x{cmd[10]:02x}")
    print(f"  [11-12] Request Count: {struct.unpack('<H', cmd[11:13])[0]}")
    print(f"  [13-14] Record Change Number: {struct.unpack('<H', cmd[13:15])[0]}")
    print()
    
    # Frame it with MCTP
    frame = MCTPFramer.build_frame(
        pldm_msg=cmd,
        dest=0,
        src=16,
        msg_type=0x01,
    )
    
    print(f"MCTP Frame (complete packet on wire):")
    print(f"  Bytes: {frame.hex()}")
    print(f"  Length: {len(frame)} bytes")
    print()
    
    print(f"MCTP Frame Structure:")
    print(f"  [0] Flag: 0x{frame[0]:02x}")
    print(f"  [1] Protocol: 0x{frame[1]:02x}")
    print(f"  [2] Byte Count: {frame[2]}")
    print(f"  [3] Dest EID: {frame[3]}")
    print(f"  [4] Src EID: {frame[4]}")
    print(f"  [5] Msg Type: 0x{frame[5]:02x}")
    print(f"  [6-{len(frame)-4}] PLDM Payload: {frame[6:-3].hex()}")
    print(f"  [{len(frame)-3}] FCS High: 0x{frame[-3]:02x}")
    print(f"  [{len(frame)-2}] FCS Low: 0x{frame[-2]:02x}")
    print(f"  [{len(frame)-1}] Flag: 0x{frame[-1]:02x}")
    print()
    
    # Now send it and get response
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    if not port.open():
        print("Failed to open port")
        return
    
    print("=" * 100)
    print("SENDING REQUEST AND RECEIVING RESPONSE")
    print("=" * 100)
    print()
    
    print(f"TX (to DUT): {frame.hex()}")
    port.write(frame)
    
    response_frame = port.read_until_idle()
    print(f"RX (from DUT): {response_frame.hex()}")
    print()
    
    # Parse response
    frames = MCTPFramer.extract_frames(response_frame)
    if frames:
        parsed = MCTPFramer.parse_frame(frames[0])
        pldm_response = parsed.get("extra", b"")
        
        print(f"Response PLDM Payload: {pldm_response.hex()}")
        print()
        
        if len(pldm_response) >= 12:
            cc = pldm_response[0]
            next_record_handle = struct.unpack('<I', pldm_response[1:5])[0]
            next_xfer_handle = struct.unpack('<I', pldm_response[5:9])[0]
            transfer_flag = pldm_response[9]
            response_count = struct.unpack('<H', pldm_response[10:12])[0]
            record_data = pldm_response[12:12 + response_count]
            
            print(f"Response Structure:")
            print(f"  [0] Completion Code: 0x{cc:02x}")
            print(f"  [1-4] Next Record Handle: 0x{next_record_handle:08x}")
            print(f"  [5-8] Next Xfer Handle: 0x{next_xfer_handle:08x}")
            print(f"  [9] Transfer Flag: 0x{transfer_flag:02x}")
            print(f"  [10-11] Response Count: {response_count}")
            print(f"  [12+] recordData ({response_count} bytes): {record_data.hex()}")
    
    port.close()

if __name__ == '__main__':
    show_request_packet()
