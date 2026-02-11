#!/usr/bin/env python3
"""Show raw data breakdown for handle 0x02."""

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
    
    print(f"Raw response buffer ({len(response_frame)} bytes):")
    print()
    
    # Show with byte positions
    for i in range(0, len(response_frame), 16):
        chunk = response_frame[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  [{i:3d}] {hex_str:<48s} |{ascii_str}|")
    
    print()
    print("Frame structure breakdown:")
    print(f"  [0]       0x7E - Start flag")
    print(f"  [1]       0x{response_frame[1]:02x} - Protocol")
    print(f"  [2]       0x{response_frame[2]:02x} - Byte count ({response_frame[2]} bytes)")
    print(f"  [3-5]     MCTP header (dest, src, flags)")
    print(f"  [6]       0x{response_frame[6]:02x} - Message type")
    print(f"  [7-9]     PLDM header")
    print(f"  [10+]     PLDM payload")
    print(f"  [42-43]   FCS")
    print(f"  [44]      0x7E - End flag")
    print(f"  [45]      0x7E - Extra flag byte")
    print()
    
    # Extract and show the PLDM response
    frames = MCTPFramer.extract_frames(response_frame)
    if frames:
        frame_data = frames[0][1:-1]  # Remove start/end flags
        unescaped = MCTPFramer._unescape_body(frame_data)
        
        print(f"Unescaped frame body ({len(unescaped)} bytes):")
        for i in range(0, len(unescaped), 16):
            chunk = unescaped[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            print(f"  [{i:3d}] {hex_str}")
        print()
        
        # Show PLDM payload
        if len(unescaped) > 10:
            pldm_payload = unescaped[10:-2]  # Skip MCTP/PLDM headers and FCS
            print(f"PLDM GetPDR Response ({len(pldm_payload)} bytes):")
            
            if len(pldm_payload) >= 12:
                cc = pldm_payload[0]
                next_handle = struct.unpack('<I', pldm_payload[1:5])[0]
                next_xfer = struct.unpack('<I', pldm_payload[5:9])[0]
                xfer_flag = pldm_payload[9]
                resp_count = struct.unpack('<H', pldm_payload[10:12])[0]
                record_data = pldm_payload[12:]
                
                print(f"  [0]     Completion Code: 0x{cc:02x}")
                print(f"  [1-4]   Next Record Handle: 0x{next_handle:08x}")
                print(f"  [5-8]   Next Xfer Handle: 0x{next_xfer:08x}")
                print(f"  [9]     Transfer Flag: 0x{xfer_flag:02x}")
                print(f"  [10-11] Response Count: {resp_count}")
                print(f"  [12+]   recordData ({len(record_data)} bytes):")
                print()
                
                for i in range(0, len(record_data), 16):
                    chunk = record_data[i:i+16]
                    hex_str = ' '.join(f'{b:02x}' for b in chunk)
                    print(f"          [{i:3d}] {hex_str}")
                
                print()
                print(f"PDR Header (first 10 bytes of recordData):")
                if len(record_data) >= 10:
                    rec_handle = struct.unpack('<I', record_data[0:4])[0]
                    hdr_ver = record_data[4]
                    pdr_type = record_data[5]
                    rec_change = struct.unpack('<H', record_data[6:8])[0]
                    data_len = struct.unpack('<H', record_data[8:10])[0]
                    
                    print(f"  [0-3]   Record Handle: 0x{rec_handle:08x}")
                    print(f"  [4]     Header Version: 0x{hdr_ver:02x}")
                    print(f"  [5]     PDR Type: 0x{pdr_type:02x} (0x14 = FRU Record Set)")
                    print(f"  [6-7]   Record Change Num: {rec_change}")
                    print(f"  [8-9]   Data Length: {data_len}")
                    print(f"  [10+]   PDR Body ({len(record_data)-10} bytes)")
    
    port.close()

if __name__ == '__main__':
    main()
