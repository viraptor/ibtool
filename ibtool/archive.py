"""Parser for the legacy Interface Builder 3 'archive' XIB format.

These files use a keyed-archive XML schema (root element <archive>) that is
effectively a direct serialization of NSCoding-style objects. Compared to the
modern <document>-based XIB format, the node names and keys already match the
NIB-native class and property names, so parsing is mostly mechanical.

Schema notes:

- <object class="X" id="Y"> defines an object of class X with id Y.
- <array class="X" key="K"> or <array key="K"> is a list property.
- <string>, <int>, <integer>, <bool>, <boolean>, <real>, <double>, <float>,
  <bytes>, <characters>, <nil> are scalar values.
- <reference ref="id"/> points to an already-declared object.
- Dictionaries use the NSMutableDictionary form: children are pairs of keys
  named "NS.key.N" and "NS.object.N".
- IBObjectContainer holds build-time metadata (object parent tree,
  connection records). These are lifted into the NIB's NSIBObjectData.
"""
import base64

from xml.etree.ElementTree import Element
from typing import Optional

from .models import (
    NibObject,
    NibString,
    NibNil,
    NibData,
    NibList,
    NibMutableList,
    NibMutableSet,
    NibMutableDictionary,
    NibInlineString,
)


def _fixed_list() -> NibObject:
    return NibList([])


_LIST_CLASSES = {"NSMutableArray", "NSArray"}
_SET_CLASSES = {"NSMutableSet", "NSSet"}


class _ArchiveState:
    """Two-pass resolver: first collect all id="X" elements, then materialize
    on demand so cycles and forward references just work."""

    def __init__(self, root: Element) -> None:
        self.id_to_elem: dict[str, Element] = {}
        self.id_to_obj: dict[str, NibObject] = {}
        self.objectid_to_obj: dict[str, NibObject] = {}
        for elem in root.iter():
            xid = elem.get("id")
            if xid is not None:
                self.id_to_elem[xid] = elem

    def resolve_ref(self, ref_id: str) -> NibObject:
        if ref_id in self.id_to_obj:
            return self.id_to_obj[ref_id]
        elem = self.id_to_elem.get(ref_id)
        if elem is None:
            raise KeyError(f"archive: unknown reference id={ref_id!r}")
        return self._materialize(elem)

    def _materialize(self, elem: Element) -> NibObject:
        xid = elem.get("id")
        if xid is not None and xid in self.id_to_obj:
            return self.id_to_obj[xid]
        obj = self._alloc(elem)
        if xid is not None:
            self.id_to_obj[xid] = obj
        self._populate(elem, obj)
        return obj

    def _alloc(self, elem: Element) -> NibObject:
        tag = elem.tag
        if tag == "object":
            cls = elem.get("class") or "NSObject"
            if cls == "NSMutableDictionary":
                return NibMutableDictionary([])
            if cls in _LIST_CLASSES:
                return NibMutableList([]) if cls == "NSMutableArray" else _fixed_list()
            if cls in _SET_CLASSES:
                return NibMutableSet([])
            return NibObject(cls)
        if tag == "array":
            cls = elem.get("class")
            if cls == "NSArray":
                return _fixed_list()
            return NibMutableList([])
        if tag == "dictionary":
            return NibMutableDictionary([])
        if tag == "set":
            return NibMutableSet([])
        raise ValueError(f"archive: unexpected id-bearing element <{tag}>")

    def _populate(self, elem: Element, obj: NibObject) -> None:
        tag = elem.tag
        cls = elem.get("class")
        if tag == "object":
            if cls == "NSMutableDictionary":
                self._fill_dict(elem, obj)
                return
            if cls in _LIST_CLASSES or cls in _SET_CLASSES:
                for child in elem:
                    if child.get("key") is not None:
                        continue
                    obj.addItem(self.value_for(child))  # type: ignore[attr-defined]
                return
            for child in elem:
                key = child.get("key")
                if key is None:
                    continue
                obj[key] = self.value_for(child)
            return
        if tag == "array" or tag == "set":
            for child in elem:
                if child.get("key") is not None:
                    continue
                obj.addItem(self.value_for(child))  # type: ignore[attr-defined]
            return
        if tag == "dictionary":
            self._fill_dict(elem, obj)
            return

    def _fill_dict(self, elem: Element, d: NibObject) -> None:
        keyed: dict[str, "object"] = {}
        for child in elem:
            k = child.get("key")
            if k is None:
                continue
            keyed[k] = self.value_for(child)
        pair_idx = 0
        while True:
            k = keyed.pop(f"NS.key.{pair_idx}", None)
            v = keyed.pop(f"NS.object.{pair_idx}", None)
            if k is None or v is None:
                break
            d.addItem(k)  # type: ignore[attr-defined]
            d.addItem(v)  # type: ignore[attr-defined]
            pair_idx += 1
        for k, v in keyed.items():
            d.addItem(NibString.intern(k))  # type: ignore[attr-defined]
            d.addItem(v)  # type: ignore[attr-defined]

    def value_for(self, elem: Element):
        tag = elem.tag
        if tag == "reference":
            ref = elem.get("ref")
            if not ref:
                return NibNil()
            return self.resolve_ref(ref)
        if tag == "string":
            return NibString.intern(elem.text or "")
        if tag == "characters":
            return NibString.intern(elem.text or "")
        if tag in ("int", "integer"):
            val = elem.get("value")
            if val is None:
                val = (elem.text or "0").strip()
            return int(val)
        if tag in ("bool", "boolean"):
            val = elem.get("value")
            if val is None:
                val = (elem.text or "").strip()
            return val in ("YES", "1", "true")
        if tag in ("double", "float", "real"):
            val = elem.get("value")
            if val is None:
                val = (elem.text or "0").strip()
            return float(val)
        if tag == "nil":
            return NibNil()
        if tag == "bytes":
            raw = (elem.text or "").strip()
            rem = len(raw) % 4
            if rem == 1:
                raw = raw[:-1]
                rem = len(raw) % 4
            if rem:
                raw += "=" * (4 - rem)
            return NibData(base64.b64decode(raw))
        return self._materialize(elem)


