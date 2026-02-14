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
        
        # Add resource_id to each endpoint
        for i, endpoint in enumerate(data['endpoints']):
            device_path = endpoint.get('dev', f'unknown_{i}')
            
            # Try to match endpoint to an AutomationNode
            # Simple heuristic: use sequential ID if available
            node_ids = sorted(automation_nodes.keys(), key=lambda x: int(x) if x.isdigit() else 999)
            
            if i < len(node_ids):
                resource_id = node_ids[i]
                endpoint['resource_id'] = resource_id
                endpoint['resource_path'] = automation_nodes[resource_id]['path']
                logger.info(f"Mapped endpoint {device_path} → {resource_id} ({automation_nodes[resource_id]['type']})")
            else:
                # Fallback: use device name
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
