from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from typing import Optional

from utils import extract_schema_version


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)


def _collect_fru_fields(ep: Optional[dict]) -> dict:
    fields = {}
    if not isinstance(ep, dict):
        return fields
    fru_recs = ep.get('fru_records') or ep.get('fru') or ep.get('fru_info')
    if isinstance(fru_recs, list):
        for rec in fru_recs:
            parsed = rec.get('parsed_records') if isinstance(rec, dict) else None
            if not isinstance(parsed, list):
                continue
            for pr in parsed:
                for f in pr.get('fields', []):
                    name = f.get('typeName')
                    val = f.get('value')
                    if not name or val is None:
                        continue
                    if name == 'Model':
                        fields['Model'] = val
                    elif name in ('Manufacture Date', 'DateOfManufacture'):
                        fields['DateOfManufacture'] = val
                    elif name in ('Serial', 'Serial Number', 'SerialNumber'):
                        fields['SerialNumber'] = val
                    elif name == 'Manufacturer':
                        fields['Manufacturer'] = val
                    elif name in ('PartNumber', 'Part Number'):
                        fields['PartNumber'] = val
                    elif name == 'SKU':
                        fields['SKU'] = val
                    elif name == 'Version':
                        fields['Version'] = val
                    elif name in ('AssetTag', 'Asset Tag'):
                        fields['AssetTag'] = val
    else:
        fru = ep.get('fru') if isinstance(ep.get('fru'), dict) else {}
        for k in ('AssetTag', 'DateOfManufacture', 'SerialNumber', 'Manufacturer', 'Model', 'PartNumber', 'SKU', 'Version'):
            if k in fru:
                fields[k] = fru[k]
    return fields


def create_chassis(dst: Path, resource_id: str, short_name: str, description: str, report: dict, ep: Optional[dict] = None, automation_manager_oid: Optional[str] = None, has_sensors: bool = False, has_controls: bool = False, has_assembly: bool = False) -> str:
    """Create a Chassis resource following the how_to template.

    Non-hardcoded: uses `ep` for FRU data and includes links conditionally.
    """
    schema = extract_schema_version(dst, 'Chassis')
    base = dst / 'redfish' / 'v1'

    fru = _collect_fru_fields(ep)

    chassis = {
        '@odata.type': (f"#Chassis.{schema}.Chassis" if schema else '#Chassis.Chassis'),
        'Id': resource_id,
        'Name': f'Chassis resource for {description}',
        'ChassisType': 'Module',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        '@odata.context': '/redfish/v1/$metadata#Chassis.Chassis',
        '@odata.id': f'/redfish/v1/Chassis/{resource_id}'
    }

    for k in ('AssetTag', 'DateOfManufacture', 'SerialNumber', 'Manufacturer', 'Model', 'PartNumber', 'SKU', 'Version'):
        if k in fru:
            chassis[k] = fru[k]

    if has_sensors:
        chassis['Sensors'] = {'@odata.id': f'/redfish/v1/Chassis/{resource_id}/Sensors'}
    if has_controls:
        chassis['Controls'] = {'@odata.id': f'/redfish/v1/Chassis/{resource_id}/Controls'}
    if has_assembly:
        chassis['Assembly'] = {'@odata.id': f'/redfish/v1/Chassis/{resource_id}/Assembly'}

    links = {}
    if automation_manager_oid:
        links['ManagedBy'] = [{'@odata.id': automation_manager_oid}]
    links['AutomationNodes'] = [{'@odata.id': f'/redfish/v1/AutomationNodes/{resource_id}'}]
    chassis['Links'] = links

    chassis_path = base / 'Chassis' / resource_id / 'index.json'
    _write_json(chassis_path, chassis)
    report.setdefault('chassis_created', []).append(str(chassis_path))

    # Ensure Sensors and Controls collections under this chassis exist
    sensors_idx = base / 'Chassis' / resource_id / 'Sensors' / 'index.json'
    controls_idx = base / 'Chassis' / resource_id / 'Controls' / 'index.json'
    if not sensors_idx.exists():
        # Collections in reference mockups typically use the unversioned
        # collection namespace (e.g. #SensorCollection.SensorCollection). Use
        # the unversioned form to match existing mockup files.
        sdata = {
            '@odata.type': '#SensorCollection.SensorCollection',
            '@odata.context': '/redfish/v1/$metadata#SensorCollection.SensorCollection',
            '@odata.id': f'/redfish/v1/Chassis/{resource_id}/Sensors',
            'Members': [],
            'Members@odata.count': 0
        }
        _write_json(sensors_idx, sdata)
    if not controls_idx.exists():
        cdata = {
            '@odata.type': '#ControlCollection.ControlCollection',
            '@odata.context': '/redfish/v1/$metadata#ControlCollection.ControlCollection',
            '@odata.id': f'/redfish/v1/Chassis/{resource_id}/Controls',
            'Members': [],
            'Members@odata.count': 0
        }
        _write_json(controls_idx, cdata)

    # Update top-level Chassis collection index
    top_idx = base / 'Chassis' / 'index.json'
    if top_idx.exists():
        try:
            data = json.loads(top_idx.read_text())
        except Exception:
            data = {'@odata.id': '/redfish/v1/Chassis', 'Members': [], 'Members@odata.count': 0}
    else:
        data = {'@odata.id': '/redfish/v1/Chassis', 'Members': [], 'Members@odata.count': 0}
    members = data.get('Members', [])
    members.append({'@odata.id': f'/redfish/v1/Chassis/{resource_id}'})
    data['Members'] = members
    data['Members@odata.count'] = len(members)
    _write_json(top_idx, data)
    report.setdefault('collections_fixed', []).append({'collection': 'Chassis', 'added': [f'/redfish/v1/Chassis/{resource_id}']})

    return f'/redfish/v1/Chassis/{resource_id}'
