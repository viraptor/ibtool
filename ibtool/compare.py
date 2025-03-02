from .ibdump import getNibSections, getNibSectionsFile, NibStructure
import sys
from typing import Any, Union, cast, Iterable, Optional

class NibCollection:
    def __init__(self, classname: str, entries: list[Any]):
        self.classname = classname
        self.entries = entries

    def __repr__(self):
        return f"{self.classname} ({len(self.entries)} entries)"

    def rec_hash(self, path):
        if id(self) in path:
            return 999
        else:
            return hash((self.classname, tuple([x.rec_hash(path + [id(self)]) if getattr(x, "rec_hash", None) else x for x in self.entries])))

class NibObject:
    def __init__(self, classname: str, entries: dict[str,Any]):
        self.classname = classname
        self.entries = entries

    def __eq__(self, other):
        assert isinstance(other, NibObject), type(other)
        return self.classname == other.classname and len(self.entries) == len(other.entries)

    def __lt__(self, other):
        assert isinstance(other, NibObject), type(other)
        return (self.classname, len(other.entries)) < (other.classname, len(other.entries))

    def __repr__(self):
        return f"{self.classname} ({len(self.entries)} entries)"

    def rec_hash(self, path):
        if id(self) in path:
            return 999
        else:
            return hash((self.classname, tuple([(k,v.rec_hash(path + [id(self)]) if getattr(v, "rec_hash", None) else v) for k,v in self.entries.items()])))

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
            res[o_idx] = NibCollection(classname, lentries)
        else:
            dentries: dict[str,Any] = {}
            for k_idx, v, v_type in obj_values:
                if keys[k_idx] not in dentries:
                    dentries[keys[k_idx]] = NibValue(v, v_type)
            res[o_idx] = NibObject(classname, dentries)

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

def diff(lhs: Union[NibValue,NibCollection,NibObject], rhs: Union[NibValue,NibCollection,NibObject], lhs_root: list[Union[NibValue,NibCollection,NibObject]], rhs_root: list[Union[NibValue,NibCollection,NibObject]], current_path: list[str]=[], lhs_path: list[int]=[], rhs_path: list[int]=[], parent_class: Optional[str] = None) -> Iterable[str]:
    if (id(lhs), id(rhs)) in already_seen:
        return
    already_seen.add((id(lhs), id(rhs)))
    lhs_path = lhs_path + [id(lhs)]
    rhs_path = rhs_path + [id(rhs)]

    path = '->'.join(str(key) for key in current_path)

    if type(lhs) != type(rhs):
        yield f"{path} (in {parent_class}): Types don't match {type(lhs)} != {type(rhs)}"
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
            yield from diff(nib_left_root, nib_right_root, nib_left_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries, nib_right_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries, current_path + ["nib"], [], [])

        elif type(lhs.value) in [int, str, float, bytes, type(None)]:
            if lhs.value != rhs.value:
                if (path.endswith("Flags") or path.endswith("Flags2")) and isinstance(lhs.value, int) and isinstance(rhs.value, int):
                    lval = lhs.value if lhs.value >= 0 else lhs.value + 0x10000000000000000
                    rval = rhs.value if rhs.value >= 0 else rhs.value + 0x10000000000000000
                    yield f"{path} (in {parent_class}): difference {hex(lval)} != {hex(rval)}"
                else:
                    yield f"{path} (in {parent_class}): difference {lhs.value} != {rhs.value}"
            return
        return

    assert isinstance(lhs, NibObject) or isinstance(lhs, NibCollection), type(lhs)
    assert isinstance(rhs, NibObject) or isinstance(rhs, NibCollection), type(rhs)

    if lhs.classname in ("NSNibConnector", "NSNibOutletConnector", "NSNibControlConnector", "NSNibAuxiliaryActionConnector") and rhs.classname in ("NSNibConnector", "NSNibOutletConnector", "NSNibControlConnector", "NSNibAuxiliaryActionConnector"):
        # Connections are unordered
        return
    if lhs.classname != rhs.classname:
        yield f"{path} (in {parent_class}): Class name doesn't match {lhs.classname} != {rhs.classname}"
        return
    if type(lhs.entries) != type(rhs.entries):
        yield f"{path} (in {parent_class}): Values types don't match"
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
            yield f"{path} Mismatched length: {len(lhs.entries)} != {len(rhs.entries)}"
        fixup_layout_constrints(lhs.entries, lhs_root)
        fixup_layout_constrints(rhs.entries, rhs_root)
        for i, (left, right) in enumerate(zip(lhs.entries, rhs.entries)):
            yield from diff(left, right, lhs_root, rhs_root, current_path + [str(i)], lhs_path, rhs_path, lhs.classname)
    elif path.endswith("NSConnections"):
        lhs_entries = sorted(lhs.entries, key=lambda x: x.rec_hash([]))
        rhs_entries = sorted(rhs.entries, key=lambda x: x.rec_hash([]))
        for i, (left, right) in enumerate(zip(lhs_entries, rhs_entries)):
            yield from diff(left, right, lhs_root, rhs_root, current_path + [str(i)], lhs_path, rhs_path, lhs.classname)
    elif isinstance(lhs, NibCollection) and isinstance(rhs, NibCollection):
        if len(lhs.entries) != len(rhs.entries):
            yield f"{path} Mismatched length: {len(lhs.entries)} != {len(rhs.entries)}"
        for i, (left, right) in enumerate(zip(lhs.entries, rhs.entries)):
            yield from diff(left, right, lhs_root, rhs_root, current_path + [str(i)], lhs_path, rhs_path, lhs.classname)
    elif isinstance(lhs, NibObject) and isinstance(rhs, NibObject):
        all_keys = set(list(lhs.entries.keys()) + list(rhs.entries.keys()))
        for key in sorted(all_keys):
            #print(f"{key}, {lhs.entries.get(key)}, {rhs.entries.get(key)}")
            if key not in lhs.entries:
                rval = rhs.entries.get(key)
                if (key.endswith("Flags") or key.endswith("Flags2")) and isinstance(rval.value, int):
                    rval = rval.value
                    rval = hex(rval if rval >= 0 else rval + 0x10000000000000000)

                yield f"{path} LHS ({lhs.classname}) missing key {key}, RHS {rval}"
                continue
            if key not in rhs.entries:
                lval = lhs.entries.get(key)
                if (key.endswith("Flags") or key.endswith("Flags2")) and isinstance(lval.value, int):
                    lval = lval.value
                    lval = hex(lval if lval >= 0 else lval + 0x10000000000000000)

                yield f"{path} RHS ({rhs.classname}) missing key {key}, LHS {lval}"
                continue
            yield from diff(lhs.entries[key], rhs.entries[key], lhs_root, rhs_root, current_path + [key], lhs_path, rhs_path, lhs.classname)
    else:
        raise Exception(f"Unknown type {type(lhs)}")

