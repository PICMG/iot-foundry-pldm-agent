"""PDR discovery and retrieval via PLDM GetPDR commands."""

import time
from typing import List, Dict, Any, Optional
from rich.console import Console
from pldm_mapping_wizard.serial_transport import SerialPort, MCTPFramer
from pldm_mapping_wizard.discovery.pldm_commands import PDLMCommandEncoder
from pldm_mapping_wizard.discovery.pdr_parser import PDRParser

console = Console()


class PDRRetriever:
    """Retrieve and parse PLDM Platform Descriptor Records (PDRs)."""

    # PLDM message type for MCTP
    PLDM_MCTP_MSG_TYPE = 0x01

    def __init__(
        self,
        port: str,
        local_eid: int = 16,
        remote_eid: int = 0,
        baudrate: int = 115200,
        debug: bool = False,
    ):
        """
        Initialize PDR retriever for a specific port.
        
        Args:
            port: Serial port path (e.g., "/dev/ttyUSB0").
            local_eid: Local endpoint ID (usually 0 for host).
            remote_eid: Remote endpoint ID (usually auto-detected).
        """
        self.port = port
        self.local_eid = local_eid
        self.remote_eid = remote_eid
        self.serial = SerialPort(port, baudrate=baudrate)
        self.connected = False
        self.instance_id = 0
        self.debug = debug

    def connect(self) -> bool:
        """
        Connect to the PLDM endpoint.
        
        Returns:
            True if connected, False otherwise.
        """
        console.print(f"📥 Retrieving PDRs from {self.port}...")
        
        if not self.serial.open():
            return False
        
        self.connected = True
        console.print(f"   ✓ Connected to {self.port}")
        return True

    def get_repository_info(self) -> Optional[Dict[str, Any]]:
        """
        Execute GetPDRRepositoryInfo command.
        
        Returns:
            Repository metadata or None on failure.
        """
        if not self.connected:
            console.print("[red]✗ Not connected[/red]")
            return None

        # Encode command
        cmd = PDLMCommandEncoder.encode_get_pdr_repository_info(
            instance_id=self.instance_id
        )
        
        # Frame for MCTP serial and send
        frame = MCTPFramer.build_frame(
            pldm_msg=cmd,
            dest=self.remote_eid,
            src=self.local_eid,
            msg_type=self.PLDM_MCTP_MSG_TYPE,
        )
        
        if self.debug:
            console.print(f"[dim]TX raw: {frame.hex()}[/dim]")

        if not self.serial.write(frame):
            console.print("[red]✗ Failed to send GetPDRRepositoryInfo[/red]")
            return None
        
        # Read response
        response_frame = self.serial.read_until_idle()
        if not response_frame:
            console.print("[red]✗ Timeout waiting for response[/red]")
            return None
        
        if self.debug:
            console.print(f"[dim]RX raw: {response_frame.hex()}[/dim]")

        frames = MCTPFramer.extract_frames(response_frame)
        parsed_frames = [MCTPFramer.parse_frame(fr) for fr in frames]
        
        # Try to reassemble fragmented frames
        reassembled = MCTPFramer.reassemble_frames(parsed_frames)
        if reassembled is None:
            # No complete frame yet, try first parsed frame
            reassembled = parsed_frames[0] if parsed_frames else None
        
        if self.debug and reassembled:
            console.print(f"[dim]RX parsed: {reassembled}[/dim]")
        
        if not reassembled or not reassembled.get("fcs_ok", False):
            console.print("[red]✗ No valid PLDM response frame received[/red]")
            return None
        if reassembled.get("msg_type") != self.PLDM_MCTP_MSG_TYPE:
            console.print("[red]✗ Wrong message type[/red]")
            return None
        if reassembled.get("cmd_code") != PDLMCommandEncoder.GET_PDR_REPOSITORY_INFO:
            console.print("[red]✗ Wrong command code[/red]")
            return None

        info = reassembled

        if info.get("resp_code") is None:
            console.print("[red]✗ Missing PLDM response code[/red]")
            return None
        
        # Response payload: [resp_code] + data
        pldm_response = info.get("extra", b"")
        result = PDLMCommandEncoder.decode_get_pdr_repository_info_response(pldm_response)
        
        if "error" in result:
            console.print(f"[red]✗ {result['error']}[/red]")
            return None
        
        return result

    def get_pdrs(self) -> List[Dict[str, Any]]:
        """
        Retrieve all PDRs from the endpoint with pagination.
        
        Returns:
            List of PDR dictionaries (parsed).
        """
        if not self.connected:
            console.print("[red]✗ Not connected[/red]")
            return []

        # First get repository info
        repo_info = self.get_repository_info()
        if not repo_info:
            return []
        
        total_records = repo_info.get("total_pdr_records", 0)
        console.print(f"   ✓ Found {total_records} PDRs")
        
        pdrs = []
        record_handle = 0  # 0 = get first PDR

        # Paginate through PDRs by following the next_record_handle chain
        max_retries = 3

        while True:
            retries = 0
            data_transfer_handle = 0
            transfer_operation_flag = 0x01  # GetFirstPart
            record_change_number = 0
            record_bytes = bytearray()
            next_record_handle = 0

            while retries < max_retries:
                try:
                    # Encode GetPDR command (DSP0248 Table 69)
                    cmd = PDLMCommandEncoder.encode_get_pdr(
                        instance_id=self.instance_id,
                        record_handle=record_handle,
                        data_transfer_handle=data_transfer_handle,
                        transfer_operation_flag=transfer_operation_flag,
                        request_count=255,
                        record_change_number=record_change_number,
                    )
                    
                    # Frame and send
                    frame = MCTPFramer.build_frame(
                        pldm_msg=cmd,
                        dest=self.remote_eid,
                        src=self.local_eid,
                        msg_type=self.PLDM_MCTP_MSG_TYPE,
                    )
                    
                    if self.debug:
                        console.print(f"[dim]TX raw: {frame.hex()}[/dim]")

                    if not self.serial.write(frame):
                        console.print("[red]✗ Failed to send GetPDR[/red]")
                        return pdrs
                    
                    # Read response with timeout
                    response_frame = self.serial.read_until_idle()
                    if not response_frame:
                        console.print(f"[yellow]⚠️  Timeout on PDR handle {record_handle:08x}, retrying...[/yellow]")
                        retries += 1
                        time.sleep(0.1)
                        continue
                    
                    if self.debug:
                        console.print(f"[dim]RX raw: {response_frame.hex()}[/dim]")

                    frames = MCTPFramer.extract_frames(response_frame)
                    parsed_frames = [MCTPFramer.parse_frame(fr) for fr in frames]
                    
                    # Try to reassemble fragmented frames
                    reassembled = MCTPFramer.reassemble_frames(parsed_frames)
                    if reassembled is None:
                        # No complete frame yet, try first parsed frame
                        reassembled = parsed_frames[0] if parsed_frames else None
                    
                    if self.debug and reassembled:
                        console.print(f"[dim]RX parsed: {reassembled}[/dim]")
                    
                    if not reassembled or not reassembled.get("fcs_ok", False):
                        console.print(f"[yellow]⚠️  No valid PLDM response on PDR handle {record_handle:08x}, retrying...[/yellow]")
                        retries += 1
                        time.sleep(0.1)
                        continue
                    if reassembled.get("msg_type") != self.PLDM_MCTP_MSG_TYPE:
                        console.print(f"[yellow]⚠️  Wrong msg_type on PDR handle {record_handle:08x}, retrying...[/yellow]")
                        retries += 1
                        time.sleep(0.1)
                        continue
                    if reassembled.get("cmd_code") != PDLMCommandEncoder.GET_PDR:
                        console.print(f"[yellow]⚠️  Wrong cmd_code on PDR handle {record_handle:08x}, retrying...[/yellow]")
                        retries += 1
                        time.sleep(0.1)
                        continue

                    info = reassembled
                    
                    pldm_response = info.get("extra", b"")
                    result = PDLMCommandEncoder.decode_get_pdr_response(pldm_response)
                    
                    if "error" in result:
                        console.print(f"[yellow]⚠️  {result['error']}, retrying...[/yellow]")
                        retries += 1
                        time.sleep(0.1)
                        continue
                    
                    # Accumulate record data
                    record_data = result.get("record_data", b"")
                    record_bytes.extend(record_data)

                    # Track handles for multipart
                    next_record_handle = result.get("next_record_handle", 0)
                    returned_transfer_handle = result.get("next_data_transfer_handle", 0)

                    if self.debug:
                        console.print(
                            f"[dim]PDR handle {record_handle:08x}: next_handle={next_record_handle:08x} "
                            f"next_xfer={returned_transfer_handle:08x} resp_cnt={result.get('response_count', 0)} "
                            f"xfer_flag=0x{result.get('transfer_flag', 0):02x}[/dim]"
                        )

                    # If transfer handle is zero, this record is complete
                    if returned_transfer_handle == 0:
                        import struct
                        
                        # Check if the device returned the complete PDR (with 10-byte header)
                        # or just the PDR body. DSP0248 specifies the response contains only
                        # record_data, but the DUT may include the complete PDR structure.
                        
                        if len(record_bytes) >= 10:
                            # Check if this looks like it already has a header:
                            # Bytes 4-5 should be version (0x01) and type
                            potential_version = record_bytes[4]
                            potential_type = record_bytes[5]
                            
                            # If version looks valid (0x01) and we get a reasonable type
                            # AND the first 4 bytes match our record_handle (LE), use it directly
                            returned_handle = struct.unpack('<I', record_bytes[0:4])[0]
                            if potential_version == 0x01 and returned_handle == record_handle:
                                # Device returned complete PDR with header - use directly
                                full_pdr = record_bytes
                                pdr_type = potential_type
                                if self.debug:
                                    console.print(f"[dim]PDR {record_handle:08x}: Using device's complete PDR (type={pdr_type})[/dim]")
                            else:
                                # Reconstruct header - device returned only body
                                pdr_type = record_bytes[0] if len(record_bytes) > 0 else 0
                                pdr_header = bytearray()
                                pdr_header.extend(struct.pack('<I', record_handle))  # Record Handle (4 bytes)
                                pdr_header.append(0x01)  # PDR Header Version (1 byte)
                                pdr_header.append(pdr_type)  # PDR Type (1 byte)
                                pdr_header.extend(struct.pack('<H', 0))  # Record Change Number (2 bytes)
                                pdr_header.extend(struct.pack('<H', len(record_bytes)))  # Data Length (2 bytes)
                                full_pdr = pdr_header + record_bytes
                                if self.debug:
                                    console.print(f"[dim]PDR {record_handle:08x}: Reconstructed header (type={pdr_type})[/dim]")
                        else:
                            # Too short to be a complete PDR, reconstruct
                            pdr_type = record_bytes[0] if len(record_bytes) > 0 else 0
                            pdr_header = bytearray()
                            pdr_header.extend(struct.pack('<I', record_handle))
                            pdr_header.append(0x01)
                            pdr_header.append(pdr_type)
                            pdr_header.extend(struct.pack('<H', 0))
                            pdr_header.extend(struct.pack('<H', len(record_bytes)))
                            full_pdr = pdr_header + record_bytes
                        
                        pdr_entry = {
                            "record_handle": record_handle,
                            "data": bytes(full_pdr),
                            "type": pdr_type,
                        }
                        pdrs.append(pdr_entry)
                        
                        # Check if we've reached the end of the PDR chain
                        if next_record_handle == 0:
                            console.print(f"[green]✓ Reached end of PDR chain (next_record_handle=0)[/green]")
                            return pdrs
                        
                        record_handle = next_record_handle
                        time.sleep(0.05)  # Small delay before next PDR
                        break

                    # Otherwise continue with GetNextPart
                    data_transfer_handle = returned_transfer_handle
                    transfer_operation_flag = 0x00  # GetNextPart
                    record_change_number = 0
                    time.sleep(0.05)
                    continue
                    
                except Exception as e:
                    console.print(f"[yellow]⚠️  Exception on PDR handle {record_handle:08x}: {e}[/yellow]")
                    retries += 1
                    time.sleep(0.1)
            
            if retries >= max_retries:
                console.print(f"[red]✗ Failed to retrieve PDR handle {record_handle:08x} after {max_retries} retries[/red]")
                console.print(f"[red]Stopping PDR retrieval due to failure[/red]")
                break
        
        return pdrs

    def disconnect(self) -> None:
        """Disconnect from the endpoint."""
        if self.connected:
            self.serial.close()
            self.connected = False
