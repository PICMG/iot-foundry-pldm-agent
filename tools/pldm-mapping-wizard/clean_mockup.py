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


def process_node(dest: Path, name: str, report: dict) -> None:
    base = dest / 'redfish' / 'v1'
    node_prefix = '/redfish/v1/AutomationNodes/' + name
    chassis_prefix = '/redfish/v1/Chassis/' + name

    # Remove AutomationNodes/<name>
    node_dir = base / 'AutomationNodes' / name
    if node_dir.exists():
        shutil.rmtree(node_dir)
        report.setdefault('nodes_removed', []).append(str(node_dir))

    # Remove Chassis/<name>
    chassis_dir = base / 'Chassis' / name
    if chassis_dir.exists():
        shutil.rmtree(chassis_dir)
        report.setdefault('chassis_removed', []).append(str(chassis_dir))

    # Cables handling
    cables_dir = base / 'Cables'
    if cables_dir.exists():
        for cable_idx in cables_dir.glob('*/index.json'):
            try:
                cable = load_json(cable_idx)
            except Exception:
                continue
            links = cable.get('Links', {})
            downstream = links.get('DownstreamChassis', []) if isinstance(links, dict) else []
            # count downstream references that match this chassis
            matching = [d for d in downstream if d.get('@odata.id') == chassis_prefix]
            if matching:
                if len(downstream) == 1:
                    # delete the entire cable resource (file and parent dir)
                    parent = cable_idx.parent
                    shutil.rmtree(parent)
                    report.setdefault('cables_deleted', []).append(str(parent))
                else:
                    # remove the matching downstream entries and write back
                    new_down = [d for d in downstream if d.get('@odata.id') != chassis_prefix]
                    links['DownstreamChassis'] = new_down
                    cable['Links'] = links
                    write_json(cable_idx, cable)
                    report.setdefault('cables_modified', []).append(str(cable_idx))

    # Remove references across all JSON files in dest
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
        new_data2, removed2 = remove_target_references(new_data, chassis_prefix)
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
@click.option('--inplace/--no-inplace', default=False, help='Operate on existing dest without copying')
def main(source: str, dest: str, inplace: bool):
    src = Path(source).expanduser()
    dst = Path(dest).expanduser()
    if not src.exists() and not (inplace and dst.exists()):
        click.echo(f'Source {src} does not exist and inplace not requested')
        raise click.Abort()

    if inplace:
        if not dst.exists():
            click.echo(f'Destination {dst} does not exist for inplace operation')
            raise click.Abort()
        click.echo(f'Running inplace cleanup on {dst}')
    else:
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

            to_add = [o for o in discovered_oids if o not in existing_oids]
            to_remove = [o for o in existing_oids if o not in discovered_oids]

            if to_add or to_remove:
                # build new members as discovered order, but keep any extra metadata if present
                new_members = [{'@odata.id': o} for o in discovered_oids]
                data['Members'] = new_members
                data['Members@odata.count'] = len(new_members)
                write_json(idx, data)
                report.setdefault('collections_fixed', []).append({
                    'collection': coll,
                    'added': to_add,
                    'removed': to_remove,
                    'final_count': len(new_members)
                })

    fix_collections(dst, report)

    # Final residual check
    click.echo('Cleanup report:')
    click.echo(json.dumps(report, indent=2))
    click.echo('Done.')


if __name__ == '__main__':
    main()
