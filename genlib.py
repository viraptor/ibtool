import struct

import nibencoding

from typing import Union, Optional, Sequence, cast, Any, TypeAlias, Iterable
from xml.etree.ElementTree import Element

""" Base classes for Nib encoding """

PropValue: TypeAlias = Union["NibObject",int,str,bytes,"NibNil","NibByte",bool,float,Iterable["PropValue"]]
PropPair: TypeAlias = tuple[str,PropValue]

class NibObject:
    _total = 1000

    def __init__(self, classnme: str ="NSObject", parent: Optional["NibObject"] = None, initProperties={}) -> None:
        self._classname = classnme
        self._serial = NibObject._total
        NibObject._total += 1
        self.properties: dict[str,PropValue] = {}
        self._nibidx = -1
        self._repr: Optional[Element] = None
        self._parent = parent
        for k, v in initProperties.items():
            self[k] = v

    def setclassname(self, newname: str):
        self._classname = newname

    def originalclassname(self):
        return self._classname

    def classname(self) -> str:
        return self._classname

    def repr(self) -> Optional[Element]:
        return self._repr

    def setrepr(self, r: Element) -> None:
        self._repr = r

    def nibidx(self) -> int:
        return self._nibidx

    def serial(self) -> int:
        return self._serial

    def get(self, key: str) -> Optional[PropValue]:
        return self.properties.get(key)

    def setIfEmpty(self, key: str, value: PropValue) -> None:
        if key not in self.properties:
            self[key] = value

    def setIfNotDefault(self, key: str, value: PropValue, default: PropValue):
        if value != default:
            self[key] = value

    def append(self, key: str, value: PropValue) -> None:
        if key in self.properties:
            prop = self[key]
            assert isinstance(prop, list)
            prop.append(value)
        else:
            self[key] = [value]

    def extend(self, key: str, values: list[PropValue]) -> None:
        if key in self.properties:
            prop = self[key]
            assert isinstance(prop, list)
            prop.extend(values)
        else:
            self[key] = list(values)

    def appendkv(self, dictKeyName: str, key: str, value: PropValue) -> None:
        if not dictKeyName:
            return
        d: Optional[Union[PropValue,dict]] = self.get(dictKeyName)
        if d is not None and not isinstance(d, dict):
            raise Exception("extendkv called non-dictionary NibObject property key")
        if d is None:
            d = {}
            self[dictKeyName] = d
        d[key] = value

    def __getitem__(self, key: str) -> PropValue:
        return self.properties[key]

    def __setitem__(self, key: str, item: Optional[PropValue]) -> None:
        if item is None:
            return
        elif isinstance(item, str):
            item = NibString.intern(item)
        elif isinstance(item, bytes):
            item = NibData.intern(item)
        self.properties[key] = item

    def __delitem__(self, item: str) -> None:
        del self.properties[item]

    def flagsOr(self, key: str, value: int) -> None:
        current = cast(int, self.get(key)) or 0
        self[key] = current | value

    def flagsAnd(self, key: str, value: int) -> None:
        current = cast(int, self.get(key)) or 0
        self[key] = current & value

    # Returns a list of tuples
    def getKeyValuePairs(self) -> list[PropPair]:
        return list(self.properties.items())
    
    def parent(self) -> Optional["NibObject"]:
        return self._parent


class NibString(NibObject):
    cache: set["NibString"] = set()

    @classmethod
    def intern(cls: type["NibString"], text: str) -> "NibString":
        for x in cls.cache:
            if x._text == text:
                return x
        new_string = NibString(text)
        cls.cache.add(new_string)
        return new_string

    def __init__(self, text: str = "Hello World") -> None:
        NibObject.__init__(self, "NSString")
        self._text = text

    def getKeyValuePairs(self) -> list[PropPair]:
        return [("NS.bytes", self._text)]

    def __repr__(self) -> str:
        return f"<{self.classname()} \"{self._text}\">"


class NibMutableString(NibObject):
    def __init__(self, text: str = "Hello World") -> None:
        NibObject.__init__(self, "NSMutableString")
        self._text = text

    def getKeyValuePairs(self) -> list[PropPair]:
        return [("NS.bytes", self._text)]

    def __repr__(self) -> str:
        return f"{object.__repr__(self)} {self._text}"


