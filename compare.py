from ibdump import getNibSections, NibStructure
import sys
from typing import Any, Union, cast, Iterable, Optional

class NibCollection:
    def __init__(self, classname: str, entries: list[Any]):
        self.classname = classname
        self.entries = entries

    def __repr__(self):
        return f"{self.classname} ({len(self.entries)} entries)"

class NibObject:
    def __init__(self, classname: str, entries: dict[str,Any]):
        self.classname = classname
        self.entries = entries

    def __eq__(self, other):
        assert isinstance(other, NibObject)
        return self.classname == other.classname and len(self.entries) == len(other.entries)

    def __lt__(self, other):
        assert isinstance(other, NibObject)
        return (self.classname, len(other.entries)) < (other.classname, len(other.entries))

    def __repr__(self):
        return f"{self.classname} ({len(self.entries)} entries)"
    
class NibValue:
    def __init__(self, value: Any, type: int):
        self.value = value
        self.type = type

    def __eq__(self, other):
        if not isinstance(other, NibValue):
            return False
        return self.value == other.value and self.type == other.type

    def __lt__(self, other):
        assert isinstance(other, NibValue)
        return self.value < other.value

    def __repr__(self):
        return f"{self.value} (type {self.type})"

def pythonObjects(nib: NibStructure) -> tuple[NibObject, list[Any]]:
    objects, keys, values, classes = nib

    res: dict[int,Union[NibObject,NibCollection]] = {}

    for o_idx, obj_tup in enumerate(objects):
        classname = classes[obj_tup[0]]
        obj_values = values[obj_tup[1] : obj_tup[1] + obj_tup[2]]

        if classname in ['NSArray', 'NSMutableArray', 'NSMutableSet']:
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


def diff(lhs: Union[NibValue,NibCollection,NibObject], rhs: Union[NibValue,NibCollection,NibObject], current_path: list[str]=[], lhs_path: list[int]=[], rhs_path: list[int]=[], parent_class: Optional[str] = None) -> Iterable[str]:
    lhs_path = lhs_path + [id(lhs)]
    rhs_path = rhs_path + [id(rhs)]

    path = '->'.join(str(key) for key in current_path)

    if type(lhs) != type(rhs):
        yield f"{path} (in {parent_class}): Types don't match {type(lhs)} != {type(rhs)}"
        return

    if isinstance(lhs, NibValue) and isinstance(rhs, NibValue):
        if lhs.type != rhs.type:
            yield f"{path} (in {parent_class}): Object types don't match {lhs.type} != {rhs.type}"

        if type(lhs.value) in [int, str, float, bytes, type(None)]:
            if lhs.value != rhs.value:
                yield f"{path} (in {parent_class}): difference {lhs.value} != {rhs.value}"
            return
        return

    assert isinstance(lhs, NibObject) or isinstance(lhs, NibCollection), type(lhs)
    assert isinstance(rhs, NibObject) or isinstance(rhs, NibCollection), type(rhs)

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
        lhs_entries = sorted(lhs.entries, key=lambda x: (x.entries.get("NSFirstAttribute").value, x.entries.get("NSSecondAttribute"), x.entries.get("NSPriority", NibValue(1, 0)), x.entries.get("NSFirstItem"), x.entries.get("NSSecondItem")))
        rhs_entries = sorted(rhs.entries, key=lambda x: (x.entries.get("NSFirstAttribute").value, x.entries.get("NSSecondAttribute"), x.entries.get("NSPriority", NibValue(1, 0)), x.entries.get("NSFirstItem"), x.entries.get("NSSecondItem")))
        for i, (left, right) in enumerate(zip(lhs_entries, rhs_entries)):
            yield from diff(left, right, current_path + [str(i)], lhs_path, rhs_path, lhs.classname)
    elif isinstance(lhs, NibCollection) and isinstance(rhs, NibCollection):
        if len(lhs.entries) != len(rhs.entries):
            yield f"{path} Mismatched length: {len(lhs.entries)} != {len(rhs.entries)}"
        for i, (left, right) in enumerate(zip(lhs.entries, rhs.entries)):
            yield from diff(left, right, current_path + [str(i)], lhs_path, rhs_path, lhs.classname)
    elif isinstance(lhs, NibObject) and isinstance(rhs, NibObject):
        all_keys = set(list(lhs.entries.keys()) + list(rhs.entries.keys()))
        for key in sorted(all_keys):
            #print(f"{key}, {lhs.entries.get(key)}, {rhs.entries.get(key)}")
            if key not in lhs.entries:
                yield f"{path} LHS ({lhs.classname}) missing key {key}, RHS {rhs.entries.get(key)}"
                continue
            if key not in rhs.entries:
                yield f"{path} RHS ({rhs.classname}) missing key {key}, LHS {lhs.entries.get(key)}"
                continue
            yield from diff(lhs.entries[key], rhs.entries[key], current_path + [key], lhs_path, rhs_path, lhs.classname)
    else:
        raise Exception(f"Unknown type {type(lhs)}")


if __name__ == "__main__":
    orig_nib = getNibSections(sys.argv[1])
    test_nib = getNibSections(sys.argv[2])

    orig_root, orig_rest = pythonObjects(orig_nib)
    test_root, test_rest = pythonObjects(test_nib)

    if orig_rest:
        print("original has unreferenced items")
    if test_rest:
        print("test has unreferenced items")

    found_issues = False
    for issue in diff(orig_root, test_root):
        found_issues = True
        print(issue)
    sys.exit(int(found_issues))
