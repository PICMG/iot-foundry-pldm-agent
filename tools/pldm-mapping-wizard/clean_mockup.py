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
            click.echo(f'Removed {dest}')
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
            return False
        report.setdefault(reason_key, []).append(str(target_dir))

        # Remove any references to this resource across the mockup
        json_files = list(dst.rglob('*.json'))
        for jf in json_files:
            try:
                data = load_json(jf)
            except Exception:
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
def main(source: str, dest: str):
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
    click.echo(f'Copying {src} -> {dst} ...')
    shutil.copytree(src, dst)
    click.echo('Copy complete.')

    report = {}

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

    click.echo(f'Found AutomationNodes: {node_names}')

    for name in node_names:
        click.echo(f'Processing node {name} ...')
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

    # Final residual check
    click.echo('Cleanup report:')
    click.echo(json.dumps(report, indent=2))
    click.echo('Done.')


if __name__ == '__main__':
    main()
