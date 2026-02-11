#!/usr/bin/env python3
"""
Detailed PDR Analysis - Shows all parsed PDRs with their type and type-specific fields
"""

import json
import sys

def format_entity(entity_dict):
    """Format an entity dictionary for display"""
    return f"{entity_dict['entity_name']} (type {entity_dict['entity_type']}) #{entity_dict['instance']}"

def analyze_pdrs():
    """Load and analyze parsed PDRs from JSON"""
    try:
        with open('/tmp/parsed_pdrs.json', 'r') as f:
            pdrs = json.load(f)
    except FileNotFoundError:
        print("ERROR: /tmp/parsed_pdrs.json not found. Run parse_pdrs.py first.")
        sys.exit(1)
    
    print("=" * 100)
    print(f"PDR DETAILED ANALYSIS - {len(pdrs)} PDRs")
    print("=" * 100)
    print()
    
    # Group by type
    by_type = {}
    for pdr in pdrs:
        pdr_type = pdr.get('type_name', f"Type {pdr.get('type')}")
        if pdr_type not in by_type:
            by_type[pdr_type] = []
        by_type[pdr_type].append(pdr)
    
    # Print summary
    print("TYPE DISTRIBUTION:")
    print("-" * 100)
    for pdr_type, pdr_list in sorted(by_type.items()):
        print(f"  {pdr_type}: {len(pdr_list)} PDRs")
    print()
    
    # Detailed analysis by type
    for pdr_type, pdr_list in sorted(by_type.items()):
        print("=" * 100)
        print(f"{pdr_type.upper()}")
        print("=" * 100)
        
        for pdr in pdr_list:
            handle = pdr['handle']
            version = pdr['version']
            change_num = pdr['change_number']
            length = pdr['length']
            content = pdr['content']
            
            print(f"\nHandle: {handle}")
            print(f"  Version: {version}, Change Number: {change_num}, Length: {length} bytes")
            
            if pdr_type == "Entity Association":
                print(f"  Container: {format_entity(content['container'])}")
                print(f"  Is Container: {content['is_container']}")
                if content['children']:
                    print(f"  Children: {len(content['children'])}")
                    for i, child in enumerate(content['children'], 1):
                        print(f"    [{i}] {format_entity(child)}")
                else:
                    print(f"  Children: (none)")
            
            elif pdr_type == "Numeric Sensor":
                print(f"  Sensor Type: {content.get('sensor_type_name', content.get('sensor_type'))}")
                print(f"  Sensor Number: {content.get('sensor_number')}")
                print(f"  Entity: {format_entity(content['entity'])}")
                print(f"  Sensor Units: {content.get('sensor_units_modifier', {}).get('units_name', 'N/A')}")
                print(f"  Rate Unit: {content.get('rate_unit', 'N/A')}")
                print(f"  Modifiers: {content.get('sensor_units_modifier', {})}")
                print(f"  Thresholds: {content.get('thresholds', {})}")
            
            elif pdr_type == "State Sensor":
                print(f"  Sensor Type: {content.get('sensor_type_name', content.get('sensor_type'))}")
                print(f"  Sensor Number: {content.get('sensor_number')}")
                print(f"  Entity: {format_entity(content['entity'])}")
                print(f"  State Mask: {content.get('composite_sensor_mask', 'N/A')}")
                print(f"  Possible States: {content.get('possible_states', 'N/A')}")
            
            else:
                # Generic content display
                print(f"  Content: {json.dumps(content, indent=4)}")
        
        print()
    
    # Summary statistics
    print("=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)
    print(f"Total PDRs: {len(pdrs)}")
    print(f"Total PDR Length (bytes): {sum(pdr['length'] for pdr in pdrs)}")
    
    entity_types = set()
    for pdr in pdrs:
        if pdr['type_name'] == 'Entity Association':
            content = pdr['content']
            entity_types.add(content['container']['entity_type'])
            for child in content.get('children', []):
                entity_types.add(child['entity_type'])
    
    print(f"Unique Entity Types Found: {sorted(entity_types)}")
    print()

if __name__ == '__main__':
    analyze_pdrs()
