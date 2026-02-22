# --- BEGIN: Simple file logger for debug visibility ---
import datetime
def export_debug_log(*args, **kwargs):
    try:
        with open('/tmp/export_pdrs_debug.log', 'a') as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(timestamp, *args, file=f, **kwargs)
    except Exception:
        pass
# --- END: Simple file logger ---
# --- BEGIN: Simple file logger for debug visibility ---
import datetime
def export_debug_log(*args, **kwargs):
    try:
        with open('/tmp/export_pdrs_debug.log', 'a') as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(timestamp, *args, file=f, **kwargs)
    except Exception:
        pass
# --- END: Simple file logger ---
#!/usr/bin/env python3
"""
Retrieve all PDRs from DUT and output as JSON with fully decoded fields.
Field names follow the PLDM Platform Monitoring and Control specification (DSP0248).
"""


import struct
import sys
import json
import builtins
import os
import base64
import zlib
sys.path.insert(0, '/home/doug/git/iot-foundry-pldm-agent/tools/pldm-mapping-wizard')

# --- BEGIN: Dedicated Export Debug Log ---
_export_log_path = '/tmp/export_pdrs_debug.log'
_export_log = open(_export_log_path, 'a')
_orig_print = builtins.print
def export_log_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    _orig_print(*args, **kwargs, file=_export_log)
    _export_log.flush()
builtins.print = export_log_print
# --- END: Dedicated Export Debug Log ---

from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder
from entity_types_dsp0249 import ENTITY_TYPES

# State Set definitions (DSP0249) for commonly used sets in this repo.
# Maps stateSetID -> {"name": str, "values": {stateValue: stateName}}
STATE_SET_DEFINITIONS = {
    64: {
        "name": "Smoke State",
        "values": {
            0: "Unknown",
            1: "Normal",
            2: "Smoke",
        },
    },
    65: {
        "name": "Humidity State",
        "values": {
            0: "Unknown",
            1: "Normal",
            2: "Humid",
        },
    },
    66: {
        "name": "Door State",
        "values": {
            0: "Unknown",
            1: "Open",
            2: "Closed",
        },
    },
    67: {
        "name": "Switch State",
        "values": {
            0: "Unknown",
            1: "Pressed/On",
            2: "Released/Off",
        },
    },
    96: {
        "name": "Lock State",
        "values": {
            0: "Unknown",
            1: "Locked",
            2: "Unlocked",
            3: "Locked Out",
        },
    },
}

# OEM state sets populated from OEM State Set PDRs at decode time.
OEM_STATE_SET_VALUES = {}
OEM_STATE_SET_NAMES = {}

def get_state_set_info(state_set_id):
    """Return (state_set_name, value_map) for standard or OEM state sets."""
    if state_set_id in OEM_STATE_SET_VALUES:
        name = OEM_STATE_SET_NAMES.get(state_set_id, f"OEM State Set (0x{state_set_id:04x})")
        return name, OEM_STATE_SET_VALUES[state_set_id]

    definition = STATE_SET_DEFINITIONS.get(state_set_id)
    if definition:
        return definition["name"], definition["values"]

    return f"Unknown State Set (0x{state_set_id:04x})", {}

RATE_UNIT_NAMES = {
    0x00: "None",
    0x01: "Per MicroSecond",
    0x02: "Per MilliSecond",
    0x03: "Per Second",
    0x04: "Per Minute",
    0x05: "Per Hour",
    0x06: "Per Day",
    0x07: "Per Week",
    0x08: "Per Month",
    0x09: "Per Year",
}

# Table 75 – sensorUnits enumeration (DSP0248 Section 27.4)
UNIT_NAMES = {
    0: "None",
    1: "Unspecified",
    2: "Degrees C",
    3: "Degrees F",
    4: "Kelvins",
    5: "Volts",
    6: "Amps",
    7: "Watts",
    8: "Joules",
    9: "Coulombs",
    10: "VA",
    11: "Nits",
    12: "Lumens",
    13: "Lux",
    14: "Candelas",
    15: "kPa",
    16: "PSI",
    17: "Newtons",
    18: "CFM",
    19: "RPM",
    20: "Hertz",
    21: "Seconds",
    22: "Minutes",
    23: "Hours",
    24: "Days",
    25: "Weeks",
    26: "Mils",
    27: "Inches",
    28: "Feet",
    29: "Cubic Inches",
    30: "Cubic Feet",
    31: "Meters",
    32: "Cubic Centimeters",
    33: "Cubic Meters",
    34: "Liters",
    35: "Fluid Ounces",
    36: "Radians",
    37: "Steradians",
    38: "Revolutions",
    39: "Cycles",
    40: "Gravities",
    41: "Ounces",
    42: "Pounds",
    43: "Foot-Pounds",
    44: "Ounce-Inches",
    45: "Gauss",
    46: "Gilberts",
    47: "Henries",
    48: "Farads",
    49: "Ohms",
    50: "Siemens",
    51: "Moles",
    52: "Becquerels",
    53: "PPM (parts/million)",
    54: "Decibels",
    55: "DbA",
    56: "DbC",
    57: "Grays",
    58: "Sieverts",
    59: "Color Temperature Degrees K",
    60: "Bits",
    61: "Bytes",
    62: "Words (data)",
    63: "DoubleWords",
    64: "QuadWords",
    65: "Percentage",
    66: "Pascals",
    67: "Counts",
    68: "Grams",
    69: "Newton-meters",
    70: "Hits",
    71: "Misses",
    72: "Retries",
    73: "Overruns/Overflows",
    74: "Underruns",
    75: "Collisions",
    76: "Packets",
    77: "Messages",
    78: "Characters",
    79: "Errors",
    80: "Corrected Errors",
    81: "Uncorrectable Errors",
    82: "Square Mils",
    83: "Square Inches",
    84: "Square Feet",
    85: "Square Centimeters",
    86: "Square Meters",
    255: "OEMUnit",
}

EFFECTER_DATA_SIZE_FORMATS = {
    0x00: ("uint8", 1, "<B"),
    0x01: ("sint8", 1, "<b"),
    0x02: ("uint16", 2, "<H"),
    0x03: ("sint16", 2, "<h"),
    0x04: ("uint32", 4, "<I"),
    0x05: ("sint32", 4, "<i"),
    0x06: ("uint64", 8, "<Q"),
    0x07: ("sint64", 8, "<q"),
}

RANGE_FIELD_FORMATS = {
    0x00: ("uint8", 1, "<B"),
    0x01: ("sint8", 1, "<b"),
    0x02: ("uint16", 2, "<H"),
    0x03: ("sint16", 2, "<h"),
    0x04: ("uint32", 4, "<I"),
    0x05: ("sint32", 4, "<i"),
    0x06: ("real32", 4, "<f"),
    0x07: ("uint64", 8, "<Q"),
    0x08: ("sint64", 8, "<q"),
}

def read_typed_value(data: bytes, offset: int, fmt_info: tuple):
    """Read a value from data using (name, size, struct_fmt)."""
    _, size, struct_fmt = fmt_info
    if offset + size > len(data):
        return None, offset
    value = struct.unpack_from(struct_fmt, data, offset)[0]
    return value, offset + size

# PDR Type to Name mapping (from Table 77 - DSP0248)
PDR_TYPE_NAMES = {
    1: "Terminus Locator PDR",
    2: "Numeric Sensor PDR",
    3: "Numeric Sensor Initialization PDR",
    4: "State Sensor PDR",
    5: "State Sensor Initialization PDR",
    6: "Sensor Auxiliary Names PDR",
    7: "OEM Unit PDR",
    8: "OEM State Set PDR",
    9: "Numeric Effecter PDR",
    10: "Numeric Effecter Initialization PDR",
    11: "State Effecter PDR",
    12: "State Effecter Initialization PDR",
    13: "Effecter Auxiliary Names PDR",
    14: "Effecter OEM Semantic PDR",
    15: "Entity Association PDR",
    16: "Entity Auxiliary Names PDR",
    17: "OEM Entity ID PDR",
    18: "Interrupt Association PDR",
    19: "PLDM Event Log PDR",
    20: "FRU Record Set PDR",
    21: "Compact Numeric Sensor PDR",
    22: "Redfish Resource PDR",
    23: "Redfish Entity Association PDR",
    24: "Redfish Action PDR",
}

def get_entity_type_name(entity_type):
    """Get human-readable name for entity type, handling P/L bit."""
    # Bit 15 is P/L flag (0=physical, 1=logical)
    is_logical = bool(entity_type & 0x8000)
    entity_id = entity_type & 0x7FFF
    
    # Look up entity name from DSP0249
    entity_name = ENTITY_TYPES.get(entity_id)
    
    if entity_name is None:
        # Check OEM ranges
        if 192 <= entity_id <= 16383:
            entity_name = f"Chassis-specific (0x{entity_id:04x})"
        elif 16384 <= entity_id <= 24575:
            entity_name = f"Board-set specific (0x{entity_id:04x})"
        elif 24576 <= entity_id <= 32767:
            entity_name = f"OEM System Integrator (0x{entity_id:04x})"
        else:
            entity_name = f"Reserved (0x{entity_id:04x})"
    
    pl_prefix = "Logical " if is_logical else ""
    return f"{pl_prefix}{entity_name}"

