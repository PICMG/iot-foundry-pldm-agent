#!/usr/bin/env python3
"""
Debug PDR retrieval to see raw request/response data.
"""

import struct
import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def debug_get_pdr(port, handle):
    """Retrieve a single PDR and show all debug info."""
    print(f"\n{'='*80}")
    print(f"REQUESTING PDR Handle: 0x{handle:08x}")
    print(f"{'='*80}")
    
    # Start with first request
    data_transfer_handle = 0
    transfer_operation_flag = 0x01  # Get First Part
    
    cmd = PDLMCommandEncoder.encode_get_pdr(
        instance_id=0,
        record_handle=handle,
        data_transfer_handle=data_transfer_handle,
        transfer_operation_flag=transfer_operation_flag,
        request_count=255,
        record_change_number=0,
    )
    
    print(f"GetPDR Request (PLDM payload):")
    print(f"  Length: {len(cmd)} bytes")
    print(f"  Hex: {cmd.hex(' ')}")
    print(f"  Breakdown:")
    print(f"    [0]    PLDM rq/IID: 0x{cmd[0]:02x}")
    print(f"    [1]    PLDM Type/Ver: 0x{cmd[1]:02x}")
    print(f"    [2]    Command Code: 0x{cmd[2]:02x} (GetPDR)")
    print(f"    [3-6]  Record Handle: 0x{struct.unpack('<I', cmd[3:7])[0]:08x}")
    print(f"    [7-10] Data Transfer Handle: 0x{struct.unpack('<I', cmd[7:11])[0]:08x}")
    print(f"    [11]   Transfer Op Flag: 0x{cmd[11]:02x}")
    print(f"    [12-13] Request Count: {struct.unpack('<H', cmd[12:14])[0]} bytes")
    print(f"    [14-15] Record Change Number: {struct.unpack('<H', cmd[14:16])[0]}")
    
    frame = MCTPFramer.build_frame(pldm_msg=cmd, dest=0, src=16, msg_type=0x01)
    print(f"\nMCTP Frame to send:")
    print(f"  Length: {len(frame)} bytes")
    print(f"  Hex: {frame.hex(' ')}")
    
    port.write(frame)
    response = port.read_until_idle()
    
    print(f"\nRaw Response from device:")
    print(f"  Length: {len(response)} bytes")
    print(f"  Hex: {response.hex(' ')}")
    
    if not response:
        print("ERROR: No response")
        return None
    
    frames = MCTPFramer.extract_frames(response)
    print(f"\nExtracted Frames: {len(frames)}")
    
    if not frames:
        print("ERROR: No frames extracted")
        return None
    
    for i, frame_data in enumerate(frames):
        print(f"\nFrame {i}:")
        print(f"  Length: {len(frame_data)} bytes")
        print(f"  Hex: {frame_data.hex(' ')}")
    
    frame_parsed = MCTPFramer.parse_frame(frames[0])
    if not frame_parsed:
        print("ERROR: Failed to parse frame")
        return None
    
    print(f"\nParsed Frame:")
    print(f"  Protocol: 0x{frame_parsed.get('protocol', 0):02x}")
    print(f"  Dest: {frame_parsed.get('dest', 0)}")
    print(f"  Src: {frame_parsed.get('src', 0)}")
    print(f"  Msg Type: 0x{frame_parsed.get('msg_type', 0):02x}")
    
    pldm_data = frame_parsed.get('extra')
    if not pldm_data or len(pldm_data) < 12:
        print(f"ERROR: Invalid PLDM payload (length: {len(pldm_data) if pldm_data else 0})")
        return None
    
    print(f"\nPLDM Response Payload:")
    print(f"  Length: {len(pldm_data)} bytes")
    print(f"  Hex: {pldm_data[:60].hex(' ')}{'...' if len(pldm_data) > 60 else ''}")
    
    completion_code = pldm_data[0]
    print(f"\n  [0]    Completion Code: 0x{completion_code:02x}")
    
    if completion_code != 0:
        completion_names = {
            0x80: "PLDM_ERROR",
            0x81: "PLDM_ERROR_INVALID_DATA",
            0x82: "PLDM_PLATFORM_INVALID_RECORD_HANDLE",
            0x83: "PLDM_PLATFORM_INVALID_DATA_TRANSFER_HANDLE",
            0x84: "PLDM_PLATFORM_TRANSFER_TIMEOUT",
        }
        error_name = completion_names.get(completion_code, "Unknown Error")
        print(f"         ERROR: {error_name}")
        return None
    
    next_handle = struct.unpack('<I', pldm_data[1:5])[0]
    xfer_handle = struct.unpack('<I', pldm_data[5:9])[0]
    xfer_flag = pldm_data[9]
    response_count = struct.unpack('<H', pldm_data[10:12])[0]
    
    print(f"  [1-4]  Next Record Handle: 0x{next_handle:08x}")
    print(f"  [5-8]  Data Transfer Handle: 0x{xfer_handle:08x}")
    print(f"  [9]    Transfer Flag: 0x{xfer_flag:02x}", end="")
    
    xfer_flag_names = {
        0x00: "Start (first part of multi-part)",
        0x01: "Middle (continuation of multi-part)",
        0x04: "End (last part of multi-part)",
        0x05: "StartAndEnd (single part, complete)",
    }
    print(f" ({xfer_flag_names.get(xfer_flag, 'Unknown')})")
    
    print(f"  [10-11] Response Count: {response_count} bytes")
    
    pdr_data = pldm_data[12:12+response_count]
    print(f"\nPDR Data:")
    print(f"  Length: {len(pdr_data)} bytes")
    
    if len(pdr_data) >= 10:
        record_handle = struct.unpack('<I', pdr_data[0:4])[0]
        pdr_version = pdr_data[4]
        pdr_type = pdr_data[5]
        change_num = struct.unpack('<H', pdr_data[6:8])[0]
        record_length = struct.unpack('<H', pdr_data[8:10])[0]
        
        print(f"  PDR Header:")
        print(f"    Record Handle: 0x{record_handle:08x}")
        print(f"    PDR Version: {pdr_version}")
        print(f"    PDR Type: {pdr_type}")
        print(f"    Change Number: {change_num}")
        print(f"    Record Length: {record_length} bytes")
        print(f"  PDR Body (first 50 bytes): {pdr_data[10:60].hex(' ')}")
        
        if record_length > response_count - 10:
            print(f"\n  ⚠ WARNING: Record length ({record_length}) > Response data ({response_count - 10})")
            print(f"            This PDR requires multi-part transfer!")
            print(f"            Need {record_length - (response_count - 10)} more bytes")
            
            # Continue multi-part transfer
            if xfer_handle != 0 and xfer_flag in [0x00, 0x01]:
                print(f"\n  🔄 CONTINUING MULTI-PART TRANSFER...")
                print(f"     Using Data Transfer Handle: 0x{xfer_handle:08x}")

                expected_total = record_length + 10
                full_pdr = bytearray(pdr_data)
                record_change_number = change_num
                part_index = 2

                while xfer_handle != 0 and len(full_pdr) < expected_total:
                    cmd_next = PDLMCommandEncoder.encode_get_pdr(
                        instance_id=0,
                        record_handle=handle,
                        data_transfer_handle=xfer_handle,
                        transfer_operation_flag=0x00,  # GetNextPart
                        request_count=255,
                        record_change_number=record_change_number,
                    )

                    print(f"\n  GetPDR Request #{part_index} (PLDM payload):")
                    print(f"    Length: {len(cmd_next)} bytes")
                    print(f"    Hex: {cmd_next.hex(' ')}")
                    print(f"    Data Transfer Handle: 0x{struct.unpack('<I', cmd_next[7:11])[0]:08x}")
                    print(f"    Transfer Op Flag: 0x{cmd_next[11]:02x}")

                    frame_next = MCTPFramer.build_frame(pldm_msg=cmd_next, dest=0, src=16, msg_type=0x01)
                    print(f"\n  MCTP Frame #{part_index} to send:")
                    print(f"    Length: {len(frame_next)} bytes")
                    print(f"    Hex: {frame_next.hex(' ')}")

                    port.write(frame_next)
                    response_next = port.read_until_idle()

                    print(f"\n  Raw Response #{part_index} from device:")
                    print(f"    Length: {len(response_next)} bytes")
                    print(f"    Hex: {response_next.hex(' ')}")

                    if not response_next:
                        break

                    frames_next = MCTPFramer.extract_frames(response_next)
                    if not frames_next:
                        break

                    frame_parsed_next = MCTPFramer.parse_frame(frames_next[0])
                    if not frame_parsed_next:
                        break

                    pldm_data_next = frame_parsed_next.get('extra')
                    if not pldm_data_next or len(pldm_data_next) < 12:
                        break

                    completion_code_next = pldm_data_next[0]
                    print(f"\n  Response #{part_index} Completion Code: 0x{completion_code_next:02x}")
                    if completion_code_next != 0:
                        break

                    xfer_handle = struct.unpack('<I', pldm_data_next[5:9])[0]
                    xfer_flag = pldm_data_next[9]
                    response_count_next = struct.unpack('<H', pldm_data_next[10:12])[0]
                    pdr_data_next = pldm_data_next[12:12+response_count_next]

                    print(f"  Transfer Flag: 0x{xfer_flag:02x} ({xfer_flag_names.get(xfer_flag, 'Unknown')})")
                    print(f"  Response Count: {response_count_next} bytes")
                    print(f"  PDR Data Part {part_index}: {pdr_data_next.hex(' ')}")

                    full_pdr.extend(pdr_data_next)

                    if xfer_flag in [0x04, 0x05] or xfer_handle == 0:
                        break

                    part_index += 1

                print(f"\n  ✅ COMPLETE PDR DATA:")
                print(f"     Total Length: {len(full_pdr)} bytes")
                print(f"     Expected: {expected_total} bytes")
                print(f"     Full Hex: {full_pdr.hex(' ')}")
                pdr_data = bytes(full_pdr)
    
    return {
        'handle': handle,
        'next_handle': next_handle,
        'xfer_handle': xfer_handle,
        'xfer_flag': xfer_flag,
        'pdr_data': pdr_data,
    }

def main():
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    # Test specific handles that were failing
    test_handles = [0, 2, 3, 4, 5, 6, 7]
    
    for handle in test_handles:
        result = debug_get_pdr(port, handle)
        if result:
            print(f"\n✓ Successfully retrieved handle 0x{handle:08x}")
        else:
            print(f"\n✗ Failed to retrieve handle 0x{handle:08x}")
        
        input("\nPress Enter to continue to next PDR...")
    
    port.close()

if __name__ == '__main__':
    main()
