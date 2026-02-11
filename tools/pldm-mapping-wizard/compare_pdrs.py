#!/usr/bin/env python3
"""Compare retrieved PDRs with expected PDRs."""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder
from pldm_mapping_wizard.discovery.pdr_parser import PDRParser

# Expected PDRs from expected_pdrs.md (as hex bytes)
EXPECTED_PDRS = {
    0x00: [  # Handle 0 might be alias for handle 1
        0x01, 0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x00, 0x09, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01, 0x00,
        0x01, 0x01, 0x01,
    ],
    0x01: [
        0x01, 0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x00, 0x09, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01, 0x00,
        0x01, 0x01, 0x01,
    ],
    0x02: [
        0x02, 0x00, 0x00, 0x00, 0x01, 0x14, 0x01, 0x00, 0x0a, 0x00, 0x01, 0x00, 0x01, 0x00, 0x50, 0x00,
        0x01, 0x00, 0x00, 0x00,
    ],
    0x03: [
        0x03, 0x00, 0x00, 0x00, 0x01, 0x0f, 0x01, 0x00, 0x10, 0x00, 0x01, 0x00, 0x01, 0x50, 0x00, 0x01,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x60, 0x01, 0x00, 0x01, 0x00,
    ],
}

def format_hex(data):
    """Format bytes as hex string."""
    if isinstance(data, (list, bytes)):
        return ' '.join(f'{b:02x}' for b in data)
    return str(data)

def extract_pdr_body(pldm_response):
    """Extract the PDR body from GetPDR response."""
    if len(pldm_response) < 12:
        return None
    
    # Parse GetPDR response format (DSP0248 Table 69):
    # [0] Completion Code
    # [1-4] Next Record Handle (LE)
    # [5-8] Next Data Transfer Handle (LE)
    # [9] Transfer Flag
    # [10-11] Response Count (LE)
    # [12+] recordData
    
    completion_code = pldm_response[0]
    if completion_code != 0:
        return None
    
    response_count = struct.unpack('<H', pldm_response[10:12])[0]
    record_data = pldm_response[12:12+response_count]
    return bytes(record_data)

def main():
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    parser = PDRParser()
    
    if not port.open():
        print("Failed to open port")
        return
    
    print("=" * 100)
    print("PDR COMPARISON: Retrieved vs Expected")
    print("=" * 100)
    print()
    
    # Retrieve first 3 PDRs to compare
    # Note: handles might not be consecutive - try 1, 2, 3
    # But if 2 fails, also try starting from 0
    test_handles = [0x00, 0x01, 0x02, 0x03]
    
    for handle in test_handles:
        print(f"\n{'=' * 100}")
        print(f"Handle: 0x{handle:08x}")
        print(f"{'=' * 100}")
        
        # Retrieve from device
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
        retrieved_bytes = []
        
        if response_frame:
            frames = MCTPFramer.extract_frames(response_frame)
            if frames:
                # Try first frame
                parsed = MCTPFramer.parse_frame(frames[0])
                
                # If parse fails but we have a frame, try to extract manually
                if not parsed and len(frames[0]) > 20:
                    # Manual extraction: remove flags, unescape, extract PLDM payload
                    frame_data = frames[0][1:-1]  # Remove start/end 0x7E
                    unescaped = MCTPFramer._unescape_body(frame_data)
                    if len(unescaped) > 10:
                        # Skip MCTP header (10 bytes) to get PLDM payload
                        pldm_response = unescaped[10:-2]  # Remove FCS at end
                        pdr_body = extract_pdr_body(pldm_response)
                        if pdr_body:
                            retrieved_bytes = list(pdr_body)
                elif parsed:
                    pldm_response = parsed.get("extra", b"")
                    pdr_body = extract_pdr_body(pldm_response)
                    if pdr_body:
                        retrieved_bytes = list(pdr_body)
        
        print(f"\nRetrieved ({len(retrieved_bytes)} bytes):")
        print(f"  {format_hex(retrieved_bytes)}")
        
        # Show expected
        if handle in EXPECTED_PDRS:
            expected_bytes = EXPECTED_PDRS[handle]
            print(f"\nExpected ({len(expected_bytes)} bytes):")
            print(f"  {format_hex(expected_bytes)}")
        else:
            print(f"\nExpected: NOT DEFINED")
            continue
        
        # Compare
        print(f"\nComparison:")
        if retrieved_bytes == expected_bytes:
            print(f"  ✓ MATCH - PDRs are identical")
        else:
            print(f"  ✗ MISMATCH")
            if len(retrieved_bytes) != len(expected_bytes):
                print(f"    Length difference: Retrieved {len(retrieved_bytes)}, Expected {len(expected_bytes)}")
            print(f"\n  Byte-by-byte breakdown:")
            max_len = max(len(retrieved_bytes), len(expected_bytes))
            for i in range(max_len):
                ret_byte = retrieved_bytes[i] if i < len(retrieved_bytes) else None
                exp_byte = expected_bytes[i] if i < len(expected_bytes) else None
                
                ret_str = f"{ret_byte:02x}" if ret_byte is not None else "  "
                exp_str = f"{exp_byte:02x}" if exp_byte is not None else "  "
                match = "✓" if ret_byte == exp_byte else "✗"
                
                print(f"    [{i:2d}] Retrieved: {ret_str}  Expected: {exp_str}  {match}")
    
    port.close()

if __name__ == '__main__':
    main()