def get_pdr(port, handle):
    export_debug_log(f"Requesting PDR: handle=0x{handle:08x}")
    """Retrieve a single PDR by handle, handling multi-part transfers."""
    accumulated_pdr_data = bytearray()
    data_transfer_handle = 0
    transfer_op_flag = 0x01  # GetFirstPart
    next_handle = None
    record_change_number = 0
    
    # Loop to handle multi-part transfers
    max_iterations = 10  # Safety limit
    for iteration in range(max_iterations):
        cmd = PDLMCommandEncoder.encode_get_pdr(
            instance_id=0,
            record_handle=handle,
            data_transfer_handle=data_transfer_handle,
            transfer_operation_flag=transfer_op_flag,
            request_count=255,
            record_change_number=record_change_number,
        )
        
        frame = MCTPFramer.build_frame(pldm_msg=cmd, dest=0, src=16, msg_type=0x01)
        port.write(frame)
        response = port.read_until_idle()
        
        if not response:
            return None, "No response"
        
        frames = MCTPFramer.extract_frames(response)
        if not frames:
            resp_len = len(response)
            expected_len = None
            if resp_len > 3:
                byte_count = response[2]
                expected_len = 1 + 1 + 1 + byte_count + 2 + 1  # start_flag + protocol + byte_count + data + FCS + end_flag
            export_debug_log(f"[get_pdr] No frames extracted for handle=0x{handle:08x}, raw response: {response.hex()}, response_len={resp_len}, expected_frame_len={expected_len}")
            return None, "No frames extracted"

        frame_bytes = frames[0]
        frame_parsed = MCTPFramer.parse_frame(frame_bytes)
        if not frame_parsed:
            export_debug_log(f"[get_pdr] Failed to parse frame for handle=0x{handle:08x}, raw frame: {frame_bytes.hex()}")
            return None, "Failed to parse frame"
        
        pldm_data = frame_parsed.get('extra')
        if not pldm_data or len(pldm_data) < 12:
            return None, "Invalid PLDM payload"
        
        completion_code = pldm_data[0]
        if completion_code != 0:
            return None, f"Completion code: 0x{completion_code:02x}"
        
        # Parse GetPDR response fields
        next_handle = struct.unpack('<I', pldm_data[1:5])[0]
        data_transfer_handle = struct.unpack('<I', pldm_data[5:9])[0]
        transfer_flag = pldm_data[9]
        response_count = struct.unpack('<H', pldm_data[10:12])[0]
        export_debug_log(f"  [iter {iteration}] next_handle=0x{next_handle:08x} transfer_flag=0x{transfer_flag:02x} response_count={response_count}")
        # Accumulate PDR data
        accumulated_pdr_data.extend(pldm_data[12:12+response_count])

        # Capture recordChangeNumber from first part (PDR header bytes 6-7)
        if transfer_op_flag == 0x01 and len(accumulated_pdr_data) >= 8:
            record_change_number = struct.unpack('<H', accumulated_pdr_data[6:8])[0]
        
        # Check transfer flag per DSP0248 Table 69
        # 0x00 = Start, 0x01 = Middle, 0x04 = End, 0x05 = StartAndEnd
        if transfer_flag == 0x05:  # StartAndEnd (single transfer complete)
            export_debug_log(f"  [iter {iteration}] transfer_flag=0x05 (StartAndEnd): complete")
            break
        elif transfer_flag == 0x04:  # End (multi-part complete)
            export_debug_log(f"  [iter {iteration}] transfer_flag=0x04 (End): complete")
            break
        elif transfer_flag in [0x00, 0x01]:  # Start or Middle
            # More data coming - use the returned dataTransferHandle for next request
            if data_transfer_handle == 0:
                export_debug_log(f"  [iter {iteration}] data_transfer_handle=0: no more data, treat as complete")
                break
            transfer_op_flag = 0x00  # GetNextPart
            continue
        else:
            export_debug_log(f"  [iter {iteration}] ERROR: Unknown transfer flag: 0x{transfer_flag:02x}")
            return None, f"Unknown transfer flag: 0x{transfer_flag:02x}"
    else:
        export_debug_log(f"  ERROR: Max iterations reached in multi-part transfer for handle=0x{handle:08x}")
        return None, "Max iterations reached in multi-part transfer"
    
    export_debug_log(f"Received PDR: handle=0x{handle:08x}, next_handle=0x{next_handle:08x}, length={len(accumulated_pdr_data)}")
    return {
        'handle': handle,
        'next_handle': next_handle,
        'pdr_data': bytes(accumulated_pdr_data),
    }, None

def decode_pdr_header(data):
    """Decode PDR header (first 10 bytes per Table 76)."""
    if len(data) < 10:
        return None
    
    record_handle = struct.unpack('<I', data[0:4])[0]
    pdr_header_version = data[4]
    pdr_type = data[5]
    record_change_number = struct.unpack('<H', data[6:8])[0]
    record_length = struct.unpack('<H', data[8:10])[0]
    
    return {
        'recordHandle': record_handle,
        'PDRHeaderVersion': pdr_header_version,
        'PDRType': pdr_type,
        'recordChangeNumber': record_change_number,
        'recordLength': record_length,
    }

def decode_entity_association_pdr(data):
    """Decode Entity Association PDR (Type 15, Table 95)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 25:
        return decoded

    body = data[10:]
    # Offsets per spec
    container_id = struct.unpack('<H', body[0:2])[0]
    association_type = body[2]
    container_entity_type = struct.unpack('<H', body[3:5])[0]
    container_entity_instance = struct.unpack('<H', body[5:7])[0]
    container_entity_container_id = struct.unpack('<H', body[7:9])[0]
    contained_entity_count = body[9]

    decoded['PDRTypeName'] = 'Entity Association PDR'
    decoded['containerID'] = container_id
    decoded['associationType'] = association_type
    assoc_names = {
        0x00: "physicalToPhysicalContainment",
        0x01: "logicalContainment",
    }
    decoded['associationTypeName'] = assoc_names.get(association_type, f"Unknown (0x{association_type:02x})")
    decoded['containerEntityType'] = container_entity_type
    decoded['containerEntityTypeName'] = get_entity_type_name(container_entity_type)
    decoded['containerEntityInstanceNumber'] = container_entity_instance
    decoded['containerEntityContainerID'] = container_entity_container_id
    decoded['numberOfContainedEntities'] = contained_entity_count

    contained_entities = []
    offset = 10
    for i in range(contained_entity_count):
        if offset + 6 <= len(body):
            entity_type = struct.unpack('<H', body[offset:offset+2])[0]
            entity_instance = struct.unpack('<H', body[offset+2:offset+4])[0]
            entity_container_id = struct.unpack('<H', body[offset+4:offset+6])[0]
            contained_entities.append({
                'containedEntityType': entity_type,
                'containedEntityTypeName': get_entity_type_name(entity_type),
                'containedEntityInstanceNumber': entity_instance,
                'containedEntityContainerID': entity_container_id,
            })
            offset += 6

    if contained_entities:
        decoded['containedEntities'] = contained_entities

    return decoded

def decode_entity_auxiliary_names_pdr(data):
    """Decode Entity Auxiliary Names PDR (Type 16, Table 96)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 13:
        return decoded
    
    body = data[10:]
    entity_type = struct.unpack('<H', body[0:2])[0]
    entity_instance = struct.unpack('<H', body[2:4])[0]
    
    decoded['PDRTypeName'] = 'Entity Auxiliary Names PDR'
    decoded['entityType'] = entity_type
    decoded['entityTypeName'] = get_entity_type_name(entity_type)
    decoded['entityInstanceNumber'] = entity_instance
    
    if len(body) > 4:
        lang_tag = body[4:10].decode('ascii', errors='replace').rstrip('\x00')
        decoded['entityNameLanguageTag'] = lang_tag
        
        if len(body) > 10:
            # UTF-16BE encoded name
            name_bytes = body[10:]
            try:
                decoded['entityName'] = name_bytes.decode('utf-16-be', errors='replace').rstrip('\x00')
            except:
                decoded['entityName_hex'] = name_bytes.hex()
    
    return decoded

