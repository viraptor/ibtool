from .ibdump import getNibSections, getNibSectionsFile, NibStructure
import sys
from typing import Any, Union, cast, Iterable, Optional

class NibCollection:
    def __init__(self, classname: str, entries: list[Any], nibidx: int = -1):
        self.classname = classname
        self.entries = entries
        self.nibidx = nibidx

    def __repr__(self):
        return f"{self.classname} ({len(self.entries)} entries)"

    def rec_hash(self, path, cache=None):
        if cache is None:
            cache = {}
        if id(self) in cache:
            return cache[id(self)]
        if id(self) in path:
            return 999
        path_next = path + [id(self)]
        result = hash((self.classname, tuple([x.rec_hash(path_next, cache) if getattr(x, "rec_hash", None) else x for x in self.entries])))
        cache[id(self)] = result
        return result

class NibObject:
    def __init__(self, classname: str, entries: dict[str,Any], nibidx: int = -1):
        self.classname = classname
        self.entries = entries
        self.nibidx = nibidx

    def __eq__(self, other):
        assert isinstance(other, NibObject), type(other)
        return self.classname == other.classname and len(self.entries) == len(other.entries)

    def __lt__(self, other):
        assert isinstance(other, NibObject), type(other)
        return (self.classname, len(other.entries)) < (other.classname, len(other.entries))

    def __repr__(self):
        return f"{self.classname} ({len(self.entries)} entries)"

    def rec_hash(self, path, cache=None):
        if cache is None:
            cache = {}
        if id(self) in cache:
            return cache[id(self)]
        if id(self) in path:
            return 999
        path_next = path + [id(self)]
        result = hash((self.classname, tuple([(k,v.rec_hash(path_next, cache) if getattr(v, "rec_hash", None) else v) for k,v in self.entries.items()])))
        cache[id(self)] = result
        return result

class NibValue:
    def __init__(self, value: Any, vtype: int):
        self.value = value
        self.type = vtype

    def __eq__(self, other):
        if not isinstance(other, NibValue):
            return False
        return self.value == other.value and self.type == other.type

    def __lt__(self, other):
        assert isinstance(other, NibValue), type(other)
        return self.value < other.value

    def __repr__(self):
        return f"{self.value} (type {self.type})"

    def __hash__(self):
        return hash((self.value, self.type))

def pythonObjects(nib: NibStructure) -> tuple[NibObject, list[Any]]:
    objects, keys, values, classes = nib

    res: dict[int,Union[NibObject,NibCollection]] = {}

    for o_idx, obj_tup in enumerate(objects):
        classname = classes[obj_tup[0]]
        obj_values = values[obj_tup[1] : obj_tup[1] + obj_tup[2]]

        if classname in ['NSArray', 'NSMutableArray', 'NSMutableSet', 'NSDictionary', 'NSMutableDictionary']:
            lentries: list[Any] = []
            for k_idx, v, v_type in obj_values:
                if keys[k_idx] == 'NSInlinedValue':
                    continue
                assert keys[k_idx] == 'UINibEncoderEmptyKey', keys[k_idx]
                lentries.append(NibValue(v, v_type))
            res[o_idx] = NibCollection(classname, lentries, nibidx=o_idx)
        else:
            dentries: dict[str,Any] = {}
            for k_idx, v, v_type in obj_values:
                if keys[k_idx] not in dentries:
                    dentries[keys[k_idx]] = NibValue(v, v_type)
            res[o_idx] = NibObject(classname, dentries, nibidx=o_idx)

    for obj in res.values():
        if isinstance(obj.entries, list):
            for entry_idx in range(len(obj.entries)):
                if obj.entries[entry_idx].type == 0xa:
                    idx = int(obj.entries[entry_idx].value[1:])
                    obj.entries[entry_idx] = res[idx]
        elif isinstance(obj.entries, dict):
            for entry_k in obj.entries:
                if obj.entries[entry_k].type == 0xa:
                    idx = int(obj.entries[entry_k].value[1:])
                    obj.entries[entry_k] = res[idx]
        else:
            raise Exception(f"bad value type {type(obj_values)}")

    for obj in res.values():
        if isinstance(obj, NibObject):
            for k,v in obj.entries.items():
                if k == 'NSClassName':
                    obj.classname += f"/{v.entries['NS.bytes'].value}"
    #for k in res:
    #    print('---', k, res[k])
    #    if isinstance(res[k], NibObject):
    #        for k2 in res[k].entries:
    #            print(k2, type(res[k].entries[k2]))
    #    if isinstance(res[k], NibCollection):
    #        for v in res[k].entries:
    #            print(type(v))


    #not_referenced = list(res.values())[1:]
    #for k,v in res.items():
    #    if v[1] == 0xa:
    #        not_refernced.remove(v[0])

    return cast(NibObject, res[0]), [] #not_referenced

