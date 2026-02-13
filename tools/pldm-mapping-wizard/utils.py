from __future__ import annotations
import re
from pathlib import Path
from typing import Optional


def extract_schema_version(dst: Path, resource_name: Optional[str] = None) -> Optional[str]:
    """Extract a schema version token (e.g. v1_27_0) from the mockup $metadata/index.xml.

    If `resource_name` is provided (e.g. 'AutomationNode') the function will first try
    to find a Namespace entry for that resource (e.g. AutomationNode.v1_0_0) and return
    the matching version token. Otherwise it falls back to selecting the numerically
    largest v1_x_y token found in the file.
    """
    meta_path = dst / 'redfish' / 'v1' / '$metadata' / 'index.xml'
    if not meta_path.exists():
        # try alternate common path
        meta_path = dst / 'redfish' / 'v1' / '$metadata.xml'
        if not meta_path.exists():
            return None
    try:
        text = meta_path.read_text()
    except Exception:
        return None
    # If a specific resource is requested, try to find its Namespace include
    if resource_name:
        # look for Namespace="<Resource>.v1_X_Y"
        m = re.search(r'Namespace="' + re.escape(resource_name) + r'\.v1_\d+_\d+"', text)
        if m:
            tok = re.search(r'v1_\d+_\d+', m.group(0))
            if tok:
                return tok.group(0)
        # If the specific resource namespace is not found, do not fall back
        # to another resource's version. Returning None will cause callers
        # to emit an unversioned @odata.type, allowing the service to use
        # the most appropriate/latest schema.
        return None

    # No specific resource requested: fall back to selecting the numerically
    # largest v1_x_y token found in the file, if any.
    matches = re.findall(r'v1_\d+_\d+', text)
    if not matches:
        return None
    # Prefer the numerically largest version in case there are many
    def keyfn(tok: str):
        parts = tok.split('_')
        return tuple(int(p) for p in parts[1:])

    matches.sort(key=keyfn, reverse=True)
    return matches[0]