def decode_terminus_locator_pdr(data):
    """Decode Terminus Locator PDR (Type 1, Table 78)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 18:
        return decoded

    body = data[10:]
    if len(body) < 8:
        return decoded

    pldm_terminus_handle = struct.unpack('<H', body[0:2])[0]
    validity = body[2]
    tid = body[3]
    container_id = struct.unpack('<H', body[4:6])[0]
    terminus_locator_type = body[6]
    terminus_locator_value_size = body[7]
    terminus_locator_value = body[8:8 + terminus_locator_value_size]

    decoded['PDRTypeName'] = 'Terminus Locator PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle

    validity_names = {
        0x00: 'notValid',
        0x01: 'valid',
    }
    decoded['validity'] = validity
    decoded['validityName'] = validity_names.get(validity, f'Unknown(0x{validity:02x})')

    decoded['TID'] = tid
    decoded['containerID'] = container_id

    locator_type_names = {
        0x00: 'UID',
        0x01: 'MCTP_EID',
        0x02: 'SMBusRelative',
        0x03: 'systemSoftware',
        0x04: 'NC_SI',
    }
    decoded['terminusLocatorType'] = terminus_locator_type
    decoded['terminusLocatorTypeName'] = locator_type_names.get(
        terminus_locator_type,
        f'Unknown(0x{terminus_locator_type:02x})'
    )
    decoded['terminusLocatorValueSize'] = terminus_locator_value_size

    # Decode terminusLocatorValue by type
    if terminus_locator_type == 0x00:  # UID
        if len(terminus_locator_value) >= 17:
            terminus_instance = terminus_locator_value[0]
            device_uid = terminus_locator_value[1:17]
            decoded['terminusLocatorValue'] = {
                'terminusInstance': terminus_instance,
                'deviceUID': device_uid.hex(),
            }
        else:
            decoded['terminusLocatorValue_hex'] = terminus_locator_value.hex()
    elif terminus_locator_type == 0x01:  # MCTP_EID
        if len(terminus_locator_value) >= 1:
            decoded['terminusLocatorValue'] = {
                'EID': terminus_locator_value[0],
            }
        else:
            decoded['terminusLocatorValue_hex'] = terminus_locator_value.hex()
    elif terminus_locator_type == 0x02:  # SMBusRelative
        if len(terminus_locator_value) >= 18:
            uid = terminus_locator_value[0:16]
            bus_number = terminus_locator_value[16]
            slave_address = terminus_locator_value[17]
            decoded['terminusLocatorValue'] = {
                'UID': uid.hex(),
                'busNumber': bus_number,
                'slaveAddress': slave_address,
            }
        else:
            decoded['terminusLocatorValue_hex'] = terminus_locator_value.hex()
    elif terminus_locator_type == 0x03:  # systemSoftware
        if len(terminus_locator_value) >= 17:
            software_class = terminus_locator_value[0]
            uuid_bytes = terminus_locator_value[1:17]
            software_class_names = {
                0x00: 'unspecified',
                0x01: 'other',
                0x02: 'systemFirmware',
                0x03: 'OSloader',
                0x04: 'OS',
                0x05: 'CIMprovider',
                0x06: 'otherProvider',
                0x07: 'virtualMachineManager',
            }
            decoded['terminusLocatorValue'] = {
                'softwareClass': software_class,
                'softwareClassName': software_class_names.get(software_class, f'Unknown(0x{software_class:02x})'),
                'UUID': uuid_bytes.hex(),
            }
        else:
            decoded['terminusLocatorValue_hex'] = terminus_locator_value.hex()
    else:
        decoded['terminusLocatorValue_hex'] = terminus_locator_value.hex()

    return decoded

def decode_oem_entity_id_pdr(data):
    """Decode OEM Entity ID PDR (Type 17, Table 97)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 19:
        return decoded
    
    body = data[10:]
    pldm_terminus_handle = struct.unpack('<H', body[0:2])[0]
    oem_entity_id_handle = struct.unpack('<H', body[2:4])[0]
    vendor_iana = struct.unpack('<I', body[4:8])[0]
    vendor_entity_id = struct.unpack('<H', body[8:10])[0]
    string_count = body[10]
    
    decoded['PDRTypeName'] = 'OEM Entity ID PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle
    decoded['OEMEntityIDHandle'] = oem_entity_id_handle
    decoded['vendorIANA'] = vendor_iana
    decoded['vendorEntityID'] = vendor_entity_id
    decoded['stringCount'] = string_count
    
    # Parse entityIDLanguageTag and entityIDName pairs
    entity_names = []
    offset = 11
    
    for i in range(string_count):
        if offset >= len(body):
            break
        
        # Read null-terminated ASCII language tag
        lang_tag_end = body.find(b'\x00', offset)
        if lang_tag_end == -1:
            break
        
        lang_tag = body[offset:lang_tag_end].decode('ascii', errors='replace')
        offset = lang_tag_end + 1
        
        # Read null-terminated UTF-16BE entity name
        # UTF-16BE null terminator is 0x00 0x00
        name_end = offset
        while name_end + 1 < len(body):
            if body[name_end] == 0x00 and body[name_end + 1] == 0x00:
                break
            name_end += 2
        
        if name_end + 1 < len(body):
            try:
                entity_name = body[offset:name_end].decode('utf-16-be', errors='replace')
                entity_names.append({
                    'entityIDLanguageTag': lang_tag,
                    'entityIDName': entity_name
                })
            except Exception:
                entity_names.append({
                    'entityIDLanguageTag': lang_tag,
                    'entityIDName_hex': body[offset:name_end].hex()
                })
            offset = name_end + 2  # Skip past the two null bytes
        else:
            entity_names.append({'entityIDLanguageTag': lang_tag})
            break
    
    if entity_names:
        decoded['entityNames'] = entity_names
    
    return decoded

