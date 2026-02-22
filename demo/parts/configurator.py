#!/usr/bin/env python3
"""
Part 2: Configurator - detects devices via PLDM and generates Redfish mockup.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from shared import ConfigManager, LogManager, ProcessManager, GracefulShutdown


def add_resource_ids(pdr_file: Path, mockup_dir: Path, logger):
    """
    Post-process PDR JSON to add resource_id mapping for each endpoint.
    resource_id will be the Redfish resource ID from the generated mockup.
    """
    if not pdr_file.exists():
        logger.warning(f"PDR file not found: {pdr_file}")
        return False
    
    if not mockup_dir.exists():
        logger.warning(f"Mockup dir not found: {mockup_dir}")
        return False
    
    try:
        data = json.loads(pdr_file.read_text())
        
        if not isinstance(data, dict) or 'endpoints' not in data:
            logger.error("Invalid PDR format: missing 'endpoints' key")
            return False
        
        # Load AutomationNodes from mockup to map to endpoints
        automation_nodes_dir = mockup_dir / 'redfish' / 'v1' / 'AutomationNodes'
        automation_nodes = {}
        
        if automation_nodes_dir.exists():
            for node_dir in sorted(automation_nodes_dir.iterdir()):
                if node_dir.is_dir():
                    index_file = node_dir / 'index.json'
                    if index_file.exists():
                        try:
                            node_data = json.loads(index_file.read_text())
                            node_id = node_data.get('Id', node_dir.name)
                            automation_nodes[node_id] = {
                                'path': f"/redfish/v1/AutomationNodes/{node_id}",
                                'name': node_data.get('Name', ''),
                                'type': node_data.get('NodeType', 'Unknown')
                            }
                            logger.debug(f"Found AutomationNode {node_id}: {automation_nodes[node_id]}")
                        except Exception as e:
                            logger.debug(f"Failed to parse {index_file}: {e}")
        
        # Build a chassis -> FRU lookup so we can match endpoints by Serial/Model
        chassis_dir = mockup_dir / 'redfish' / 'v1' / 'Chassis'
        chassis_fru_map = {}  # maps serial -> resource_id, and model -> list(resource_id)
        if chassis_dir.exists():
            for ch in chassis_dir.iterdir():
                if not ch.is_dir():
                    continue
                try:
                    idx = ch / 'Assembly' / 'index.json'
                    ch_info = {}
                    # Primary source: Chassis index (may contain SerialNumber/Model)
                    main_idx = ch / 'index.json'
                    if main_idx.exists():
                        try:
                            main = json.loads(main_idx.read_text())
                            if isinstance(main, dict):
                                if 'SerialNumber' in main:
                                    ch_info['serial'] = main.get('SerialNumber')
                                if 'Model' in main:
                                    ch_info['model'] = main.get('Model')
                        except Exception:
                            pass
                    # Assembly may contain richer FRU fields
                    if idx.exists():
                        try:
                            asm = json.loads(idx.read_text())
                            if isinstance(asm, dict):
                                members = asm.get('Assemblies', [])
                                if isinstance(members, list) and members:
                                    entry = members[0]
                                    if 'SerialNumber' in entry:
                                        ch_info['serial'] = entry.get('SerialNumber')
                                    if 'Model' in entry:
                                        ch_info['model'] = entry.get('Model')
                        except Exception:
                            pass

                    if ch_info:
                        rid = ch.name
                        serial = ch_info.get('serial')
                        model = ch_info.get('model')
                        if serial:
                            chassis_fru_map.setdefault('serial', {})[str(serial)] = rid
                        if model:
                            chassis_fru_map.setdefault('model', {}).setdefault(str(model), []).append(rid)
                except Exception:
                    continue

        def _extract_fru_fields(endpoint: dict) -> dict:
            """Extract simple FRU fields (SerialNumber, Model) from endpoint fru_records."""
            out = {}
            try:
                fru_sets = endpoint.get('fru_records') or []
                for rec in fru_sets:
                    parsed = rec.get('parsed_records') if isinstance(rec, dict) else None
                    if not isinstance(parsed, list):
                        continue
                    for pr in parsed:
                        fields = pr.get('fields', [])
                        for f in fields:
                            name = f.get('typeName')
                            val = f.get('value')
                            if not name or val is None:
                                continue
                            if name in ('Serial', 'Serial Number', 'SerialNumber') and 'serial' not in out:
                                out['serial'] = str(val)
                            if name == 'Model' and 'model' not in out:
                                out['model'] = str(val)
            except Exception:
                pass
            return out

        # Add resource_id to each endpoint, preferring FRU-based matching
        node_ids = sorted(automation_nodes.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        for i, endpoint in enumerate(data['endpoints']):
            device_path = endpoint.get('dev', f'unknown_{i}')
            fru_fields = _extract_fru_fields(endpoint)

            matched = None
            # First: match by serial number against chassis map
            serial = fru_fields.get('serial')
            if serial and 'serial' in chassis_fru_map and serial in chassis_fru_map['serial']:
                matched = chassis_fru_map['serial'][serial]

            # Next: match by exact model if serial not found
            if not matched:
                model = fru_fields.get('model')
                if model and 'model' in chassis_fru_map and model in chassis_fru_map['model']:
                    # If multiple chassis share same model, prefer positional mapping by index
                    candidates = chassis_fru_map['model'][model]
                    if len(candidates) == 1:
                        matched = candidates[0]
                    else:
                        # try to pick candidate by position if available
                        if i < len(candidates):
                            matched = candidates[i]

            # If we found a match, assign it
            if matched:
                resource_id = matched
                endpoint['resource_id'] = resource_id
                endpoint['resource_path'] = f"/redfish/v1/AutomationNodes/{resource_id}"
                logger.info(f"Mapped endpoint {device_path} → {resource_id} (matched by FRU)")
                continue

            # Fallback: Try to match by AutomationNodes index order
            if i < len(node_ids):
                resource_id = node_ids[i]
                endpoint['resource_id'] = resource_id
                endpoint['resource_path'] = automation_nodes[resource_id]['path']
                logger.info(f"Mapped endpoint {device_path} → {resource_id} ({automation_nodes[resource_id]['type']})")
            else:
                # Final fallback: use device name
                device_name = Path(device_path).name
                endpoint['resource_id'] = f"Device_{device_name}"
                logger.warning(f"No AutomationNode available for endpoint {device_path}, using: {endpoint['resource_id']}")
        
        # Write back to file
        pdr_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Added resource_id mappings to {len(data['endpoints'])} endpoints")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add resource_ids: {e}", exc_info=True)
        return False


def run_configurator(config: ConfigManager, logger):
    """Run device collection and mockup generation."""
    logger.info("Starting configurator (scan + generate mockup)...")
    
    # Paths
    demo_root = Path(__file__).parents[1]
    cli_script = demo_root / 'pldm_tools' / 'pldm_mapping_wizard' / 'cli.py'
    
    if not cli_script.exists():
        logger.error(f"CLI script not found: {cli_script}")
        return False
    
    # Config values
    pdr_output = config.get('configurator', 'pdr_output', '/tmp/pdr_and_fru_records.json')
    dest_mockup = config.get('configurator', 'dest_mockup', '/tmp/generated_mockup')
    auto_select = config.getbool('configurator', 'auto_select', True)
    
    logger.info(f"PDR output: {pdr_output}")
    logger.info(f"Destination mockup: {dest_mockup}")
    logger.info(f"Auto-select devices: {auto_select}")
    
    # Build command
    cmd = [
        sys.executable,
        str(cli_script),
        'scan-and-generate',
        '-c', pdr_output,
        '-d', dest_mockup,
    ]
    
    if auto_select:
        cmd.append('--auto-select')
    else:
        cmd.append('--no-auto-select')
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        # Set up environment with PYTHONPATH to find pldm_mapping_wizard module
        env = os.environ.copy()
        tools_dir = demo_root / 'pldm_tools'
        env['PYTHONPATH'] = str(tools_dir) + ':' + env.get('PYTHONPATH', '')
        
        result = subprocess.run(cmd, cwd=demo_root, capture_output=False, text=True, env=env)
        if result.returncode == 0:
            logger.info("Configurator completed successfully")
            
            # Post-process: add resource_id mappings to PDR
            pdr_path = Path(pdr_output)
            mockup_path = Path(dest_mockup)
            if add_resource_ids(pdr_path, mockup_path, logger):
                logger.info(f"Resource ID mapping added to {pdr_output}")
            
            return True
        else:
            logger.error(f"Configurator failed with exit code {result.returncode}")
            return False
    except Exception as e:
        logger.error(f"Failed to run configurator: {e}", exc_info=True)
        return False


def main():
    """Main entry point for configurator.py."""
    # Load config
    demo_root = Path(__file__).parents[1]
    config_path = demo_root / 'configs' / 'demo.ini'
    config = ConfigManager(config_path)
    config.load()
    
    # Set up logging
    log_level = config.get('logging', 'log_level', 'INFO')
    log_dir = config.get('logging', 'log_dir', str(demo_root / 'logs'))
    log_mgr = LogManager('configurator', log_dir, log_level)
    logger = log_mgr.get_logger()
    
    logger.info("=" * 60)
    logger.info("Configurator - Device Discovery & Mockup Generation")
    logger.info("=" * 60)
    
    # Run configurator
    success = run_configurator(config, logger)
    
    if success:
        logger.info("Configuration complete - mockup is ready")
        logger.info("You can now start the Redfish Mockup Server")
    
    logger.info("Configurator terminated")
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
