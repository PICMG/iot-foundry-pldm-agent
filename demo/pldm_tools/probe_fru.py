#!/usr/bin/env python3
"""Helper script to probe a serial device for PLDM FRU metadata.

Usage: probe_fru.py /dev/ttyUSB0

Exits 0 on success (metadata retrieved), 1 on failure, 2 on error.
"""
import sys
import importlib.util
from pathlib import Path


def load_export_module():
    path = Path(__file__).parent / 'export_pdrs_to_json.py'
    spec = importlib.util.spec_from_file_location('export_pdrs', str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    if len(sys.argv) < 2:
        print('Usage: probe_fru.py /dev/ttyUSB0', file=sys.stderr)
        return 2

    dev = sys.argv[1]
    timeout = 1

    try:
        mod = load_export_module()
        SerialPort = getattr(mod, 'SerialPort', None)
        # Try to import package SerialPort if available
        try:
            from pldm_mapping_wizard.serial_transport import SerialPort as SP
            SerialPort = SP
        except Exception:
            pass

        if not SerialPort:
            # Can't probe without serial port implementation
            return 2

        p = None
        try:
            p = SerialPort(dev, baudrate=115200, timeout=timeout)
            
            sys.stderr.write(f"PROBE: probing device {dev} with timeout {timeout}s\n")
            
            if not p.open():
                sys.stderr.write(f"PROBE: open failed for {dev}\n")
                return 3
            
            sys.stderr.write(f"PROBE: device {dev} opened successfully\n")
            
            # Get metadata (use existing stack which enforces FCS and PLDM type checks)
            metadata, ferr = mod.get_fru_record_table_metadata(p)
            sys.stderr.write(f"PROBE: metadata={metadata} ferr={ferr}\n")

            # Success if metadata parsed and no error
            if not ferr and metadata:
                try:
                    p.close()
                except Exception:
                    pass
                sys.stderr.write(f"PROBE: ok device={dev}\n")
                return 0

            try:
                p.close()
            except Exception:
                pass
            return 1
        except Exception as e:
            try:
                if p:
                    p.close()
            except Exception:
                pass
            sys.stderr.write(f"PROBE: error device={dev} exc={e}\n")
            return 2

    except Exception as e:
        sys.stderr.write(f"PROBE: loader error exc={e}\n")
        return 2


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
