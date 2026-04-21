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
    ArrayLike,
    NibObject,
    NibNSNumber,
    NibString,
    NibNil,
    NibData,
    NibList,
    NibDictionary,
    NibMutableList,
    NibMutableSet,
    NibMutableDictionary,
    NibInlineString,
)


def _wrap_primitive(val):
    if isinstance(val, bool) or isinstance(val, int) or isinstance(val, float):
        return NibNSNumber(val)
    return val


def _fixed_list() -> NibObject:
    return NibList([])


_LIST_CLASSES = {"NSMutableArray", "NSArray"}
_SET_CLASSES = {"NSMutableSet", "NSSet"}

def _attach_view_constraints(state: "_ArchiveState") -> None:
    """Attach constraints to their containing views as NSViewConstraints."""
    if not state.view_constraints:
        return
    id_to_view: dict[int, NibObject] = {}
    for obj in state.id_to_obj.values():
        id_to_view[id(obj)] = obj
    for view_id, constraints in state.view_constraints.items():
        view = id_to_view.get(view_id)
        if view is None:
            continue
        existing = view.get("NSViewConstraints")
        if existing is None:
            lst = NibList(constraints)
            view["NSViewConstraints"] = lst
        elif hasattr(existing, "addItem"):
            for c in constraints:
                existing.addItem(c)  # type: ignore[attr-defined]


def _finalize_constraint(obj: NibObject) -> None:
    """Shape an archive IBNSLayoutConstraint to match Apple's compiled form."""
    for noisy in ("NSContainingView", "NSMultiplier", "NSPriority", "NSRelation",
                  "NSScoringType", "NSScoringTypeFloat", "NSLayoutConstraintContentType"):
        obj.properties.pop(noisy, None)
    first_attr = obj.properties.get("NSFirstAttribute")
    if first_attr is not None and "NSFirstAttributeV2" not in obj.properties:
        obj["NSFirstAttributeV2"] = first_attr
    second_attr = obj.properties.get("NSSecondAttribute")
    if second_attr is not None and "NSSecondAttributeV2" not in obj.properties:
        obj["NSSecondAttributeV2"] = second_attr
    if "NSSecondItem" not in obj.properties:
        constant = obj.properties.get("NSConstant")
        if constant is not None and "NSConstantV2" not in obj.properties:
            obj["NSConstantV2"] = constant
    else:
        obj.properties.pop("NSConstant", None)
        obj.properties.pop("NSConstantV2", None)
    obj.setIfEmpty("NSShouldBeArchived", True)


_LAYOUT_KEY_REMAP = {
    "firstItem": "NSFirstItem",
    "firstAttribute": "NSFirstAttribute",
    "relation": "NSRelation",
    "secondItem": "NSSecondItem",
    "secondAttribute": "NSSecondAttribute",
    "multiplier": "NSMultiplier",
    "constant": "NSConstant",
    "priority": "NSPriority",
    "containingView": "NSContainingView",
    "scoringType": "NSScoringType",
    "scoringTypeFloat": "NSScoringTypeFloat",
    "contentType": "NSLayoutConstraintContentType",
}

_CLASS_REMAP = {
    "IBNSLayoutConstraint": "NSLayoutConstraint",
}