def _build_nib_object_data(state: _ArchiveState, data_root: Element) -> NibObject:
    """Translate IBDocument.RootObjects + IBDocument.Objects into NSIBObjectData."""
    top_keyed: dict[str, Element] = {}
    for child in data_root:
        k = child.get("key")
        if k:
            top_keyed[k] = child

    root_objects_elem = top_keyed.get("IBDocument.RootObjects")
    objects_container_elem = top_keyed.get("IBDocument.Objects")
    if root_objects_elem is None or objects_container_elem is None:
        raise ValueError("archive: missing IBDocument.RootObjects or IBDocument.Objects")

    root_objects = state.value_for(root_objects_elem)

    container_keyed: dict[str, Element] = {}
    for child in objects_container_elem:
        k = child.get("key")
        if k:
            container_keyed[k] = child

    ns_objdata = NibObject("NSIBObjectData")

    files_owner = _find_named(state, container_keyed.get("objectRecords"), "File's Owner")
    if files_owner is not None:
        ns_objdata["NSRoot"] = files_owner

    ns_objdata["NSVisibleWindows"] = NibMutableSet([])
    ns_objdata["NSConnections"] = _build_connections(state, container_keyed.get("connectionRecords"))

    keys_arr, vals_arr = _build_object_map(state, container_keyed.get("objectRecords"))
    ns_objdata["NSObjectsKeys"] = keys_arr
    ns_objdata["NSObjectsValues"] = vals_arr
    ns_objdata["NSOidsKeys"] = NibList([])
    ns_objdata["NSOidsValues"] = NibList([])
    ns_objdata["NSAccessibilityConnectors"] = NibMutableList([])
    ns_objdata["NSAccessibilityOidsKeys"] = NibList([])
    ns_objdata["NSAccessibilityOidsValues"] = NibList([])

    _populate_visible_windows(state, container_keyed.get("flattenedProperties"),
                              root_objects, ns_objdata["NSVisibleWindows"])

    return ns_objdata


