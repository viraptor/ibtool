from typing import Optional, Union, Iterable, TypeAlias, Sequence, Any, cast
from xml.etree.ElementTree import Element
import struct

PropValue: TypeAlias = Union["NibObject",int,str,bytes,"NibNil","NibByte",bool,float,Iterable["PropValue"]]
PropPair: TypeAlias = tuple[str,PropValue]

class XibId:
    def __init__(self, val: str) -> None:
        self._val = val

    def is_negative_id(self) -> bool:
        try:
            val = int(self._val)
            return val < 0
        except ValueError:
            return False
        
    def is_placeholder_id(self) -> bool:
        return len(self._val.split('-')) == 3

    def val(self) -> str:
        return self._val

    def __repr__(self) -> str:
        return f"XibId({self._val})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, XibId):
            return self._val == other._val
        else:
            return False

    def __lt__(self, other: object) -> bool:
        if isinstance(other, XibId):
            return self.val() < other.val()
        elif isinstance(other, XibObject):
            return self.val() < other.xibid.val()
        else:
            return False

    def __hash__(self) -> int:
        return hash(self._val)


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
    
class NibProxyObject(NibObject):
    def __init__(self, identifier: str) -> None:
        NibObject.__init__(self, "UIProxyObject")
        self["UIProxiedObjectIdentifier"] = identifier


class ArchiveContext:
    def __init__(self, useAutolayout: bool=False, customObjectInstantitationMethod: Optional[str]=None, toolsVersion: Optional[int]=None) -> None:
        self.useAutolayout = useAutolayout
        self.customObjectInstantitationMethod = customObjectInstantitationMethod
        self.toolsVersion = toolsVersion
        self.connections: list[NibObject] = []

        # We need the list of constraints to be able to set the NSDoNotTranslateAutoresizingMask prop correctly
        self.constraints: list[XibObject] = []

        # When parsing a storyboard, this doesn't include the main view or any of its descendant objects.
        self.objects: dict[XibId, NibObject] = {} # should be int
        self.toplevel: list[NibObject] = []

        self.extraNibObjects: list[NibObject] = []
        self.isStoryboard = False

        # These are used only for storyboards.
        self.isParsingStoryboardView = False
        self.viewObjects: dict[XibId, NibObject] = {}
        self.viewConnections: list[NibObject] = []
        self.sceneConnections: list[NibObject] = []
        self.segueConnections: list[NibObject] = []

        self.isPrototypeList = False
        self.visibleWindows: list[NibObject] = []

        # What I plan on using after the context revision:

        self.upstreamPlaceholders: dict[str,XibId] = {}
        self.parentContext: Optional[ArchiveContext] = None
        # List of tuples (view id, referencing object, referencing key)
        self.viewReferences: list[tuple[str,NibObject,str]] = []
        self.viewControllerLayoutGuides: list = []
        # self.view = None
        # self.viewController = None

        self.viewKeyList: list[XibObject] = []

    def contextForSegues(self) -> 'ArchiveContext':
        if self.isPrototypeList:
            assert self.parentContext is not None
            return self.parentContext
        return self

    def addObject(self, objid: XibId, obj: NibObject, forceSceneObject: Any =None) -> None:
        dct = self.viewObjects if self.isParsingStoryboardView else self.objects
        if forceSceneObject is not None:
            dct = self.objects if forceSceneObject else self.viewObjects
        dct[objid] = obj

        # if self.isParsingStoryboardView:
        #     self.viewObjects[objid] = obj
        # else:
        #     self.objects[objid] = obj

    # to be used for objects that are known to be in the same context, given a valid document. (For possibly
    # unkown values, use getObject)
    # Also this meant to be an abstraction around the shitty 'objects' vs 'viewObjects' vs $whatever organization scheme.
    def findObject(self, objid: XibId) -> NibObject:
        obj = self.getObject(objid)
        if obj is None and objid is not None:
            raise Exception("Object with id %s not found in archive context." % (objid))
        return obj

    def getObject(self, objid: XibId) -> Optional[NibObject]:
        if not objid:
            return None
        if objid in self.viewObjects:
            return self.viewObjects[objid]
        if objid in self.objects:
            return self.objects[objid]
        return None

    # Kinda ugly. If we ever use a separate ArchiveContext for storyboard scenes and their views, we can use just use getObject.
    # Basically this is like getObject, but only searches in the right one of 'objects' or 'viewObjects'
    def getObjectInCurrentContext(self, objid: XibId) -> Optional[NibObject]:
        if objid is None:
            return None
        if self.isParsingStoryboardView:
            return self.viewObjects.get(objid)
        else:
            return self.objects[objid]
        return None

    def _add_translation_flag(self, target: Optional[Union[XibId,NibObject]]):
        if target is None:
            return

        if isinstance(target, XibId):
            target = self.getObject(target)
        if target.extraContext.get("NSDoNotTranslateAutoresizingMask"):
            target["NSDoNotTranslateAutoresizingMask"] = True

    def processConstraints(self) -> None:
        for constraint in self.constraints:
            self._add_translation_flag(constraint["NSFirstItem"])
            if second_item := constraint.get("NSSecondItem"):
                self._add_translation_flag(second_item)

    def resolveConnections(self) -> None:
        self._resolveConnections_xib()
        self._resolveViewReferences()

    def _resolveViewReferences(self) -> None:
        for ref in self.viewReferences:
            view_id, obj, key = ref
            obj[key] = self.findObject(view_id)

    def _resolveConnections_xib(self) -> None:
        result = []
        for con in self.connections:
            dst = cast(Union[XibId, NibProxyObject], con["NSDestination"])
            if isinstance(dst, NibProxyObject):
                result.append(con)
                continue

            assert isinstance(dst, XibId)

            #print("Resolving standalone xib connection with id", dst)
            if dst in self.objects:
                con["NSDestination"] = self.objects[dst]
                result.append(con)
                continue
            phid = makePlaceholderIdentifier()
            con["NSDestination"] = NibProxyObject(phid)
            self.upstreamPlaceholders[phid] = dst
            result.append(con)

        self.connections = result