class _ArchiveState:
    """Two-pass resolver: first collect all id="X" elements, then materialize
    on demand so cycles and forward references just work."""

    def __init__(self, root: Element) -> None:
        self.id_to_elem: dict[str, Element] = {}
        self.id_to_obj: dict[str, NibObject] = {}
        self.objectid_to_obj: dict[str, NibObject] = {}
        self.view_constraints: dict[int, list[NibObject]] = {}
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
            if cls == "NSDictionary":
                return NibDictionary([])
            if cls in _LIST_CLASSES:
                return NibMutableList([]) if cls == "NSMutableArray" else _fixed_list()
            if cls in _SET_CLASSES:
                return NibMutableSet([])
            cls = _CLASS_REMAP.get(cls, cls)
            return NibObject(cls)
        if tag == "array":
            cls = elem.get("class")
            if cls == "NSMutableArray":
                return NibMutableList([])
            return _fixed_list()
        if tag == "dictionary":
            cls = elem.get("class")
            if cls == "NSMutableDictionary":
                return NibMutableDictionary([])
            return NibDictionary([])
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
                    obj.addItem(_wrap_primitive(self.value_for(child)))  # type: ignore[attr-defined]
                return
            is_layout = cls == "IBNSLayoutConstraint"
            for child in elem:
                key = child.get("key")
                if key is None:
                    continue
                value = self.value_for(child)
                if is_layout and key in _LAYOUT_KEY_REMAP:
                    key = _LAYOUT_KEY_REMAP[key]
                if is_layout and key == "NSConstant" and isinstance(value, NibObject):
                    inner_cls = value.classname()
                    inner = value.get("value")
                    if inner_cls == "IBNSLayoutSymbolicConstant":
                        key = "NSSymbolicConstant"
                        if isinstance(inner, (int, float)) and float(inner) == 20.0:
                            value = NibString.intern("NSSpace")
                        else:
                            value = NibString.intern(str(inner))
                    elif inner is not None:
                        value = inner
                if is_layout and key == "NSSecondItem" and isinstance(value, NibNil):
                    continue
                obj[key] = value
            if is_layout:
                container = obj.properties.get("NSContainingView")
                if isinstance(container, NibObject):
                    self.view_constraints.setdefault(id(container), []).append(obj)
                _finalize_constraint(obj)
            return
        if tag == "array" or tag == "set":
            for child in elem:
                if child.get("key") is not None:
                    continue
                obj.addItem(_wrap_primitive(self.value_for(child)))  # type: ignore[attr-defined]
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
            return NibInlineString(base64.b64decode(raw))
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
    state.files_owner = files_owner  # type: ignore[attr-defined]

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
    # Action connections store source=receiver / destination=sender; the NIB
    # format flips the roles so NSSource is the control firing the action.
    key_map = dict(_CONN_KEY_REMAP)
    if src_cls == "IBActionConnection":
        key_map["source"] = "NSDestination"
        key_map["destination"] = "NSSource"
    for child in conn_elem:
        key = child.get("key")
        if key is None:
            continue
        mapped = key_map.get(key, key)
        obj[mapped] = state.value_for(child)
    if src_cls == "IBOutletConnection":
        obj["NSChildControllerCreationSelectorName"] = NibNil()
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
    ordered = records_elem.find("array[@key='orderedObjects']")
    if ordered is None:
        ordered = records_elem

    # Index every record by the id of its `object` reference, and find the
    # root placeholder (the synthetic array with id).
    records_by_ref: dict[str, Element] = {}
    root_placeholder_id: Optional[str] = None
    root_record: Optional[Element] = None
    for rec in ordered:
        obj_child = rec.find("*[@key='object']")
        if obj_child is None:
            continue
        if obj_child.tag == "array" and obj_child.get("id") is not None:
            root_placeholder_id = obj_child.get("id")
            root_record = rec
            continue
        if obj_child.tag == "reference":
            records_by_ref[obj_child.get("ref", "")] = rec

    def record_children(rec: Element) -> list[str]:
        ch = rec.find("*[@key='children']")
        if ch is None:
            return []
        target = ch
        if ch.tag == "reference":
            target = state.id_to_elem.get(ch.get("ref", ""))
            if target is None:
                return []
        result: list[str] = []
        for c in target:
            if c.get("key") is not None:
                continue
            if c.tag == "reference":
                result.append(c.get("ref", ""))
            elif c.tag == "object":
                cid = c.get("id")
                if cid is not None:
                    result.append(cid)
        return result

    # Depth-first walk the children tree starting from the root placeholder.
    order: list[tuple[str, str, Element]] = []  # (ref_id, parent_ref_id, rec)
    if root_record is not None:
        def walk(rec: Element, parent_ref: str) -> None:
            for child_ref in record_children(rec):
                child_rec = records_by_ref.get(child_ref)
                if child_rec is None:
                    continue
                order.append((child_ref, parent_ref, child_rec))
                walk(child_rec, child_ref)
        walk(root_record, "")

    # Also emit any records that weren't reachable via the children walk,
    # in their original XML order. Keeps objects that the archive registered
    # but didn't link through the children tree (e.g. top-level placeholders
    # other than File's Owner, layout constraints, etc.).
    walked: set[str] = {entry[0] for entry in order}
    for rec in ordered:
        obj_child = rec.find("*[@key='object']")
        if obj_child is None or obj_child.tag != "reference":
            continue
        ref_id = obj_child.get("ref", "")
        if ref_id in walked:
            continue
        parent_child = rec.find("*[@key='parent']")
        parent_ref = parent_child.get("ref", "") if (parent_child is not None and parent_child.tag == "reference") else ""
        order.append((ref_id, parent_ref, rec))
        walked.add(ref_id)

    seen_refs: set[str] = set()
    for ref_id, parent_ref, rec in order:
        name_child = rec.find("string[@key='objectName']")
        if name_child is not None and (name_child.text or "") == "First Responder":
            continue
        if ref_id in seen_refs:
            continue
        ref_elem = state.id_to_elem.get(ref_id)
        if ref_elem is not None and ref_elem.get("class") == "NSCustomObject":
            cls_child = ref_elem.find("string[@key='NSClassName']")
            cls_name = cls_child.text if cls_child is not None else None
            if cls_name:
                dup = False
                for seen in seen_refs:
                    seen_elem = state.id_to_elem.get(seen)
                    if seen_elem is not None and seen_elem.get("class") == "NSCustomObject":
                        seen_cls = seen_elem.find("string[@key='NSClassName']")
                        if seen_cls is not None and seen_cls.text == cls_name:
                            dup = True
                            break
                if dup:
                    continue
        seen_refs.add(ref_id)
        obj = state.resolve_ref(ref_id)
        keys.addItem(obj)
        if parent_ref == root_placeholder_id and getattr(state, "files_owner", None) is not None:
            vals.addItem(state.files_owner)
        elif parent_ref:
            vals.addItem(state.resolve_ref(parent_ref))
        else:
            vals.addItem(NibNil())
        id_child = rec.find("int[@key='objectID']")
        if id_child is not None:
            oid = (id_child.text or "").strip()
            if oid:
                state.objectid_to_obj[oid] = obj
    return keys, vals


