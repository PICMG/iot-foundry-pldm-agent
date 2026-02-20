#!/usr/bin/env python3
"""Copy a mockup and remove AutomationNodes and associated resources.

Usage:
  python3 clean_mockup.py [--source PATH] [--dest PATH]

Default source: samples/mockup
Default dest: output/mockup

Behavior:
- If dest exists, prompt to remove it, choose another, or cancel.
- Copy source -> dest, then for each AutomationNode in dest:
  - remove AutomationNodes/<Name>/ subtree
  - remove Chassis/<Name>/ subtree (if present)
  - for each cable referencing the chassis as a downstream endpoint:
      - if the cable lists ONLY that downstream endpoint -> delete the cable resource
      - otherwise remove the downstream endpoint reference from the cable
  - remove member entries from collection index files and decrement counts
  - remove any DataSourceUri/@odata.id references to the removed resources

This script modifies the copied mockup only.
"""
from __future__ import annotations
import os
import shutil
import json
import glob
import click
from pathlib import Path
from typing import Any, Tuple

import generate_automation_node
from utils import extract_schema_version


def load_json(path: Path) -> Any:
    with open(path, 'r') as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)


def prompt_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    click.echo(f'Destination {dest} already exists.')
    while True:
        choice = click.prompt("Choose action: (r)emove, (c)hoose another, (x) cancel", default='r')
        choice = choice.strip().lower()
        if choice in ('r', 'remove'):
            shutil.rmtree(dest)
            return dest
        if choice in ('c', 'choose'):
            new = click.prompt('Enter new destination path')
            newp = Path(new).expanduser()
            if newp.exists():
                click.echo(f'{newp} exists; choose again or remove it manually')
                continue
            return newp
        if choice in ('x', 'cancel'):
            raise click.Abort()


def members_count_fix(index_path: Path) -> None:
    try:
        data = load_json(index_path)
    except Exception:
        return
    if isinstance(data, dict) and 'Members' in data:
        data['Members@odata.count'] = len(data.get('Members', []))
        write_json(index_path, data)


def remove_target_references(obj: Any, target: str) -> Tuple[Any, int]:
    """Recursively remove references equal to target.

    - Remove dict entries whose value == target
    - Remove list items that contain a dict with any value == target
    - Remove keys like DataSourceUri whose value == target
    Returns (new_obj, removals_count)
    """
    removals = 0
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            v = obj[k]
            if v == target:
                del obj[k]
                removals += 1
                continue
            new_v, r = remove_target_references(v, target)
            if r:
                obj[k] = new_v
                removals += r
        return obj, removals

    if isinstance(obj, list):
        new_list = []
        for item in obj:
            # if item is a dict that contains the target as a value, drop it
            def contains_target(x):
                if x == target:
                    return True
                if isinstance(x, dict):
                    for vv in x.values():
                        if contains_target(vv):
                            return True
                if isinstance(x, list):
                    for vv in x:
                        if contains_target(vv):
                            return True
                return False

            if contains_target(item):
                removals += 1
                continue
            new_item, r = remove_target_references(item, target)
            new_list.append(new_item)
            removals += r
        return new_list, removals

    # primitives
    return obj, 0


def oid_to_collection_and_id(oid: str) -> Tuple[str, str] | None:
    """Convert an @odata.id like '/redfish/v1/Chassis/<id>' to (collection, id).

    Returns None if the oid doesn't look like a Redfish resource under /redfish/v1.
    """
    if not isinstance(oid, str):
        return None
    oid = oid.rstrip('/')
    parts = oid.split('/')
    # Expect at least ['', 'redfish', 'v1', '<Collection>', '<Id>']
    if len(parts) >= 5 and parts[1] == 'redfish' and parts[2] == 'v1':
        collection = parts[3]
        resource_id = parts[4]
        return collection, resource_id
    return None