class XibObject(NibObject):
    def __init__(self, ctx: ArchiveContext, classname: str, elem: Optional[Element], parent: Optional["NibObject"], ) -> None:
        NibObject.__init__(self, classname, parent)

        if elem is not None and (xibid := elem.attrib.get("id")) is not None:
            self.xibid = XibId(xibid)
        else:
            self.xibid = None
        self.extraContext: dict[str,Any] = {"original_class": classname}
        if elem is not None and (key := elem.attrib.get("key")):
            self.extraContext["key"] = key
        if isinstance(self, XibObject) and elem is not None:
            _xibparser_handle_custom_class(ctx, elem, self)

    def originalclassname(self) -> Optional[str]:
        name = self.extraContext.get("original_class")
        if name is None:
            return self.classname()
        assert isinstance(name, str)
        return name
    
    def classname(self) -> str:
        return self.extraContext.get("swapped_class") or super().classname()
    
    def xib_parent(self) -> Optional["XibObject"]:
        parent = self.parent()
        while parent is not None and (not isinstance(parent, XibObject) or parent.originalclassname() == "NSTableColumn"):
            parent = parent.parent()
        if isinstance(parent, XibObject):
            return parent
        else:
            return None

    def __lt__(self, other: object) -> bool:
        if self.xibid is None:
            return False
        elif isinstance(other, XibId):
            return self.xibid.val() < other.val()
        elif isinstance(other, XibObject):
            return self.xibid.val() < other.xibid.val()
        else:
            return False

    def frame(self) -> Optional[tuple[int, int, int, int]]:
        if parent := self.xib_parent():
            insets = parent.extraContext.get("insets")
        else:
            insets = None

        if self.xib_parent() and (auto_resizing := self.extraContext.get("parsed_autoresizing")):
            assert (parent := self.xib_parent())
            if my_frame := self.extraContext.get("NSFrame"):
                x, y, mw, mh = my_frame
            elif my_frame_size := self.extraContext.get("NSFrameSize"):
                mw, mh = my_frame_size
                x, y = 0, 0
            else:
                raise Exception(f"No frame or framesize for {self}")
            parent_frame = parent.frame()

            result = [x, y, mw, mh]
            if auto_resizing.get("widthSizable"):
                result[2] = parent_frame[2]
            if auto_resizing.get("heightSizable"):
                result[3] = parent_frame[3]
            if insets:
                result[2] -= insets[0]
                result[3] -= insets[1]
            return tuple(result)
        else:
            if frame := self.extraContext.get("NSFrame"):
                result = list(frame)
                if insets:
                    result[2] -= insets[0]
                    result[3] -= insets[1]
                return frame
            elif frame_size := self.extraContext.get("NSFrameSize"):
                result = [0, 0, frame_size[0], frame_size[1]]
                if insets:
                    result[2] -= insets[0]
                    result[3] -= insets[1]
                return result
            else:
                return None

def _xibparser_handle_custom_class(ctx: ArchiveContext, elem: Element, obj: "XibObject") -> None:
    custom_module = elem.attrib.get("customModule")
    custom_module_provider = elem.attrib.get("customModuleProvider")
    custom_class = elem.attrib.get("customClass")

    if obj.xibid.is_negative_id():
        if obj.xibid == XibId("-2"):
            obj["NSClassName"] = NibString.intern(custom_class or "NSApplication")
        else:
            obj["NSClassName"] = NibString.intern("NSApplication")
        if custom_class:
            obj["IBClassReference"] = make_class_reference(custom_class or "NSApplication", None, None)
    elif custom_class:
        #print(obj.xibid, obj.originalclassname(), obj.classname(), custom_class)
        if ctx.customObjectInstantitationMethod == "direct" and not (obj.originalclassname() in ("NSCustomObject", "NSWindowTemplate") and not custom_module) or obj.originalclassname() in ("NSView", "NSOutlineView", "NSButton"):
            #print("direct")
            if custom_module:
                obj["NSClassName"] = NibString.intern(f"_TtC{len(custom_module)}{custom_module}{len(custom_class)}{custom_class}")
            else:
                obj["NSClassName"] = NibString.intern(custom_class)
            if obj.classname() not in ("NSView", "NSCustomView", "NSButton", "NSOutlineView"):
                obj["NSInitializeWithInit"] = True
            final_original_class = {
                "NSCustomObject": "NSObject",
                "NSCustomView": "NSView",
            }.get(obj.classname(), obj.classname())
            obj["NSOriginalClassName"] = NibString.intern(final_original_class)
            obj.setclassname("NSClassSwapper")
        else:
            #print("other")
            obj["IBClassReference"] = make_class_reference(custom_class, custom_module, custom_module_provider)
            obj["NSClassName"] = NibString.intern(f"_TtC{len(custom_module)}{custom_module}{len(custom_class)}{custom_class}" if custom_module else custom_class)

def make_class_reference(class_name: str, module_name: Optional[str]=None, module_provider: Optional[str]=None) -> NibObject:
    return NibObject("IBClassReference", None, {
        "IBClassName": NibString(class_name),
        "IBModuleName": NibNil() if module_name is None else NibString(module_name),
        "IBModuleProvider": NibNil() if module_provider is None else NibString(module_provider),
    })