_VIEW_DEFAULT_CLASSES = {
    "NSView", "NSCustomView", "NSBox", "NSTextView", "NSTextField",
    "NSButton", "NSImageView", "NSScrollView", "NSClipView", "NSScroller",
    "NSSplitView", "NSTableView", "NSOutlineView", "NSTabView", "NSStackView",
    "NSControl", "NSPopUpButton", "NSComboBox", "NSSlider", "NSProgressIndicator",
    "NSSecureTextField", "NSSearchField", "NSTokenField", "NSColorWell",
    "NSSegmentedControl", "NSLevelIndicator", "NSMatrix", "NSRuleEditor",
    "NSPathControl", "NSBrowser", "NSDatePicker", "NSStepper",
}

_CONTROL_CLASSES = {
    "NSButton", "NSImageView", "NSTextField", "NSSecureTextField",
    "NSSearchField", "NSTokenField", "NSComboBox", "NSPopUpButton",
    "NSSlider", "NSScroller", "NSSegmentedControl", "NSLevelIndicator",
    "NSColorWell", "NSPathControl", "NSBrowser", "NSDatePicker",
    "NSStepper", "NSMatrix", "NSRuleEditor", "NSProgressIndicator",
    "NSControl",
}


def _apply_view_defaults(obj: NibObject, seen: set) -> None:
    if id(obj) in seen:
        return
    seen.add(id(obj))
    cls = obj.classname() if hasattr(obj, "classname") else None
    if cls in _VIEW_DEFAULT_CLASSES:
        obj.setIfEmpty("IBNSClipsToBounds", 0)
        obj.setIfEmpty("IBNSLayoutMarginsGuide", NibNil())
        obj.setIfEmpty("IBNSSafeAreaLayoutGuide", NibNil())
        obj.setIfEmpty("NSViewWantsBestResolutionOpenGLSurface", True)
        obj.setIfEmpty("NSNibTouchBar", NibNil())
    if cls == "NSScroller":
        obj.setIfEmpty("NSViewIsLayerTreeHost", True)
    if cls in _CONTROL_CLASSES:
        action = obj.properties.get("NSAction")
        if action is not None and "NSControlAction" not in obj.properties:
            obj["NSControlAction"] = action
        target = obj.properties.get("NSTarget")
        if target is not None and "NSControlTarget" not in obj.properties:
            obj["NSControlTarget"] = target
        obj.setIfEmpty("NSControlSize", 0)
        obj.setIfEmpty("NSControlContinuous", False)
        obj.setIfEmpty("NSControlRefusesFirstResponder", False)
        obj.setIfEmpty("NSControlUsesSingleLineMode", False)
        obj.setIfEmpty("NSControlTextAlignment", 0)
        obj.setIfEmpty("NSControlLineBreakMode", 0)
        obj.setIfEmpty("NSControlWritingDirection", 0)
        obj.setIfEmpty("NSControlSendActionMask", 4)
    if cls == "NSClipView":
        obj.setIfEmpty("NSAutomaticallyAdjustsContentInsets", True)
    if cls == "NSImage":
        obj.setIfEmpty("NSResizingMode", 0)
        obj.setIfEmpty("NSTintColor", NibNil())
    if cls == "NSMenuItem":
        obj.setIfEmpty("NSAllowedForLimitedAppMode", True)
        obj.setIfEmpty("NSAllowsKeyEquivalentLocalization", True)
        obj.setIfEmpty("NSAllowsKeyEquivalentMirroring", True)
        obj.setIfEmpty("NSHiddenInRepresentation", False)
    if isinstance(obj, ArrayLike):
        for item in obj.items():
            if isinstance(item, NibObject):
                _apply_view_defaults(item, seen)
    for v in list(obj.properties.values()):
        if isinstance(v, NibObject):
            _apply_view_defaults(v, seen)


def parse_archive(root: Element) -> NibObject:
    data_elem = root.find("data")
    if data_elem is None:
        raise ValueError("archive: missing <data> element")
    state = _ArchiveState(root)
    ns_objdata = _build_nib_object_data(state, data_elem)
    _attach_view_constraints(state)
    _apply_view_defaults(ns_objdata, set())

    top = NibObject("NSObject")
    top["IB.objectdata"] = ns_objdata
    top["IB.systemFontUpdateVersion"] = 1
    return top