def decode_fru_record_set_pdr(data):
    """Decode FRU Record Set PDR (Type 20, Table 100)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 20:
        return decoded
    
    body = data[10:]
    pldm_terminus_handle = struct.unpack('<H', body[0:2])[0]
    fru_record_set_id = struct.unpack('<H', body[2:4])[0]
    entity_type = struct.unpack('<H', body[4:6])[0]
    entity_instance = struct.unpack('<H', body[6:8])[0]
    container_id = struct.unpack('<H', body[8:10])[0]
    
    decoded['PDRTypeName'] = 'FRU Record Set PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle
    decoded['FRURecordSetIdentifier'] = fru_record_set_id
    decoded['entityType'] = entity_type
    decoded['entityTypeName'] = get_entity_type_name(entity_type)
    decoded['entityInstanceNumber'] = entity_instance
    decoded['containerID'] = container_id
    
    return decoded

def decode_numeric_sensor_pdr(data):
    """Decode Numeric Sensor PDR (Type 2, Table 79)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 20:
        return decoded
    
    body = data[10:]
    offset = 0
    
    # Table 79 fields start directly after common header (no sensorType field!)
    pldm_terminus_handle = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    sensor_id = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    entity_type = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    entity_instance = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    container_id = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    
    # Sensor properties
    sensor_init = body[offset]
    offset += 1
    sensor_aux_names_pdr = bool(body[offset])
    offset += 1
    
    # Unit fields
    base_unit = body[offset]
    offset += 1
    unit_modifier = struct.unpack('<b', body[offset:offset+1])[0]
    offset += 1
    rate_unit = body[offset]
    offset += 1
    base_oem_unit_handle = body[offset]
    offset += 1
    aux_unit = body[offset]
    offset += 1
    aux_unit_modifier = struct.unpack('<b', body[offset:offset+1])[0]
    offset += 1
    aux_rate_unit = body[offset]
    offset += 1
    rel = body[offset]
    offset += 1
    aux_oem_unit_handle = body[offset]
    offset += 1
    
    # Linearity and data size
    is_linear = bool(body[offset])
    offset += 1
    sensor_data_size = body[offset]
    offset += 1
    
    # Sensor conversions (real32 values)
    resolution, offset = read_typed_value(body, offset, ("real32", 4, "<f"))
    offset_value, offset = read_typed_value(body, offset, ("real32", 4, "<f"))
    
    # Accuracy and tolerance
    accuracy = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    plus_tolerance = body[offset]
    offset += 1
    minus_tolerance = body[offset]
    offset += 1
    
    # Hysteresis (variable size per sensorDataSize)
    hysteresis_fmt = EFFECTER_DATA_SIZE_FORMATS.get(sensor_data_size)
    hysteresis, offset = read_typed_value(body, offset, hysteresis_fmt)
    
    # Threshold support bitfield
    supported_thresholds = body[offset]
    offset += 1
    
    # Threshold and hysteresis volatility
    threshold_volatility = body[offset]
    offset += 1
    
    # Timing intervals (real32)
    state_transition_interval, offset = read_typed_value(body, offset, ("real32", 4, "<f"))
    update_interval, offset = read_typed_value(body, offset, ("real32", 4, "<f"))
    
    # Readable ranges (variable size per sensorDataSize)
    max_readable, offset = read_typed_value(body, offset, hysteresis_fmt)
    min_readable, offset = read_typed_value(body, offset, hysteresis_fmt)
    
    # Range field format
    range_field_format = body[offset]
    offset += 1
    range_field_support = body[offset]
    offset += 1
    
    # Parse range fields based on rangeFieldFormat
    range_fmt = RANGE_FIELD_FORMATS.get(range_field_format)
    nominal_value = normal_max = normal_min = None
    warning_high = warning_low = critical_high = critical_low = fatal_high = fatal_low = None
    
    if range_fmt:
        # These fields are always present if rangeFieldFormat is valid
        nominal_value, offset = read_typed_value(body, offset, range_fmt)
        normal_max, offset = read_typed_value(body, offset, range_fmt)
        normal_min, offset = read_typed_value(body, offset, range_fmt)
        warning_high, offset = read_typed_value(body, offset, range_fmt)
        warning_low, offset = read_typed_value(body, offset, range_fmt)
        critical_high, offset = read_typed_value(body, offset, range_fmt)
        critical_low, offset = read_typed_value(body, offset, range_fmt)
        fatal_high, offset = read_typed_value(body, offset, range_fmt)
        fatal_low, offset = read_typed_value(body, offset, range_fmt)
    
    # Build output
    decoded['PDRTypeName'] = 'Numeric Sensor PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle
    decoded['sensorID'] = sensor_id
    decoded['entityType'] = entity_type
    decoded['entityTypeName'] = get_entity_type_name(entity_type)
    decoded['entityInstanceNumber'] = entity_instance
    decoded['containerID'] = container_id
    
    sensor_init_names = {
        0x00: 'noInit',
        0x01: 'useInitPDR',
        0x02: 'enableSensor',
        0x03: 'disableSensor',
    }
    decoded['sensorInit'] = sensor_init
    decoded['sensorInitName'] = sensor_init_names.get(sensor_init, f'Unknown(0x{sensor_init:02x})')
    decoded['sensorAuxiliaryNamesPDR'] = sensor_aux_names_pdr
    
    decoded['baseUnit'] = base_unit
    decoded['baseUnitName'] = UNIT_NAMES.get(base_unit, f"Unknown(0x{base_unit:02x})")
    decoded['unitModifier'] = unit_modifier
    decoded['rateUnit'] = rate_unit
    decoded['rateUnitName'] = RATE_UNIT_NAMES.get(rate_unit, f"Unknown(0x{rate_unit:02x})")
    decoded['baseOEMUnitHandle'] = base_oem_unit_handle
    
    decoded['auxUnit'] = aux_unit
    decoded['auxUnitName'] = UNIT_NAMES.get(aux_unit, f"Unknown(0x{aux_unit:02x})")
    decoded['auxUnitModifier'] = aux_unit_modifier
    decoded['auxRateUnit'] = aux_rate_unit
    decoded['auxRateUnitName'] = RATE_UNIT_NAMES.get(aux_rate_unit, f"Unknown(0x{aux_rate_unit:02x})")
    rel_names = {0x00: 'dividedBy', 0x01: 'multipliedBy'}
    decoded['auxUnitRelationship'] = rel_names.get(rel, f"Unknown(0x{rel:02x})")
    decoded['auxOEMUnitHandle'] = aux_oem_unit_handle
    
    decoded['isLinear'] = is_linear
    decoded['sensorDataSize'] = sensor_data_size
    if hysteresis_fmt:
        decoded['sensorDataSizeName'] = hysteresis_fmt[0]
    
    decoded['resolution'] = resolution
    decoded['offset'] = offset_value
    decoded['accuracy'] = accuracy
    decoded['plusTolerance'] = plus_tolerance
    decoded['minusTolerance'] = minus_tolerance
    decoded['hysteresis'] = hysteresis
    
    decoded['supportedThresholds'] = supported_thresholds
    decoded['supportedThresholdsFlags'] = {
        'upperThresholdWarning': bool(supported_thresholds & 0x01),
        'upperThresholdCritical': bool(supported_thresholds & 0x02),
        'upperThresholdFatal': bool(supported_thresholds & 0x04),
        'lowerThresholdWarning': bool(supported_thresholds & 0x08),
        'lowerThresholdCritical': bool(supported_thresholds & 0x10),
        'lowerThresholdFatal': bool(supported_thresholds & 0x20),
    }
    
    decoded['thresholdVolatility'] = threshold_volatility
    decoded['thresholdVolatilityFlags'] = {
        'initAgentRestart': bool(threshold_volatility & 0x01),
        'subsystemPowerUp': bool(threshold_volatility & 0x02),
        'hardReset': bool(threshold_volatility & 0x04),
        'warmReset': bool(threshold_volatility & 0x10),
        'terminusOnline': bool(threshold_volatility & 0x20),
    }
    
    decoded['stateTransitionInterval'] = state_transition_interval
    decoded['updateInterval'] = update_interval
    decoded['maxReadable'] = max_readable
    decoded['minReadable'] = min_readable
    
    decoded['rangeFieldFormat'] = range_field_format
    if range_fmt:
        decoded['rangeFieldFormatName'] = range_fmt[0]
    decoded['rangeFieldSupport'] = range_field_support
    decoded['rangeFieldSupportFlags'] = {
        'nominalValueSupported': bool(range_field_support & 0x01),
        'normalMaxSupported': bool(range_field_support & 0x02),
        'normalMinSupported': bool(range_field_support & 0x04),
        'criticalHighSupported': bool(range_field_support & 0x08),
        'criticalLowSupported': bool(range_field_support & 0x10),
        'fatalHighSupported': bool(range_field_support & 0x20),
        'fatalLowSupported': bool(range_field_support & 0x40),
    }
    
    decoded['nominalValue'] = nominal_value
    decoded['normalMax'] = normal_max
    decoded['normalMin'] = normal_min
    decoded['warningHigh'] = warning_high
    decoded['warningLow'] = warning_low
    decoded['criticalHigh'] = critical_high
    decoded['criticalLow'] = critical_low
    decoded['fatalHigh'] = fatal_high
    decoded['fatalLow'] = fatal_low
    
    return decoded