already_seen = set()

def _xib_annotation(obj: Union[NibValue,NibCollection,NibObject], xibid_map: Optional[dict[int,str]]) -> str:
    """Return ' [xib:ID]' annotation if the object has a known XIB id, else ''."""
    if xibid_map is None:
        return ""
    nibidx = getattr(obj, 'nibidx', -1)
    if nibidx >= 0 and nibidx in xibid_map:
        return f" [xib:{xibid_map[nibidx]}]"
    return ""

def diff(lhs: Union[NibValue,NibCollection,NibObject], rhs: Union[NibValue,NibCollection,NibObject], lhs_root: list[Union[NibValue,NibCollection,NibObject]], rhs_root: list[Union[NibValue,NibCollection,NibObject]], current_path: list[str]=[], lhs_path: list[int]=[], rhs_path: list[int]=[], parent_class: Optional[str] = None, xibid_map: Optional[dict[int,str]] = None) -> Iterable[str]:
    if (id(lhs), id(rhs)) in already_seen:
        return
    already_seen.add((id(lhs), id(rhs)))
    lhs_path = lhs_path + [id(lhs)]
    rhs_path = rhs_path + [id(rhs)]

    path = '->'.join(str(key) for key in current_path)

    if path.endswith("NSOidsValues") or path.endswith("NSAccessibilityOidsValues") or path.endswith("NSAccessibilityOidsKeys"):
        return

    if type(lhs) != type(rhs):
        yield f"{path}{_xib_annotation(rhs, xibid_map)} (in {parent_class}): Types don't match {type(lhs)} != {type(rhs)}"
        return

    if isinstance(lhs, NibValue) and isinstance(rhs, NibValue):
        if lhs.type != rhs.type:
            yield f"{path} (in {parent_class}): Object types don't match {lhs.type} != {rhs.type}"

        if type(lhs.value) is bytes and lhs.value.startswith(b"NIBArchive") and not rhs.value.startswith(b"NIBArchive"):
            yield f"{path} (in {parent_class}): LHS is a NIB, but RHS isn't"
        elif type(rhs.value) is bytes and rhs.value.startswith(b"NIBArchive") and not lhs.value.startswith(b"NIBArchive"):
            yield f"{path} (in {parent_class}): RHS is a NIB, but LHS isn't"
        elif type(lhs.value) is bytes and lhs.value.startswith(b"NIBArchive"):
            nib_left = getNibSections(lhs.value, "(inlined)")
            nib_left_root, _ = pythonObjects(nib_left)
            nib_right = getNibSections(rhs.value, "(inlined)")
            nib_right_root, _ = pythonObjects(nib_right)
            nib_left_objects = nib_left_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries
            nib_right_objects = nib_right_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries
            fixup_layout_constrints(nib_left_objects, nib_left_objects)
            fixup_layout_constrints(nib_right_objects, nib_right_objects)
            nib_left_oids = nib_left_root.entries["IB.objectdata"].entries.get("NSOidsKeys")
            nib_right_oids = nib_right_root.entries["IB.objectdata"].entries.get("NSOidsKeys")
            if nib_left_oids is not None:
                fixup_layout_constrints(nib_left_oids.entries, nib_left_objects)
            if nib_right_oids is not None:
                fixup_layout_constrints(nib_right_oids.entries, nib_right_objects)
            yield from diff(nib_left_root, nib_right_root, nib_left_objects, nib_right_objects, current_path + ["nib"], [], [], xibid_map=xibid_map)

        elif type(lhs.value) in [int, str, float, bytes, type(None)]:
            if lhs.value != rhs.value:
                if (path.endswith("Flags") or path.endswith("Flags2") or path.endswith("Mask")) and isinstance(lhs.value, int) and isinstance(rhs.value, int):
                    lval = lhs.value if lhs.value >= 0 else lhs.value + 0x10000000000000000
                    rval = rhs.value if rhs.value >= 0 else rhs.value + 0x10000000000000000
                    yield f"{path} (in {parent_class}): difference {hex(lval)} != {hex(rval)}"
                else:
                    yield f"{path} (in {parent_class}): difference {lhs.value} != {rhs.value}"
            return
        return

    assert isinstance(lhs, NibObject) or isinstance(lhs, NibCollection), type(lhs)
    assert isinstance(rhs, NibObject) or isinstance(rhs, NibCollection), type(rhs)

    annotation = _xib_annotation(rhs, xibid_map)

    connector_classes = ("NSNibConnector", "NSNibOutletConnector", "NSNibControlConnector", "NSNibAuxiliaryActionConnector", "NSIBHelpConnector", "NSNibBindingConnector", "NSIBUserDefinedRuntimeAttributesConnector")
    if lhs.classname in connector_classes and rhs.classname in connector_classes:
        # Connections are unordered
        return
    if lhs.classname != rhs.classname:
        yield f"{path}{annotation} (in {parent_class}): Class name doesn't match {lhs.classname} != {rhs.classname}"
        return
    if type(lhs.entries) != type(rhs.entries):
        yield f"{path}{annotation} (in {parent_class}): Values types don't match"
        return

    l_ind = lhs_path.index(id(lhs))
    r_ind = rhs_path.index(id(rhs))

    if l_ind != r_ind:
        yield f"{path}: Cycle to different places"
        return
    if l_ind < len(lhs_path)-1:
        # don't get stuck in a loop
        return

    if path.endswith("NSViewConstraints"):
        # They're hopefully unordered. TODO match the apple's order later
        if len(lhs.entries) != len(rhs.entries):
            yield f"{path}{annotation} Mismatched length: {len(lhs.entries)} != {len(rhs.entries)}"
        fixup_layout_constrints(lhs.entries, lhs_root)
        fixup_layout_constrints(rhs.entries, rhs_root)
        for i, (left, right) in enumerate(zip(lhs.entries, rhs.entries)):
            yield from diff(left, right, lhs_root, rhs_root, current_path + [str(i)], lhs_path, rhs_path, lhs.classname, xibid_map=xibid_map)
    elif path.endswith("NSConnections"):
        cache = {}
        lhs_entries = sorted(lhs.entries, key=lambda x: x.rec_hash([], cache))
        rhs_entries = sorted(rhs.entries, key=lambda x: x.rec_hash([], cache))
        for i, (left, right) in enumerate(zip(lhs_entries, rhs_entries)):
            yield from diff(left, right, lhs_root, rhs_root, current_path + [str(i)], lhs_path, rhs_path, lhs.classname, xibid_map=xibid_map)
    elif path.endswith("NSAccessibilityConnectors"):
        def ax_sort_key(x):
            dest = x.entries.get("AXDestinationArchiveKey")
            val = x.entries.get("AXAttributeValueArchiveKey")
            dest_cls = dest.classname if dest else ""
            dest_name = ""
            if dest and hasattr(dest, 'entries'):
                n = dest.entries.get("NSClassName")
                if n and hasattr(n, 'entries'):
                    b = n.entries.get("NS.bytes")
                    if b and hasattr(b, 'value'):
                        dest_name = str(b.value)
            val_str = ""
            if val and hasattr(val, 'entries'):
                b = val.entries.get("NS.bytes")
                if b and hasattr(b, 'value'):
                    val_str = str(b.value)
            return (val_str, dest_cls, dest_name)
        lhs_entries = sorted(lhs.entries, key=ax_sort_key)
        rhs_entries = sorted(rhs.entries, key=ax_sort_key)
        for i, (left, right) in enumerate(zip(lhs_entries, rhs_entries)):
            yield from diff(left, right, lhs_root, rhs_root, current_path + [str(i)], lhs_path, rhs_path, lhs.classname, xibid_map=xibid_map)
    elif isinstance(lhs, NibCollection) and isinstance(rhs, NibCollection):
        l_entries = lhs.entries
        r_entries = rhs.entries
        if path.endswith("NSSubviews"):
            l_entries = [e for e in l_entries if not (isinstance(e, NibObject) and e.classname == "_NSCornerView")]
            r_entries = [e for e in r_entries if not (isinstance(e, NibObject) and e.classname == "_NSCornerView")]
        if len(l_entries) != len(r_entries):
            yield f"{path}{annotation} Mismatched length: {len(l_entries)} != {len(r_entries)}"
        for i, (left, right) in enumerate(zip(l_entries, r_entries)):
            yield from diff(left, right, lhs_root, rhs_root, current_path + [str(i)], lhs_path, rhs_path, lhs.classname, xibid_map=xibid_map)
    elif isinstance(lhs, NibObject) and isinstance(rhs, NibObject):
        all_keys = set(list(lhs.entries.keys()) + list(rhs.entries.keys()))
        if lhs.classname == "_NSCornerView":
            all_keys -= {"NSNextResponder", "NSSuperview", "NSvFlags"}
        if lhs.classname == "NSScrollView":
            all_keys -= {"NSCornerView"}
        for key in sorted(all_keys):
            if key not in lhs.entries:
                rval = rhs.entries.get(key)
                if (key.endswith("Flags") or key.endswith("Flags2") or key.endswith("Mask")) and isinstance(rval.value, int):
                    rval = rval.value
                    rval = hex(rval if rval >= 0 else rval + 0x10000000000000000)

                yield f"{path}{annotation} LHS ({lhs.classname}) missing key {key}, RHS {rval}"
                continue
            if key not in rhs.entries:
                lval = lhs.entries.get(key)
                if (key.endswith("Flags") or key.endswith("Flags2") or key.endswith("Mask")) and isinstance(lval.value, int):
                    lval = lval.value
                    lval = hex(lval if lval >= 0 else lval + 0x10000000000000000)

                yield f"{path}{annotation} RHS ({rhs.classname}) missing key {key}, LHS {lval}"
                continue
            yield from diff(lhs.entries[key], rhs.entries[key], lhs_root, rhs_root, current_path + [key], lhs_path, rhs_path, lhs.classname, xibid_map=xibid_map)
    else:
        raise Exception(f"Unknown type {type(lhs)}")

