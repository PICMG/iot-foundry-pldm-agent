#!/usr/bin/env python3
"""
Shared utilities for demo parts: config, logging, process management.
"""
import os
import sys
import json
import signal
import logging
import subprocess
from pathlib import Path
from configparser import ConfigParser
from typing import Optional, Dict, Any


class ConfigManager:
    """Manages demo configuration from INI file."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = ConfigParser()
        self.repo_root = Path(__file__).parents[2]
        self.demo_root = Path(__file__).parents[1]
        
    def load(self) -> ConfigParser:
        """Load and interpolate config file."""
        self.config.read(self.config_path)
        
        # Add default interpolation values (DEFAULT section always exists in ConfigParser)
        self.config.set('DEFAULT', 'REPO_ROOT', str(self.repo_root))
        self.config.set('DEFAULT', 'DEMO_ROOT', str(self.demo_root))
        
        return self.config
    
    def get(self, section: str, key: str, fallback: Optional[str] = None) -> str:
        """Get config value with fallback."""
        try:
            return self.config.get(section, key)
        except Exception:
            return fallback if fallback else ""
    
    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Get integer config value."""
        try:
            return self.config.getint(section, key)
        except Exception:
            return fallback
    
    def getbool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get boolean config value."""
        try:
            return self.config.getboolean(section, key)
        except Exception:
            return fallback


class LogManager:
    """Manages logging for all demo parts."""
    
    def __init__(self, name: str, log_dir: Path, level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # File handler
        fh = logging.FileHandler(self.log_dir / f"{name}.log")
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def get_logger(self) -> logging.Logger:
        """Get configured logger."""
        return self.logger


class ProcessManager:
    """Manages process state and lifecycle."""
    
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "demo_state.json"
    
    def get_state(self) -> Dict[str, Any]:
        """Load current state."""
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {}
    
    def save_state(self, state: Dict[str, Any]):
        """Save state to file."""
        self.state_file.write_text(json.dumps(state, indent=2))
    
    def set_running(self, name: str, pid: int):
        """Mark process as running."""
        state = self.get_state()
        state[name] = {"running": True, "pid": pid}
        self.save_state(state)
    
    def set_stopped(self, name: str):
        """Mark process as stopped."""
        state = self.get_state()
        if name in state:
            state[name]["running"] = False
        self.save_state(state)
    
    def is_running(self, name: str) -> bool:
        """Check if process is running."""
        state = self.get_state()
        if name not in state:
            return False
        
        pid = state[name].get("pid")
        if not pid:
            return False
        
        try:
            os.kill(pid, 0)  # Check if process exists
            return state[name].get("running", False)
        except (OSError, ProcessLookupError):
            return False
    
    def get_pid(self, name: str) -> Optional[int]:
        """Get process PID."""
        state = self.get_state()
        return state.get(name, {}).get("pid")
    
    def stop_process(self, name: str, logger: logging.Logger):
        """Stop a running process gracefully."""
        pid = self.get_pid(name)
        if not pid:
            logger.warning(f"No PID found for {name}")
            return
        
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to {name} (PID {pid})")
            self.set_stopped(name)
        except ProcessLookupError:
            logger.warning(f"Process {name} (PID {pid}) not found")
            self.set_stopped(name)
        except Exception as e:
            logger.error(f"Failed to stop {name}: {e}")


class GracefulShutdown:
    """Handle graceful shutdown on signals."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.running = True
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle termination signals."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name}, gracefully shutting down...")
        self.running = False
    
    def is_running(self) -> bool:
        """Check if should continue running."""
        return self.running


def run_command(cmd: list, logger: logging.Logger, cwd: Optional[Path] = None) -> int:
    """Run external command and return exit code."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=False, text=True)
        return result.returncode
    except Exception as e:
        logger.error(f"Failed to run command {cmd}: {e}")
        return 1
