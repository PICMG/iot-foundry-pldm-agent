#!/usr/bin/env python3
"""
Part 3: Runtime Agent - monitors USB port connectivity and manages resource state.
"""
import sys
import json
import base64
import asyncio
import subprocess
import importlib.util
import requests
import io
from pathlib import Path
from typing import Dict, Set, Tuple, Optional
from shared import ConfigManager, LogManager, ProcessManager, GracefulShutdown


class FRUMatcher:
    """Matches endpoints by comparing FRU data byte-for-byte."""
    
    def __init__(self, logger):
        self.logger = logger
        self.serial_port_cls = None
        self.export_mod = self._load_export_module()
    
    def _load_export_module(self):
        """Dynamically load export_pdrs_to_json module for FRU retrieval."""
        try:
            repo_root = Path(__file__).parents[2]
            export_path = repo_root / 'tools' / 'pldm-mapping-wizard' / 'export_pdrs_to_json.py'
            
            if not export_path.exists():
                self.logger.error(f"Export module not found: {export_path}")
                return None
            
            # Add pldm-mapping-wizard to path BEFORE importing
            pldm_tools_dir = str(repo_root / 'tools' / 'pldm-mapping-wizard')
            if pldm_tools_dir not in sys.path:
                sys.path.insert(0, pldm_tools_dir)
            
            # Load export module
            spec = importlib.util.spec_from_file_location('export_pdrs', export_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.logger.debug("Export module loaded successfully")
            
            # Load SerialPort for PLDM communication
            try:
                from pldm_mapping_wizard.serial_transport import SerialPort
                self.serial_port_cls = SerialPort
                self.logger.debug("SerialPort class loaded successfully")
            except ImportError as ie:
                self.logger.warning(f"Could not import SerialPort: {ie}")
                return None
            
            return mod
        except Exception as e:
            self.logger.error(f"Failed to load export module: {e}")
            return None
    
    async def get_fru_data_async(self, port: str) -> Optional[bytes]:
        """Retrieve FRU data from a device path asynchronously (in thread pool).
        
        Args:
            port: Device path like /dev/ttyUSB0
        
        Returns:
            FRU data bytes or None if retrieval fails
        """
        if not self.export_mod:
            self.logger.debug(f"No export module for {port}, skipping FRU read")
            return None
        
        try:
            loop = asyncio.get_running_loop()
            # Run in thread pool to avoid blocking
            fru_data = await loop.run_in_executor(
                None,
                self._get_fru_data_sync,
                port
            )
            return fru_data
        except Exception as e:
            self.logger.debug(f"Failed to get FRU from {port}: {e}")
            return None
    
    def _get_fru_data_sync(self, port: str) -> Optional[bytes]:
        """Synchronous FRU data retrieval using export module's built-in functions.
        
        Args:
            port: Device path like /dev/ttyUSB0
        
        Returns:
            FRU data bytes or None if retrieval fails
        """
        try:
            if not self.export_mod or not self.serial_port_cls:
                self.logger.warning(f"  [FRU SYNC] Export module or SerialPort not loaded for {port}")
                return None
            
            self.logger.debug(f"  [FRU SYNC] Opening PLDM port {port}...")
            
            # Use the same approach as the export module
            pldm_port = self.serial_port_cls(port=port, baudrate=115200, timeout=2)
            
            if not pldm_port.open():
                self.logger.warning(f"  [FRU SYNC] Failed to open port {port}")
                return None
            
            try:
                # Call the export module's get_fru_record_table function directly
                table_data, ferr = self.export_mod.get_fru_record_table(pldm_port, transfer_context=0)
                
                if ferr or not table_data:
                    self.logger.warning(f"  [FRU SYNC] Failed to get FRU table from {port}, ferr={ferr}")
                    return None
                
                self.logger.info(f"  [FRU SYNC] Retrieved {len(table_data)} bytes from {port}")
                return table_data
                
            finally:
                pldm_port.close()
                
        except FileNotFoundError:
            self.logger.warning(f"  [FRU SYNC] Device not found: {port}")
            return None
        except PermissionError:
            self.logger.warning(f"  [FRU SYNC] Permission denied opening {port}")
            return None
        except Exception as e:
            self.logger.warning(f"  [FRU SYNC] Exception on {port}: {type(e).__name__}: {e}")
            return None
    
    def compare_fru(self, fru1: bytes, fru2: bytes) -> bool:
        """Compare two FRU data blocks byte-for-byte."""
        return fru1 == fru2


class USBPortMonitor:
    """Monitors USB port connectivity."""
    
    def __init__(self, logger):
        self.logger = logger
        self.connected_ports = set()
        self.endpoint_map = {}
        self.port_to_device = {}  # Maps port ID (e.g., "1-1") to device path (e.g., "/dev/ttyUSB0")
        self.fru_matcher = FRUMatcher(logger)
    
    def load_pdr_endpoints(self, pdr_file: Path) -> Dict[str, Dict]:
        """Load known endpoints from PDR JSON file, with decoded FRU data and resource_id."""
        if not pdr_file.exists():
            self.logger.warning(f"PDR file not found: {pdr_file}")
            return {}
        
        try:
            data = json.loads(pdr_file.read_text())
            endpoints = {}
            
            # Extract endpoints from PDR data
            if isinstance(data, dict) and "endpoints" in data:
                for ep in data["endpoints"]:
                    bus_port = ep.get("bus_port") or ep.get("USBAddress")
                    if not bus_port:
                        usb_addr = ep.get("usb_addr", {})
                        sysfs_path = usb_addr.get("sysfs_path")
                        bus_port = self._extract_bus_port(sysfs_path)
                    if bus_port:
                        # Decode FRU data if present
                        fru_b64 = ep.get("raw_fru_data") or ep.get("fru_records", [{}])[0].get("raw_fru_data")
                        fru_bytes = None
                        if fru_b64:
                            try:
                                fru_bytes = base64.b64decode(fru_b64)
                                self.logger.debug(f"Loaded endpoint: {bus_port} ({len(fru_bytes)} bytes FRU)")
                            except Exception as e:
                                self.logger.debug(f"Failed to decode FRU for {bus_port}: {e}")
                        
                        endpoints[bus_port] = {
                            "device": ep.get("device"),
                            "resource_id": ep.get("resource_id", f"unknown_{bus_port}"),
                            "resource_path": ep.get("resource_path", f"/redfish/v1/AutomationNodes/{ep.get('resource_id', 'unknown')}"),
                            "fru_data": fru_bytes
                        }
            
            return endpoints
        except Exception as e:
            self.logger.error(f"Failed to load PDR endpoints: {e}")
            return {}

    def _extract_bus_port(self, sysfs_path: Optional[str]) -> Optional[str]:
        """Extract a bus/port key like "1-1" from a sysfs path."""
        if not sysfs_path:
            return None

        parts = sysfs_path.strip().split("/")
        for part in reversed(parts):
            if part and part[0].isdigit() and "-" in part:
                # Drop interface suffix like "1-1:1.0"
                return part.split(":", 1)[0]

        return None
    
    def scan_usb_ports(self) -> Dict[str, str]:
        """Scan for currently connected USB ports and their bus paths."""
        current_ports = {}
        
        try:
            # Use lsusb to get USB bus/port info
            result = subprocess.run(
                ["lsusb", "-t"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                self.logger.debug("lsusb -t not available, trying alternative method")
                return self._scan_tty_devices()
            
            # Parse lsusb -t output
            # Format: /: Bus 01.Port 1: Dev 1, Class=root_hub, Driver=xhci_hcd/1p, 5000M
            for line in result.stdout.split('\n'):
                if 'Port' in line and 'Dev' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.startswith('/'):
                            bus_info = part.strip('/:')
                            if '.' in bus_info:
                                current_ports[bus_info] = f"usb_{bus_info}"
            
            if not current_ports:
                return self._scan_tty_devices()
            
            return current_ports
        except Exception as e:
            self.logger.debug(f"lsusb failed: {e}, trying tty devices")
            return self._scan_tty_devices()
    
    def _scan_tty_devices(self) -> Dict[str, str]:
        """Fallback: scan for ttyUSB devices."""
        current_ports = {}
        
        try:
            result = subprocess.run(
                ["find", "/sys/devices", "-name", "ttyUSB*"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            for sysfs_line in result.stdout.strip().split('\n'):
                if sysfs_line:
                    # Extract the ttyUSB* device name from sysfs path
                    # e.g., /sys/devices/.../ttyUSB0
                    sysfs_parts = sysfs_line.split('/')
                    ttyusb_name = None
                    for part in sysfs_parts:
                        if part.startswith('ttyUSB'):
                            ttyusb_name = part
                            break
                    
                    if not ttyusb_name:
                        continue
                    
                    # Map to /dev/ttyUSB*
                    device_path = f"/dev/{ttyusb_name}"
                    
                    # Extract bus/port from sysfs path: 
                    # /sys/devices/pci0000:00/.../usb1/1-2/1-2:1.0/ttyUSB0 -> "1-2"
                    port_id = None
                    for part in sysfs_parts:
                        if part.startswith(('1-', '2-', '3-', '4-', '5-')):  # Bus port pattern
                            port_id = part.split(":", 1)[0]  # Drop :1.0 suffix
                            break
                    
                    if port_id:
                        current_ports[port_id] = sysfs_line
                        self.port_to_device[port_id] = device_path
                        self.logger.debug(f"  Mapped {port_id} → {device_path}")
            
            return current_ports
        except Exception as e:
            self.logger.debug(f"tty scan failed: {e}")
            return {}
    
    def detect_changes(self, known_endpoints: Dict[str, Dict]) -> Tuple[Set[str], Set[str]]:
        """Detect added and removed ports."""
        current = self.scan_usb_ports()
        current_ports = set(current.keys())
        
        # Get previously connected ports
        previous_ports = self.connected_ports
        
        # Detect changes
        added = current_ports - previous_ports
        removed = previous_ports - current_ports
        
        self.connected_ports = current_ports
        
        if added or removed:
            self.logger.info(f"USB topology change: added={added}, removed={removed}")
        
        return added, removed
    
    async def match_endpoint_by_fru(self, new_port: str, known_endpoints: Dict[str, Dict]) -> Optional[str]:
        """
        Match a new USB port to a known endpoint by comparing FRU data.
        
        Args:
            new_port: Port ID like "1-1"
            known_endpoints: Dict of known endpoints
        
        Returns:
            Bus/port of matched known endpoint, or None if no match.
        """
        self.logger.info(f"Attempting FRU match for new port {new_port}...")
        
        # Get device path for this port
        device_path = self.port_to_device.get(new_port)
        if not device_path:
            self.logger.warning(f"  [FRU] No device path found for port {new_port}")
            return None
        
        # Get FRU data from new port
        new_fru = await self.fru_matcher.get_fru_data_async(device_path)
        if not new_fru:
            self.logger.warning(f"  [FRU] Could not retrieve FRU from {new_port} ({device_path})")
            return None
        
        self.logger.info(f"  [FRU] Retrieved {len(new_fru)} bytes from {new_port} ({device_path})")
        
        # Compare against known endpoints
        for bus_port, ep_data in known_endpoints.items():
            if ep_data.get("fru_data"):
                known_fru = ep_data["fru_data"]
                self.logger.debug(f"  [FRU] Comparing {new_port} ({len(new_fru)} bytes) vs {bus_port} ({len(known_fru)} bytes)...")
                # Compare byte-for-byte
                match_result = self.fru_matcher.compare_fru(new_fru, known_fru)
                if match_result:
                    self.logger.info(f"  ✓ FRU match! {new_port} matches known endpoint {bus_port}")
                    return bus_port
                else:
                    self.logger.debug(f"    → Mismatch: {bus_port} (comparing {len(new_fru)} vs {len(known_fru)} bytes)")
            else:
                self.logger.debug(f"  [FRU] Skipping {bus_port}: no FRU data available")
        
        self.logger.warning(f"  [FRU] No FRU match found for {new_port}")
        return None


def disable_resources(port: str, resource_id: str, resource_path: str, logger, server_url: str = "http://localhost:8000"):
    """
    Disable Redfish resources for a dropped endpoint by setting State to UnavailableOffline.
    Search from top-level collections (Chassis, AutomationNodes) for the resource with matching ID.
    Then recursively disable the resource tree.
    """
    logger.info(f"[DISABLE] Starting for resource_id={resource_id}, port={port}...")
    
    try:
        # Find matches in both collections so we can update both trees when IDs overlap.
        logger.info(f"[DISABLE] Searching Chassis collection for ID={resource_id}...")
        chassis_path = _find_resource_in_collection(f"{server_url}/redfish/v1/Chassis", resource_id, logger, server_url)
        if chassis_path:
            logger.info(f"[DISABLE] Found Chassis at {chassis_path}")

        logger.info(f"[DISABLE] Searching AutomationNodes collection for ID={resource_id}...")
        node_path = _find_resource_in_collection(f"{server_url}/redfish/v1/AutomationNodes", resource_id, logger, server_url)
        if node_path:
            logger.info(f"[DISABLE] Found AutomationNode at {node_path}")

        targets = [path for path in (chassis_path, node_path) if path]
        if not targets:
            logger.warning(f"[DISABLE] Could not find resource with ID={resource_id} in any collection")
            return

        for target_path in targets:
            response = requests.get(f"{server_url}{target_path}", timeout=5)
            if response.status_code != 200:
                logger.warning(f"[DISABLE] Failed to fetch {target_path}: {response.status_code}")
                continue

            resource = response.json()
            logger.info(f"[DISABLE] Disabling resource tree from {target_path}...")
            _disable_resource_tree(resource, target_path, resource_id, logger, server_url)

        logger.info(f"[DISABLE] Successfully disabled resources for {resource_id}")

    except Exception as e:
        logger.error(f"[DISABLE] Error disabling resources: {e}", exc_info=True)


def re_enable_resources(port: str, resource_id: str, resource_path: str, logger, server_url: str = "http://localhost:8000"):
    """
    Re-enable Redfish resources for a reconnected endpoint by setting State to Enabled.
    Search from top-level collections (Chassis, AutomationNodes) for the resource with matching ID.
    Then recursively enable the resource tree.
    """
    logger.info(f"[ENABLE] Starting for resource_id={resource_id}, port={port}...")
    
    try:
        # Find matches in both collections so we can update both trees when IDs overlap.
        logger.info(f"[ENABLE] Searching Chassis collection for ID={resource_id}...")
        chassis_path = _find_resource_in_collection(f"{server_url}/redfish/v1/Chassis", resource_id, logger, server_url)
        if chassis_path:
            logger.info(f"[ENABLE] Found Chassis at {chassis_path}")

        logger.info(f"[ENABLE] Searching AutomationNodes collection for ID={resource_id}...")
        node_path = _find_resource_in_collection(f"{server_url}/redfish/v1/AutomationNodes", resource_id, logger, server_url)
        if node_path:
            logger.info(f"[ENABLE] Found AutomationNode at {node_path}")

        targets = [path for path in (chassis_path, node_path) if path]
        if not targets:
            logger.warning(f"[ENABLE] Could not find resource with ID={resource_id} in any collection")
            return

        for target_path in targets:
            response = requests.get(f"{server_url}{target_path}", timeout=5)
            if response.status_code != 200:
                logger.warning(f"[ENABLE] Failed to fetch {target_path}: {response.status_code}")
                continue

            resource = response.json()
            logger.info(f"[ENABLE] Enabling resource tree from {target_path}...")
            _enable_resource_tree(resource, target_path, resource_id, logger, server_url)

        logger.info(f"[ENABLE] Successfully re-enabled resources for {resource_id}")

    except Exception as e:
        logger.error(f"[ENABLE] Error re-enabling resources: {e}", exc_info=True)


def _find_resource_in_collection(collection_url: str, resource_id: str, logger, server_url: str) -> Optional[str]:
    """
    Search a collection for a resource with the given ID.
    Returns the full path to the resource, or None if not found.
    """
    try:
        logger.debug(f"[FIND] Fetching collection: {collection_url}")
        response = requests.get(collection_url, timeout=5)
        
        if response.status_code != 200:
            logger.debug(f"[FIND] Collection not accessible: {response.status_code}")
            return None
        
        collection = response.json()
        members = collection.get("Members", [])
        
        logger.debug(f"[FIND] Collection has {len(members)} members")
        
        for member in members:
            if isinstance(member, dict) and "@odata.id" in member:
                member_path = member["@odata.id"]
                logger.debug(f"[FIND] Checking member: {member_path}")
                
                try:
                    member_response = requests.get(f"{server_url}{member_path}", timeout=5)
                    if member_response.status_code == 200:
                        member_data = member_response.json()
                        member_id = member_data.get("Id")
                        
                        if member_id == resource_id:
                            logger.info(f"[FIND] ✓ Found resource ID={resource_id} at {member_path}")
                            return member_path
                except Exception as e:
                    logger.debug(f"[FIND] Error checking {member_path}: {e}")
        
        logger.debug(f"[FIND] Resource ID={resource_id} not found in collection")
        return None
        
    except Exception as e:
        logger.error(f"[FIND] Error searching collection: {e}")
        return None


def _disable_resource_tree(resource: dict, resource_path: str, resource_id: str, logger, server_url: str):
    """
    Recursively disable a resource tree by setting all State fields to UnavailableOffline.
    """
    # Set State on this resource
    if "Status" in resource and isinstance(resource["Status"], dict) and "State" in resource["Status"]:
        _set_resource_state(resource_path, "UnavailableOffline", logger, server_url)
        logger.debug(f"  Disabled {resource_path}")
    
    # Traverse collections
    collections_to_visit = {
        "Sensors": "Sensor.#",
        "Controls": "Control.#",
        "Assemblies": "Assembly.#",
        "AutomationInstrumentation": "AutomationInstrumentation.#",
        "Instrumentation": "AutomationInstrumentation.#"
    }
    
    for collection_name, item_type in collections_to_visit.items():
        if collection_name in resource:
            collection_data = resource[collection_name]
            
            # Handle reference (with @odata.id)
            if isinstance(collection_data, dict) and "@odata.id" in collection_data:
                collection_path = collection_data["@odata.id"]
                if collection_name in ("AutomationInstrumentation", "Instrumentation"):
                    member_response = requests.get(f"{server_url}{collection_path}", timeout=5)
                    if member_response.status_code == 200:
                        member_data = member_response.json()
                        _disable_resource_tree(member_data, collection_path, resource_id, logger, server_url)
                else:
                    _disable_collection(collection_path, resource_id, logger, server_url)
            
            # Handle inline collection
            elif isinstance(collection_data, dict) and "Members" in collection_data:
                for member in collection_data.get("Members", []):
                    if isinstance(member, dict) and "@odata.id" in member:
                        _disable_resource_tree(member, member["@odata.id"], resource_id, logger, server_url)


def _enable_resource_tree(resource: dict, resource_path: str, resource_id: str, logger, server_url: str):
    """
    Recursively enable a resource tree by setting all State fields to Enabled.
    """
    # Set State on this resource
    if "Status" in resource and isinstance(resource["Status"], dict) and "State" in resource["Status"]:
        _set_resource_state(resource_path, "Enabled", logger, server_url)
        logger.debug(f"  Enabled {resource_path}")
    
    # Traverse collections
    collections_to_visit = {
        "Sensors": "Sensor.#",
        "Controls": "Control.#",
        "Assemblies": "Assembly.#",
        "AutomationInstrumentation": "AutomationInstrumentation.#",
        "Instrumentation": "AutomationInstrumentation.#"
    }
    
    for collection_name, item_type in collections_to_visit.items():
        if collection_name in resource:
            collection_data = resource[collection_name]
            
            # Handle reference (with @odata.id)
            if isinstance(collection_data, dict) and "@odata.id" in collection_data:
                collection_path = collection_data["@odata.id"]
                if collection_name in ("AutomationInstrumentation", "Instrumentation"):
                    member_response = requests.get(f"{server_url}{collection_path}", timeout=5)
                    if member_response.status_code == 200:
                        member_data = member_response.json()
                        _enable_resource_tree(member_data, collection_path, resource_id, logger, server_url)
                else:
                    _enable_collection(collection_path, resource_id, logger, server_url)
            
            # Handle inline collection
            elif isinstance(collection_data, dict) and "Members" in collection_data:
                for member in collection_data.get("Members", []):
                    if isinstance(member, dict) and "@odata.id" in member:
                        _enable_resource_tree(member, member["@odata.id"], resource_id, logger, server_url)


def _disable_collection(collection_path: str, resource_id: str, logger, server_url: str):
    """Recursively disable all members of a collection."""
    try:
        response = requests.get(f"{server_url}{collection_path}", timeout=5)
        if response.status_code != 200:
            logger.debug(f"  Could not fetch collection {collection_path}: {response.status_code}")
            return
        
        collection = response.json()
        for member in collection.get("Members", []):
            if isinstance(member, dict) and "@odata.id" in member:
                member_path = member["@odata.id"]
                member_response = requests.get(f"{server_url}{member_path}", timeout=5)
                if member_response.status_code == 200:
                    member_data = member_response.json()
                    if "Status" in member_data and isinstance(member_data["Status"], dict) and "State" in member_data["Status"]:
                        _set_resource_state(member_path, "UnavailableOffline", logger, server_url)
                        logger.debug(f"  Disabled {member_path}")
    except Exception as e:
        logger.debug(f"  Error processing collection {collection_path}: {e}")


def _enable_collection(collection_path: str, resource_id: str, logger, server_url: str):
    """Recursively enable all members of a collection."""
    try:
        response = requests.get(f"{server_url}{collection_path}", timeout=5)
        if response.status_code != 200:
            logger.debug(f"  Could not fetch collection {collection_path}: {response.status_code}")
            return
        
        collection = response.json()
        for member in collection.get("Members", []):
            if isinstance(member, dict) and "@odata.id" in member:
                member_path = member["@odata.id"]
                member_response = requests.get(f"{server_url}{member_path}", timeout=5)
                if member_response.status_code == 200:
                    member_data = member_response.json()
                    if "Status" in member_data and isinstance(member_data["Status"], dict) and "State" in member_data["Status"]:
                        _set_resource_state(member_path, "Enabled", logger, server_url)
                        logger.debug(f"  Enabled {member_path}")
    except Exception as e:
        logger.debug(f"  Error processing collection {collection_path}: {e}")


def _set_resource_state(resource_path: str, state: str, logger, server_url: str):
    """PATCH a resource to set its Status.State field."""
    try:
        payload = {"Status": {"State": state}}
        full_url = f"{server_url}{resource_path}"
        logger.debug(f"[PATCH] {full_url} → State={state}")
        
        response = requests.patch(
            full_url,
            json=payload,
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in (200, 204):
            logger.info(f"[PATCH] {resource_path}: State={state} ✓")
        else:
            logger.warning(f"[PATCH] {resource_path}: status {response.status_code}, response: {response.text[:200]}")
    except Exception as e:
        logger.error(f"[PATCH] Error patching {resource_path}: {e}")


async def run_agent(config: ConfigManager, logger):
    """Run the runtime agent monitoring loop (async)."""
    logger.info("Starting runtime agent...")
    
    poll_interval = config.getint('agent', 'poll_interval', 2)
    pdr_file = Path(config.get('configurator', 'pdr_output', '/tmp/pdr_and_fru_records.json'))
    
    logger.info(f"Poll interval: {poll_interval}s")
    logger.info(f"PDR file: {pdr_file}")
    
    # Set up graceful shutdown
    shutdown = GracefulShutdown(logger)
    logger.info(f"GracefulShutdown initialized")
    
    # Initialize USB monitor
    monitor = USBPortMonitor(logger)
    logger.info(f"USBPortMonitor initialized")
    
    known_endpoints = monitor.load_pdr_endpoints(pdr_file)
    logger.info(f"Loaded endpoints from PDR")
    
    if known_endpoints:
        logger.info(f"Loaded {len(known_endpoints)} known endpoints from PDR")
        for bus_port, ep_data in known_endpoints.items():
            fru_info = f"({len(ep_data.get('fru_data', b''))} bytes FRU)" if ep_data.get('fru_data') else "(no FRU)"
            resource_id = ep_data.get('resource_id', 'unknown')
            logger.debug(f"  - {bus_port}: {ep_data.get('device', 'unknown')} → {resource_id} {fru_info}")
    else:
        logger.warning("No endpoints loaded from PDR - run configurator first")
    
    poll_count = 0
    port_state = {}  # Track state: {"1-2": "connected", "1-3": "disconnected"}
    
    logger.info("Entering main polling loop...")
    logger.info(f"GracefulShutdown object: {shutdown}")
    logger.info(f"is_running() = {shutdown.is_running()}")
    
    loop_iteration = 0
    while shutdown.is_running():
        loop_iteration += 1
        logger.info(f"=== LOOP ITERATION {loop_iteration} ===")
        try:
            poll_count += 1
            logger.debug(f"Poll #{poll_count}: checking USB topology...")
            
            # Detect USB topology changes
            changes_result = monitor.detect_changes(known_endpoints)
            logger.debug(f"detect_changes returned: {changes_result}")
            added, removed = changes_result
            
            # Get server URL from config
            server_host = config.get('server', 'host', 'localhost')
            server_port = config.get('server', 'port', '8000')
            server_url = f"http://{server_host}:{server_port}"
            logger.debug(f"Server URL: {server_url}")
            
            # Process added ports with async FRU matching
            if added:
                logger.info(f"Processing {len(added)} added port(s): {added}")
                matching_tasks = []
                for port in added:
                    logger.info(f"USB port added: {port}")
                    matching_tasks.append(monitor.match_endpoint_by_fru(port, known_endpoints))

                # Run all FRU matches concurrently
                if matching_tasks:
                    try:
                        logger.debug(f"Spawning {len(matching_tasks)} FRU match task(s)...")
                        matches = await asyncio.gather(*matching_tasks)
                        logger.debug(f"FRU matching completed: {matches}")

                        for port, matched_endpoint in zip(added, matches):
                            if matched_endpoint:
                                ep_data = known_endpoints[matched_endpoint]
                                resource_id = ep_data.get('resource_id', 'unknown')
                                resource_path = ep_data.get('resource_path', '')
                                logger.info(f"  → Recognized as {matched_endpoint} ({resource_id}), re-enabling resources")
                                re_enable_resources(matched_endpoint, resource_id, resource_path, logger, server_url)
                                port_state[matched_endpoint] = "connected"
                            else:
                                logger.debug(f"  → Unknown device, ignoring")
                    except Exception as e:
                        logger.error(f"Error during FRU matching: {e}", exc_info=True)
            
            if removed:
                for port in removed:
                    logger.info(f"USB port removed: {port}")
                    
                    # Disable resources for known endpoints
                    if port in known_endpoints:
                        ep_data = known_endpoints[port]
                        resource_id = ep_data.get('resource_id', 'unknown')
                        resource_path = ep_data.get('resource_path', '')
                        logger.info(f"  → Known endpoint disconnected ({resource_id}), disabling resources")
                        disable_resources(port, resource_id, resource_path, logger, server_url)
                        port_state[port] = "disconnected"
                    else:
                        logger.debug(f"  → Unknown port, no action needed")
            
            # Periodic status
            if poll_count % max(1, 10 // poll_interval) == 0:  # Every ~10 seconds
                connected = monitor.connected_ports
                logger.info(f"Agent status: {len(connected)} USB ports connected")
                if port_state:
                    logger.debug(f"  Port states: {port_state}")
            
            logger.debug(f"Poll #{poll_count}: sleeping for {poll_interval}s...")
            await asyncio.sleep(poll_interval)
            logger.debug(f"Poll #{poll_count}: woke up, continuing...")
        
        except Exception as e:
            logger.error(f"Error in poll loop: {e}", exc_info=True)
            logger.info("Continuing despite error...")
            await asyncio.sleep(poll_interval)
    
    logger.info("While loop exited, shutdown.is_running() is now False")
    logger.info("Agent stopped gracefully")
    return True


def main():
    """Main entry point for runtime_agent.py."""
    try:
        print("[MAIN] Starting...", file=sys.stderr, flush=True)
        
        # Load config
        demo_root = Path(__file__).parents[1]
        config_path = demo_root / 'configs' / 'demo.ini'
        print(f"[MAIN] Config path: {config_path}", file=sys.stderr, flush=True)
        
        config = ConfigManager(config_path)
        config.load()
        print(f"[MAIN] Config loaded", file=sys.stderr, flush=True)
        
        # Set up logging
        log_level = config.get('logging', 'log_level', 'INFO')
        log_dir = config.get('logging', 'log_dir', str(demo_root / 'logs'))
        print(f"[MAIN] Log level: {log_level}, dir: {log_dir}", file=sys.stderr, flush=True)
        
        log_mgr = LogManager('runtime_agent', log_dir, log_level)
        logger = log_mgr.get_logger()
        
        logger.info("=" * 60)
        logger.info("Runtime Agent - USB Port & Resource Monitor (Async)")
        logger.info("=" * 60)
        logger.info("Starting...")
        print("[MAIN] About to run asyncio.run()...", file=sys.stderr, flush=True)
        
        # Run agent
        aio_result = asyncio.run(run_agent(config, logger))
        logger.info(f"asyncio.run returned: {aio_result}")
        print(f"[MAIN] asyncio.run returned: {aio_result}", file=sys.stderr, flush=True)
        
    except KeyboardInterrupt as e:
        print("[MAIN] Agent terminated by user", file=sys.stderr, flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[MAIN] FATAL ERROR: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    
    print("[MAIN] Exiting normally", file=sys.stderr, flush=True)
    sys.exit(0)


if __name__ == '__main__':
    main()
