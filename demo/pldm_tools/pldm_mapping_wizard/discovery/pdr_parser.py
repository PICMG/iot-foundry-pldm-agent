"""PDR (Platform Descriptor Record) parser for PICMG IoT.2 and PLDM Platform Control.

Implements parsing of PDR types per DSP0248 Table 17 and PICMG IoT.2 specifications.
"""

import struct
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


# PDR Types per DSP0248 Table 17
PDR_TYPES = {
    0: "PDR Header (not a record)",
    1: "Entity Association",
    2: "FRU Record",
    3: "Full Sensor",
    4: "Compact Sensor",
    5: "Sensor Arrangement",
    6: "NVSR",
    7: "Event Receiver",
    8: "Numeric Sensor",
    9: "Numeric Sensor Threshold",
    10: "State Sensor",
    11: "State Sensor Possible States",
    12: "Sensor Auxiliary Names",
    13: "Effecter Auxiliary Names",
    14: "OEM Device FRU Record",
    15: "Attribute",
    16: "Byte Value Effecter",
    17: "Word Value Effecter",
    18: "State Effecter",
    19: "State Effecter Possible States",
    20: "Entity Auxiliary Names",
    21: "Power Supply Auxiliary Names",
    22: "Effecter Auxiliary Names",
}

# Entity Types (PICMG IoT.2 / DSP0248)
ENTITY_TYPES = {
    0x01: "Unspecified",
    0x03: "Processor",
    0x04: "Disk Drive",
    0x05: "Disk Drive Bay",
    0x06: "Power Module",
    0x07: "Power Module Bay",
    0x08: "Power Supply",
    0x09: "Power Supply Bay",
    0x0A: "Cooling Unit",
    0x0B: "Cooling Unit Bay",
    0x0C: "Cable/Interconnect",
    0x0D: "Memory Module",
    0x0E: "Memory Module Bay",
    0x14: "Motherboard",
    0x16: "Power Converter",
    0x17: "Power Converter Bay",
    0x18: "Management Controller",
    0x19: "System Management Module",
    0x1A: "System Chassis",
    0x20: "Temperature Sensor",
    0x21: "Voltage Sensor",
    0x22: "Current Sensor",
    0x23: "Fan",
    0x24: "Power Meter",
    0x29: "Cooling Device",
    0x2A: "Watchdog Timer",
}

# Sensor Types (DSP0248)
SENSOR_TYPES = {
    0x01: "Temperature",
    0x02: "Voltage",
    0x03: "Current",
    0x04: "Fan",
    0x05: "Physical Security",
    0x06: "Platform Security Violation",
    0x07: "Processor",
    0x08: "Power Supply",
    0x09: "Power Unit",
    0x0A: "Cooling Device",
    0x0B: "Other Units-Based Sensor",
    0x0C: "Memory",
    0x0D: "Drive Slot",
}


@dataclass
class PDRHeaderCommon:
    """Common 10-byte PDR header per DSP0248."""
    record_handle: int
    version: int
    pdr_type: int
    record_change_number: int
    record_length: int

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple["PDRHeaderCommon", bytes]:
        """Parse PDR header and return (header, remaining_data)."""
        if len(data) < 10:
            raise ValueError(f"PDR data too short for header: {len(data)} bytes")
        
        record_handle = struct.unpack_from('<I', data, 0)[0]
        version = data[4]
        pdr_type = data[5]
        record_change_number = struct.unpack_from('<H', data, 6)[0]
        record_length = struct.unpack_from('<H', data, 8)[0]
        
        header = cls(
            record_handle=record_handle,
            version=version,
            pdr_type=pdr_type,
            record_change_number=record_change_number,
            record_length=record_length
        )
        
        return header, data[10:]


