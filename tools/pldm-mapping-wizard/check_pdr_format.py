#!/usr/bin/env python3
"""Check if PDR record data includes header."""

from pldm_mapping_wizard.discovery.pdr_retriever import PDRRetriever

retriever = PDRRetriever(
    port="/dev/ttyUSB0",
    local_eid=16,
    remote_eid=0,
    baudrate=115200,
    debug=False,
)

if not retriever.connect():
    print("❌ Failed to connect")
    exit(1)

# Get first PDR
pdrs = retriever.get_pdrs()

if pdrs:
    print(f"Retrieved {len(pdrs)} PDRs\n")
    
    for i, pdr in enumerate(pdrs[:3]):
        print(f"=== PDR {i} ===")
        print(f"Record Handle from response: 0x{pdr['record_handle']:08x}")
        print(f"Data length: {len(pdr['data'])} bytes")
        print(f"Raw data (hex): {pdr['data'].hex()}")
        
        if len(pdr['data']) >= 10:
            # Check if data starts with PDR header format (DSP0248 Table 17)
            handle_in_data = int.from_bytes(pdr['data'][0:4], 'little')
            header_ver = pdr['data'][4]
            pdr_type = pdr['data'][5]
            change_num = int.from_bytes(pdr['data'][6:8], 'little')
            data_len = int.from_bytes(pdr['data'][8:10], 'little')
            
            print(f"  If data contains header:")
            print(f"    Handle in data: 0x{handle_in_data:08x}")
            print(f"    Header version: {header_ver}")
            print(f"    PDR type: {pdr_type}")
            print(f"    Change number: {change_num}")
            print(f"    Data length field: {data_len}")
            print(f"    Total if with header: {10 + data_len} bytes")
        print()

retriever.disconnect()
