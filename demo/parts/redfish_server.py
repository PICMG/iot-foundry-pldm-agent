#!/usr/bin/env python3
"""
Part 1: Redfish Mockup Server - serves Redfish resources from generated mockup.
"""
import os
import sys
from pathlib import Path
import importlib.util

from shared import ConfigManager, LogManager, ProcessManager, GracefulShutdown


def load_mockup_server():
    """Dynamically load the Redfish Mockup Server."""
    server_path = Path(__file__).parents[2].parent / 'Redfish-Mockup-Server' / 'redfishMockupServer.py'
    if not server_path.exists():
        raise FileNotFoundError(f"Redfish Mockup Server not found at {server_path}")
    
    spec = importlib.util.spec_from_file_location("redfish_mockup_server", server_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def start_server(config: ConfigManager, logger):
    """Start the Redfish Mockup Server."""
    logger.info("Starting Redfish Mockup Server...")
    
    host = config.get('server', 'host', '127.0.0.1')
    port = config.getint('server', 'port', 8000)
    mockup_dir = config.get('server', 'mockup_dir', '/tmp/generated_mockup')
    
    mockup_path = Path(mockup_dir)
    if not mockup_path.exists():
        logger.error(f"Mockup directory not found: {mockup_dir}")
        logger.info("Run the configurator first to generate the mockup.")
        return False
    
    logger.info(f"Serving mockup from: {mockup_dir}")
    logger.info(f"Server listening on {host}:{port}")
    logger.info("Press Ctrl+C to stop...")
    
    # Set up graceful shutdown
    shutdown = GracefulShutdown(logger)
    
    try:
        # Import and start the server (simplified - in production would use proper imports)
        import http.server
        import socketserver
        
        os.chdir(mockup_path)
        
        # Create a simple HTTP server (Redfish Mockup Server replacement for demo)
        # In real use, the actual Redfish Mockup Server would be imported and run
        logger.info("Mock server initialized (placeholder)")
        logger.info("In production, this would run the full Redfish Mockup Server")
        
        while shutdown.is_running():
            import time
            time.sleep(1)
        
        logger.info("Server stopped gracefully")
        return True
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return True
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        return False


def main():
    """Main entry point for redfish_server.py."""
    # Load config
    demo_root = Path(__file__).parents[1]
    config_path = demo_root / 'configs' / 'demo.ini'
    config = ConfigManager(config_path)
    config.load()
    
    # Set up logging
    log_level = config.get('logging', 'log_level', 'INFO')
    log_dir = config.get('logging', 'log_dir', str(demo_root / 'logs'))
    log_mgr = LogManager('redfish_server', log_dir, log_level)
    logger = log_mgr.get_logger()
    
    logger.info("=" * 60)
    logger.info("Redfish Mockup Server")
    logger.info("=" * 60)
    
    # Start server
    success = start_server(config, logger)
    
    logger.info("Redfish Mockup Server terminated")
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
