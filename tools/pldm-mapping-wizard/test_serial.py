#!/usr/bin/env python3
"""Test MCTP/PLDM serial communication modules."""

from pldm_mapping_wizard.serial_transport import MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder

def test_mctp_framing():
    """Test MCTP frame encoding/decoding."""
    print("Testing MCTP framing...")
    
    # Test data: PLDM header bytes
    payload = PDLMCommandEncoder.encode_get_pdr_repository_info(instance_id=0)
    
    # Frame it
    frame = MCTPFramer.build_frame(
        pldm_msg=payload,
        dest=0,
        src=0x10,
        msg_type=0x01,
    )
    
    print(f"  Payload: {payload.hex()}")
    print(f"  Frame:   {frame.hex()}")
    
    # Unframe it
    info = MCTPFramer.parse_frame(frame)
    assert info is not None, "Failed to parse frame"
    assert info["fcs_ok"], "FCS failed"
    assert info["msg_type"] == 0x01, "Message type mismatch"
    assert info["type"] == PDLMCommandEncoder.PLDM_TYPE, "PLDM type mismatch"
    assert info["cmd_code"] == PDLMCommandEncoder.GET_PDR_REPOSITORY_INFO, "Command mismatch"
    print("  ✓ MCTP framing/parsing works")


def test_pldm_command_encoding():
    """Test PLDM command encoding."""
    print("\nTesting PLDM command encoding...")
    
    # Test GetPDRRepositoryInfo
    cmd = PDLMCommandEncoder.encode_get_pdr_repository_info(instance_id=0)
    print(f"  GetPDRRepositoryInfo: {cmd.hex()}")
    assert len(cmd) >= 2, "Command too short"
    print("  ✓ GetPDRRepositoryInfo encoded")
    
    # Test GetPDR
    cmd = PDLMCommandEncoder.encode_get_pdr(
        instance_id=0,
        record_handle=0,
        data_transfer_handle=0,
        transfer_operation_flag=0x01,
        request_count=254,
        record_change_number=0,
    )
    print(f"  GetPDR: {cmd.hex()}")
    assert len(cmd) >= 2, "Command too short"
    print("  ✓ GetPDR encoded")


def test_pldm_response_decoding():
    """Test PLDM response decoding."""
    print("\nTesting PLDM response decoding...")
    
    # Simulate GetPDRRepositoryInfo response (13 bytes minimum)
    # [0] CC=0 (success)
    # [1-4] change_count=0x00000000
    # [5-8] total_records=0x00000005 (5 records)
    # [9-12] repo_size=0x00000400 (1024 bytes)
    response = b"\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x04\x00\x00"
    
    result = PDLMCommandEncoder.decode_get_pdr_repository_info_response(response)
    assert "error" not in result, f"Unexpected error: {result}"
    assert result["total_pdr_records"] == 5, "Record count mismatch"
    assert result["repository_size"] == 1024, "Repo size mismatch"
    print(f"  Decoded: {result}")
    print("  ✓ GetPDRRepositoryInfo response decoded")


if __name__ == "__main__":
    test_mctp_framing()
    test_pldm_command_encoding()
    test_pldm_response_decoding()
    print("\n✅ All serial/PLDM tests passed!")
