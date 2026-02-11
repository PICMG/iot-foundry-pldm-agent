#!/usr/bin/env python3
"""Parse retrieved PDRs using IoT.2 and DSP0248 specifications."""

import json
from pldm_mapping_wizard.discovery.pdr_retriever import PDRRetriever
from pldm_mapping_wizard.discovery.pdr_parser import PDRParser, PDR_TYPES

def main():
    """Retrieve and parse PDRs from device."""
    print("=" * 100)
    print("PDR Parser - PICMG IoT.2 and DSP0248 Compliance")
    print("=" * 100)
    
    # Connect and retrieve PDRs
    retriever = PDRRetriever(
        port="/dev/ttyUSB0",
        local_eid=16,
        remote_eid=0,
        baudrate=115200,
        debug=False,  # Reduce noise
    )
    
    if not retriever.connect():
        print("❌ Failed to connect")
        return
    
    try:
        # Get repository info
        repo_info = retriever.get_repository_info()
        if not repo_info or "error" in repo_info:
            print(f"❌ Failed to get repository info: {repo_info}")
            return
        
        print(f"✓ Repository: {repo_info['total_pdr_records']} PDRs")
        
        # Retrieve PDRs
        print(f"📥 Retrieving PDRs...")
        pdrs = retriever.get_pdrs()
        print(f"✓ Retrieved {len(pdrs)} PDRs\n")
        
        # Parse PDRs
        print("=" * 100)
        print("PARSED PDRs - IoT.2 and DSP0248 Format")
        print("=" * 100)
        
        parsed_pdrs = []
        type_summary = {}
        
        for i, pdr in enumerate(pdrs):
            pdr_data = pdr.get("data", b"")
            parsed = PDRParser.parse(pdr_data)
            parsed_pdrs.append(parsed)
            
            pdr_type = parsed.get("type_name", "Unknown")
            type_summary[pdr_type] = type_summary.get(pdr_type, 0) + 1
            
            # Print summary for each PDR
            handle = parsed.get("handle", "unknown")
            pdr_type = parsed.get("type_name", "Unknown")
            content_type = parsed.get("content", {}).get("type", "?")
            
            print(f"\n[{i}] Handle {handle}: {pdr_type}")
            
            # Print specific details based on type
            content = parsed.get("content", {})
            if content_type == "Entity Association":
                container = content.get("container", {})
                print(f"    Container: {container.get('entity_name', '?')} #{container.get('instance', '?')}")
                children = content.get("children", [])
                print(f"    Children: {len(children)} entities")
                for child in children[:3]:
                    print(f"      - {child.get('entity_name', '?')} #{child.get('instance', '?')}")
            
            elif content_type == "Numeric Sensor":
                entity = content.get("entity", {})
                print(f"    Sensor {content.get('sensor_number', '?')}: {content.get('sensor_type_name', '?')}")
                print(f"    Entity: {entity.get('entity_name', '?')} #{entity.get('instance', '?')}")
            
            elif content_type == "State Sensor":
                entity = content.get("entity", {})
                print(f"    Sensor {content.get('sensor_number', '?')}: {content.get('sensor_type_name', '?')}")
                print(f"    Entity: {entity.get('entity_name', '?')} #{entity.get('instance', '?')}")
                print(f"    States: {content.get('states_mask', '?')}")
            
            else:
                if "error" in content or "parse_error" in content:
                    print(f"    ⚠️  {content.get('error') or content.get('parse_error')}")
                else:
                    print(f"    Size: {content.get('size', '?')} bytes")
        
        # Summary
        print(f"\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)
        print(f"Total PDRs: {len(pdrs)}")
        print(f"\nPDR Type Distribution:")
        for pdr_type, count in sorted(type_summary.items()):
            print(f"  {pdr_type}: {count}")
        
        # Save detailed JSON
        output_file = "/tmp/parsed_pdrs.json"
        with open(output_file, "w") as f:
            json.dump(parsed_pdrs, f, indent=2, default=str)
        print(f"\n✓ Detailed parse saved to {output_file}")
    
    finally:
        retriever.disconnect()
        print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