def _populate_visible_windows(state, flat_elem, root_objects, windows_set):
    """Add NSWindowTemplate objects flagged visibleAtLaunch=1 in flattenedProperties."""
    if flat_elem is None:
        return
    visible_ids: set[str] = set()
    for child in flat_elem:
        k = child.get("key") or ""
        if k.endswith(".NSWindowTemplate.visibleAtLaunch"):
            oid = k.split(".", 1)[0]
            val = child.get("value")
            if val is None:
                val = (child.text or "").strip()
            if val in ("1", "YES", "true"):
                visible_ids.add(oid)
    if not visible_ids:
        return
    # Map objectID -> object via objectRecords.
    id_to_obj: dict[str, NibObject] = {}
    # No direct objectID→obj map here; flattenedProperties keys reference objectRecords'
    # integer objectIDs which we capture in _build_object_map via side table below.
    for oid, obj in getattr(state, "objectid_to_obj", {}).items():
        id_to_obj[oid] = obj
    for oid in visible_ids:
        obj = id_to_obj.get(oid)
        if obj is not None:
            windows_set.addItem(obj)


def _find_named(state: _ArchiveState, records_elem: Optional[Element], name: str) -> Optional[NibObject]:
    if records_elem is None:
        return None
    ordered = records_elem.find("array[@key='orderedObjects']")
    if ordered is None:
        return None
    for rec in ordered:
        nm = rec.find("string[@key='objectName']")
        if nm is not None and (nm.text or "") == name:
            obj_ref = rec.find("*[@key='object']")
            if obj_ref is not None and obj_ref.tag == "reference":
                return state.resolve_ref(obj_ref.get("ref", ""))
    return None


_CONN_KEY_REMAP = {
    "label": "NSLabel",
    "source": "NSSource",
    "destination": "NSDestination",
}

_CONN_CLASS_REMAP = {
    "IBActionConnection": "NSNibControlConnector",
    "IBOutletConnection": "NSNibOutletConnector",
    "IBBindingConnection": "NSNibBindingConnector",
    "NSNibBindingConnector": "NSNibBindingConnector",
}


def _build_connection(state: _ArchiveState, conn_elem: Element) -> NibObject:
    src_cls = conn_elem.get("class") or "NSObject"
    if src_cls == "IBBindingConnection":
        nested = conn_elem.find("object[@key='connector']")
        if nested is not None:
            return state.value_for(nested)
    target_cls = _CONN_CLASS_REMAP.get(src_cls, src_cls)
    obj = NibObject(target_cls)
    for child in conn_elem:
        key = child.get("key")
        if key is None:
            continue
        mapped = _CONN_KEY_REMAP.get(key, key)
        obj[mapped] = state.value_for(child)
    return obj


def _build_connections(state: _ArchiveState, records_elem: Optional[Element]) -> NibObject:
    conns = NibMutableList([])
    if records_elem is None:
        return conns
    for rec in records_elem:
        if rec.tag != "object":
            continue
        conn_elem = rec.find("*[@key='connection']")
        if conn_elem is None:
            continue
        conns.addItem(_build_connection(state, conn_elem))
    return conns


def _build_object_map(state: _ArchiveState, records_elem: Optional[Element]):
    keys = NibList([])
    vals = NibList([])
    if records_elem is None:
        return keys, vals
    for rec in records_elem:
        obj_child = rec.find("*[@key='object']")
        parent_child = rec.find("*[@key='parent']")
        id_child = rec.find("int[@key='objectID']")
        if obj_child is None or obj_child.tag != "reference":
            continue
        obj = state.resolve_ref(obj_child.get("ref", ""))
        keys.addItem(obj)
        if parent_child is not None and parent_child.tag == "reference":
            vals.addItem(state.resolve_ref(parent_child.get("ref", "")))
        else:
            vals.addItem(NibNil())
        if id_child is not None:
            oid = (id_child.text or "").strip()
            if oid:
                state.objectid_to_obj[oid] = obj
    return keys, vals


def parse_archive(root: Element) -> NibObject:
    data_elem = root.find("data")
    if data_elem is None:
        raise ValueError("archive: missing <data> element")
    state = _ArchiveState(root)
    ns_objdata = _build_nib_object_data(state, data_elem)

    top = NibObject("NSObject")
    top["IB.objectdata"] = ns_objdata
    top["IB.systemFontUpdateVersion"] = 1
    return top
