#!/usr/bin/env python3
"""Complete analysis of handle 0x02: summary and raw data."""

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
    
    # Send request
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
    print(f"HANDLE 0x{handle:08X} ANALYSIS")
    print("=" * 100)
    print()
    
    # RAW DATA
    print("RAW RESPONSE DATA:")
    print("-" * 100)
    for i in range(0, len(response_frame), 16):
        chunk = response_frame[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  [{i:3d}] {hex_str:<48s} |{ascii_str}|")
    print()
    
    # Extract frame data
    frames = MCTPFramer.extract_frames(response_frame)
    if not frames:
        print("ERROR: No frames extracted")
        port.close()
        return
    
    frame_data = frames[0][1:-1]  # Remove start/end flags
    unescaped = MCTPFramer._unescape_body(frame_data)
    
    if len(unescaped) < 10:
        print("ERROR: Frame too short")
        port.close()
        return
    
    pldm_payload = unescaped[10:-2]  # Skip MCTP/PLDM headers and FCS
    
    # Parse GetPDR response
    if len(pldm_payload) < 12:
        print("ERROR: PLDM payload too short")
        port.close()
        return
    
    cc = pldm_payload[0]
    next_handle = struct.unpack('<I', pldm_payload[1:5])[0]
    next_xfer = struct.unpack('<I', pldm_payload[5:9])[0]
    xfer_flag = pldm_payload[9]
    resp_count = struct.unpack('<H', pldm_payload[10:12])[0]
    record_data = pldm_payload[12:]
    
    # Parse PDR header from recordData
    if len(record_data) < 10:
        print("ERROR: recordData too short for PDR header")
        port.close()
        return
    
    rec_handle = struct.unpack('<I', record_data[0:4])[0]
    hdr_ver = record_data[4]
    pdr_type = record_data[5]
    rec_change = struct.unpack('<H', record_data[6:8])[0]
    data_len = struct.unpack('<H', record_data[8:10])[0]
    pdr_body = record_data[10:]
    
    # SUMMARY
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print()
    
    print("GetPDR Response Structure:")
    print(f"  Total response buffer:        {len(response_frame)} bytes")
    print(f"  Frame flags:                  0x7E at positions 0, 44, 45 (extra 0x7E AFTER data)")
    print(f"  MCTP frame body:              40 bytes (byte count field = 0x28)")
    print(f"  PLDM GetPDR response:         {len(pldm_payload)} bytes")
    print()
    
    print("GetPDR Response Fields:")
    print(f"  [0]       Completion Code:    0x{cc:02x} {'(Success)' if cc == 0 else '(Error)'}")
    print(f"  [1-4]     Next Record Handle: 0x{next_handle:08x}")
    print(f"  [5-8]     Next Xfer Handle:   0x{next_xfer:08x}")
    print(f"  [9]       Transfer Flag:      0x{xfer_flag:02x} (0x05 = StartAndEnd)")
    print(f"  [10-11]   Response Count:     {resp_count} bytes")
    print(f"  [12+]     recordData:         {len(record_data)} bytes RECEIVED")
    print()
    
    print("PDR Header (first 10 bytes of recordData):")
    print(f"  [0-3]     Record Handle:      0x{rec_handle:08x}")
    print(f"  [4]       Header Version:     0x{hdr_ver:02x}")
    print(f"  [5]       PDR Type:           0x{pdr_type:02x} (0x14 = FRU Record Set)")
    print(f"  [6-7]     Record Change Num:  {rec_change}")
    print(f"  [8-9]     Data Length:        {data_len} bytes (body length)")
    print(f"  [10+]     PDR Body:           {len(pdr_body)} bytes RECEIVED")
    print()
    
    print("ISSUE DETECTED:")
    print(f"  ⚠  Response Count field says:    {resp_count} bytes")
    print(f"  ⚠  Actual recordData received:   {len(record_data)} bytes")
    print(f"  ⚠  Missing:                       {resp_count - len(record_data)} byte(s)")
    print()
    print(f"  ⚠  PDR Data Length field says:    {data_len} bytes")
    print(f"  ⚠  Actual PDR body received:      {len(pdr_body)} bytes")
    print(f"  ⚠  Missing from body:             {data_len - len(pdr_body)} byte(s)")
    print()
    
    # Expected PDR
    expected_pdr = [
        0x02, 0x00, 0x00, 0x00, 0x01, 0x14, 0x01, 0x00, 0x0a, 0x00,  # Header
        0x01, 0x00, 0x01, 0x00, 0x50, 0x00, 0x01, 0x00, 0x00, 0x00,  # Body
    ]
    
    print("COMPARISON WITH EXPECTED:")
    print(f"  Expected total PDR:             {len(expected_pdr)} bytes (10 header + 10 body)")
    print(f"  Received total PDR:             {len(record_data)} bytes (10 header + {len(pdr_body)} body)")
    print(f"  Missing:                        {len(expected_pdr) - len(record_data)} byte(s)")
    print()
    
    print("Expected FRU Record Set PDR:")
    hex_str = ' '.join(f'{b:02x}' for b in expected_pdr)
    print(f"  {hex_str}")
    print()
    
    print("Received FRU Record Set PDR:")
    hex_str = ' '.join(f'{b:02x}' for b in record_data)
    print(f"  {hex_str}")
    print()
    
    print("Byte-by-byte comparison:")
    for i in range(max(len(expected_pdr), len(record_data))):
        exp_byte = expected_pdr[i] if i < len(expected_pdr) else None
        rec_byte = record_data[i] if i < len(record_data) else None
        
        exp_str = f"{exp_byte:02x}" if exp_byte is not None else "  "
        rec_str = f"{rec_byte:02x}" if rec_byte is not None else "  "
        match = "✓" if exp_byte == rec_byte else "✗"
        
        section = ""
        if i < 10:
            section = " [HEADER]"
        else:
            section = " [BODY]"
        
        print(f"  [{i:2d}] Expected: {exp_str}  Received: {rec_str}  {match}{section}")
    
    print()
    print("=" * 100)
    
    port.close()

if __name__ == '__main__':
    main()