class NibData(NibObject):
    cache: set["NibData"] = set()

    @classmethod
    def intern(cls: type["NibData"], data: bytes) -> "NibData":
        for x in cls.cache:
            if x._data == data:
                return x
        new_data = NibData(data)
        cls.cache.add(new_data)
        return new_data

    def __init__(self, data: bytes) -> None:
        NibObject.__init__(self, "NSData")
        self._data = data

    def getKeyValuePairs(self) -> list[PropPair]:
        # print("MARCO YOLO", type(self._data))
        # raise Exception("EVERYTHING IS OK")
        return [("NS.bytes", self._data)]

    def __repr__(self) -> str:
        return f"<{self.classname()} \"{self._data}\">"


class NibInlineString:
    def __init__(self, text: str ="") -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class NibByte:
    def __init__(self, val: int = 0) -> None:
        self._val = val

    def val(self) -> int:
        return self._val


class NibFloat:
    def __init__(self, val: float = 0.0) -> None:
        self._val = val

    def val(self) -> float:
        return self._val


class NibNil:
    def __init__(self) -> None:
        pass


def NibFloatToWord(num: int) -> bytes:
    return struct.pack(">f", num)


class ArrayLike(NibObject):
    def __init__(self, classname: str, items: Optional[Sequence[PropValue]]) -> None:
        if items is None:
            items = []
        NibObject.__init__(self, classname)
        self._items: list[PropValue] = list(items)

    def __len__(self) -> int:
        return len(self._items)
    
    def __getitem__(self, key: int) -> PropValue:
        return self._items[key]

    def addItem(self, item: PropValue) -> None:
        self._items.append(item)

    def getKeyValuePairs(self) -> list[PropPair]:
        return [("NSInlinedValue", True)] + [
            ("UINibEncoderEmptyKey", item) for item in self._items
        ]

class NibList(ArrayLike):
    def __init__(self, items: Optional[Sequence[PropValue]] = None) -> None:
        super().__init__("NSArray", items)

class NibMutableList(ArrayLike):
    def __init__(self, items: Optional[Sequence[PropValue]]=None) -> None:
        super().__init__("NSMutableArray", items)

class NibMutableSet(ArrayLike):
    def __init__(self, items: Optional[Sequence[PropValue]]=None) -> None:
        super().__init__("NSMutableSet", items)

class NibDictionary(ArrayLike):
    def __init__(self, items: Optional[Sequence[PropValue]]=None) -> None:
        super().__init__("NSDictionary", items)

class NibMutableDictionary(ArrayLike):
    def __init__(self, items: Optional[Sequence[PropValue]]=None) -> None:
        super().__init__("NSMutableDictionary", items)


class NibNSNumber(NibObject):
    def __init__(self, value=0):
        NibObject.__init__(self, "NSNumber")
        self._value = value

        if isinstance(value, str):
            try:
                self._value = int(value)
            except ValueError:
                self._value = float(value)
        elif value:
            self._value = value
        else:
            self._value = 0

    def value(self):
        return self._value

    def getKeyValuePairs(self):
        val = self._value
        if isinstance(val, float):
            return [("NS.dblval", val)]
        if val >= 0 and val < 256:
            return [("NS.intval", NibByte(val))]
        return ("NS.intval", val)


# TODO: Have more stuff use this.
# TODO: Make this recursive.
# Is this only for dictionaries?
def convertToNibObject(obj):
    if isinstance(obj, NibObject):
        return obj  # Yep, here is where we would put recursion. IF WE HAD ANY.
    elif isinstance(obj, str):
        return NibString.intern(obj)
    elif isinstance(obj, int) or isinstance(obj, float):
        return NibNSNumber(obj)
    elif isinstance(obj, NibByte):
        return NibNSNumber(obj.val())
    return obj


class NibDictionaryImpl(NibObject):
    def __init__(self, objects):
        NibObject.__init__(self, "NSDictionary")
        if isinstance(objects, dict):
            t = []
            for k, v in objects.items():
                k = convertToNibObject(k)
                v = convertToNibObject(v)
                t.extend([k, v])
            objects = t
        self._objects = objects

    def getKeyValuePairs(self):
        pairs = [("NSInlinedValue", True)]
        pairs.extend([("UINibEncoderEmptyKey", obj) for obj in self._objects])
        return pairs


""" Convenience Classes """


class NibProxyObject(NibObject):
    def __init__(self, identifier: str) -> None:
        NibObject.__init__(self, "UIProxyObject")
        self["UIProxiedObjectIdentifier"] = identifier


""" Conversion Stuff """


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
                elif str(type(v)) == "<class 'xibparser.XibId'>":
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
                    elif v < 0x7f:
                        out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_BYTE, v))
                    elif v < 0x7fff:
                        out_values.append((idx_of_key(k), nibencoding.NIB_TYPE_SHORT, v))
                    elif v < 0x7ffffffff:
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
