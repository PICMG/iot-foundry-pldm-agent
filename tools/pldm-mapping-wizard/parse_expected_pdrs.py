#!/usr/bin/env python3
"""Parse expected_pdrs.md and extract all PDRs."""

import re

def parse_expected_pdrs(filename):
    """Parse expected_pdrs.md and return dictionary of handle -> bytes."""
    pdrs = {}
    current_handle = None
    current_bytes = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Extract hex bytes from line
            hex_pattern = r'0x[0-9a-fA-F]{2}'
            matches = re.findall(hex_pattern, line)
            
            if matches:
                # Convert to integers
                bytes_list = [int(m, 16) for m in matches]
                
                # First 4 bytes are the handle (little-endian)
                if not current_bytes:
                    handle = bytes_list[0] | (bytes_list[1] << 8) | (bytes_list[2] << 16) | (bytes_list[3] << 24)
                    current_handle = handle
                
                current_bytes.extend(bytes_list)
                
                # Check if this completes a PDR (look for next PDR starting)
                # We'll process all collected bytes when we hit a comment or EOF
                
            elif current_bytes:
                # Save completed PDR
                if current_handle is not None:
                    pdrs[current_handle] = current_bytes
                current_bytes = []
                current_handle = None
    
    # Save last PDR if any
    if current_bytes and current_handle is not None:
        pdrs[current_handle] = current_bytes
    
    return pdrs

if __name__ == '__main__':
    pdrs = parse_expected_pdrs('/home/doug/git/iot-foundry-pldm-agent/expected_pdrs.md')
    
    print("# Parsed Expected PDRs")
    print(f"# Found {len(pdrs)} PDRs\n")
    print("EXPECTED_PDRS = {")
    
    for handle in sorted(pdrs.keys()):
        bytes_list = pdrs[handle]
        print(f"    0x{handle:02x}: [  # {len(bytes_list)} bytes")
        
        # Format as rows of 16 bytes
        for i in range(0, len(bytes_list), 16):
            chunk = bytes_list[i:i+16]
            hex_str = ', '.join(f'0x{b:02x}' for b in chunk)
            print(f"        {hex_str},")
        
        print("    ],")
    
    print("}")