def decode_state_sensor_pdr(data):
    """Decode State Sensor PDR (Type 4, Table 81)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 25:
        return decoded
    
    body = data[10:]
    pldm_terminus_handle = struct.unpack('<H', body[0:2])[0]
    sensor_id = struct.unpack('<H', body[2:4])[0]
    entity_type = struct.unpack('<H', body[4:6])[0]
    entity_instance = struct.unpack('<H', body[6:8])[0]
    container_id = struct.unpack('<H', body[8:10])[0]
    sensor_init = body[10]
    sensor_aux_names_pdr = bool(body[11])
    composite_sensor_count = body[12]
    
    decoded['PDRTypeName'] = 'State Sensor PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle
    decoded['sensorID'] = sensor_id
    decoded['entityType'] = entity_type
    decoded['entityTypeName'] = get_entity_type_name(entity_type)
    decoded['entityInstanceNumber'] = entity_instance
    decoded['containerID'] = container_id
    
    sensor_init_names = {
        0x00: 'noInit',
        0x01: 'useInitPDR',
        0x02: 'enableSensor',
        0x03: 'disableSensor',
    }
    decoded['sensorInit'] = sensor_init
    decoded['sensorInitName'] = sensor_init_names.get(sensor_init, f'Unknown(0x{sensor_init:02x})')
    decoded['sensorAuxiliaryNamesPDR'] = sensor_aux_names_pdr
    decoded['compositeSensorCount'] = composite_sensor_count
    
    possible_states = []
    offset = 13
    for _ in range(composite_sensor_count):
        if offset + 3 > len(body):
            break
        state_set_id = struct.unpack('<H', body[offset:offset+2])[0]
        possible_states_size = body[offset+2]
        offset += 3
        if possible_states_size > 0 and offset + possible_states_size <= len(body):
            bitfield = body[offset:offset+possible_states_size]
            state_set_name, value_map = get_state_set_info(state_set_id)
            export_debug_log(f"decode_state_sensor_pdr: stateSetID={state_set_id}, value_map={value_map}, bitfield={list(bitfield)}")
            supported_state_values = []
            for byte_idx, byte_val in enumerate(bitfield):
                for bit_idx in range(8):
                    if byte_val & (1 << bit_idx):
                        # Per spec: bit0 => state 1, bit1 => state 2, etc.
                        state_value = byte_idx * 8 + bit_idx + 1
                        state_name = value_map.get(state_value, f'Unknown(0x{state_value:02x})')
                        export_debug_log(f"decode_state_sensor_pdr: stateSetID={state_set_id}, stateValue={state_value}, stateName={state_name}")
                        supported_state_values.append({
                            'stateValue': state_value,
                            'stateName': state_name
                        })
            possible_states.append({
                'stateSetID': state_set_id,
                'stateSetName': state_set_name,
                'possibleStatesSize': possible_states_size,
                'possibleStateValues': supported_state_values,
                'possibleStates_hex': bitfield.hex(),
            })
            offset += possible_states_size
        elif possible_states_size == 0:
            possible_states.append({
                'stateSetID': state_set_id,
                'possibleStatesSize': 0,
                'note': 'Sensor unavailable or disabled',
            })
    if possible_states:
        decoded['stateSetPossibleStates'] = possible_states
    
    return decoded

def decode_numeric_effecter_pdr(data):
    """Decode Numeric Effecter PDR (Type 9, Table 88)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 44:
        return decoded
    
    body = data[10:]
    offset = 0
    pldm_terminus_handle = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    effecter_id = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    entity_type = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    entity_instance = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    container_id = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    effecter_semantic_id = struct.unpack('<H', body[offset:offset+2])[0]
    offset += 2
    effecter_init = body[offset]
    offset += 1
    effecter_aux_names_pdr = bool(body[offset])
    offset += 1
    base_unit = body[offset]
    offset += 1
    unit_modifier = struct.unpack_from('<b', body, offset)[0]
    offset += 1
    rate_unit = body[offset]
    offset += 1
    base_oem_unit_handle = body[offset]
    offset += 1
    aux_unit = body[offset]
    offset += 1
    aux_unit_modifier = struct.unpack_from('<b', body, offset)[0]
    offset += 1
    aux_rate_unit = body[offset]
    offset += 1
    aux_oem_unit_handle = body[offset]
    offset += 1
    is_linear = bool(body[offset])
    offset += 1
    effecter_data_size = body[offset]
    offset += 1

    resolution = struct.unpack_from('<f', body, offset)[0]
    offset += 4
    offset_value = struct.unpack_from('<f', body, offset)[0]
    offset += 4
    accuracy = struct.unpack_from('<H', body, offset)[0]
    offset += 2
    plus_tolerance = body[offset]
    offset += 1
    minus_tolerance = body[offset]
    offset += 1
    state_transition_interval = struct.unpack_from('<f', body, offset)[0]
    offset += 4
    transition_interval = struct.unpack_from('<f', body, offset)[0]
    offset += 4

    data_fmt = EFFECTER_DATA_SIZE_FORMATS.get(effecter_data_size)
    if data_fmt:
        max_settable, offset = read_typed_value(body, offset, data_fmt)
        min_settable, offset = read_typed_value(body, offset, data_fmt)
    else:
        max_settable = None
        min_settable = None

    range_field_format = body[offset] if offset < len(body) else 0
    offset += 1
    range_field_support = body[offset] if offset < len(body) else 0
    offset += 1

    range_fmt = RANGE_FIELD_FORMATS.get(range_field_format)
    nominal_value = normal_max = normal_min = rated_max = rated_min = None
    if range_fmt:
        nominal_value, offset = read_typed_value(body, offset, range_fmt)
        normal_max, offset = read_typed_value(body, offset, range_fmt)
        normal_min, offset = read_typed_value(body, offset, range_fmt)
        rated_max, offset = read_typed_value(body, offset, range_fmt)
        rated_min, offset = read_typed_value(body, offset, range_fmt)

    decoded['PDRTypeName'] = 'Numeric Effecter PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle
    decoded['effecterID'] = effecter_id
    decoded['entityType'] = entity_type
    decoded['entityTypeName'] = get_entity_type_name(entity_type)
    decoded['entityInstanceNumber'] = entity_instance
    decoded['containerID'] = container_id
    decoded['effecterSemanticID'] = effecter_semantic_id

    effecter_init_names = {
        0x00: 'noInit',
        0x01: 'useInitPDR',
        0x02: 'enableEffecter',
        0x03: 'disableEffecter',
    }
    decoded['effecterInit'] = effecter_init
    decoded['effecterInitName'] = effecter_init_names.get(effecter_init, f'Unknown(0x{effecter_init:02x})')
    decoded['effecterAuxiliaryNamesPDR'] = effecter_aux_names_pdr

    decoded['baseUnit'] = base_unit
    decoded['baseUnitName'] = UNIT_NAMES.get(base_unit, f"Unknown(0x{base_unit:02x})")
    decoded['unitModifier'] = unit_modifier
    decoded['rateUnit'] = rate_unit
    decoded['rateUnitName'] = RATE_UNIT_NAMES.get(rate_unit, f"Unknown(0x{rate_unit:02x})")
    decoded['baseOEMUnitHandle'] = base_oem_unit_handle

    decoded['auxUnit'] = aux_unit
    decoded['auxUnitName'] = UNIT_NAMES.get(aux_unit, f"Unknown(0x{aux_unit:02x})")
    decoded['auxUnitModifier'] = aux_unit_modifier
    decoded['auxRateUnit'] = aux_rate_unit
    decoded['auxRateUnitName'] = RATE_UNIT_NAMES.get(aux_rate_unit, f"Unknown(0x{aux_rate_unit:02x})")
    decoded['auxOEMUnitHandle'] = aux_oem_unit_handle

    decoded['isLinear'] = is_linear
    decoded['effecterDataSize'] = effecter_data_size
    if data_fmt:
        decoded['effecterDataSizeName'] = data_fmt[0]

    decoded['resolution'] = resolution
    decoded['offset'] = offset_value
    decoded['accuracy'] = accuracy
    decoded['plusTolerance'] = plus_tolerance
    decoded['minusTolerance'] = minus_tolerance
    decoded['stateTransitionInterval'] = state_transition_interval
    decoded['transitionInterval'] = transition_interval
    decoded['maxSettable'] = max_settable
    decoded['minSettable'] = min_settable

    decoded['rangeFieldFormat'] = range_field_format
    if range_fmt:
        decoded['rangeFieldFormatName'] = range_fmt[0]
    decoded['rangeFieldSupport'] = range_field_support
    decoded['rangeFieldSupportFlags'] = {
        'nominalValueSupported': bool(range_field_support & 0x01),
        'normalMaxSupported': bool(range_field_support & 0x02),
        'normalMinSupported': bool(range_field_support & 0x04),
        'ratedMaxSupported': bool(range_field_support & 0x08),
        'ratedMinSupported': bool(range_field_support & 0x10),
    }

    decoded['nominalValue'] = nominal_value
    decoded['normalMax'] = normal_max
    decoded['normalMin'] = normal_min
    decoded['ratedMax'] = rated_max
    decoded['ratedMin'] = rated_min

    return decoded

def decode_state_effecter_pdr(data):
    """Decode State Effecter PDR (Type 11, Table 90)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 27:
        return decoded
    
    body = data[10:]
    pldm_terminus_handle = struct.unpack('<H', body[0:2])[0]
    effecter_id = struct.unpack('<H', body[2:4])[0]
    entity_type = struct.unpack('<H', body[4:6])[0]
    entity_instance = struct.unpack('<H', body[6:8])[0]
    container_id = struct.unpack('<H', body[8:10])[0]
    effecter_semantic_id = struct.unpack('<H', body[10:12])[0]
    effecter_init = body[12]
    effecter_description_pdr = bool(body[13])
    composite_effecter_count = body[14]
    
    decoded['PDRTypeName'] = 'State Effecter PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle
    decoded['effecterID'] = effecter_id
    decoded['entityType'] = entity_type
    decoded['entityTypeName'] = get_entity_type_name(entity_type)
    decoded['entityInstanceNumber'] = entity_instance
    decoded['containerID'] = container_id
    decoded['effecterSemanticID'] = effecter_semantic_id
    
    effecter_init_names = {
        0x00: 'noInit',
        0x01: 'useInitPDR',
        0x02: 'enableEffecter',
        0x03: 'disableEffecter',
    }
    decoded['effecterInit'] = effecter_init
    decoded['effecterInitName'] = effecter_init_names.get(effecter_init, f'Unknown(0x{effecter_init:02x})')
    decoded['effecterDescriptionPDR'] = effecter_description_pdr
    decoded['compositeEffecterCount'] = composite_effecter_count
    
    # Parse possible states for each effecter
    possible_states = []
    offset = 15
    
    for i in range(composite_effecter_count):
        if offset + 3 > len(body):
            break
        
        state_set_id = struct.unpack('<H', body[offset:offset+2])[0]
        possible_states_size = body[offset+2]
        offset += 3
        
        if possible_states_size > 0 and offset + possible_states_size <= len(body):
            possible_states_bitfield = body[offset:offset+possible_states_size]
            
            # Decode which states are possible
            supported_state_values = []
            state_set_name, value_map = get_state_set_info(state_set_id)
            for byte_idx, byte_val in enumerate(possible_states_bitfield):
                for bit_idx in range(8):
                    if byte_val & (1 << bit_idx):
                        # Per spec: bit0 => state 1, bit1 => state 2, etc.
                        state_value = byte_idx * 8 + bit_idx + 1
                        supported_state_values.append({
                            'stateValue': state_value,
                            'stateName': value_map.get(state_value, f'Unknown(0x{state_value:02x})')
                        })
            
            possible_states.append({
                'stateSetID': state_set_id,
                'stateSetName': state_set_name,
                'possibleStatesSize': possible_states_size,
                'possibleStateValues': supported_state_values,
                'possibleStates_hex': possible_states_bitfield.hex(),
            })
            offset += possible_states_size
        elif possible_states_size == 0:
            # Effecter unavailable/disabled
            possible_states.append({
                'stateSetID': state_set_id,
                'possibleStatesSize': 0,
                'note': 'Effecter unavailable or disabled',
            })
    
    if possible_states:
        decoded['stateSetPossibleStates'] = possible_states
    
    return decoded

def decode_compact_numeric_sensor_pdr(data):
    """Decode Compact Numeric Sensor PDR (Type 21, Table 103)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 20:
        return decoded
    
    body = data[10:]
    sensor_type = body[0]
    sensor_number = struct.unpack('<H', body[1:3])[0]
    entity_type = struct.unpack('<H', body[3:5])[0]
    entity_instance = struct.unpack('<H', body[5:7])[0]
    
    decoded['PDRTypeName'] = 'Compact Numeric Sensor PDR'
    decoded['sensorType'] = sensor_type
    decoded['sensorNumber'] = sensor_number
    decoded['entityType'] = entity_type
    decoded['entityTypeName'] = get_entity_type_name(entity_type)
    decoded['entityInstanceNumber'] = entity_instance
    
    if len(body) > 7:
        decoded['remainingFields_hex'] = body[7:].hex()
    
    return decoded

