"""PLDM command encoding for PDR discovery."""

import struct
from typing import Tuple
from rich.console import Console

console = Console()


class PDLMCommandEncoder:
    """Encode PLDM commands for PDR discovery."""

    # PLDM Type 2 (Platform Monitoring and Control) commands
    PLDM_TYPE = 2
    
    # PLDM Type 4 (FRU Data) commands
    PLDM_TYPE_FRU = 4

    # Commands (per DSP0248 Table 110)
    GET_PDR_REPOSITORY_INFO = 0x50
    GET_PDR = 0x51
    
    # FRU commands (per DSP0257 Table 7)
    GET_FRU_RECORD_TABLE_METADATA = 0x01  # (Type 4)
    GET_FRU_RECORD_TABLE = 0x02  # (Type 4)
    SET_FRU_RECORD_TABLE = 0x03  # (Type 4)

    # PLDM header structure
    # [0] Request(1)/Datagram(1)/Reserved(1)/InstanceId(5)
    # [1] PLDM Type (6) + Header Version (2)
    # [2] Command code
    # [3+] Payload

    @staticmethod
    def _build_pldm_header(command: int, pldm_type: int, instance_id: int, request: int = 1) -> bytes:
        """Build PLDM message header bytes."""
        first = ((request & 0x01) << 7) | (0 << 6) | (0 << 5) | (instance_id & 0x1F)
        header_ver = 0
        second = ((header_ver & 0x03) << 6) | (pldm_type & 0x3F)
        third = command & 0xFF
        return bytes([first, second, third])

    @staticmethod
    def encode_get_pdr_repository_info(instance_id: int = 0) -> bytes:
        """
        Encode GetPDRRepositoryInfo command.

        Request has no payload.

        Args:
            instance_id: Instance ID (0-31).

        Returns:
            Encoded PLDM message.
        """
        return PDLMCommandEncoder._build_pldm_header(
            PDLMCommandEncoder.GET_PDR_REPOSITORY_INFO,
            PDLMCommandEncoder.PLDM_TYPE,
            instance_id,
            request=1,
        )

    @staticmethod
    def encode_get_pdr(
        instance_id: int = 0,
        record_handle: int = 0,
        data_transfer_handle: int = 0,
        transfer_operation_flag: int = 0x01,
        request_count: int = 254,
        record_change_number: int = 0,
    ) -> bytes:
        """
        Encode GetPDR command (DSP0248 26.2).

        Args:
            instance_id: Instance ID (0-31).
            record_handle: PDR record handle (0x00000000 = first).
            data_transfer_handle: Handle for multipart transfers (0 if GetFirstPart).
            transfer_operation_flag: 0x00=XFER_FIRST_PART, 0x01=XFER_NEXT_PART.
            request_count: Max bytes to return in response.
            record_change_number: 0 for GetFirstPart, from response for GetNextPart.

        Returns:
            Encoded PLDM message.
        """
        msg = bytearray()

        # PLDM header
        msg.extend(
            PDLMCommandEncoder._build_pldm_header(
                PDLMCommandEncoder.GET_PDR,
                PDLMCommandEncoder.PLDM_TYPE,
                instance_id,
                request=1,
            )
        )

        # Payload (per DSP0248 Table 69)
        msg.extend(struct.pack("<I", record_handle))  # 4 bytes
        msg.extend(struct.pack("<I", data_transfer_handle))  # 4 bytes
        msg.append(transfer_operation_flag & 0xFF)  # 1 byte: 0x00=FirstPart, 0x01=NextPart
        msg.extend(struct.pack("<H", request_count))  # 2 bytes
        msg.extend(struct.pack("<H", record_change_number))  # 2 bytes

        return bytes(msg)

    @staticmethod
    def decode_get_pdr_repository_info_response(
        response: bytes,
    ) -> dict:
        """
        Decode GetPDRRepositoryInfo response.

        Response format:
          [0] Completion Code
          [1-4] Repository Change Count (little-endian)
          [5-8] Total PDR Record Count (little-endian)
          [9-12] Repository Size in bytes (little-endian)

        Args:
            response: Raw PLDM response bytes.

        Returns:
            Dictionary with repository info or error.
        """
        if len(response) < 1:
            return {"error": "Response too short"}

        cc = response[0]
        if cc != 0:
            return {"error": f"Command failed with CC={cc}"}

        if len(response) < 13:
            return {"error": "Invalid response length"}

        try:
            repo_change_count = struct.unpack("<I", response[1:5])[0]
            total_pdr_records = struct.unpack("<I", response[5:9])[0]
            repository_size = struct.unpack("<I", response[9:13])[0]

            return {
                "repository_change_count": repo_change_count,
                "total_pdr_records": total_pdr_records,
                "repository_size": repository_size,
            }
        except Exception as e:
            return {"error": f"Decode failed: {e}"}

    @staticmethod
    def decode_get_pdr_response(response: bytes) -> dict:
        """
        Decode GetPDR response (DSP0248 26.2).

        Response format (DSP0248 Table 69):
          [0] Completion Code
          [1-4] Next Record Handle (uint32, LE)
          [5-8] Next Data Transfer Handle (uint32, LE)
          [9] Transfer Flag (enum8): Start=0x00, Middle=0x01, End=0x04, StartAndEnd=0x05
          [10-11] Response Count (uint16, LE)
          [12+] Record Data
          [end] Transfer CRC (uint8, only if transferFlag=End)

        Args:
            response: Raw PLDM response bytes.

        Returns:
            Dictionary with PDR data or error.
        """
        if len(response) < 1:
            return {"error": "Response too short"}

        cc = response[0]
        if cc != 0:
            return {"error": f"Command failed with CC={cc}"}

        if len(response) < 12:
            return {"error": "Invalid response length"}

        try:
            next_record_handle = struct.unpack("<I", response[1:5])[0]
            next_data_transfer_handle = struct.unpack("<I", response[5:9])[0]
            transfer_flag = response[9]
            response_count = struct.unpack("<H", response[10:12])[0]
            
            # Record data starts at offset 12
            record_data = response[12:12 + response_count]
            
            # If transferFlag = End (0x04), last byte is transfer CRC
            transfer_crc = None
            if transfer_flag == 0x04 and len(response) > 12 + response_count:
                transfer_crc = response[12 + response_count]

            return {
                "next_record_handle": next_record_handle,
                "next_data_transfer_handle": next_data_transfer_handle,
                "transfer_flag": transfer_flag,
                "response_count": response_count,
                "record_data": record_data,
                "transfer_crc": transfer_crc,
            }
        except Exception as e:
            return {"error": f"Decode failed: {e}"}

    @staticmethod
    def encode_get_fru_record_table_metadata(instance_id: int = 0) -> bytes:
        """
        Encode GetFRURecordTableMetadata command (DSP0257 13.1).

        Request has no payload.

        Args:
            instance_id: Instance ID (0-31).

        Returns:
            Encoded PLDM message.
        """
        return PDLMCommandEncoder._build_pldm_header(
            PDLMCommandEncoder.GET_FRU_RECORD_TABLE_METADATA,
            PDLMCommandEncoder.PLDM_TYPE_FRU,
            instance_id,
            request=1,
        )

    @staticmethod
    def encode_get_fru_record_table(
        instance_id: int = 0,
        pldm_type: int = 0x04,
        transfer_operation: int = 0x00,
        transfer_context: int = 0x00000000,
        data_transfer_handle: int = 0x00000000,
        requested_section_offset: int = 0x00000000,
        requested_section_length: int = 0x00000000,
    ) -> bytes:
        """
        Encode GetFRURecordTable command (DSP0257 13.2).

        This is a MultipartReceive implementation per DSP0240 Table 17.

        Args:
            instance_id: Instance ID (0-31).
            pldm_type: PLDM Type for transfer (0x04 = FRU).
            transfer_operation: Transfer operation enum:
                PLDM_XFER_FIRST_PART  = 0x00,
                PLDM_XFER_NEXT_PART   = 0x01,
                PLDM_XFER_ABORT       = 0x02,
                PLDM_XFER_COMPLETE    = 0x03,
                PLDM_XFER_CURRENT_PART= 0x04
            Request payload layout (per user):
                uint32_t data_transfer_handle;
                uint8_t  transfer_operation_flag;
            transfer_context: Record Set ID (bits 31:16) | Record Type (bits 15:8) | FieldType (bits 7:0).
                             0x00000000 = wildcard (all records).
            data_transfer_handle: Handle for multipart transfers (0 for initial request).
            requested_section_offset: Offset within section (0 to start from beginning).
            requested_section_length: Requested length (0 = unknown/full table).

        Returns:
            Encoded PLDM message.
        """
        msg = bytearray()

        # PLDM header
        msg.extend(
            PDLMCommandEncoder._build_pldm_header(
                PDLMCommandEncoder.GET_FRU_RECORD_TABLE,
                PDLMCommandEncoder.PLDM_TYPE_FRU,
                instance_id,
                request=1,
            )
        )

        # Request payload: DataTransferHandle (4 bytes LE) then TransferOperation (1 byte)
        msg.extend(struct.pack("<I", data_transfer_handle))  # 4 bytes: DataTransferHandle
        msg.append(transfer_operation & 0xFF)  # 1 byte: TransferOperation

        return bytes(msg)

    @staticmethod
    def decode_get_fru_record_table_metadata_response(response: bytes) -> dict:
        """
        Decode GetFRURecordTableMetadata response (DSP0257 Table 8).

        Response format:
          [0] Completion Code
          [1] FRUDataMajorVersion (should be 0x02)
          [2] FRUDataMinorVersion (should be 0x00)
          [3:6] FRUTableMaximumSize (uint32, LE)
          [7:10] FRUTableLength (uint32, LE)
          [11:12] Total number of Record Set Identifiers (uint16, LE)
          [13:14] Total number of records (uint16, LE)
          [15:18] FRUDataStructureTableIntegrityChecksum CRC-32 (uint32, LE)

        Args:
            response: Raw PLDM response bytes.

        Returns:
            Dictionary with FRU metadata or error.
        """
        if len(response) < 1:
            return {"error": "Response too short"}

        cc = response[0]
        if cc == 0x83:
            return {"error": "NO_FRU_DATA_STRUCTURE_TABLE_METADATA (0x83)"}
        if cc != 0:
            return {"error": f"Command failed with CC=0x{cc:02x}"}

        if len(response) < 19:
            return {"error": f"Invalid response length: {len(response)} (expected 19)"}

        try:
            fru_major_version = response[1]
            fru_minor_version = response[2]
            fru_table_max_size = struct.unpack("<I", response[3:7])[0]
            fru_table_length = struct.unpack("<I", response[7:11])[0]
            num_record_sets = struct.unpack("<H", response[11:13])[0]
            num_records = struct.unpack("<H", response[13:15])[0]
            crc32_checksum = struct.unpack("<I", response[15:19])[0]

            return {
                "fru_major_version": fru_major_version,
                "fru_minor_version": fru_minor_version,
                "fru_table_max_size": fru_table_max_size,
                "fru_table_length": fru_table_length,
                "num_record_sets": num_record_sets,
                "num_records": num_records,
                "crc32_checksum": crc32_checksum,
            }
        except Exception as e:
            return {"error": f"Decode failed: {e}"}

    @staticmethod
    def decode_get_fru_record_table_response(response: bytes) -> dict:
        """
        Decode GetFRURecordTable response (per DSP0240 MultipartReceive).

        Response format:
          [0] Completion Code
          [1-4] Next Data Transfer Handle (uint32, LE)
          [5] Transfer Flag (enum8): Start=0x00, Middle=0x01, End=0x04, StartAndEnd=0x05
          [6-7] Response Count (uint16, LE)
          [8+] FRU Record Table Data
          [end] Transfer CRC (uint8, only if transferFlag=End)

        Args:
            response: Raw PLDM response bytes.

        Returns:
            Dictionary with FRU table data or error.
        """
        if len(response) < 1:
            return {"error": "Response too short"}

        cc = response[0]
        if cc != 0:
            return {"error": f"Command failed with CC=0x{cc:02x}"}

        # Minimum length: completion_code (1) + next_data_transfer_handle (4) + transfer_flag (1)
        if len(response) < 6:
            return {"error": "Invalid response length"}

        try:
            next_data_transfer_handle = struct.unpack("<I", response[1:5])[0]
            transfer_flag = response[5]

            # FRU record table data starts at offset 6
            fru_data = response[6:]

            return {
                "next_data_transfer_handle": next_data_transfer_handle,
                "transfer_flag": transfer_flag,
                "fru_data": fru_data,
            }
        except Exception as e:
            return {"error": f"Decode failed: {e}"}
