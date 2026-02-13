#!/usr/bin/env python3
"""
Part 3: Runtime Agent - monitors and manages the automation system.
"""
import sys
import time
from pathlib import Path
from shared import ConfigManager, LogManager, ProcessManager, GracefulShutdown


def run_agent(config: ConfigManager, logger):
    """Run the runtime agent."""
    logger.info("Starting runtime agent...")
    
    poll_interval = config.getint('agent', 'poll_interval', 5)
    server_host = config.get('server', 'host', '127.0.0.1')
    server_port = config.getint('server', 'port', 8000)
    
    logger.info(f"Poll interval: {poll_interval}s")
    logger.info(f"Server endpoint: {server_host}:{server_port}")
    
    # Set up graceful shutdown
    shutdown = GracefulShutdown(logger)
    
    poll_count = 0
    
    try:
        while shutdown.is_running():
            poll_count += 1
            logger.debug(f"Poll #{poll_count} - checking system state...")
            
            # In a real agent, this would:
            # - Query the Redfish server for system state
            # - Execute automation rules
            # - Manage device state transitions
            # - Handle errors and edge cases
            
            # For now, just log that we're alive
            logger.info(f"Agent alive (Poll #{poll_count})")
            
            time.sleep(poll_interval)
        
        logger.info("Agent stopped gracefully")
        return True
        
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
        return True
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return False


def main():
    """Main entry point for runtime_agent.py."""
    # Load config
    demo_root = Path(__file__).parents[1]
    config_path = demo_root / 'configs' / 'demo.ini'
    config = ConfigManager(config_path)
    config.load()
    
    # Set up logging
    log_level = config.get('logging', 'log_level', 'INFO')
    log_dir = config.get('logging', 'log_dir', str(demo_root / 'logs'))
    log_mgr = LogManager('runtime_agent', log_dir, log_level)
    logger = log_mgr.get_logger()
    
    logger.info("=" * 60)
    logger.info("Runtime Agent - System Monitor & Manager")
    logger.info("=" * 60)
    
    # Run agent
    success = run_agent(config, logger)
    
    logger.info("Runtime Agent terminated")
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