def delete_resource_by_oid(dst: Path, oid: str, report: dict, reason_key: str) -> bool:
    """Delete a resource directory identified by @odata.id and remove references.

    Returns True if a directory was deleted.
    """
    if not isinstance(oid, str):
        return False
    parts = oid.rstrip('/').split('/')
    # Expect parts like ['', 'redfish', 'v1', ...resource path...]
    try:
        idx = parts.index('v1')
    except ValueError:
        return False
    rel_parts = parts[idx + 1 :]
    if not rel_parts:
        return False
    target_dir = dst / 'redfish' / 'v1'
    for p in rel_parts:
        target_dir = target_dir / p
    if target_dir.exists():
        try:
            shutil.rmtree(target_dir)
        except Exception:
            import traceback
            err = traceback.format_exc()
            report.setdefault('errors', []).append(f'delete_rmtree_failed:{target_dir}:{err}')
            click.echo(f'Error deleting {target_dir}: {err}', err=True)
            return False
        report.setdefault(reason_key, []).append(str(target_dir))

        # Remove any references to this resource across the mockup
        json_files = list(dst.rglob('*.json'))
        for jf in json_files:
            try:
                data = load_json(jf)
            except Exception:
                import traceback
                report.setdefault('errors', []).append(f'load_json_failed:{jf}:{traceback.format_exc()}')
                click.echo(f'Error loading JSON {jf}', err=True)
                continue
            new_data, removed = remove_target_references(data, oid)
            if removed:
                write_json(jf, new_data)
                rid = target_dir.name
                report.setdefault(f'refs_removed_{rid}', []).append((str(jf), removed))
        return True
    return False


def process_node(dest: Path, name: str, report: dict) -> None:
    base = dest / 'redfish' / 'v1'
    node_prefix = '/redfish/v1/AutomationNodes/' + name

    # Determine chassis @odata.id(s) from the AutomationNode Links->Chassis
    chassis_oids: list[str] = []
    node_index = base / 'AutomationNodes' / name / 'index.json'
    if node_index.exists():
        try:
            node_data = load_json(node_index)
            links = node_data.get('Links', {})
            chassis_links = links.get('Chassis', []) if isinstance(links, dict) else []
            for c in chassis_links:
                oid = c.get('@odata.id') if isinstance(c, dict) else None
                if oid:
                    chassis_oids.append(oid.rstrip('/'))
        except Exception:
            pass

    # Remove AutomationNodes/<name>
    node_dir = base / 'AutomationNodes' / name
    if node_dir.exists():
        shutil.rmtree(node_dir)
        report.setdefault('nodes_removed', []).append(str(node_dir))

    # Remove the chassis resources referenced by this AutomationNode (if any)
    for chassis_oid in chassis_oids:
        deleted = delete_resource_by_oid(dest, chassis_oid, report, 'chassis_removed')
        if not deleted:
            # fall back to removing by name if the referenced chassis dir exists
            parsed = oid_to_collection_and_id(chassis_oid)
            if parsed:
                coll, rid = parsed
                fallback_dir = base / coll / rid
                if fallback_dir.exists():
                    shutil.rmtree(fallback_dir)
                    report.setdefault('chassis_removed', []).append(str(fallback_dir))

    # Remove references to the removed AutomationNode and referenced Chassis OIDs across all JSON files in dest
    json_files = list(dest.rglob('*.json'))
    for jf in json_files:
        try:
            data = load_json(jf)
        except Exception:
            import traceback
            report.setdefault('errors', []).append(f'load_json_failed:{jf}:{traceback.format_exc()}')
            click.echo(f'Error loading JSON {jf}', err=True)
            continue
        new_data, removed = remove_target_references(data, node_prefix)
        if removed:
            write_json(jf, new_data)
            report.setdefault('refs_removed_node', []).append((str(jf), removed))
        for chassis_oid in chassis_oids:
            new_data2, removed2 = remove_target_references(new_data, chassis_oid)
            if removed2:
                write_json(jf, new_data2)
                report.setdefault('refs_removed_chassis', []).append((str(jf), removed2))

    # Update collections counts (AutomationNodes, Chassis, Cables)
    for coll in [('AutomationNodes',), ('Chassis',), ('Cables',)]:
        idx = dest / 'redfish' / 'v1' / coll[0] / 'index.json'
        if idx.exists():
            members_count_fix(idx)