def decode_oem_state_set_pdr(data):
    """Decode OEM State Set PDR (Type 8, Table 86)."""
    decoded = decode_pdr_header(data)
    if not decoded or len(data) < 22:
        return decoded
    
    body = data[10:]
    pldm_terminus_handle = struct.unpack('<H', body[0:2])[0]
    oem_state_set_id_handle = struct.unpack('<H', body[2:4])[0]
    vendor_iana = struct.unpack('<I', body[4:8])[0]
    oem_state_set_id = struct.unpack('<H', body[8:10])[0]
    unspecified_value_hint = body[10]
    state_count = body[11]
    
    decoded['PDRTypeName'] = 'OEM State Set PDR'
    decoded['PLDMTerminusHandle'] = pldm_terminus_handle
    decoded['OEMStateSetIDHandle'] = oem_state_set_id_handle
    decoded['vendorIANA'] = vendor_iana
    decoded['OEMStateSetID'] = oem_state_set_id
    
    hint_names = {0: "treatAsUnspecified", 1: "treatAsError"}
    decoded['unspecifiedValueHint'] = hint_names.get(unspecified_value_hint, f"Unknown(0x{unspecified_value_hint:02x})")
    decoded['stateCount'] = state_count
    
    # Parse OEM State Value Records (Table 87)
    oem_state_records = []
    offset = 12
    for i in range(state_count):
        if offset + 3 > len(body):
            break
        
        min_state = body[offset]
        max_state = body[offset + 1]
        string_count = body[offset + 2]
        offset += 3
        
        state_record = {
            'minStateValue': min_state,
            'maxStateValue': max_state,
            'stringCount': string_count,
            'stateNames': []
        }
        
        # Parse language tags and state names for this value record
        for s in range(string_count):
            if offset >= len(body):
                break
            
            # Read null-terminated ASCII language tag
            lang_end = offset
            while lang_end < len(body) and body[lang_end] != 0:
                lang_end += 1
            
            if lang_end >= len(body):
                break
            
            lang_tag = body[offset:lang_end].decode('ascii', errors='replace')
            offset = lang_end + 1  # Skip past null terminator
            
            # Read null-terminated UTF-16BE state name
            # Look for 0x00 0x00 (UTF-16BE null terminator)
            name_end = offset
            while name_end + 1 < len(body):
                if body[name_end] == 0 and body[name_end + 1] == 0:
                    break
                name_end += 2
            
            if name_end + 1 < len(body):
                try:
                    state_name = body[offset:name_end].decode('utf-16-be', errors='replace')
                    state_record['stateNames'].append({
                        'languageTag': lang_tag,
                        'stateName': state_name
                    })
                except Exception as e:
                    state_record['stateNames'].append({
                        'languageTag': lang_tag,
                        'stateName_hex': body[offset:name_end].hex()
                    })
                offset = name_end + 2  # Skip past the two null bytes
            else:
                # No state name found, just add language tag
                state_record['stateNames'].append({'languageTag': lang_tag})
                break
        
        oem_state_records.append(state_record)
    
    if oem_state_records:
        decoded['OEMStateValueRecords'] = oem_state_records

        # Build OEM state set value map for later use by sensor/effecter decoding
        state_value_map = {}
        for record in oem_state_records:
            min_val = record.get('minStateValue')
            max_val = record.get('maxStateValue')
            names = record.get('stateNames', [])
            # If there are as many names as values, map each value to its name
            if len(names) == (max_val - min_val + 1):
                for idx, v in enumerate(range(min_val, max_val + 1)):
                    name = names[idx].get('stateName')
                    if name is not None:
                        state_value_map[v] = name
            else:
                # Otherwise, map all values in the range to the first name (legacy behavior)
                name = names[0].get('stateName') if names else None
                if name is not None:
                    for v in range(min_val, max_val + 1):
                        state_value_map[v] = name

        if state_value_map:
            OEM_STATE_SET_VALUES[oem_state_set_id_handle] = state_value_map
            OEM_STATE_SET_NAMES[oem_state_set_id_handle] = f"OEM State Set {oem_state_set_id}"
            # Log the mapping for debug visibility
            export_debug_log(f"OEM_STATE_SET_VALUES[{oem_state_set_id_handle}] = {state_value_map}")
    
    return decoded

def decode_pdr(pdr_data):
    export_debug_log(f"decode_pdr called, type={pdr_data[5] if len(pdr_data) > 5 else 'N/A'}, len={len(pdr_data)}")
    """Decode a PDR based on its type."""
    if len(pdr_data) < 10:
        return {'error': 'PDR too short'}
    
    pdr_type = pdr_data[5]
    
    decoders = {
        1: decode_terminus_locator_pdr,
        15: decode_entity_association_pdr,
        16: decode_entity_auxiliary_names_pdr,
        17: decode_oem_entity_id_pdr,
        20: decode_fru_record_set_pdr,
        2: decode_numeric_sensor_pdr,
        4: decode_state_sensor_pdr,
        8: decode_oem_state_set_pdr,
        9: decode_numeric_effecter_pdr,
        11: decode_state_effecter_pdr,
        21: decode_compact_numeric_sensor_pdr,
    }
    
    decoder = decoders.get(pdr_type, decode_pdr_header)
    decoded = decoder(pdr_data)
    
    if decoded and 'PDRTypeName' not in decoded:
        decoded['PDRTypeName'] = PDR_TYPE_NAMES.get(pdr_type, f'PDR Type 0x{pdr_type:02x}')
    
    return decoded



def get_fru_record_table_metadata(port):
    """Retrieve FRU Record Table metadata."""
    cmd = PDLMCommandEncoder.encode_get_fru_record_table_metadata(instance_id=0)

    frame = MCTPFramer.build_frame(pldm_msg=cmd, dest=0, src=16, msg_type=0x01)
    port.write(frame)

    sys.stderr.write(f"get_fru_record_table_metadata: sent command ({len(frame)} bytes): {frame.hex()}\n")
    response = port.read_until_idle()
    sys.stderr.write(f"get_fru_record_table_metadata: raw response ({len(response) if response else 0} bytes): {response.hex() if response else 'None'}\n") 

    if not response:
        return None, "No response"
    
    frames = MCTPFramer.extract_frames(response)
    if not frames:
        return None, "No frames extracted"
    
    frame_parsed = MCTPFramer.parse_frame(frames[0])
    if not frame_parsed:
        return None, "Failed to parse frame"
    # Verify frame integrity (FCS) and that this is a PLDM FRU response
    if not frame_parsed.get('fcs_ok'):
        return None, "FCS mismatch"
    # Ensure message is PLDM and FRU type (type == 0x04)
    if frame_parsed.get('msg_type') != 1 or frame_parsed.get('type') != 0x04:
        return None, "Unexpected message type"
    
    pldm_data = frame_parsed.get('extra')
    if not pldm_data or len(pldm_data) < 1:
        return None, "Invalid PLDM payload"
    
    completion_code = pldm_data[0]
    if completion_code != 0:
        return None, f"Completion code: 0x{completion_code:02x}"
    
    if len(pldm_data) < 19:
        return None, f"Response too short: {len(pldm_data)} bytes"
    
    # Parse metadata response
    metadata = {
        'fru_major_version': pldm_data[1],
        'fru_minor_version': pldm_data[2],
        'fru_table_max_size': struct.unpack('<I', pldm_data[3:7])[0],
        'fru_table_length': struct.unpack('<I', pldm_data[7:11])[0],
        'num_record_sets': struct.unpack('<H', pldm_data[11:13])[0],
        'num_records': struct.unpack('<H', pldm_data[13:15])[0],
        'crc32_checksum': struct.unpack('<I', pldm_data[15:19])[0],
    }
    
    return metadata, None


