#!/usr/bin/env python3
"""
Part 2: Configurator - detects devices via PLDM and generates Redfish mockup.
"""
import os
import sys
import subprocess
from pathlib import Path
from shared import ConfigManager, LogManager, ProcessManager, GracefulShutdown


def run_configurator(config: ConfigManager, logger):
    """Run device collection and mockup generation."""
    logger.info("Starting configurator (scan + generate mockup)...")
    
    # Paths
    repo_root = Path(__file__).parents[2]
    cli_script = repo_root / 'tools' / 'pldm-mapping-wizard' / 'pldm_mapping_wizard' / 'cli.py'
    
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
        tools_dir = repo_root / 'tools' / 'pldm-mapping-wizard'
        env['PYTHONPATH'] = str(tools_dir) + ':' + env.get('PYTHONPATH', '')
        
        result = subprocess.run(cmd, cwd=repo_root, capture_output=False, text=True, env=env)
        if result.returncode == 0:
            logger.info("Configurator completed successfully")
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
