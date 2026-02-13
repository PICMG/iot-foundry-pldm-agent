from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional

from utils import extract_schema_version
from generate_chassis import create_chassis
from generate_sensors import create_sensor
from generate_controls import create_control


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)


def _unique_resource_id(base_dir: Path, coll: str, short_name: str) -> str:
    rid = short_name.replace(' ', '_').lower()
    coll_dir = base_dir / 'redfish' / 'v1' / coll
    if not coll_dir.exists():
        return rid
    existing = {p.name for p in coll_dir.iterdir() if p.is_dir()}
    if rid not in existing:
        return rid
    # append _2, _3 ...
    i = 2
    while True:
        cand = f"{rid}_{i}"
        if cand not in existing:
            return cand
        i += 1


def create_automation_node(dst: Path, ep: dict, short_name: str, short_description: str, report: dict, automation_manager_oid: str) -> str:
    """Create an AutomationNode resource and add it to the AutomationNodes collection.

    `ep` is the endpoint dict from the pdr_file; the function inspects `ep` for
    `entityIDName` and PDR records to include PID/Profiled-specific fields.

    Returns the created resource @odata.id
    """
    schema = extract_schema_version(dst, 'AutomationNode')
    base = dst / 'redfish' / 'v1'
    resource_id = _unique_resource_id(dst, 'AutomationNodes', short_name)

    # determine entityIDName from endpoint
    entityIDName = None
    if isinstance(ep, dict):
        entityIDName = ep.get('entityIDName')
        if not entityIDName:
            # nested search
            def find_entity(x):
                if isinstance(x, dict):
                    if 'entityIDName' in x:
                        return x.get('entityIDName')
                    for vv in x.values():
                        r = find_entity(vv)
                        if r:
                            return r
                if isinstance(x, list):
                    for vv in x:
                        r = find_entity(vv)
                        if r:
                            return r
                return None
            entityIDName = find_entity(ep)
    entityIDName = entityIDName or 'Unknown'

    # detect presence of sensor/effecter IDs in pdr_records and collect decoded PDRs
    pdrs = ep.get('pdr_records') if isinstance(ep, dict) else None
    sensor_pdrs: dict[int, dict] = {}
    effecter_pdrs: dict[int, dict] = {}
    if isinstance(pdrs, list):
        for r in pdrs:
            dec = r.get('decoded') if isinstance(r, dict) else None
            if not isinstance(dec, dict):
                continue
            if 'sensorID' in dec:
                sid = dec.get('sensorID')
                sensor_pdrs[int(sid)] = r
            if 'effecterID' in dec:
                eid = dec.get('effecterID')
                effecter_pdrs[int(eid)] = r

    # Build Actions block per how_to.md
    actions = {'@odata.type': (f"#AutomationNode.{schema}.Actions" if schema else '#AutomationNode.Actions')}
    actions['#AutomationNode.Reset'] = {'target': f"/redfish/v1/AutomationNodes/{resource_id}/Actions/AutomationNode.Reset"}
    actions['#AutomationNode.SendTrigger'] = {'target': f"/redfish/v1/AutomationNodes/{resource_id}/Actions/AutomationNode.SendTrigger"}
    if entityIDName in ('PID', 'Profiled'):
        actions['#AutomationNode.Start'] = {'target': f"/redfish/v1/AutomationNodes/{resource_id}/Actions/AutomationNode.Start"}
        actions['#AutomationNode.Stop'] = {'target': f"/redfish/v1/AutomationNodes/{resource_id}/Actions/AutomationNode.Stop"}
    if entityIDName == 'Profiled':
        actions['#AutomationNode.Wait'] = {'target': f"/redfish/v1/AutomationNodes/{resource_id}/Actions/AutomationNode.Wait"}
    actions['Oem'] = {}

    links = {'Chassis': [ { '@odata.id': f'/redfish/v1/Chassis/{resource_id}' } ]}
    # We'll fill OutputControl/PidFeedbackSensor/PositionSensor links below after we know which
    # sensors/effecters were created. For now leave them to be set later.

    node = {
        '@odata.type': (f"#AutomationNode.{schema}.AutomationNode" if schema else '#AutomationNode.AutomationNode'),
        'Id': resource_id,
        'Name': short_name,
        'Description': short_description,
        'Actions': actions,
        'Links': links,
        'Instrumentation': { '@odata.id': f'/redfish/v1/AutomationNodes/{resource_id}/AutomationInstrumentation' },
        'NodeType': ('PID' if entityIDName == 'PID' else ('Simple' if entityIDName == 'Simple' else 'MotionPosition')),
        'NodeState': 'Idle',
        'Status': { 'State': 'Enabled', 'Health': 'OK' },
        '@odata.context': '/redfish/v1/$metadata#AutomationNode.AutomationNode',
        '@odata.id': f'/redfish/v1/AutomationNodes/{resource_id}'
    }

    node_path = base / 'AutomationNodes' / resource_id / 'index.json'
    _write_json(node_path, node)
    report.setdefault('nodes_created', []).append(str(node_path))

    # Update AutomationNodes collection
    idx_path = base / 'AutomationNodes' / 'index.json'
    if idx_path.exists():
        data = json.loads(idx_path.read_text())
    else:
        data = { '@odata.id': '/redfish/v1/AutomationNodes', 'Members': [], 'Members@odata.count': 0 }
    members = data.get('Members', [])
    members.append({'@odata.id': f'/redfish/v1/AutomationNodes/{resource_id}'})
    data['Members'] = members
    data['Members@odata.count'] = len(members)
    _write_json(idx_path, data)
    report.setdefault('collections_fixed', []).append({'collection': 'AutomationNodes', 'added': [f'/redfish/v1/AutomationNodes/{resource_id}']})

    # Step 3.3: create chassis and subordinate resources referenced by the node
    has_assembly = False
    if isinstance(ep, dict):
        has_assembly = bool(ep.get('fru_records') or ep.get('fru') or ep.get('fru_info'))

    create_chassis(dst, resource_id, short_name, f'{short_description} chassis', report, ep=ep, automation_manager_oid=automation_manager_oid, has_sensors=bool(sensor_pdrs), has_controls=bool(effecter_pdrs), has_assembly=has_assembly)

    # Normalize entity name for table matching (treat 'Profiled' as 'Position')
    norm_entity = entityIDName
    if isinstance(entityIDName, str) and entityIDName.lower() == 'profiled':
        norm_entity = 'Position'

    # Create all sensors found in the PDRs
    sensors_by_id: dict[int, dict] = {}
    def _sensor_function(sid: int, entity: str) -> tuple[Optional[str], bool]:
        # SENSOR_DATA table mapping from how_to.md — return (function, is_percent)
        # when the table indicates the sensor should NOT be created for this
        # entity type, return (None, False).
        # NOTE: a future enhancement can read the table from a config; for now
        # encode the mapping here. The second value indicates the 'percent'
        # override described by the how_to additions.
        # Default: not percent
        is_percent = False
        if sid == 1:
            return ('Global Interlock', True)
        if sid == 2:
            return ('Trigger', True)
        if 3 <= sid <= 255 and entity == 'Simple':
            return ('General Sensor', False)
        if sid == 4 and entity == 'PID':
            return ('Control Error', False)
        if sid == 5 and entity == 'PID':
            return ('Feedback', False)
        if sid == 4 and entity == 'Position':
            return ('Velocity Error', False)
        if sid == 5 and entity == 'Position':
            # Example: make SENSOR_ID_5 a percent sensor for Position (if desired)
            return ('Position Error', False)
        if sid == 6 and entity == 'Position':
            return ('Velocity', False)
        if sid == 7 and entity == 'Position':
            return ('Position', False)
        if sid == 8 and entity == 'Position':
            return ('Positive Limit', True)
        if sid == 9 and entity == 'Position':
            return ('Negative Limit', True)
        return (None, False)

    for sid in sorted(sensor_pdrs.keys()):
        kind, is_percent = _sensor_function(sid, norm_entity)
        if not kind:
            continue
        # pass percent info as a tuple in sensor_kind so create_sensor can
        # detect and emit the reduced percent-style sensor structure
        s_oid = create_sensor(dst, resource_id, sid, (kind, is_percent), report, sensor_pdr=sensor_pdrs.get(sid), short_name=short_name, entityIDName=entityIDName)
        sensors_by_id[sid] = {'DataSourceUri': s_oid, 'Reading': None}

    # Create all effecters/controls and map referenced sensors according to CONTROL_DATA table
    effecter_sensor_map: dict[int, dict] = {}
    def _control_function(eid: int, entity: str) -> tuple[Optional[str], Optional[int], bool]:
        # returns (function, referenced_sensor_id, is_percent) or (None,None,False)
        # when not applicable. The is_percent flag comes from the CONTROL_DATA
        # table's "make percent" column.
        if eid == 1:
            return ('Global Interlock', 1, True)
        if eid == 2:
            return ('Trigger', 2, True)
        if 3 <= eid <= 255 and entity == 'Simple':
            return ('General Effecter', None, False)
        if eid == 4 and entity == 'PID':
            return ('SetPoint', 5, False)
        if eid == 4 and entity == 'Position':
            return ('Position', 7, False)
        if eid == 5 and entity == 'Position':
            return ('Velocity Profile', None, False)
        if eid == 6 and entity == 'Position':
            return ('Acceleration Profile', None, False)
        if eid == 7 and entity == 'Position':
            return ('Acceleration Gain', None, False)
        return (None, None, False)

    for eid in sorted(effecter_pdrs.keys()):
        func, ref_sid, is_percent = _control_function(eid, norm_entity)
        if not func:
            continue
        if ref_sid and ref_sid in sensors_by_id:
            effecter_sensor_map[eid] = sensors_by_id[ref_sid]
        # Pass percent flag to create_control via a tuple control_kind
        create_control(dst, resource_id, eid, (func, is_percent), report, effecter_pdr=effecter_pdrs.get(eid), short_name=short_name, entityIDName=entityIDName, sensor_lookup=effecter_sensor_map)

    # Now set AutomationNode Links that refer to specific sensors/effecters per how_to rules
    # OutputControl: include only if PID or Profiled and find a matching effecter (SetPoint for PID, Position for Profiled)
    if entityIDName in ('PID', 'Profiled'):
        desired = 'SetPoint' if entityIDName == 'PID' else 'Position'
        for eid in effecter_pdrs.keys():
            func, _, _ = _control_function(eid, entityIDName)
            if func == desired:
                links['OutputControl'] = {'@odata.id': f'/redfish/v1/Chassis/{resource_id}/Controls/EFFECTER_ID_{eid}'}
                break
    # PidFeedbackSensor only for PID -> find sensor mapped to Feedback
    if entityIDName == 'PID':
        for sid in sensors_by_id.keys():
            if _sensor_function(sid, entityIDName).lower().startswith('feedback'):
                links['PidFeedbackSensor'] = {'@odata.id': f'/redfish/v1/Chassis/{resource_id}/Sensors/SENSOR_ID_{sid}'}
                break
    # PositionSensor only if Profiled and a Position sensor exists
    if entityIDName == 'Profiled':
        for sid in sensors_by_id.keys():
            if _sensor_function(sid, entityIDName) == 'Position':
                links['PositionSensor'] = {'@odata.id': f'/redfish/v1/Chassis/{resource_id}/Sensors/SENSOR_ID_{sid}'}
                break

    # update node Links
    node['Links'] = links

    return node['@odata.id']
