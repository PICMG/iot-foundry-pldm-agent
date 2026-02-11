#!/usr/bin/env python3
"""Capture complete TX/RX trace for DUT debugging."""

import sys
from pldm_mapping_wizard.discovery.pdr_retriever import PDRRetriever

def main():
    """Capture traces."""
    print("=" * 140)
    print("COMPLETE TX/RX TRACE FOR DUT DEBUGGING")
    print("=" * 140)
    
    retriever = PDRRetriever(
        port="/dev/ttyUSB0",
        local_eid=16,
        remote_eid=0,
        baudrate=115200,
        debug=False,  # Disable verbose debug output
    )
    
    if not retriever.connect():
        print("❌ Failed to connect")
        return
    
    try:
        # Get repository info
        print("\n[STEP 1] GetPDRRepositoryInfo")
        repo_info = retriever.get_repository_info()
        if repo_info and "error" not in repo_info:
            print(f"✓ Found {repo_info['total_pdr_records']} PDRs\n")
        else:
            print(f"❌ Failed\n")
            return
        
        # Get PDRs
        print("[STEP 2] GetPDR commands")
        pdrs = retriever.get_pdrs()
        
        print(f"\n✓ Retrieved {len(pdrs)} PDRs")
    
    finally:
        retriever.disconnect()
        print("\n" + "=" * 140)
        print("TRACE COMPLETE")
        print("=" * 140)

if __name__ == "__main__":
    main()
