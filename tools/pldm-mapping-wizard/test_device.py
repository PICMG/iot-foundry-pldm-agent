#!/usr/bin/env python3
"""Test PLDM device communication and show request/response traces."""

from pldm_mapping_wizard.discovery.pdr_retriever import PDRRetriever
import sys

def hexdump(data: bytes, prefix: str = "") -> None:
    """Print hex dump in readable format."""
    if not data:
        print(f"{prefix}(empty)")
        return
    
    # Print as continuous hex string
    print(f"{prefix}{data.hex()}")
    
    # Print as formatted hex dump (16 bytes per line)
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{prefix}{i:04x}:  {hex_part:<48}  {ascii_part}")

def main():
    """Run PDR discovery with detailed traces."""
    print("=" * 100)
    print("PLDM Device Discovery Test - Complete TX/RX Traces")
    print("=" * 100)
    
    retriever = PDRRetriever(
        port="/dev/ttyUSB0",
        local_eid=16,
        remote_eid=0,
        baudrate=115200,
        debug=True,  # Enable debug output
    )
    
    if not retriever.connect():
        print("❌ Failed to connect")
        return
    
    try:
        # Get repository info
        print("\n" + "=" * 100)
        print("Step 1: GetPDRRepositoryInfo")
        print("=" * 100)
        repo_info = retriever.get_repository_info()
        if repo_info and "error" not in repo_info:
            print(f"\n✓ Repository Info: {repo_info['total_pdr_records']} PDRs, {repo_info['repository_size']} bytes")
        else:
            print(f"❌ Repository Info failed: {repo_info}")
            return
        
        # Get first few PDRs
        print("\n" + "=" * 100)
        print("Step 2: GetPDR commands (retrieving all PDRs)")
        print("=" * 100)
        pdrs = retriever.get_pdrs()
        
        print(f"\n" + "=" * 100)
        print(f"✓ Retrieved {len(pdrs)} PDRs successfully")
        print("=" * 100)
        for i, pdr in enumerate(pdrs[:10]):  # Show first 10
            print(f"  PDR {i}: handle={pdr.get('record_handle', '?')}, "
                  f"type={pdr.get('type', '?')}, size={len(pdr.get('data', b''))} bytes")
    
    finally:
        retriever.disconnect()
        print("\n" + "=" * 100)
        print("Test complete")
        print("=" * 100)

if __name__ == "__main__":
    main()
