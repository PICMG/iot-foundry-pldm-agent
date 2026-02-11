# Entity Type ID Mappings extracted from DSP0249 PLDM State Set Specification v1.0.0
# Table 15 – Entity ID Codes
# Source: PLDM State Set Specification DSP0249_1.0.0.pdf

ENTITY_TYPES = {
    # Unspecified and Other
    0: "Unspecified",
    1: "Other",
    
    # Miscellaneous Entities
    2: "Network",
    3: "Group",
    4: "Remote (Out of Band) Management Communication Device",
    5: "External Environment",
    6: "Communication Channel",
    7: "PLDM Terminus",
    8: "Platform Event Log",
    
    # Human Interface Entities
    15: "Keypad",
    16: "Switch",
    17: "Pushbutton",
    18: "Display",
    19: "Indicator",
    
    # Software/Firmware Entities
    30: "System Management Software",
    31: "System Firmware",
    32: "Operating System",
    33: "Virtual Machine Manager",
    34: "OS Loader",
    35: "Device Driver",
    36: "Management Controller Firmware",
    
    # Chassis/Enclosure Entities
    45: "System chassis",
    46: "Sub-chassis",
    47: "Disk Drive Bay",
    48: "Peripheral Bay",
    49: "Device Bay",
    50: "Door",
    51: "Access Panel",
    52: "Cover",
    
    # Board/Card/Module Entities
    60: "Board",
    61: "Card",
    62: "Module",
    63: "System management module",
    64: "System board",
    65: "Memory board",
    66: "Memory module",
    67: "Processor module",
    68: "Add-in card",
    69: "Chassis front panel board",
    70: "Back panel board",
    71: "Power management/power distribution board",
    72: "Power system board",
    73: "Drive backplane",
    74: "System internal expansion board",
    75: "Other system board",
    76: "Chassis back panel board",
    77: "Processing blade",
    78: "Connectivity switch",
    79: "Processor/memory module",
    80: "I/O module",
    81: "Processor/I/O module",
    
    # Cooling Entities
    90: "Cooling device",
    91: "Cooling subsystem",
    92: "Cooling unit/domain",
    93: "Fan",
    94: "Peltier Cooling Device",
    95: "Liquid Cooling Device",
    96: "Liquid Cooling subsystem",
    
    # Storage Device Entities
    105: "Other storage device",
    106: "Floppy Drive",
    107: "Fixed Disk / Hard Drive",
    108: "CD Drive",
    109: "CD/DVD Drive",
    110: "Other Silicon Storage Device",
    111: "Solid State Drive",
    
    # Power Entities
    120: "Power supply",
    121: "Battery",
    122: "Super capacitor",
    123: "Power converter",
    124: "DC-DC converter",
    125: "AC mains power supply",
    126: "DC mains power supply",
    
    # Chip Entities
    135: "Processor",
    136: "Chipset component",
    137: "Management controller",
    138: "Peripheral controller",
    139: "SEEPROM",
    140: "NVRAM chip",
    141: "FLASH Memory chip",
    142: "Memory chip",
    143: "Memory controller",
    144: "Network controller",
    145: "I/O controller",
    146: "South bridge",
    147: "Real Time Clock (RTC)",
    
    # Bus Entities
    160: "Other Bus",
    161: "System Bus",
    162: "I2C Bus",
    163: "SMBus Bus",
    164: "SPI Bus",
    165: "PCI Bus",
    166: "PCI Express Bus",
    167: "PECI Bus",
    168: "LPC Bus",
    169: "USB Bus",
    170: "FireWire Bus",
    171: "SCSI Bus",
    172: "SATA/SAS Bus",
    173: "Processor/front-side Bus",
    174: "Inter-processor Bus",
    
    # Connectors/Cables
    185: "Connector",
    186: "Slot",
    187: "Cable",
    188: "Interconnect",
    189: "Plug",
    190: "Socket",
    
    # OEM/Vendor-Defined Entities (ranges with representative value)
    # 192-16383 (0x900xAF): Chassis-specific entities
    # 16384-24575 (0xB00xCF): Board-set specific entities
    # 24576-32767 (0xD00xFF): OEM System Integrator defined
    # All other values are reserved
}

# OEM/Vendor-Defined Entity Ranges (for reference)
OEM_ENTITY_RANGES = {
    "chassis_specific": {"start": 192, "end": 16383, "description": "Chassis-specific entities"},
    "board_set_specific": {"start": 16384, "end": 24575, "description": "Board-set specific entities"},
    "oem_system_integrator": {"start": 24576, "end": 32767, "description": "OEM System Integrator defined"},
}

if __name__ == "__main__":
    # Print all entity types
    print("PLDM Entity Types from DSP0249:")
    print("=" * 80)
    for code, name in sorted(ENTITY_TYPES.items()):
        print(f"{code:3d}: {name}")
    
    print("\n\nOEM Ranges:")
    print("=" * 80)
    for range_name, range_info in OEM_ENTITY_RANGES.items():
        print(f"{range_name}: {range_info['start']}-{range_info['end']} - {range_info['description']}")
    
    print(f"\n\nTotal defined entities: {len(ENTITY_TYPES)}")