@click.command()
@click.option('--source', '-s', default='samples/mockup', help='Source mockup folder')
@click.option('--dest', '-d', default='output/mockup', help='Destination mockup folder')
@click.option('--pdr-file', '-p', default=None, help='Path to pdr_file JSON for resource generation')
def main(source: str, dest: str, pdr_file: str | None):
    src = Path(source).expanduser()
    dst = Path(dest).expanduser()
    if not src.exists():
        click.echo(f'Source {src} does not exist')
        raise click.Abort()

    try:
        dst = prompt_dest(dst)
    except click.Abort:
        click.echo('Cancelled')
        return

    # Copy
    try:
        shutil.copytree(src, dst)
    except Exception as e:
        click.echo(f'Error copying {src} -> {dst}: {e}', err=True)
        raise click.Abort()

    report = {}

    # --- Preparation phase (Step 2 in how_to.md) ---
    def ensure_collection_exists(dst_path: Path, coll: str, odata_type: str):
        coll_dir = dst_path / 'redfish' / 'v1' / coll
        idx = coll_dir / 'index.json'
        if not coll_dir.exists():
            coll_dir.mkdir(parents=True, exist_ok=True)
        if not idx.exists():
            data = {
                '@odata.id': f'/redfish/v1/{coll}',
                '@odata.type': odata_type,
                'Members': [],
                'Members@odata.count': 0
            }
            write_json(idx, data)
            report.setdefault('preparation', []).append({'collection_created': coll})

    def pick_resource_from_collection(dst_path: Path, coll: str, kind: str) -> str | None:
        idx = dst_path / 'redfish' / 'v1' / coll / 'index.json'
        if not idx.exists():
            return None
        data = load_json(idx)
        members = [m.get('@odata.id') for m in data.get('Members', []) if isinstance(m, dict) and m.get('@odata.id')]
        if not members:
            return None
        if len(members) == 1:
            return members[0]
        # multiple: prompt user to select
        click.echo(f'Multiple {coll} resources found; select {kind}:')
        for i, m in enumerate(members, start=1):
            click.echo(f'{i}) {m}')
        while True:
            choice = click.prompt(f'Enter number for the {kind} (1-{len(members)})')
            try:
                n = int(choice)
                if 1 <= n <= len(members):
                    return members[n-1]
            except Exception:
                pass
            click.echo('Invalid choice; try again')

    # Ensure Systems collection exists and select automation_system
    while True:
        systems_idx = dst / 'redfish' / 'v1' / 'Systems' / 'index.json'
        if systems_idx.exists():
            automation_system = pick_resource_from_collection(dst, 'Systems', 'automation_system')
            if automation_system is None:
                click.echo('No System resources found in Systems collection.')
                # allow user to pick alternate reference mockup or exit
                alt = click.prompt('Specify alternate reference mockup path or (x) to exit', default='x')
                if alt.strip().lower() == 'x':
                    raise click.Abort()
                altp = Path(alt).expanduser()
                if not altp.exists():
                    click.echo(f'Path {altp} does not exist; exiting')
                    raise click.Abort()
                # replace dst with copy of new source
                shutil.rmtree(dst)
                shutil.copytree(altp, dst)
                continue
            break
        # systems collection missing
        click.echo('No top-level Systems collection found in mockup.')
        alt = click.prompt('Specify alternate reference mockup path or (x) to exit', default='x')
        if alt.strip().lower() == 'x':
            raise click.Abort()
        altp = Path(alt).expanduser()
        if not altp.exists():
            click.echo(f'Path {altp} does not exist; exiting')
            raise click.Abort()
        shutil.rmtree(dst)
        shutil.copytree(altp, dst)

    report.setdefault('preparation', []).append({'automation_system': automation_system})

    # Ensure Managers collection exists and select automation_manager
    while True:
        managers_idx = dst / 'redfish' / 'v1' / 'Managers' / 'index.json'
        if managers_idx.exists():
            automation_manager = pick_resource_from_collection(dst, 'Managers', 'automation_manager')
            if automation_manager is None:
                click.echo('No Manager resources found in Managers collection.')
                alt = click.prompt('Specify alternate reference mockup path or (x) to exit', default='x')
                if alt.strip().lower() == 'x':
                    raise click.Abort()
                altp = Path(alt).expanduser()
                if not altp.exists():
                    click.echo(f'Path {altp} does not exist; exiting')
                    raise click.Abort()
                shutil.rmtree(dst)
                shutil.copytree(altp, dst)
                continue
            break
        click.echo('No top-level Managers collection found in mockup.')
        alt = click.prompt('Specify alternate reference mockup path or (x) to exit', default='x')
        if alt.strip().lower() == 'x':
            raise click.Abort()
        altp = Path(alt).expanduser()
        if not altp.exists():
            click.echo(f'Path {altp} does not exist; exiting')
            raise click.Abort()
        shutil.rmtree(dst)
        shutil.copytree(altp, dst)

    report.setdefault('preparation', []).append({'automation_manager': automation_manager})

    # Ensure Cables and AutomationNodes collections exist
    ensure_collection_exists(dst, 'Cables', '#CableCollection.CableCollection')
    ensure_collection_exists(dst, 'AutomationNodes', '#AutomationNodeCollection.AutomationNodeCollection')


    # Scan AutomationNodes collection
    automation_index = dst / 'redfish' / 'v1' / 'AutomationNodes' / 'index.json'
    if not automation_index.exists():
        click.echo('No AutomationNodes collection found in mockup copy.')
        # continue to try fixing collections anyway

    node_names = []
    if automation_index.exists():
        data = load_json(automation_index)
        members = data.get('Members', [])
        for m in members:
            oid = m.get('@odata.id')
            if not oid:
                continue
            parts = oid.rstrip('/').split('/')
            if parts:
                node_names.append(parts[-1])

    for name in node_names:
        process_node(dst, name, report)

    # Fix collections: remove only missing resources from collection members and decrement counts
    def fix_collections(dst_path: Path, report: dict, collections=('AutomationNodes', 'Chassis', 'Cables')):
        for coll in collections:
            idx = dst_path / 'redfish' / 'v1' / coll / 'index.json'
            coll_dir = dst_path / 'redfish' / 'v1' / coll
            if not coll_dir.exists():
                continue
            # discover actual resource dirs (having index.json)
            discovered = []
            for child in sorted(coll_dir.iterdir()):
                if child.is_dir() and (child / 'index.json').exists():
                    discovered.append(child.name)

            discovered_members = [ {'@odata.id': f'/redfish/v1/{coll}/{name}'} for name in discovered ]

            if not idx.exists():
                # create index.json if missing
                data = {
                    '@odata.id': f'/redfish/v1/{coll}',
                    'Members': discovered_members,
                    'Members@odata.count': len(discovered_members)
                }
                write_json(idx, data)
                report.setdefault('collections_fixed', []).append({
                    'collection': coll,
                    'added': [m['@odata.id'] for m in discovered_members],
                })
                continue

            try:
                data = load_json(idx)
            except Exception:
                continue

            existing_oids = [m.get('@odata.id') for m in data.get('Members', []) if isinstance(m, dict) and m.get('@odata.id')]
            discovered_oids = [f'/redfish/v1/{coll}/{name}' for name in discovered]

            # Always rewrite Members and count to reflect actual discovered resources
            new_members = [{'@odata.id': o} for o in discovered_oids]
            data['Members'] = new_members
            data['Members@odata.count'] = len(new_members)
            write_json(idx, data)
            report.setdefault('collections_fixed', []).append({
                'collection': coll,
                'added': [o for o in discovered_oids if o not in existing_oids],
                'removed': [o for o in existing_oids if o not in discovered_oids],
                'final_count': len(new_members)
            })

    fix_collections(dst, report)

    # Additional cleanup passes per how_to.md
    # 1) Remove cables that have no DownstreamChassis reference
    cables_dir = dst / 'redfish' / 'v1' / 'Cables'
    if cables_dir.exists():
        for cable_idx in list(cables_dir.glob('*/index.json')):
            try:
                cable = load_json(cable_idx)
            except Exception:
                continue
            links = cable.get('Links', {})
            downstream = links.get('DownstreamChassis', []) if isinstance(links, dict) else []
            if not downstream:
                parent = cable_idx.parent
                # Only remove cables that look like AutomationNode cables:
                # (Cable resource `Name` contains the substring 'AutomationNode')
                name_field = ''
                try:
                    name_field = str(cable.get('Name', '')) if isinstance(cable, dict) else ''
                except Exception:
                    name_field = ''
                if 'AutomationNode' in name_field:
                    # build oid for deletion so references are removed too
                    oid = f"/redfish/v1/Cables/{parent.name}"
                    deleted = delete_resource_by_oid(dst, oid, report, 'cables_deleted')
                    if not deleted:
                        try:
                            shutil.rmtree(parent)
                            report.setdefault('cables_deleted', []).append(str(parent))
                        except Exception:
                            pass

    # 2) Remove any USBController with ID AutomationUsb under Systems
    systems_dir = dst / 'redfish' / 'v1' / 'Systems'
    if systems_dir.exists():
        for system in systems_dir.iterdir():
            if not system.is_dir():
                continue
            usb_controllers_dir = system / 'USBControllers'
            auto_usb = usb_controllers_dir / 'AutomationUsb'
            if auto_usb.exists():
                # Try to delete via oid to remove references
                system_id = system.name
                oid = f"/redfish/v1/Systems/{system_id}/USBControllers/AutomationUsb"
                deleted = delete_resource_by_oid(dst, oid, report, 'usbcontrollers_deleted')
                if not deleted:
                    try:
                        shutil.rmtree(auto_usb)
                        report.setdefault('usbcontrollers_deleted', []).append(str(auto_usb))
                    except Exception:
                        pass

        # Re-run collection fixes after the additional deletion passes
            fix_collections(dst, report)

        # Note: cleanup report is recorded in `report`; only surface errors to the user
        if 'errors' in report:
            click.echo('Errors during cleanup:', err=True)
            for e in report.get('errors', []):
                click.echo(str(e), err=True)

    # --- Resource Generation (Step 3, including 3.1 and 3.2) ---
    if pdr_file:
        pdr_path = Path(pdr_file).expanduser()
        if not pdr_path.exists():
            click.echo(f'PDR file {pdr_path} does not exist; skipping resource generation')
        else:
            try:
                pdr_data = load_json(pdr_path)
            except Exception:
                click.echo(f'Failed to load PDR file {pdr_path}; skipping generation')
                pdr_data = None

            endpoints = []
            if isinstance(pdr_data, dict):
                for key in ('endpoints', 'pdrs', 'devices'):
                    if key in pdr_data and isinstance(pdr_data[key], list):
                        endpoints = pdr_data[key]
                        break
                if not endpoints:
                    # if top-level dict contains numeric-indexed map, try values
                    vals = [v for v in pdr_data.values() if isinstance(v, dict) or isinstance(v, list)]
                    # no reliable fallback — try root list
            if isinstance(pdr_data, list):
                endpoints = pdr_data

            if not endpoints:
                click.echo('No endpoints found in pdr_file; skipping generation')
            else:
                for ep in endpoints:
                    # Extract entityIDName from endpoint
                    entityIDName = None
                    devpath = None
                    model = None
                    serial = None
                    if isinstance(ep, dict):
                        # common locations
                        devpath = ep.get('dev') or ep.get('device')
                        # FRU data in our collected JSON is stored under 'fru_records'
                        # as parsed_records -> fields (list of dicts with typeName/value).
                        def _fru_field(ep_dict: dict, type_name: str):
                            if not isinstance(ep_dict, dict):
                                return None
                            for fru_set in ep_dict.get('fru_records', []) or []:
                                for parsed in fru_set.get('parsed_records', []) or []:
                                    for f in parsed.get('fields', []) or []:
                                        if f.get('typeName') == type_name and 'value' in f:
                                            return f.get('value')
                            return None

                        # Try FRU parsed_fields first, then fall back to top-level PDR keys.
                        model = _fru_field(ep, 'Model') or ep.get('Model')
                        # FRU uses 'Serial Number' as the typeName in parsed fields
                        serial = _fru_field(ep, 'Serial Number') or ep.get('SerialNumber')
                        # search for entityIDName
                        if 'entityIDName' in ep:
                            entityIDName = ep.get('entityIDName')
                        else:
                            # maybe inside entityNames or pdr list
                            en = ep.get('entityNames')
                            if isinstance(en, dict):
                                # try OEM Entity ID PDR key
                                for k, v in en.items():
                                    if isinstance(v, dict) and 'entityIDName' in v:
                                        entityIDName = v.get('entityIDName')
                                        break
                            # fallback: search nested for entityIDName
                            if entityIDName is None:
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

                    if not entityIDName:
                        click.echo('Endpoint missing entityIDName; skipping this endpoint')
                        continue

                    click.echo('\nEndpoint:')
                    click.echo(f'  device: {devpath}')
                    click.echo(f'  entityIDName: {entityIDName}')
                    click.echo(f'  Model: {model}')
                    click.echo(f'  Serial: {serial}')

                    # Prompt user for short_name and description as specified in how_to.md
                    short_name = click.prompt('short_name (e.g. XMover)')
                    short_description = click.prompt('short_description', default=f'Automation node for {short_name}')

                    try:
                        oid = generate_automation_node.create_automation_node(dst, ep, short_name, short_description, report, report.get('preparation', [{}])[-1].get('automation_manager', ''))
                        click.echo(f'Created AutomationNode {oid}')
                    except Exception as e:
                        click.echo(f'Failed to create AutomationNode: {e}')
                        continue



if __name__ == '__main__':
    main()
