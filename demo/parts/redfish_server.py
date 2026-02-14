#!/usr/bin/env python3
"""
Part 1: Redfish Mockup Server - serves Redfish resources from generated mockup.
Handles GET (static files) and PATCH (modify Status.State).
"""
import os
import sys
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from shared import ConfigManager, LogManager, ProcessManager, GracefulShutdown


class RedfishHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Redfish API."""
    
    # Class variables to share state
    mockup_dir = None
    logger = None
    shutdown = None
    
    def do_GET(self):
        """Handle GET requests - serve static JSON files."""
        # Parse the path
        parsed_path = urlparse(self.path)
        rel_path = parsed_path.path.lstrip('/')
        
        # Map to file path
        if rel_path == '' or rel_path == 'redfish/v1':
            file_path = self.mockup_dir / 'redfish' / 'v1' / 'index.json'
        else:
            file_path = self.mockup_dir / rel_path
        
        # Security: prevent path traversal
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(self.mockup_dir)):
                self.send_error(403, "Access denied")
                return
        except Exception as e:
            self.send_error(400, f"Invalid path: {e}")
            return
        
        # If path is a directory, serve index.json
        if file_path.is_dir():
            file_path = file_path / 'index.json'
        
        # Serve the file
        if file_path.exists() and file_path.is_file():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                self.logger.info(f"GET {self.path} → 200")
            except Exception as e:
                self.send_error(500, f"Error reading file: {e}")
                self.logger.error(f"GET {self.path} → 500: {e}")
        else:
            self.send_error(404, "Not found")
            self.logger.info(f"GET {self.path} → 404")
    
    def do_PATCH(self):
        """Handle PATCH requests - modify resource state."""
        # Parse the path
        parsed_path = urlparse(self.path)
        rel_path = parsed_path.path.lstrip('/')
        
        # Map to file path
        file_path = self.mockup_dir / rel_path
        if file_path.is_dir():
            file_path = file_path / 'index.json'
        
        try:
            # Security: prevent path traversal
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(self.mockup_dir)):
                self.send_error(403, "Access denied")
                return
            
            if not file_path.exists():
                self.send_error(404, "Not found")
                self.logger.info(f"PATCH {self.path} → 404")
                return
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Empty body")
                return
            
            body_data = self.rfile.read(content_length)
            patch_payload = json.loads(body_data.decode('utf-8'))
            
            # Read current resource
            with open(file_path, 'r') as f:
                resource = json.load(f)
            
            # Apply patch (simple merge for Status.State)
            if 'Status' in patch_payload:
                if 'Status' not in resource:
                    resource['Status'] = {}
                resource['Status'].update(patch_payload['Status'])
                self.logger.info(f"PATCH {self.path}: Updated Status.State → {patch_payload['Status'].get('State', '?')}")
            
            # Write back to file
            with open(file_path, 'w') as f:
                json.dump(resource, f, indent=2)
            
            # Return 200 OK
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"Status": resource.get("Status", {})}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            self.logger.info(f"PATCH {self.path} → 200 OK")
            
        except json.JSONDecodeError as e:
            self.send_error(400, f"Invalid JSON: {e}")
            self.logger.error(f"PATCH {self.path} → 400: {e}")
        except Exception as e:
            self.send_error(500, f"Error processing PATCH: {e}")
            self.logger.error(f"PATCH {self.path} → 500: {e}")
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass  # We're using our own logger


def start_server(config: ConfigManager, logger, shutdown):
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
    
    # Set class variables
    RedfishHandler.mockup_dir = mockup_path
    RedfishHandler.logger = logger
    RedfishHandler.shutdown = shutdown
    
    try:
        # Create and start HTTP server
        server_address = (host, port)
        httpd = HTTPServer(server_address, RedfishHandler)
        
        # Run server until shutdown signal
        while shutdown.is_running():
            httpd.handle_request()  # Handle one request at a time
        
        httpd.server_close()
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
    try:
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
        logger.info("Redfish Mockup Server - HTTP Handler")
        logger.info("=" * 60)
        
        # Set up graceful shutdown
        shutdown = GracefulShutdown(logger)
        
        # Start server
        success = start_server(config, logger, shutdown)
        
        logger.info("Redfish Mockup Server terminated")
        sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