def get_fru_record_table(port, transfer_context=0, expected_length: int | None = None):
    """Retrieve FRU Record Table data, handling multi-part transfers."""
    accumulated_fru_data = bytearray()
    data_transfer_handle = 0
    transfer_operation = 0x00  # XFER_FIRST_PART for initial request
    
    # Loop to handle multi-part transfers
    max_iterations = 50  # Safety limit
    for iteration in range(max_iterations):
        cmd = PDLMCommandEncoder.encode_get_fru_record_table(
            instance_id=0,
            pldm_type=0x04,
            transfer_operation=transfer_operation,
            transfer_context=transfer_context,
            data_transfer_handle=data_transfer_handle,
            requested_section_offset=0x00000000,
            requested_section_length=0x00000000,
        )
        
        frame = MCTPFramer.build_frame(pldm_msg=cmd, dest=0, src=16, msg_type=0x01)
        port.write(frame)
        response = port.read_until_idle()

        if not response:
            return None, "No response"

        # Debug dump of the raw response
        try:
            export_debug_log(f"[get_fru_record_table] RAW response ({len(response)} bytes): {response.hex()}")
        except Exception:
            pass

        frames = MCTPFramer.extract_frames(response)
        if not frames:
            export_debug_log(f"[get_fru_record_table] No frames extracted for FRU response; raw_len={len(response)}")
            return None, "No frames extracted"

        # Log extracted frames
        try:
            for i, fr in enumerate(frames):
                export_debug_log(f"[get_fru_record_table] Extracted frame[{i}] ({len(fr)} bytes): {fr.hex()}")
        except Exception:
            pass

        frame_parsed = MCTPFramer.parse_frame(frames[0])
        if not frame_parsed:
            export_debug_log(f"[get_fru_record_table] Failed to parse first frame, first_frame_hex={frames[0].hex() if frames and isinstance(frames[0], (bytes, bytearray)) else 'NA'}")
            return None, "Failed to parse frame"
        # Verify FCS and PLDM type before accepting
        if not frame_parsed.get('fcs_ok'):
            export_debug_log(f"[get_fru_record_table] FCS mismatch on parsed frame")
            return None, "FCS mismatch"
        if frame_parsed.get('msg_type') != 1 or frame_parsed.get('type') != 0x04:
            export_debug_log(f"[get_fru_record_table] Unexpected message type: msg_type={frame_parsed.get('msg_type')} type={frame_parsed.get('type')}")
            return None, "Unexpected message type"
        pldm_data = frame_parsed.get('extra')
        if not pldm_data or len(pldm_data) < 1:
            export_debug_log(f"[get_fru_record_table] Invalid PLDM payload: extra_present={bool(pldm_data)} len={(len(pldm_data) if isinstance(pldm_data, (bytes, bytearray)) else 'NA')}")
            return None, f"Invalid PLDM payload"
        try:
            if isinstance(pldm_data, (bytes, bytearray)):
                export_debug_log(f"[get_fru_record_table] Parsed frame extra ({len(pldm_data)} bytes): {pldm_data.hex()}")
        except Exception:
            pass
        
        completion_code = pldm_data[0]
        if completion_code != 0:
            return None, f"Completion code: 0x{completion_code:02x}"
        
        # Response format expected per user:
        # [0] CompletionCode
        # [1-4] NextDataTransferHandle (uint32, LE)
        # [5] TransferFlag (response): PLDM_START=0x01, PLDM_MIDDLE=0x02, PLDM_END=0x04,
        #                              PLDM_START_AND_END=0x05, PLDM_ACKNOWLEDGE_COMPLETION=0x08
        # [6+] FRU Record Table data
        if len(pldm_data) < 6:
            return None, f"Response too short: {len(pldm_data)} bytes"

        # Parse GetFRURecordTable response fields
        next_data_transfer_handle = struct.unpack('<I', pldm_data[1:5])[0]
        transfer_flag = pldm_data[5]

        # FRU data starts at offset 6
        fru_data = pldm_data[6:]

        # Some DUTs append a per-packet 4-byte CRC to each FRU fragment.
        # Detect and strip a trailing 4-byte little-endian CRC if it matches
        # the CRC32 of the preceding bytes in this fragment.
        try:
            if len(fru_data) >= 4:
                possible_crc = struct.unpack_from('<I', fru_data, len(fru_data) - 4)[0]
                payload_part = fru_data[:-4]
                calc = zlib.crc32(payload_part) & 0xFFFFFFFF
                if calc == possible_crc:
                    export_debug_log(f"[get_fru_record_table] Stripping per-fragment CRC (4 bytes) from fragment iteration={iteration}, fragment_len={len(fru_data)}")
                    fru_data = payload_part
        except Exception:
            pass

        # Accumulate FRU data (with any per-fragment CRC removed)
        accumulated_fru_data.extend(fru_data)

        # Response flags: treat END/START_AND_END/ACKNOWLEDGE_COMPLETION as completion
        if transfer_flag in (0x05, 0x04, 0x08):
            break
        elif transfer_flag in (0x00, 0x01, 0x02):
            # More data coming - treat 0x00 as a valid START/continuation on some DUTs
            # Use returned data_transfer_handle for next request
            if next_data_transfer_handle == 0:
                break
            data_transfer_handle = next_data_transfer_handle
            transfer_operation = 0x01  # XFER_NEXT_PART for continuation
            continue
        else:
            return None, f"Unknown transfer flag: 0x{transfer_flag:02x}"
    else:
        return None, "Max iterations reached in multi-part transfer"
    
    # Final debug dump of accumulated FRU data (hex prefix and base64 prefix)
    try:
        export_debug_log(f"[get_fru_record_table] Accumulated FRU bytes: len={len(accumulated_fru_data)} hex_prefix={accumulated_fru_data[:64].hex()}")
        try:
            export_debug_log(f"[get_fru_record_table] Accumulated FRU base64 (prefix): {base64.b64encode(accumulated_fru_data)[:128].decode('ascii', errors='replace')}")
        except Exception:
            pass
    except Exception:
        pass

    # If caller provided an expected length (from metadata), trim to it
    try:
        if expected_length is not None:
            exp = int(expected_length)
            if len(accumulated_fru_data) > exp:
                export_debug_log(f"[get_fru_record_table] Trimming accumulated FRU data from {len(accumulated_fru_data)} to expected_length={exp} (remove padding/CRC)")
                accumulated_fru_data = accumulated_fru_data[:exp]
    except Exception:
        pass

    return bytes(accumulated_fru_data), None


def parse_fru_record_table(data: bytes, total_length: int | None = None):
    """Parse FRU Record Table per DSP0257 Section 10.5.

    Returns a list of records. Each record is a dict with keys:
      - fru_record_set_id
      - fru_record_type
      - number_of_fields
      - encoding (numeric)
      - fields: list of {type, length, raw_hex, value}
    """
    FIELD_TYPE_NAMES = {
        1: 'Chassis Type',
        2: 'Model',
        3: 'Part Number',
        4: 'Serial Number',
        5: 'Manufacturer',
        6: 'Manufacture Date',
        7: 'Vendor',
        8: 'Name',
        9: 'SKU',
        10: 'Version',
        11: 'Asset Tag',
        12: 'Description',
        13: 'Engineering Change Level',
        14: 'Other Information',
        15: 'Vendor IANA',
        16: 'Spare Part Number',
    }

    # Friendly short names for common FRU field types (for JSON keys)
    FRIENDLY_FIELD_NAMES = {
        1: 'chassisType',
        2: 'model',
        3: 'partNumber',
        4: 'serialNumber',
        5: 'manufacturer',
        6: 'manufactureDate',
        7: 'vendor',
        8: 'name',
        9: 'sku',
        10: 'version',
        11: 'assetTag',
        12: 'description',
        13: 'engineeringChangeLevel',
        14: 'otherInfo',
        15: 'vendorIANA',
        16: 'sparePartNumber',
    }

    records = []
    offset = 0
    # Restrict parsing to total_length if provided (to avoid parsing CRC/padding)
    max_len = len(data) if total_length is None else min(len(data), int(total_length))
    while offset + 5 <= max_len:
        # Minimum header: 2 bytes RecordSetID, 1 byte RecordType,
        # 1 byte NumFields, 1 byte Encoding
        fru_record_set_id = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        fru_record_type = data[offset]
        offset += 1
        num_fields = data[offset]
        offset += 1
        encoding = data[offset]
        offset += 1

        rec = {
            'fru_record_set_id': fru_record_set_id,
            'fru_record_type': fru_record_type,
            'number_of_fields': num_fields,
            'encoding': encoding,
            'fields': []
        }

        for i in range(num_fields):
            if offset + 2 > max_len:
                break
            field_type = data[offset]
            offset += 1
            field_len = data[offset]
            offset += 1
            if offset + field_len > max_len:
                # truncated value - clamp to max_len
                value_bytes = data[offset:max_len]
                offset = max_len
            else:
                value_bytes = data[offset:offset+field_len]
                offset += field_len

            field = {
                'field_type': field_type,
                'field_length': field_len,
                'field_type_name': FIELD_TYPE_NAMES.get(field_type, f'Unknown(0x{field_type:02x})'),
                'raw_hex': value_bytes.hex(),
            }

            # Interpret per DSP0257 Table 4/5
            # OEM records (type 254) have special rule: field type 1 => Vendor IANA (uint32)
            if rec.get('fru_record_type') == 254:
                if field_type == 1 and len(value_bytes) == 4:
                    field['format'] = 'uint32'
                    field['value'] = struct.unpack_from('<I', value_bytes, 0)[0]
                else:
                    # OEM-specific types: leave as raw bytes unless the code knows otherwise
                    field['format'] = 'bytes'
                    field['value'] = list(value_bytes)
            else:
                # General FRU record types
                if field_type == 15 and len(value_bytes) == 4:
                    field['format'] = 'uint32'
                    field['value'] = struct.unpack_from('<I', value_bytes, 0)[0]
                elif field_type == 6 and len(value_bytes) == 13:
                    # timestamp104: expose raw bytes as array (spec expects timestamp104 type)
                    field['format'] = 'timestamp104'
                    field['value'] = list(value_bytes)
                    try:
                        year_le = struct.unpack_from('<H', value_bytes, 0)[0]
                        year_be = struct.unpack_from('>H', value_bytes, 0)[0]
                        month = value_bytes[2]
                        day = value_bytes[3]
                        hour = value_bytes[4]
                        minute = value_bytes[5]
                        second = value_bytes[6]
                        remainder = value_bytes[7:]
                        field['value_components'] = {
                            'year_le': year_le,
                            'year_be': year_be,
                            'month': month,
                            'day': day,
                            'hour': hour,
                            'minute': minute,
                            'second': second,
                            'remainder_hex': remainder.hex(),
                        }
                    except Exception:
                        pass
                elif field_type in (1,2,3,4,5,7,8,9,10,11,12,13,14,16):
                    # String-like types; use DSP0257 encoding tokens for format
                    ENCODING_TOKENS = {
                        0: 'Unspecified',
                        1: 'strASCII',
                        2: 'strUTF-8',
                        3: 'strUTF-16',
                        4: 'strUTF-16LE',
                        5: 'strUTF-16BE',
                    }

                    token = ENCODING_TOKENS.get(encoding)
                    # Reserved encodings (6-255) -> treat as reserved octet data
                    if token is None:
                        field['format'] = 'reserved'
                        field['value'] = list(value_bytes)
                    elif token == 'Unspecified':
                        field['format'] = 'Unspecified'
                        field['value'] = list(value_bytes)
                    else:
                        # Known text encodings: decode accordingly and set format to spec token
                        field['format'] = token
                        try:
                            if token == 'strASCII':
                                field['value'] = value_bytes.decode('ascii', errors='replace')
                            elif token == 'strUTF-8':
                                field['value'] = value_bytes.decode('utf-8', errors='replace')
                            elif token == 'strUTF-16':
                                field['value'] = value_bytes.decode('utf-16', errors='replace')
                            elif token == 'strUTF-16LE':
                                field['value'] = value_bytes.decode('utf-16-le', errors='replace')
                            elif token == 'strUTF-16BE':
                                field['value'] = value_bytes.decode('utf-16-be', errors='replace')
                            else:
                                field['value'] = list(value_bytes)
                        except Exception:
                            field['format'] = 'reserved'
                            field['value'] = list(value_bytes)
                else:
                    # Reserved/unknown field types -> raw bytes
                    field['format'] = 'bytes'
                    field['value'] = list(value_bytes)
            

            # Attach a friendly name (if available) for easier JSON access
            friendly = FRIENDLY_FIELD_NAMES.get(field_type)
            if friendly:
                field['friendly_name'] = friendly

            rec['fields'].append(field)

        # No fields_map: leave raw fields list intact (avoid redundancy)

        records.append(rec)

    # Return parsed records and number of bytes consumed from the input
    return records, offset