def fixup_layout_constrints(collection, all_objects):
    # We need to order the layout constraints explicitly for comparison. Apple's tool uses random order.
    def constraint_sort_key(obj):
        def _item_key(item):
            if item is None:
                return ("", b"")
            frame = item.entries.get("NSFrame")
            frame_bytes = frame.entries.get("NS.bytes").value if frame is not None and hasattr(frame, "entries") and frame.entries.get("NS.bytes") is not None else b""
            return (item.classname, frame_bytes)
        first = obj.entries.get("NSFirstAttribute").value if obj.entries.get("NSFirstAttribute") is not None else -1
        firstv2 = obj.entries.get("NSFirstAttributeV2").value if obj.entries.get("NSFirstAttributeV2") is not None else -1
        second = obj.entries.get("NSSecondAttribute").value if obj.entries.get("NSSecondAttribute") is not None else -1
        secondv2 = obj.entries.get("NSSecondAttributeV2").value if obj.entries.get("NSSecondAttributeV2") is not None else -1
        firstitem_key = _item_key(obj.entries.get("NSFirstItem"))
        seconditem_key = _item_key(obj.entries.get("NSSecondItem"))
        priority = obj.entries.get("NSPriority").value if obj.entries.get("NSPriority") is not None else -1
        constantval = obj.entries.get("NSConstantValue").value if obj.entries.get("NSConstantValue") is not None else -1
        constantvalv2 = obj.entries.get("NSConstantValueV2").value if obj.entries.get("NSConstantValueV2") is not None else -1
        constant = obj.entries.get("NSConstant").value if obj.entries.get("NSConstant") is not None else -1
        constantv2 = obj.entries.get("NSConstantV2").value if obj.entries.get("NSConstantV2") is not None else -1
        symbolic = obj.entries.get("NSSymbolicConstant").entries["NS.bytes"].value if obj.entries.get("NSSymbolicConstant") is not None else b""
        relation = obj.entries.get("NSRelation").value if obj.entries.get("NSRelation") is not None else -1
        return (first, firstv2, second, secondv2, priority, constantval, constantvalv2, constant, constantv2, symbolic, relation, firstitem_key, seconditem_key)

    all_objects_copy = all_objects.copy()
    constraint_indices = [i for i, obj in enumerate(collection)
                          if any(obj is k and k.classname == "NSLayoutConstraint" for k in all_objects_copy)
                          or (obj.classname == "NSLayoutConstraint" if hasattr(obj, "classname") else False)]
    constraints = [collection[i] for i in constraint_indices]
    constraints.sort(key=constraint_sort_key)
    for idx, sorted_obj in zip(constraint_indices, constraints):
        collection[idx] = sorted_obj

