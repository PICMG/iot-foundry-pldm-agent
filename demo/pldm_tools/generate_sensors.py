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


def create_sensor(dst: Path, chassis_id: str, sensor_id: int, sensor_kind: Any, report: dict, sensor_pdr: Optional[dict] = None, short_name: Optional[str] = None, entityIDName: Optional[str] = None) -> str:
    """Create a Sensor resource following how_to.md template.

    sensor_pdr is the parsed PDR dict for this sensor (decoded). short_name used for descriptions.
    """
    schema = extract_schema_version(dst, 'Sensor')
    base = dst / 'redfish' / 'v1'
    sid = f'SENSOR_ID_{sensor_id}'
    # Build sensor template following how_to.md
    # sensor_kind may be a (function, is_percent) tuple from the table mapper
    if isinstance(sensor_kind, (list, tuple)):
        func_name, is_percent = sensor_kind[0], bool(sensor_kind[1])
    else:
        func_name, is_percent = sensor_kind, False
    name_desc = f"{func_name} for {short_name}" if short_name else f"{func_name} Sensor"
    sensor = {
        '@odata.type': (f"#Sensor.{schema}.Sensor" if schema else '#Sensor.Sensor'),
        '@odata.context': '/redfish/v1/$metadata#Sensor.Sensor',
        '@odata.id': f'/redfish/v1/Chassis/{chassis_id}/Sensors/{sid}',
        'Id': sid,
        'Name': name_desc,
        'Description': name_desc,
        'Reading': None,
        'ReadingType': ('Percent' if is_percent else 'Numeric'),
        'Status': {'State': 'Enabled', 'Health': 'OK'},
    }

    # If this sensor is forced to be a percent sensor, emit the reduced
    # percent-style structure per how_to: ReadingType 'Percent', Reading=0,
    # ReadingUnits '%', and omit accuracy/range/sensing fields and thresholds.
    if is_percent:
        sensor['Reading'] = 0
        sensor['ReadingUnits'] = '%'
    else:
        # Populate numeric-specific fields from sensor_pdr if available
        if isinstance(sensor_pdr, dict):
            dec = sensor_pdr.get('decoded', sensor_pdr)
            base_unit = dec.get('baseUnit', 0)
            base_power = dec.get('unitModifier', 0)
            aux = dec.get('auxUnit', 0)
            aux_power = dec.get('auxUnitModifier', 0)
            rel = 0 if dec.get('auxUnitRelationship') == 'multipliedBy' else 1
            rate = dec.get('rateUnit', 0)
            aux_rate = dec.get('auxRateUnit', 0)
            sensor['ReadingUnits'] = pdr_units_to_ucum(base_unit, base_power, aux, aux_power, rel, rate, aux_rate)
            # ReadingAccuracy per how_to: plusTolerance + maxReadable*accuracy/100
            plus_tol = dec.get('plusTolerance', 0)
            accuracy = dec.get('accuracy', 0)
            max_read = dec.get('maxReadable', 0)
            try:
                sensor['ReadingAccuracy'] = plus_tol + (max_read * accuracy / 100.0)
            except Exception:
                sensor['ReadingAccuracy'] = plus_tol
            sensor['ReadingRangeMax'] = dec.get('maxReadable')
            sensor['ReadingRangeMin'] = dec.get('minReadable')
            sensor['SensingInterval'] = dec.get('updateInterval')

            # Thresholds: include fields based solely on `rangeFieldSupportFlags`
            rf_flags = dec.get('rangeFieldSupportFlags', {}) or {}
            # If no range/threshold flags are set, skip thresholds
            if rf_flags:
                thr = {}
                h = dec.get('hysteresis', None)
                # LowerCaution: present when normalMinSupported is true
                if rf_flags.get('normalMinSupported') and 'warningLow' in dec:
                    thr['LowerCaution'] = {'Reading': dec.get('warningLow'), 'Activation': 'Disabled', 'HysteresisReading': h}
                # LowerCritical
                if rf_flags.get('criticalLowSupported') and 'criticalLow' in dec:
                    thr['LowerCritical'] = {'Reading': dec.get('criticalLow'), 'Activation': 'Disabled', 'HysteresisReading': h}
                # LowerFatal
                if rf_flags.get('fatalLowSupported') and 'fatalLow' in dec:
                    thr['LowerFatal'] = {'Reading': dec.get('fatalLow'), 'Activation': 'Disabled', 'HysteresisReading': h}
                # UpperCaution
                if rf_flags.get('normalMaxSupported') and 'warningHigh' in dec:
                    thr['UpperCaution'] = {'Reading': dec.get('warningHigh'), 'Activation': 'Disabled', 'HysteresisReading': h}
                # UpperCritical
                if rf_flags.get('criticalHighSupported') and 'criticalHigh' in dec:
                    thr['UpperCritical'] = {'Reading': dec.get('criticalHigh'), 'Activation': 'Disabled', 'HysteresisReading': h}
                # UpperFatal
                if rf_flags.get('fatalHighSupported') and 'fatalHigh' in dec:
                    thr['UpperFatal'] = {'Reading': dec.get('fatalHigh'), 'Activation': 'Disabled', 'HysteresisReading': h}
                if thr:
                    sensor['Thresholds'] = thr

    # Links
    sensor['Links'] = {'Chassis': {'@odata.id': f'/redfish/v1/Chassis/{chassis_id}'}}

    path = base / 'Chassis' / chassis_id / 'Sensors' / sid / 'index.json'
    _write_json(path, sensor)
    report.setdefault('sensors_created', []).append(str(path))

    # Add to chassis Sensors collection
    idx = base / 'Chassis' / chassis_id / 'Sensors' / 'index.json'
    if idx.exists():
        try:
            data = json.loads(idx.read_text())
        except Exception:
            data = {'@odata.id': f'/redfish/v1/Chassis/{chassis_id}/Sensors', 'Members': [], 'Members@odata.count': 0}
    else:
        data = {'@odata.id': f'/redfish/v1/Chassis/{chassis_id}/Sensors', 'Members': [], 'Members@odata.count': 0}
    members = data.get('Members', [])
    members.append({'@odata.id': f'/redfish/v1/Chassis/{chassis_id}/Sensors/{sid}'})
    data['Members'] = members
    data['Members@odata.count'] = len(members)
    _write_json(idx, data)
    report.setdefault('collections_fixed', []).append({'collection': f'Chassis/{chassis_id}/Sensors', 'added': [f'/redfish/v1/Chassis/{chassis_id}/Sensors/{sid}']})

    return f'/redfish/v1/Chassis/{chassis_id}/Sensors/{sid}'