def convert_parsed_to_spec(parsed_records, pdr_records):
    """Convert internal parsed FRU records to DSP0257-like JSON structure.

    Each output record will have:
      - vendorIANA: (if available from PDRs)
      - required: true
      - description: null
      - fields: list of {type, required, description, format, length, value}
    """
    spec_records = []

    for rec in parsed_records:
        spec_rec = {
            'required': True,
            'description': None,
            'fields': []
        }

        for f in rec.get('fields', []):
            ftype = f.get('field_type')
            raw_hex = f.get('raw_hex', '')
            fmt = f.get('format')

            # Apply Table 4 / Table 5 exceptions: only
            # - Manufacture Date (field type 6) => timestamp104
            # - Vendor IANA (field type 15) => uint32
            # - OEM FRU (record type 254) field type 1 => uint32
            # Otherwise, fields are strings encoded by the record encoding token; unspecified/reserved -> octetArray
            rec_type = rec.get('fru_record_type')

            # Determine format
            # Enforce OEM FRU (record type 254) rule per Table 5:
            #   - field type 1 => Vendor IANA (uint32)
            #   - other field types are OEM-defined -> represent as octetArray
            if rec_type == 254:
                if ftype == 1:
                    out_fmt = 'uint32'
                else:
                    out_fmt = 'octetArray'
            elif ftype == 6:
                out_fmt = 'timestamp104'
            elif ftype == 15:
                out_fmt = 'uint32'
            elif fmt in ('strASCII', 'strUTF-8', 'strUTF-16', 'strUTF-16LE', 'strUTF-16BE'):
                out_fmt = fmt
            elif fmt in ('Unspecified', 'reserved', 'bytes') or fmt is None:
                out_fmt = 'octetArray'
            else:
                out_fmt = fmt

            # Compute length (use field_length if present)
            length = f.get('field_length') if f.get('field_length') is not None else None

            # Compute value
            if out_fmt == 'uint32':
                # Parse little-endian uint32 from raw_hex when possible
                try:
                    vb = bytes.fromhex(raw_hex) if raw_hex else b''
                    if len(vb) >= 4:
                        value = struct.unpack_from('<I', vb, 0)[0]
                    else:
                        # fallback to stored value
                        value = f.get('value')
                except Exception:
                    value = f.get('value')
            elif out_fmt == 'timestamp104' or out_fmt == 'octetArray':
                try:
                    vb = bytes.fromhex(raw_hex) if raw_hex else b''
                    # For timestamp104, prefer a human-readable ISO-8601 string
                    if out_fmt == 'timestamp104':
                        comps = f.get('value_components') or {}
                        year = comps.get('year_le') or comps.get('year_be')
                        month = comps.get('month')
                        day = comps.get('day')
                        hour = comps.get('hour')
                        minute = comps.get('minute')
                        second = comps.get('second')
                        remainder_hex = comps.get('remainder_hex') if isinstance(comps.get('remainder_hex'), str) else None
                        if year is not None and month is not None and day is not None and hour is not None and minute is not None and second is not None:
                            # Basic ISO-8601 UTC timestamp; append remainder hex if present
                            iso = f"{int(year):04d}-{int(month):02d}-{int(day):02d}T{int(hour):02d}:{int(minute):02d}:{int(second):02d}Z"
                            if remainder_hex:
                                iso = iso.replace('Z', f'.{remainder_hex}Z')
                            value = iso
                        else:
                            value = list(vb)
                    else:
                        value = list(vb)
                except Exception:
                    value = f.get('value')
            else:
                value = f.get('value')

            # Determine type name (use parsed name when available).
            # For OEM FRU (record type 254) only field 1 is Vendor IANA; other fields are OEM-defined.
            type_name = f.get('field_type_name') if isinstance(f.get('field_type_name'), str) else ''
            if rec_type == 254:
                if ftype == 1:
                    type_name = 'Vendor IANA'
                else:
                    type_name = 'OEM-defined'
            else:
                if ftype == 15:
                    type_name = 'Vendor IANA'
                elif not type_name or type_name.startswith('Unknown'):
                    type_name = 'Reserved'

            field_obj = {
                'type': ftype,
                'typeName': type_name,
                'required': True,
                'description': None,
                'format': out_fmt,
                'length': length,
                'value': value
            }

            spec_rec['fields'].append(field_obj)

        spec_records.append(spec_rec)

    return spec_records





def main():
    port = SerialPort('/dev/ttyUSB0', baudrate=115200)
    
    if not port.open():
        print("Failed to open port")
        return
    
    pdr_records = []
    handle = 0
    max_pdrs = 50
    max_retries = 3  # Retry up to 3 times for transient errors
    # Pass 1: Retrieve all PDRs (raw)
    for i in range(max_pdrs):
        retry_count = 0
        result = None
        error = None
        while retry_count < max_retries:
            result, error = get_pdr(port, handle)
            if not error:
                break
            completion_code_names = {
                0x80: "PLDM_ERROR (PDR not ready or unavailable)",
                0x82: "PLDM_PLATFORM_INVALID_RECORD_HANDLE",
                0x83: "PLDM_PLATFORM_INVALID_DATA_TRANSFER_HANDLE",
            }
            error_name = completion_code_names.get(int(error.split("0x")[1], 16) if "0x" in error else 0, "Unknown")
            if "0x82" in error:
                print(f"⚠ Invalid handle 0x{handle:08x}: reached end of PDR repository")
                break
            retry_count += 1
            if retry_count < max_retries:
                print(f"⚠ Error retrieving handle 0x{handle:08x}: {error} ({error_name}) - retrying ({retry_count}/{max_retries})...")
            else:
                print(f"⚠ Error retrieving handle 0x{handle:08x}: {error} ({error_name}) - max retries exceeded")
        if error:
            if "0x82" in error:
                break
            if handle < max_pdrs:
                handle += 1
                continue
            else:
                break
        pdr_data = result['pdr_data']
        next_handle = result['next_handle']
        if isinstance(pdr_data, str):
            pdr_bytes = bytes.fromhex(pdr_data)
        else:
            pdr_bytes = pdr_data
        if len(pdr_bytes) >= 10:
            pdr_records.append({'pdr_data': pdr_bytes, 'handle': handle, 'next_handle': next_handle})
            pdr_type = pdr_bytes[5]
            print(f"✓ Retrieved handle 0x{handle:08x} (Type {pdr_type:2d}: {PDR_TYPE_NAMES.get(pdr_type, 'Unknown')})")
        if next_handle == 0 or next_handle == handle:
            print(f"[DEBUG] Breaking loop at handle 0x{handle:08x} (next_handle=0x{next_handle:08x})")
            break
        handle = next_handle

    # Pass 2: Decode all OEM State Set PDRs first to populate OEM_STATE_SET_VALUES
    for pdr in pdr_records:
        pdr_bytes = pdr['pdr_data']
        if len(pdr_bytes) >= 10 and pdr_bytes[5] == 8:  # PDRType 8 = OEM State Set PDR
            decode_oem_state_set_pdr(pdr_bytes)

    # Pass 3: Decode all PDRs, now with OEM state sets available
    for pdr in pdr_records:
        pdr_bytes = pdr['pdr_data']
        if len(pdr_bytes) >= 10:
            pdr['decoded'] = decode_pdr(pdr_bytes)

    # ...existing code for FRU and output file writing...


if __name__ == '__main__':
    main()
