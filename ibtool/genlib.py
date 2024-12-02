import struct
from . import nibencoding
from typing import Union
from .models import PropValue, NibObject, NibDictionaryImpl, ArrayLike, NibInlineString, NibByte, NibFloat, NibNil, XibId


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

        def idx_of_class(cls: str) -> int:
            if cls in out_classes:
                return out_classes.index(cls)
            if cls == "NSNibAuxiliaryActionConnector":
                current_class_len = len(out_classes)
                out_classes.append((cls, current_class_len + 1))
                out_classes.append("NSNibConnector")
                return current_class_len
            else:
                out_classes.append(cls)
                return len(out_classes) - 1

        def idx_of_key(key: str) -> int:
            if key in out_keys:
                return out_keys.index(key)
            out_keys.append(key)
            return len(out_keys) - 1

        for obj in self.object_list:
            obj_values_start = len(out_values)
            kvpairs = obj.getKeyValuePairs()
            for k, v in kvpairs:
                if isinstance(v, NibObject):
                    key_idx = idx_of_key(k)
                    vtuple_obj = (key_idx, nibencoding.NIB_TYPE_OBJECT, v.nibidx(), v)
                    out_values.append(vtuple_obj)
                elif isinstance(v, XibId):
                    key_idx = idx_of_key(k)
                    id_target = [o for o in self.object_list if isinstance(o, NibObject) and getattr(o, "xibid", None) == v][0]
                    vtuple_obj = (key_idx, nibencoding.NIB_TYPE_OBJECT, id_target.nibidx(), id_target)
                    out_values.append(vtuple_obj)
                elif isinstance(v, str) or isinstance(v, bytearray) or isinstance(v, bytes):
                    key_idx = idx_of_key(k)
                    vtuple_str = (key_idx, nibencoding.NIB_TYPE_STRING, v)
                    out_values.append(vtuple_str)
                elif isinstance(v, NibInlineString):
                    key_idx = idx_of_key(k)
                    vtuple_inline = (key_idx, nibencoding.NIB_TYPE_STRING, v.text())
                    out_values.append(vtuple_inline)
                elif isinstance(v, NibByte):
                    out_values.append(
                        (idx_of_key(k), nibencoding.NIB_TYPE_BYTE, v.val())
                    )
                elif isinstance(v, NibFloat):
                    out_values.append(
                        (idx_of_key(k), nibencoding.NIB_TYPE_FLOAT, v.val())
                    )
                elif v is True:
                    out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_TRUE))
                elif v is False:
                    out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_FALSE))
                elif isinstance(v, NibNil):
                    out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_NIL))
                elif isinstance(v, float):
                    out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_DOUBLE, v))
                elif isinstance(v, int):
                    if v < 0:
                        out_values.append(
                            (idx_of_key(k), nibencoding.NIB_TYPE_LONG_LONG, v)
                        )
                    elif v <= 0x7f:
                        out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_BYTE, v))
                    elif v <= 0x7fff:
                        out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_SHORT, v))
                    elif v <= 0x7fffffff:
                        out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_LONG, v))
                    else:
                        out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_LONG_LONG, v))

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
                    out_values.append(
                        (idx_of_key(k), nibencoding.NIB_TYPE_STRING, data)
                    )
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
    t = ctx.makeTuples()
    return nibencoding.WriteNib(t)
