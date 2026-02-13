from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional

from utils import extract_schema_version
from pdr_units_to_ucum import pdr_units_to_ucum


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)


def create_control(dst: Path, chassis_id: str, effecter_id: int, control_kind: Any, report: dict, effecter_pdr: Optional[dict] = None, short_name: Optional[str] = None, entityIDName: Optional[str] = None, sensor_lookup: Optional[dict] = None) -> str:
    """Create a Control resource following how_to.md template.

    effecter_pdr is the parsed PDR dict for this effecter; sensor_lookup maps sensor_id->info to populate Sensor section.
    """
    schema = extract_schema_version(dst, 'Control')
    base = dst / 'redfish' / 'v1'
    eid = f'EFFECTER_ID_{effecter_id}'
    # control_kind may be a (function, is_percent) tuple from the table mapper
    if isinstance(control_kind, (list, tuple)):
        func_name, is_percent = control_kind[0], bool(control_kind[1])
    else:
        func_name, is_percent = control_kind, False
    name_desc = f"{func_name} for {short_name}" if short_name else func_name
    control = {
        '@odata.type': (f"#Control.{schema}.Control" if schema else '#Control.Control'),
        'Id': eid,
        'Name': name_desc,
        'Description': name_desc,
        'SetPointType': 'Single',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'ControlMode': 'Manual',
        'SetPoint': None,
    }

    # Populate from effecter_pdr
    if isinstance(effecter_pdr, dict):
        dec = effecter_pdr.get('decoded', effecter_pdr)
        base_unit = dec.get('baseUnit', 0)
        base_power = dec.get('unitModifier', 0)
        aux = dec.get('auxUnit', 0)
        aux_power = dec.get('auxUnitModifier', 0)
        rel = 0 if dec.get('auxUnitRelationship') == 'multipliedBy' else 1
        rate = dec.get('rateUnit', 0)
        aux_rate = dec.get('auxRateUnit', 0)
        # If control is made percent, override units and omit min/max fields
        if is_percent:
            control['SetPointUnits'] = '%'
        else:
            control['SetPointUnits'] = pdr_units_to_ucum(base_unit, base_power, aux, aux_power, rel, rate, aux_rate)
            max_set = dec.get('maxSettable')
            min_set = dec.get('minSettable')
            control['AllowableMax'] = max_set
            control['AllowableMin'] = min_set
            control['SettingMax'] = max_set
            control['SettingMin'] = min_set

    # If this control references a sensor, include Sensor block
    if sensor_lookup and effecter_id in sensor_lookup:
        sref = sensor_lookup[effecter_id]
        control['Sensor'] = {
            'Reading': sref.get('Reading'),
            'DataSourceUri': sref.get('DataSourceUri')
        }

    # PID-specific ControlLoop
    if entityIDName == 'PID' and effecter_id == 4:
        control['ControlLoop'] = {'Proportional': 0, 'Integral': 0, 'Differential': 0}

    control['@odata.context'] = '/redfish/v1/$metadata#Control.Control'
    control['@odata.id'] = f'/redfish/v1/Chassis/{chassis_id}/Controls/{eid}'

    path = base / 'Chassis' / chassis_id / 'Controls' / eid / 'index.json'
    _write_json(path, control)
    report.setdefault('controls_created', []).append(str(path))

    # Add to chassis Controls collection
    idx = base / 'Chassis' / chassis_id / 'Controls' / 'index.json'
    if idx.exists():
        try:
            data = json.loads(idx.read_text())
        except Exception:
            data = {'@odata.id': f'/redfish/v1/Chassis/{chassis_id}/Controls', 'Members': [], 'Members@odata.count': 0}
    else:
        data = {'@odata.id': f'/redfish/v1/Chassis/{chassis_id}/Controls', 'Members': [], 'Members@odata.count': 0}
    members = data.get('Members', [])
    members.append({'@odata.id': f'/redfish/v1/Chassis/{chassis_id}/Controls/{eid}'})
    data['Members'] = members
    data['Members@odata.count'] = len(members)
    _write_json(idx, data)
    report.setdefault('collections_fixed', []).append({'collection': f'Chassis/{chassis_id}/Controls', 'added': [f'/redfish/v1/Chassis/{chassis_id}/Controls/{eid}']})

    return f'/redfish/v1/Chassis/{chassis_id}/Controls/{eid}'
