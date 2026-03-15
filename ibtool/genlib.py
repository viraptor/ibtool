import struct
from . import nibencoding
from typing import Union
from .models import PropValue, NibObject, NibDictionaryImpl, ArrayLike, NibInlineString, NibByte, NibFloat, NibNil, NibNSNumber, XibId


class CompilationContext:
    def __init__(self):
        self.class_set = set()
        # a set of serial numbers for objects that have been added to the object list.
        self.serial_set = set()
        self.object_list = []

    def addBinObject(self, obj):
        pass

    def addObjects(self, objects: list[PropValue]):
        for o in objects:
            if isinstance(o, NibObject):
                self.addObject(o)

    def addObject(self, obj: NibObject):
        if not isinstance(obj, NibObject):
            print("CompilationContext.addObject: Non-NibObject value:", obj)
            raise Exception("Not supported.")

        serial = obj.serial()
        if serial in self.serial_set:
            return
        self.serial_set.add(serial)

        cls = obj.classname()
        if cls not in self.class_set:
            self.class_set.add(cls)

        obj._nibidx = len(self.object_list)
        self.object_list.append(obj)

        if isinstance(obj, NibDictionaryImpl):
            self.addObjects(obj._objects)

        elif isinstance(obj, ArrayLike):
            self.addObjects(obj._items)

        else:
            self.addObjects(obj.properties.values())

    def makeTuples(self) -> tuple[
            list[tuple[int,int,int]],
            list[str],
            list[Union[tuple[int,int],tuple[int,int,Union[int,str,bytearray,float]],tuple[int,int,int,PropValue]]],
            list[str]
            ]:
        out_objects: list[tuple[int,int,int]] = []
        out_keys: list[str] = []
        out_values: list[Union[tuple[int,int],tuple[int,int,Union[int,str,bytearray,float]],tuple[int,int,int,PropValue]]] = []
        out_classes: list[str] = []

        class_index: dict[str, int] = {}

        def idx_of_class(cls: str) -> int:
            idx = class_index.get(cls)
            if idx is not None:
                return idx
            if cls == "NSNibAuxiliaryActionConnector":
                current_class_len = len(out_classes)
                out_classes.append((cls, current_class_len + 1))
                class_index[cls] = current_class_len
                out_classes.append("NSNibConnector")
                class_index["NSNibConnector"] = current_class_len + 1
                return current_class_len
            else:
                idx = len(out_classes)
                out_classes.append(cls)
                class_index[cls] = idx
                return idx

        key_index: dict[str, int] = {}

        def idx_of_key(key: str) -> int:
            idx = key_index.get(key)
            if idx is not None:
                return idx
            idx = len(out_keys)
            out_keys.append(key)
            key_index[key] = idx
            return idx

        xibid_index: dict = {}
        for o in self.object_list:
            xid = getattr(o, "xibid", None)
            if xid is not None:
                xibid_index.setdefault(xid, o)

        OBJ = nibencoding.NIB_TYPE_OBJECT
        STR = nibencoding.NIB_TYPE_STRING
        BYTE = nibencoding.NIB_TYPE_BYTE
        SHORT = nibencoding.NIB_TYPE_SHORT
        LONG = nibencoding.NIB_TYPE_LONG
        LLONG = nibencoding.NIB_TYPE_LONG_LONG
        TRUE = nibencoding.NIB_TYPE_TRUE
        FALSE = nibencoding.NIB_TYPE_FALSE
        TNIL = nibencoding.NIB_TYPE_NIL
        FLOAT = nibencoding.NIB_TYPE_FLOAT
        DOUBLE = nibencoding.NIB_TYPE_DOUBLE

        for obj in self.object_list:
            obj_values_start = len(out_values)
            kvpairs = obj.getKeyValuePairs()
            for k, v in kvpairs:
                # Ordered by frequency: int > NibObject > bool > NibNil > str/bytes > ...
                if isinstance(v, int):
                    if v is True:
                        out_values.append((idx_of_key(k), TRUE))
                    elif v is False:
                        out_values.append((idx_of_key(k), FALSE))
                    elif v < 0:
                        out_values.append((idx_of_key(k), LLONG, v))
                    elif v <= 0x7f:
                        out_values.append((idx_of_key(k), BYTE, v))
                    elif v <= 0x7fff:
                        out_values.append((idx_of_key(k), SHORT, v))
                    elif v <= 0x7fffffff:
                        out_values.append((idx_of_key(k), LONG, v))
                    else:
                        out_values.append((idx_of_key(k), LLONG, v))
                elif isinstance(v, NibObject):
                    out_values.append((idx_of_key(k), OBJ, v.nibidx(), v))
                elif isinstance(v, NibNil):
                    out_values.append((idx_of_key(k), TNIL))
                elif isinstance(v, (str, bytearray, bytes)):
                    out_values.append((idx_of_key(k), STR, v))
                elif isinstance(v, NibInlineString):
                    out_values.append((idx_of_key(k), STR, v.text()))
                elif isinstance(v, NibByte):
                    out_values.append((idx_of_key(k), BYTE, v.val()))
                elif isinstance(v, NibFloat):
                    out_values.append((idx_of_key(k), FLOAT, v.val()))
                elif isinstance(v, float):
                    out_values.append((idx_of_key(k), DOUBLE, v))
                elif isinstance(v, XibId):
                    id_target = xibid_index.get(v)
                    if id_target is not None:
                        out_values.append((idx_of_key(k), OBJ, id_target.nibidx(), id_target))
                elif isinstance(v, tuple):
                    for el in v:
                        if not isinstance(el, float):
                            raise Exception(
                                "Only tuples of floats are supported now. Type = "
                                + str(type(el))
                            )
                    data = bytearray()
                    data.append(0x07)
                    data.extend(struct.pack("<" + "d" * len(v), *v))
                    out_values.append((idx_of_key(k), STR, data))
                else:
                    raise Exception(f"Unknown type: {type(v)} in key {k} of {obj.classname()}")

            obj_values_end = len(out_values)
            class_idx = idx_of_class(obj.classname())
            out_objects.append(
                (class_idx, obj_values_start, obj_values_end - obj_values_start)
            )

        return (out_objects, out_keys, out_values, out_classes)