class PDRParser:
    """Enhanced PDR parser for IoT.2 and DSP0248 compliance."""

    @staticmethod
    def parse(pdr_data: bytes) -> Dict[str, Any]:
        """Parse a complete PDR (with 10-byte header) and return dictionary.
        
        Args:
            pdr_data: Complete PDR data including 10-byte header
            
        Returns:
            Dictionary with parsed PDR information
        """
        try:
            header, payload = PDRHeaderCommon.from_bytes(pdr_data)
        except Exception as e:
            return {
                "error": f"Failed to parse PDR header: {e}",
                "raw_size": len(pdr_data)
            }
        
        # Dispatch to type-specific parser
        parsed_content = PDRParser._parse_content(header.pdr_type, payload)
        
        return {
            "handle": f"0x{header.record_handle:08x}",
            "type": header.pdr_type,
            "type_name": PDR_TYPES.get(header.pdr_type, "Unknown"),
            "version": header.version,
            "change_number": header.record_change_number,
            "length": header.record_length,
            "content": parsed_content
        }

    @staticmethod
    def _parse_content(pdr_type: int, payload: bytes) -> Dict[str, Any]:
        """Parse PDR content based on type."""
        try:
            if pdr_type == 1:
                # Entity Association
                return PDRParser._parse_entity_association(payload)
            
            elif pdr_type == 8:
                # Numeric Sensor
                return PDRParser._parse_numeric_sensor(payload)
            
            elif pdr_type == 10:
                # State Sensor
                return PDRParser._parse_state_sensor(payload)
            
            else:
                # For unknown types, return hex dump of first 64 bytes
                return {
                    "type": PDR_TYPES.get(pdr_type, f"Unknown Type {pdr_type}"),
                    "raw_hex": payload[:64].hex() if payload else "(empty)",
                    "size": len(payload)
                }
        
        except Exception as e:
            return {
                "type": PDR_TYPES.get(pdr_type, f"Unknown Type {pdr_type}"),
                "parse_error": str(e),
                "raw_size": len(payload)
            }

    @staticmethod
    def _parse_entity_association(data: bytes) -> Dict[str, Any]:
        """Parse Entity Association PDR (Type 1)."""
        if len(data) < 4:
            raise ValueError(f"Entity Association PDR too short: {len(data)} bytes")
        
        container_entity_type = data[0]
        container_entity_instance = data[1]
        flags = data[2]
        num_child_entities = data[3]
        
        child_entities = []
        offset = 4
        
        for i in range(num_child_entities):
            if offset + 2 > len(data):
                break
            entity_type = data[offset]
            entity_instance = data[offset + 1]
            child_entities.append((entity_type, entity_instance))
            offset += 2
        
        return {
            "type": "Entity Association",
            "container": {
                "entity_type": container_entity_type,
                "entity_name": ENTITY_TYPES.get(container_entity_type, f"Type 0x{container_entity_type:02x}"),
                "instance": container_entity_instance
            },
            "is_container": bool(flags & 0x80),
            "children": [
                {
                    "entity_type": et,
                    "entity_name": ENTITY_TYPES.get(et, f"Type 0x{et:02x}"),
                    "instance": ei
                }
                for et, ei in child_entities
            ]
        }

    @staticmethod
    def _parse_numeric_sensor(data: bytes) -> Dict[str, Any]:
        """Parse Numeric Sensor PDR (Type 8)."""
        if len(data) < 15:
            raise ValueError(f"Numeric Sensor PDR too short: {len(data)} bytes")
        
        sensor_type = data[0]
        sensor_number = struct.unpack_from('<H', data, 1)[0]
        entity_type = data[3]
        entity_instance = data[4]
        sensor_direction = data[5] & 0x03
        sensor_init_scanning = bool(data[5] & 0x04)
        sensor_events_enabled = bool(data[5] & 0x08)
        threshold_access_support = (data[5] >> 4) & 0x03
        hysteresis_support = (data[6] >> 4) & 0x03
        sensor_auto_rearm_support = bool(data[6] & 0x08)
        sensor_ignore_if_unreportable = bool(data[6] & 0x01)
        flags = data[7]
        base_unit = data[8]
        modifier_unit = data[9]
        rate_unit = data[10]
        
        return {
            "type": "Numeric Sensor",
            "sensor_type": sensor_type,
            "sensor_type_name": SENSOR_TYPES.get(sensor_type, f"Type 0x{sensor_type:02x}"),
            "sensor_number": sensor_number,
            "entity": {
                "entity_type": entity_type,
                "entity_name": ENTITY_TYPES.get(entity_type, f"Type 0x{entity_type:02x}"),
                "instance": entity_instance
            },
            "direction": ["Unspecified", "Input", "Output", "Threshold"][sensor_direction],
            "scanning_enabled": sensor_init_scanning,
            "events_enabled": sensor_events_enabled,
            "threshold_support": threshold_access_support,
            "hysteresis_support": hysteresis_support,
            "auto_rearm": sensor_auto_rearm_support,
            "ignore_if_unreportable": sensor_ignore_if_unreportable,
            "base_unit": f"0x{base_unit:02x}",
            "modifier_unit": f"0x{modifier_unit:02x}",
            "rate_unit": f"0x{rate_unit:02x}"
        }

    @staticmethod
    def _parse_state_sensor(data: bytes) -> Dict[str, Any]:
        """Parse State Sensor PDR (Type 10)."""
        if len(data) < 10:
            raise ValueError(f"State Sensor PDR too short: {len(data)} bytes")
        
        sensor_type = data[0]
        sensor_number = struct.unpack_from('<H', data, 1)[0]
        entity_type = data[3]
        entity_instance = data[4]
        sensor_direction = data[5] & 0x03
        sensor_init_scanning = bool(data[5] & 0x04)
        sensor_events_enabled = bool(data[5] & 0x08)
        sensor_states_support_mask = struct.unpack_from('<H', data, 6)[0]
        
        return {
            "type": "State Sensor",
            "sensor_type": sensor_type,
            "sensor_type_name": SENSOR_TYPES.get(sensor_type, f"Type 0x{sensor_type:02x}"),
            "sensor_number": sensor_number,
            "entity": {
                "entity_type": entity_type,
                "entity_name": ENTITY_TYPES.get(entity_type, f"Type 0x{entity_type:02x}"),
                "instance": entity_instance
            },
            "direction": ["Unspecified", "Input", "Output", "Threshold"][sensor_direction],
            "scanning_enabled": sensor_init_scanning,
            "events_enabled": sensor_events_enabled,
            "states_mask": f"0x{sensor_states_support_mask:04x}"
        }

    @staticmethod
    def parse_batch(pdr_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse multiple PDRs from retriever output.
        
        Args:
            pdr_list: List of PDR dicts with 'data' key containing bytes
            
        Returns:
            List of parsed PDR dictionaries
        """
        parsed_pdrs = []
        
        for pdr_record in pdr_list:
            pdr_data = pdr_record.get("data", b"")
            
            if isinstance(pdr_data, str):
                try:
                    pdr_data = bytes.fromhex(pdr_data)
                except:
                    continue
            
            parsed = PDRParser.parse(pdr_data)
            parsed_pdrs.append(parsed)
        
        return parsed_pdrs