def fixup_connections(collection):
    connector_classes = {"NSNibConnector", "NSNibOutletConnector", "NSNibControlConnector",
        "NSNibAuxiliaryActionConnector", "NSIBHelpConnector", "NSNibBindingConnector",
        "NSIBUserDefinedRuntimeAttributesConnector"}
    connectors = [x for x in collection if x.classname in connector_classes]
    non_connectors = [x for x in collection if x.classname not in connector_classes]
    def conn_sort_key(c):
        cls = c.classname
        dest = c.entries.get("NSDestination")
        dest_cls = dest.classname if dest is not None else ""
        src = c.entries.get("NSSource")
        src_cls = src.classname if src is not None else ""
        label = c.entries.get("NSLabel")
        label_val = label.entries.get("NS.bytes").value if label is not None and hasattr(label, "entries") and label.entries.get("NS.bytes") is not None else b""
        return (cls, dest_cls, src_cls, label_val)
    connectors.sort(key=conn_sort_key)
    collection[:] = non_connectors + connectors

def main(orig_path, test_path, xib_path=None):
    orig_nib = getNibSectionsFile(orig_path)
    test_nib = getNibSectionsFile(test_path)

    orig_root, orig_rest = pythonObjects(orig_nib)
    test_root, test_rest = pythonObjects(test_nib)

    if orig_rest:
        print("original has unreferenced items")
    if test_rest:
        print("test has unreferenced items")

    # Build xibid map if a XIB source file is provided
    xibid_map = None
    if xib_path:
        from .xibmap import build_nibidx_to_xibid
        xibid_map = build_nibidx_to_xibid(xib_path)

    found_issues = False
    orig_objects = orig_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries
    test_objects = test_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries
    fixup_layout_constrints(orig_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries, orig_objects)
    fixup_layout_constrints(test_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries, test_objects)
    fixup_layout_constrints(orig_root.entries["IB.objectdata"].entries["NSOidsKeys"].entries, orig_objects)
    fixup_layout_constrints(test_root.entries["IB.objectdata"].entries["NSOidsKeys"].entries, test_objects)
    fixup_connections(orig_root.entries["IB.objectdata"].entries["NSOidsKeys"].entries)
    fixup_connections(test_root.entries["IB.objectdata"].entries["NSOidsKeys"].entries)
    for issue in diff(orig_root, test_root, lhs_root=orig_objects, rhs_root=test_objects, xibid_map=xibid_map):
        found_issues = True
        print(issue)
    sys.exit(int(found_issues))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
