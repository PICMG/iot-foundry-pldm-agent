#!/usr/bin/env python3
"""Enumerate serial endpoints, let user select devices and extract PDR/FRU from each.

Usage:
  python3 collect_endpoints.py

This script scans /dev for ttyUSB* and ttyACM* devices, prompts the user to
select which to query, then runs the extraction logic for each selected
endpoint and writes a JSON file `pdr_and_fru_records.json` with a top-level
`endpoints` array.
"""
import os
import sys
import glob
import json
import time
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
import importlib.util
from typing import List, Optional
import base64

console = Console()


def discover_devices() -> List[dict]:
    """Return list of candidate serial devices (ttyUSB* and ttyACM*).
    
    Note: pts devices can be added manually by entering their path directly.
    """
    devs = []

    # Add regular USB devices
    paths = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
    for p in paths:
        usb = get_usb_address(p)
        devs.append({'path': p, 'usb_addr': usb, 'valid': True})
    
    return devs


def get_usb_address(dev_path: str) -> Optional[dict]:
    """Resolve USB metadata from sysfs for the given tty device.

    Returns a dict with keys: busnum, devnum, idVendor, idProduct, serial,
    manufacturer, product, sysfs_path, and a short `usb_identifier` string.
    Returns None if not discoverable.
    """
    name = os.path.basename(dev_path)
    sys_tty = f'/sys/class/tty/{name}/device'
    if not os.path.exists(sys_tty):
        return None
    try:
        real = os.path.realpath(sys_tty)
        # Walk up directory tree to find a parent that contains idVendor (USB device)
        cur = real
        while cur and cur != '/' and os.path.exists(cur):
            if os.path.exists(os.path.join(cur, 'idVendor')):
                # Found USB device directory
                info = {}
                info['sysfs_path'] = cur
                def read_file(name):
                    try:
                        with open(os.path.join(cur, name), 'r') as f:
                            return f.read().strip()
                    except Exception:
                        return None

                info['idVendor'] = read_file('idVendor')
                info['idProduct'] = read_file('idProduct')
                info['serial'] = read_file('serial')
                info['manufacturer'] = read_file('manufacturer')
                info['product'] = read_file('product')
                # Bus/dev numbers may be under the device directory or the root usb bus
                info['busnum'] = read_file('busnum') or read_file(os.path.join('..', 'busnum'))
                info['devnum'] = read_file('devnum') or read_file(os.path.join('..', 'devnum'))
                # Normalize numeric fields
                try:
                    if info.get('busnum'):
                        info['busnum'] = int(info['busnum'])
                except Exception:
                    pass
                try:
                    if info.get('devnum'):
                        info['devnum'] = int(info['devnum'])
                except Exception:
                    pass

                # Construct a compact identifier that is stable across /dev renames
                vendor = info.get('idVendor') or '????'
                product = info.get('idProduct') or '????'
                bus = info.get('busnum') or ''
                dev = info.get('devnum') or ''
                usb_id = f"{vendor}:{product}"
                if bus or dev:
                    usb_id = f"{bus}-{dev} {usb_id}"
                info['usb_identifier'] = usb_id
                return info

            # Move up one directory
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    except Exception:
        return None
    return None