"""
This really has (at least) two phases.
1. Traverse/examine the object graph to find the objects/keys/values/classes that need to be encoded.
2. Once those lists are built and resolved, convert them into binary format.
"""


def CompileNibObjects(objects: list[NibObject]) -> bytes:
    ctx = CompilationContext()
    ctx.addObjects(objects)

    # Deduplicate OID value NSNumbers: Apple's ibtool reuses existing NSNumber
    # objects, so e.g. OID value 11 becomes NS.dblval 11.0 if that already exists.
    # Use the already-collected object_list to find candidates, then replace.
    root_data = objects[0].properties.get("IB.objectdata") if objects else None
    oids_values = root_data.properties.get("NSOidsValues") if isinstance(root_data, NibObject) else None
    if isinstance(oids_values, ArrayLike):
        oid_set = set(id(item) for item in oids_values._items)
        number_by_value: dict[float, NibNSNumber] = {}
        for o in ctx.object_list:
            if isinstance(o, NibNSNumber) and id(o) not in oid_set:
                val = o.value()
                if isinstance(val, (int, float)):
                    number_by_value.setdefault(float(val), o)
        for i, item in enumerate(oids_values._items):
            if isinstance(item, NibNSNumber):
                val = item.value()
                if isinstance(val, (int, float)):
                    existing = number_by_value.get(float(val))
                    if existing is not None and existing is not item:
                        oids_values._items[i] = existing

    t = ctx.makeTuples()
    return nibencoding.WriteNib(t)
