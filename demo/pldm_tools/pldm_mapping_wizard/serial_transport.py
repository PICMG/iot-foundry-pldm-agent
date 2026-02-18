"""Serial port communication for PLDM/MCTP endpoints."""

import time
import serial
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class MCTPMessage:
    """MCTP message structure."""

    source_eid: int
    destination_eid: int
    message_type: int
    payload: bytes


class SerialPort:
    """Low-level serial port communication."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0):
        """
        Initialize serial port.

        Args:
            port: Serial device path (e.g., "/dev/ttyUSB0").
            baudrate: Serial communication speed.
            timeout: Read/write timeout in seconds.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def open(self) -> bool:
        """
        Open serial port.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.serial = serial.Serial(
                self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            return True
        except Exception as e:
            console.print(f"[red]✗ Failed to open {self.port}: {e}[/red]")
            return False

    def close(self) -> None:
        """Close serial port."""
        if self.serial:
            self.serial.close()
            self.serial = None

    def write(self, data: bytes) -> bool:
        """
        Write data to serial port.

        Args:
            data: Bytes to write.

        Returns:
            True if successful, False otherwise.
        """
        if not self.serial or not self.serial.is_open:
            return False
        try:
            self.serial.write(data)
            self.serial.flush()
            return True
        except Exception as e:
            console.print(f"[red]✗ Write failed: {e}[/red]")
            return False

    def read(self, size: int = 1024) -> Optional[bytes]:
        """
        Read data from serial port.

        Args:
            size: Maximum bytes to read.

        Returns:
            Bytes read, or None on timeout/error.
        """
        if not self.serial or not self.serial.is_open:
            return None
        try:
            data = self.serial.read(size)
            return data if data else None
        except Exception as e:
            console.print(f"[red]✗ Read failed: {e}[/red]")
            return None

    def read_until_idle(self, timeout: float = 2.0, idle: float = 0.2) -> bytes:
        """
        Read until the line is idle or timeout expires.

        Args:
            timeout: Overall timeout in seconds.
            idle: Idle time in seconds to stop after last byte.

        Returns:
            Bytes collected.
        """
        if not self.serial or not self.serial.is_open:
            return b""

        data = bytearray()
        last = time.time()
        deadline = time.time() + timeout
        while time.time() < deadline:
            n = self.serial.in_waiting
            if n:
                data.extend(self.serial.read(n))
                last = time.time()
            else:
                if data and (time.time() - last) > idle:
                    break
                time.sleep(0.001)
        return bytes(data)

    def is_open(self) -> bool:
        """Check if port is open."""
        return self.serial is not None and self.serial.is_open


class MCTPFramer:
    """MCTP serial framing compatible with mctp-serial-linux."""

    FRAME_CHAR = 0x7E
    ESCAPE_CHAR = 0x7D
    INITFCS = 0xFFFF

    # SOM/EOM flags in the flags byte (bits 7-6)
    SOM_BIT = 0x80  # Start of Message (bit 7)
    EOM_BIT = 0x40  # End of Message (bit 6)

    # Frame layout (escaped between frame chars):
    # [FRAME][protocol_v][byte_count][body...][fcs_hi][fcs_lo][FRAME]
    # body layout:
    # [header_version][dest][src][flags][msg_type][pldm_msg...]
    
    def __init__(self):
        """Initialize frame reassembler state."""
        self.reassembly_buffer = bytearray()
        self.assembling = False

    @staticmethod
    def _calc_fcs(data: bytes) -> int:
        """PPP FCS-16 per RFC1662 / DSP0237 Annex A (reflected polynomial 0x8408)."""
        # FCS lookup table for polynomial 0x8408 (reflected 0x1021)
        fcstab = [
            0x0000, 0x1189, 0x2312, 0x329b, 0x4624, 0x57ad, 0x6536, 0x74bf,
            0x8c48, 0x9dc1, 0xaf5a, 0xbed3, 0xca6c, 0xdbe5, 0xe97e, 0xf8f7,
            0x1081, 0x0108, 0x3393, 0x221a, 0x56a5, 0x472c, 0x75b7, 0x643e,
            0x9cc9, 0x8d40, 0xbfdb, 0xae52, 0xdaed, 0xcb64, 0xf9ff, 0xe876,
            0x2102, 0x308b, 0x0210, 0x1399, 0x6726, 0x76af, 0x4434, 0x55bd,
            0xad4a, 0xbcc3, 0x8e58, 0x9fd1, 0xeb6e, 0xfae7, 0xc87c, 0xd9f5,
            0x3183, 0x200a, 0x1291, 0x0318, 0x77a7, 0x662e, 0x54b5, 0x453c,
            0xbdcb, 0xac42, 0x9ed9, 0x8f50, 0xfbef, 0xea66, 0xd8fd, 0xc974,
            0x4204, 0x538d, 0x6116, 0x709f, 0x0420, 0x15a9, 0x2732, 0x36bb,
            0xce4c, 0xdfc5, 0xed5e, 0xfcd7, 0x8868, 0x99e1, 0xab7a, 0xbaf3,
            0x5285, 0x430c, 0x7197, 0x601e, 0x14a1, 0x0528, 0x37b3, 0x263a,
            0xdecd, 0xcf44, 0xfddf, 0xec56, 0x98e9, 0x8960, 0xbbfb, 0xaa72,
            0x6306, 0x728f, 0x4014, 0x519d, 0x2522, 0x34ab, 0x0630, 0x17b9,
            0xef4e, 0xfec7, 0xcc5c, 0xddd5, 0xa96a, 0xb8e3, 0x8a78, 0x9bf1,
            0x7387, 0x620e, 0x5095, 0x411c, 0x35a3, 0x242a, 0x16b1, 0x0738,
            0xffcf, 0xee46, 0xdcdd, 0xcd54, 0xb9eb, 0xa862, 0x9af9, 0x8b70,
            0x8408, 0x9581, 0xa71a, 0xb693, 0xc22c, 0xd3a5, 0xe13e, 0xf0b7,
            0x0840, 0x19c9, 0x2b52, 0x3adb, 0x4e64, 0x5fed, 0x6d76, 0x7cff,
            0x9489, 0x8500, 0xb79b, 0xa612, 0xd2ad, 0xc324, 0xf1bf, 0xe036,
            0x18c1, 0x0948, 0x3bd3, 0x2a5a, 0x5ee5, 0x4f6c, 0x7df7, 0x6c7e,
            0xa50a, 0xb483, 0x8618, 0x9791, 0xe32e, 0xf2a7, 0xc03c, 0xd1b5,
            0x2942, 0x38cb, 0x0a50, 0x1bd9, 0x6f66, 0x7eef, 0x4c74, 0x5dfd,
            0xb58b, 0xa402, 0x9699, 0x8710, 0xf3af, 0xe226, 0xd0bd, 0xc134,
            0x39c3, 0x284a, 0x1ad1, 0x0b58, 0x7fe7, 0x6e6e, 0x5cf5, 0x4d7c,
            0xc60c, 0xd785, 0xe51e, 0xf497, 0x8028, 0x91a1, 0xa33a, 0xb2b3,
            0x4a44, 0x5bcd, 0x6956, 0x78df, 0x0c60, 0x1de9, 0x2f72, 0x3efb,
            0xd68d, 0xc704, 0xf59f, 0xe416, 0x90a9, 0x8120, 0xb3bb, 0xa232,
            0x5ac5, 0x4b4c, 0x79d7, 0x685e, 0x1ce1, 0x0d68, 0x3ff3, 0x2e7a,
            0xe70e, 0xf687, 0xc41c, 0xd595, 0xa12a, 0xb0a3, 0x8238, 0x93b1,
            0x6b46, 0x7acf, 0x4854, 0x59dd, 0x2d62, 0x3ceb, 0x0e70, 0x1ff9,
            0xf78f, 0xe606, 0xd49d, 0xc514, 0xb1ab, 0xa022, 0x92b9, 0x8330,
            0x7bc7, 0x6a4e, 0x58d5, 0x495c, 0x3de3, 0x2c6a, 0x1ef1, 0x0f78
        ]
        
        fcs = MCTPFramer.INITFCS
        for b in data:
            fcs = (fcs >> 8) ^ fcstab[(fcs ^ b) & 0xff]
        return fcs

    @staticmethod
    def _unescape_body(raw: bytes) -> bytes:
        out = bytearray()
        i = 0
        while i < len(raw):
            b = raw[i]
            if b == MCTPFramer.ESCAPE_CHAR:
                i += 1
                if i >= len(raw):
                    break
                out.append((raw[i] + 0x20) & 0xFF)
            else:
                out.append(b)
            i += 1
        return bytes(out)

    @staticmethod
    def build_frame(
        pldm_msg: bytes,
        dest: int,
        src: int,
        msg_type: int = 0x01,
        header_version: int = 0x01,
        protocol_version: int = 0x01,
        flags: int = 0xC8,
    ) -> bytes:
        """Wrap PLDM message bytes into MCTP serial frame."""
        body = bytearray()
        body.append(header_version)
        body.append(dest & 0xFF)
        body.append(src & 0xFF)
        body.append(flags & 0xFF)
        body.append(msg_type & 0xFF)
        body.extend(pldm_msg)

        byte_count = len(body)
        frame = bytearray()
        frame.append(MCTPFramer.FRAME_CHAR)
        frame.append(protocol_version & 0xFF)
        frame.append(byte_count & 0xFF)
        frame.extend(body)
        fcs = MCTPFramer._calc_fcs(bytes(frame[1:]))
        frame.append((fcs >> 8) & 0xFF)
        frame.append(fcs & 0xFF)
        frame.append(MCTPFramer.FRAME_CHAR)

        tx = bytearray()
        payload_start = 3
        payload_end = 3 + byte_count
        for i, b in enumerate(frame):
            # Only escape FRAME_CHAR and ESCAPE_CHAR in the body (payload_start to payload_end-1)
            if (i >= payload_start and i < payload_end) and (b in (MCTPFramer.FRAME_CHAR, MCTPFramer.ESCAPE_CHAR)):
                tx.append(MCTPFramer.ESCAPE_CHAR)
                tx.append((b - 0x20) & 0xFF)
            else:
                tx.append(b)
        # FCS and end flag must never be escaped
        return bytes(tx)

    @staticmethod
    def parse_frame(data: bytes) -> Optional[Dict[str, Any]]:
        """Parse a raw serial frame into MCTP/PLDM fields."""
        if not data:
            return None
        try:
            start = data.index(MCTPFramer.FRAME_CHAR)
            end = data.rindex(MCTPFramer.FRAME_CHAR)
        except ValueError:
            return None

        # Only unescape the payload region, not FCS/end sync
        raw_payload = data[start + 1:end]
        if len(raw_payload) < 6:
            return None
        protocol = raw_payload[0]
        byte_count = raw_payload[1]
        header_version = raw_payload[2]
        dest = raw_payload[3]
        src = raw_payload[4]
        flags = raw_payload[5]
        msg_type = raw_payload[6] if len(raw_payload) > 6 else None

        # Unescape only the body (payload) region
        body_start = 0
        body_end = 2 + byte_count
        unescaped_body = MCTPFramer._unescape_body(raw_payload[body_start:body_end])
        # FCS and end sync are not unescaped
        fcs_and_end = raw_payload[body_end:]
        payload = unescaped_body + fcs_and_end
        
        # PLDM header bit-field parsing (if msg_type == 1 = PLDM)
        instance = None
        pldm_type = None
        command_code = None
        response_code = None
        
        if msg_type == 1 and len(payload) > 9:
            # Byte 7: [rq(1)|D(1)|rsvd(1)|IID(5)]
            byte7 = payload[7]
            instance = byte7 & 0x1F  # Lower 5 bits = instance ID
            is_request = (byte7 & 0x80) != 0
            
            # Byte 8: [hdr_ver(2)|type(6)]
            byte8 = payload[8]
            pldm_type = byte8 & 0x3F  # Lower 6 bits = PLDM type
            
            # Byte 9: command code
            command_code = payload[9]
            
            # For responses, byte 10 is completion code
            # Requests have rq bit set, responses have it clear
            if not is_request and len(payload) > 10:
                response_code = payload[10]

        if len(payload) < (2 + byte_count + 2):
            return None

        fcs_calc = MCTPFramer._calc_fcs(payload[:2 + byte_count])
        msg_fcs = (payload[2 + byte_count] << 8) | payload[2 + byte_count + 1]

        # Extract extra (PLDM payload) starting after PLDM header
        # MCTP header: protocol(1) + byte_count(1) + hdr_ver(1) + dest(1) + src(1) + flags(1) + msg_type(1) = 7 bytes
        # PLDM header: byte7(1) + byte8(1) + cmd(1) = 3 bytes
        # Total header = 10 bytes
        pldm_payload_start = 10
        body_end = 2 + byte_count
        extra = b""
        if len(payload) > pldm_payload_start and body_end > pldm_payload_start:
            extra = payload[pldm_payload_start:body_end]

        # Extract SOM and EOM bits
        som = (flags & MCTPFramer.SOM_BIT) != 0
        eom = (flags & MCTPFramer.EOM_BIT) != 0

        return {
            "protocol": protocol,
            "byte_count": byte_count,
            "header_version": header_version,
            "dest": dest,
            "src": src,
            "flags": flags,
            "som": som,
            "eom": eom,
            "msg_type": msg_type,
            "instance": instance,
            "type": pldm_type,
            "cmd_code": command_code,
            "resp_code": response_code,
            "extra": extra,
            "fcs_ok": (fcs_calc == msg_fcs),
            "raw_fcs": msg_fcs,
            "fcs_calc": fcs_calc,
        }

    @staticmethod
    def extract_frames(data: bytes) -> List[bytes]:
        """
        Split a buffer into individual MCTP frames delimited by FRAME_CHAR.
        
        Per RFC1662, FCS bytes are NOT escaped, so 0x7E can appear in the FCS.
        We must calculate the expected frame length from the byte_count field
        and only look for the end flag at the correct position.
        """
        frames: List[bytes] = []
        if not data:
            return frames

        i = 0
        while i < len(data):
            # Find start flag
            if data[i] != MCTPFramer.FRAME_CHAR:
                i += 1
                continue
            start = i
            i += 1
            # Need at least: protocol(1) + byte_count(1) + FCS(2) + end_flag(1) = 5 more bytes
            if i + 4 >= len(data):
                break
            protocol = data[i]
            byte_count = data[i + 1]
            # Calculate expected end position:
            expected_end = start + 1 + 1 + 1 + byte_count + 2 + 1
            # Only count end flag if it's not escaped (should be literal 0x7E)
            if expected_end <= len(data) and data[expected_end - 1] == MCTPFramer.FRAME_CHAR:
                # Check for any escaped 0x7E in the body (payload_start to payload_end-1)
                payload_start = start + 3
                payload_end = payload_start + byte_count
                # Only check for ESCAPE_CHAR in the payload region
                if MCTPFramer.ESCAPE_CHAR in data[payload_start:payload_end]:
                    i = start + 1
                    continue
                frames.append(data[start:expected_end])
                i = expected_end - 1
            else:
                i = start + 1
        return frames

    @staticmethod
    def reassemble_frames(frames: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Reassemble fragmented MCTP frames based on SOM/EOM bits.
        
        Handles frame reassembly state machine:
        - SOM=1, EOM=1: Complete message in single frame (return immediately)
        - SOM=1, EOM=0: Start of fragmented message (accumulate)
        - SOM=0, EOM=0: Middle fragment (accumulate)
        - SOM=0, EOM=1: End fragment (accumulate and return complete)
        - SOM=1 during reassembly: Discard incomplete buffer and start fresh
        
        Args:
            frames: List of parsed frames from parse_frame().
            
        Returns:
            Reassembled frame dict, or None if incomplete.
        """
        reassembly_buffer = bytearray()
        assembling = False
        
        for frame in frames:
            if not frame:
                continue
            
            som = frame.get("som", False)
            eom = frame.get("eom", False)
            extra = frame.get("extra", b"")
            
            # Complete single-frame message
            if som and eom:
                return frame
            
            # Start of fragmented message
            if som and not eom:
                reassembly_buffer = bytearray(extra)
                assembling = True
                continue
            
            # Middle or end fragment
            if assembling:
                # If we see SOM while assembling, discard and start fresh
                if som:
                    reassembly_buffer = bytearray(extra)
                    continue
                
                # Append fragment
                reassembly_buffer.extend(extra)
                
                # End of message - return reassembled frame
                if eom:
                    # Copy frame structure and update extra with reassembled data
                    result = dict(frame)
                    result["extra"] = bytes(reassembly_buffer)
                    assembling = False
                    reassembly_buffer = bytearray()
                    return result
        
        # Incomplete reassembly
        return None
