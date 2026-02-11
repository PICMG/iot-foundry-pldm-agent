#!/usr/bin/env python3
"""Debug script to show raw PDR bytes vs expected"""

import sys
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

from pldm_mapping_wizard.discovery.pdr_retriever import PDRRetriever

def bytes_to_hex(data):
    """Convert bytes to hex string with 16 bytes per line"""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = ', '.join(f'0x{b:02x}' for b in chunk)
        lines.append(hex_str)
    return ',\n   '.join(lines)

try:
    print("Connecting to device and retrieving PDRs...")
    retriever = PDRRetriever(port='/dev/ttyUSB0', baudrate=115200)
    pdrs = retriever.get_pdrs()
    
    print(f"\nRetrieved {len(pdrs)} PDRs\n")
    
    # Show first few PDRs in hex format
    for i, pdr_data in enumerate(pdrs[:5]):
        print(f"PDR[{i}] - Handle {pdr_data[:4].hex()}:")
        print(f"   {bytes_to_hex(pdr_data)}")
        print()
        
        # Decode header
        handle = int.from_bytes(pdr_data[0:4], 'little')
        version = pdr_data[4]
        pdr_type = pdr_data[5]
        change_num = int.from_bytes(pdr_data[6:8], 'little')
        length = int.from_bytes(pdr_data[8:10], 'little')
        
        print(f"   Header: handle={handle:08x}, version={version}, type={pdr_type}, change={change_num}, length={length}")
        print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