def load_export_module():
    """Dynamically load export_pdrs_to_json module for reuse of functions."""
    path = os.path.join(os.path.dirname(__file__), 'export_pdrs_to_json.py')
    spec = importlib.util.spec_from_file_location('export_pdrs', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@click.command()
@click.option('--output', '-o', default='pdr_and_fru_records.json', help='Output JSON file')
def main(output):
    try:
        devs = discover_devices()
        if not devs:
            console.print('[yellow]No /dev/ttyUSB* or /dev/ttyACM* devices found.[/yellow]')
            sel = click.prompt("Enter a custom device path like '/dev/pts/1', or 'none' to cancel", default='none')
        else:
            table = Table(title='Discovered serial endpoints')
            table.add_column('#', justify='right')
            table.add_column('Device')
            table.add_column('USB address', style='cyan')
            for i, d in enumerate(devs):
                usb = d.get('usb_addr')
                usb_display = '-'
                if isinstance(usb, dict):
                    usb_display = usb.get('usb_identifier') or usb.get('serial') or usb.get('product') or '-'
                elif usb:
                    usb_display = str(usb)
                table.add_row(str(i), d['path'], usb_display)
            console.print(table)

            sel = click.prompt("Select devices by index (comma separated), 'all' to select all, 'none' to cancel\n(or type a custom device path like '/dev/pts/1')", default='all')
        sel = sel.strip()
        
        selected = []
        
        if sel.lower() in ('none', 'n'):
            console.print('Cancelled.')
            return
        elif sel.lower() in ('all', 'a'):
            indices = list(range(len(devs)))
            selected = [devs[i] for i in indices]
        else:
            # Parse comma-separated list of indices and/or paths
            try:
                indices = []
                for part in sel.split(','):
                    part = part.strip()
                    
                    # Check if this part is a device path (starts with /)
                    if part.startswith('/'):
                        if os.path.exists(part):
                            selected.append({'path': part, 'usb_addr': get_usb_address(part), 'valid': True})
                        else:
                            console.print(f'[red]Device not found: {part}[/red]')
                            return
                    # Otherwise treat it as an index or range
                    else:
                        if '-' in part:
                            a, b = part.split('-', 1)
                            indices.extend(range(int(a), int(b) + 1))
                        elif part:
                            indices.append(int(part))
                
                # Add devices by index
                indices = sorted(set(i for i in indices if 0 <= i < len(devs)))
                selected.extend([devs[i] for i in indices])
            except Exception:
                console.print('[red]Invalid selection[/red]')
                return

        console.print(f'Processing {len(selected)} endpoints...')

        mod = load_export_module()
        SerialPort = None
        try:
            from pldm_mapping_wizard.serial_transport import SerialPort
        except Exception:
            # Fall back to module's SerialPort if package import fails
            SerialPort = getattr(mod, 'SerialPort', None)

        endpoints = []

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TimeElapsedColumn()) as progress:
            task = progress.add_task('Overall', total=len(selected))
            for dev in selected:
                desc = f"{dev['path']}"
                progress.start_task(task)
                subtask = progress.add_task(desc, total=1)
                ep = {'dev': dev['path'], 'usb_addr': dev.get('usb_addr'), 'pdr_records': [], 'fru_records': [], 'error': None}
                try:
                    port = SerialPort(dev['path'], baudrate=115200)
                    if not port.open():
                        ep['error'] = 'Failed to open port'
                        console.print(f"[red]Failed to open {dev['path']}[/red]")
                        endpoints.append(ep)
                        progress.update(subtask, advance=1)
                        progress.update(task, advance=1)
                        continue

                    # Retrieve PDRs
                    pdrs = []
                    handle = 0
                    max_pdrs = 500
                    for _ in range(max_pdrs):
                        mod.export_debug_log(f"[collect_endpoints] get_pdr: handle=0x{handle:08x}")
                        res, err = mod.get_pdr(port, handle)
                        if err:
                            mod.export_debug_log(f"[collect_endpoints] get_pdr ERROR: handle=0x{handle:08x}, err={err}")
                            # If no response for first handle, stop
                            if handle == 0:
                                mod.export_debug_log(f"[collect_endpoints] get_pdr: break on first handle error")
                                break
                            else:
                                mod.export_debug_log(f"[collect_endpoints] get_pdr: break on error, handle=0x{handle:08x}")
                                break
                        pdrs.append(res)
                        next_handle = res.get('next_handle', 0)
                        mod.export_debug_log(f"[collect_endpoints] get_pdr: handle=0x{handle:08x} -> next_handle=0x{next_handle:08x}")
                        handle = next_handle
                        if not handle:
                            mod.export_debug_log(f"[collect_endpoints] get_pdr: break, next_handle=0")
                            break
                    mod.export_debug_log(f"[collect_endpoints] get_pdr: total PDRs collected: {len(pdrs)}")

                    # Two-pass decode: first decode all OEM State Set PDRs to populate OEM_STATE_SET_VALUES
                    for r in pdrs:
                        pdr_data = r.get('pdr_data', b'')
                        if len(pdr_data) > 5 and pdr_data[5] == 8:  # OEM State Set PDR type
                            try:
                                mod.decode_oem_state_set_pdr(pdr_data)
                            except Exception as e:
                                mod.export_debug_log(f"[collect_endpoints] ERROR decoding OEM State Set PDR: handle=0x{r.get('handle'):08x}, error={e}")

                    # Second pass: decode all PDRs
                    decoded_pdrs = []
                    for r in pdrs:
                        handle = r.get('handle')
                        pdr_data = r.get('pdr_data', b'')
                        try:
                            mod.export_debug_log(f"[collect_endpoints] Decoding PDR: handle=0x{handle:08x}, len={len(pdr_data)}")
                            decoded = mod.decode_pdr(pdr_data)
                            mod.export_debug_log(f"[collect_endpoints] Decoded PDR: handle=0x{handle:08x}, type={pdr_data[5] if len(pdr_data) > 5 else 'N/A'}")
                        except Exception as e:
                            mod.export_debug_log(f"[collect_endpoints] ERROR decoding PDR: handle=0x{handle:08x}, error={e}")
                            decoded = {'error': f'decode error: {e}'}
                        decoded_pdrs.append({
                            'handle': handle,
                            'next_handle': r.get('next_handle'),
                            'pdr_data': pdr_data,
                            'decoded': decoded,
                        })
                    ep['pdr_records'] = decoded_pdrs

                    # Retrieve FRU metadata and table; capture raw binary as base64 in `raw_fru_data`
                    fru_sets = []
                    raw_fru_b64 = None
                    metadata, ferr = mod.get_fru_record_table_metadata(port)
                    if not ferr and metadata:
                        table_data, ferr2 = mod.get_fru_record_table(port, transfer_context=0)
                        if not ferr2 and table_data:
                            parsed = mod.parse_fru_record_table(table_data)
                            spec_parsed = mod.convert_parsed_to_spec(parsed, pdrs)
                            fru_sets.append({'metadata': metadata, 'data_length': len(table_data), 'parsed_records': spec_parsed})
                            try:
                                raw_fru_b64 = base64.b64encode(table_data).decode('ascii')
                            except Exception:
                                raw_fru_b64 = None
                        else:
                            fru_sets.append({'metadata': metadata, 'note': 'GetFRURecordTable not supported or failed', 'error': ferr2})
                    elif ferr:
                        # No metadata support
                        ep['fru_records'] = []
                    ep['fru_records'] = fru_sets
                    # Add raw FRU data (base64) at endpoint level; keep None if unavailable
                    ep['raw_fru_data'] = raw_fru_b64

                    port.close()
                except Exception as e:
                    ep['error'] = str(e)
                endpoints.append(ep)
                progress.update(subtask, advance=1)
                progress.update(task, advance=1)

        out = {'endpoints': endpoints}
        def make_json_serializable(obj):
            """Recursively convert non-JSON-serializable types (bytes) to hex strings."""
            if isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [make_json_serializable(v) for v in obj]
            if isinstance(obj, bytes):
                return obj.hex()
            # Leave other simple types as-is
            return obj

        ser = make_json_serializable(out)
        try:
            with open(output, 'w') as f:
                json.dump(ser, f, indent=2)
            console.print(f'[green]Saved results to {output}[/green]')
        except Exception as e:
            console.print(f'[red]Failed to write output: {e}[/red]')
    
    except Exception as e:
        console.print(f'[red]Error during collection: {e}[/red]')
        sys.exit(1)


if __name__ == '__main__':
    main()