def fixup_layout_constrints(collection, all_objects):
    # We need to order the layout constraints explicitly for comparison. Apple's tool uses random order.
    def find_order(obj, keys):
        order_tuple = (-200000, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1)
        for i, key in enumerate(keys):
            if key is obj:
                if key.classname == "NSLayoutConstraint":
                    first = key.entries.get("NSFirstAttribute").value if key.entries.get("NSFirstAttribute") is not None else -1
                    firstv2 = key.entries.get("NSFirstAttributeV2").value if key.entries.get("NSFirstAttributeV2") is not None else -1
                    second = key.entries.get("NSSecondAttribute").value if key.entries.get("NSSecondAttribute") is not None else -1
                    secondv2 = key.entries.get("NSSecondAttributeV2").value if key.entries.get("NSSecondAttributeV2") is not None else -1
                    firstitem = keys.index(key.entries.get("NSFirstItem")) if key.entries.get("NSFirstItem") is not None else -1
                    seconditem = keys.index(key.entries.get("NSSecondItem")) if key.entries.get("NSSecondItem") is not None else -1
                    priority = key.entries.get("NSPriority").value if key.entries.get("NSPriority") is not None else -1
                    constantval = key.entries.get("NSConstantValue").value if key.entries.get("NSConstantValue") is not None else -1
                    constantvalv2 = key.entries.get("NSConstantValueV2").value if key.entries.get("NSConstantValueV2") is not None else -1
                    constant = key.entries.get("NSConstant").value if key.entries.get("NSConstant") is not None else -1
                    constantv2 = key.entries.get("NSConstantV2").value if key.entries.get("NSConstantV2") is not None else -1
                    symbolic = key.entries.get("NSSymbolicConstant").entries["NS.bytes"].value if key.entries.get("NSSymbolicConstant") is not None else b""
                    relation = key.entries.get("NSRelation").value if key.entries.get("NSRelation") is not None else -1

                    order_tuple = (first, firstv2, second, secondv2, firstitem, seconditem, priority, constantval, constantvalv2, constant, constantv2, symbolic, relation)
                else:
                    order_tuple = (-100000 + i, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1)
        return order_tuple

    all_objects = all_objects.copy()
    collection.sort(key=lambda x: find_order(x, all_objects))

def main(orig_path, test_path):
    orig_nib = getNibSectionsFile(orig_path)
    test_nib = getNibSectionsFile(test_path)

    orig_root, orig_rest = pythonObjects(orig_nib)
    test_root, test_rest = pythonObjects(test_nib)

    if orig_rest:
        print("original has unreferenced items")
    if test_rest:
        print("test has unreferenced items")

    found_issues = False
    orig_objects = orig_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries
    test_objects = test_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries
    fixup_layout_constrints(orig_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries, orig_objects)
    fixup_layout_constrints(test_root.entries["IB.objectdata"].entries["NSObjectsKeys"].entries, test_objects)
    fixup_layout_constrints(orig_root.entries["IB.objectdata"].entries["NSOidsKeys"].entries, orig_objects)
    fixup_layout_constrints(test_root.entries["IB.objectdata"].entries["NSOidsKeys"].entries, test_objects)
    for issue in diff(orig_root, test_root, lhs_root=orig_objects, rhs_root=test_objects):
        found_issues = True
        print(issue)
    sys.exit(int(found_issues))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
