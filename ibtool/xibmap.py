import xml.etree.ElementTree as ET
from . import xibparser
from . import genlib
from .models import XibObject, NibObject


def build_xibmap(xib_path: str) -> list[tuple[str, int, str, str]]:
    """Parse a XIB, compile it, and return a list of (xibid, nibidx, classname, original_classname) tuples."""
    tree = ET.parse(xib_path)
    root = tree.getroot()
    context, nibroot = xibparser.ParseXIBObjects(root)

    # Compile to assign _nibidx to all objects
    genlib.CompileNibObjects([nibroot])

    # Walk all objects in context to collect xibid -> nibidx mappings
    entries = []
    seen = set()
    _collect_xibmap(nibroot, entries, seen)
    entries.sort(key=lambda e: e[1])
    return entries


def _collect_xibmap(obj: NibObject, entries: list, seen: set):
    if id(obj) in seen:
        return
    seen.add(id(obj))

    if isinstance(obj, XibObject) and obj.xibid is not None:
        entries.append((
            str(obj.xibid),
            obj.nibidx(),
            obj.classname(),
            obj.originalclassname(),
        ))

    # Recurse into properties
    for val in obj.properties.values():
        if isinstance(val, NibObject):
            _collect_xibmap(val, entries, seen)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, NibObject):
                    _collect_xibmap(item, entries, seen)

    # Recurse into _items (for NibMutableList and similar collection types)
    if hasattr(obj, '_items'):
        for item in obj._items:
            if isinstance(item, NibObject):
                _collect_xibmap(item, entries, seen)


def build_nibidx_to_xibid(xib_path: str) -> dict[int, str]:
    """Build a mapping from NIB object index to XIB element id."""
    entries = build_xibmap(xib_path)
    return {nibidx: xibid for xibid, nibidx, _, _ in entries}


def print_xibmap(xib_path: str):
    entries = build_xibmap(xib_path)

    # Column widths
    id_w = max((len(e[0]) for e in entries), default=3)
    idx_w = max((len(str(e[1])) for e in entries), default=3)
    cls_w = max((len(e[2]) for e in entries), default=5)

    print(f"{'XIB id':<{id_w}}  {'NIB#':>{idx_w}}  {'Class':<{cls_w}}  Original")
    print(f"{'-'*id_w}  {'-'*idx_w}  {'-'*cls_w}  --------")
    for xibid, nibidx, classname, origclass in entries:
        orig = "" if origclass == classname else origclass
        print(f"{xibid:<{id_w}}  {nibidx:>{idx_w}}  {classname:<{cls_w}}  {orig}")
