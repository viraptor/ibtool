import re
from genlib import (
    NibData,
    NibInlineString,
    NibNSNumber,
    NibObject,
    NibProxyObject,
    NibString,
    NibMutableString,
    NibNil,
    NibList,
    NibMutableList,
    NibMutableSet,
    NibDictionary,
    PropValue,
    PropPair,
)
from xml.etree.ElementTree import Element
from typing import Optional, Any, Union, cast, Callable
from enum import IntEnum, Enum
from contextlib import contextmanager


class NSColorSpaceModels(IntEnum):
    NSUnknownColorSpaceModel = -1
    NSGrayColorSpaceModel = 0
    NSRGBColorSpaceModel = 1
    NSCMYKColorSpaceModel = 2
    NSLABColorSpaceModel = 3
    NSDeviceNColorSpaceModel = 4
    NSIndexedColorSpaceModel = 5
    NSPatternColorSpaceModel = 6

class WTFlags(IntEnum):
    DEFER = 0x20000000
    RELEASED_WHEN_CLOSED = 0x40000000
    HIDES_ON_DEACTIVATE = 0x80000000
    ALLOWS_TOOL_TIPS_WHEN_APPLICATION_IS_INACTIVE = 0x2000
    AUTORECALCULATES_KEY_VIEW_LOOP = 0x800

    STRUTS_BOTTOM_LEFT = 0
    STRUTS_BOTTOM_RIGHT = 0x50000
    STRUTS_TOP_LEFT = 0x280000
    STRUTS_TOP_RIGHT = 0x300000
    STRUTS_LEFT = 0x680000
    STRUTS_RIGHT = 0x700000
    STRUTS_BOTTOM = 0x580000
    STRUTS_TOP = 0x380000
    STRUTS_ALL = 0x780000
    STRUTS_MASK = 0x780000

class TVFlags(IntEnum):
    HORIZONTALLY_RESIZABLE = 0x1
    VERTICALLY_RESIZABLE = 0x2

class vFlags(IntEnum):
    AUTORESIZES_SUBVIEWS = 0x100
    HIDDEN = 0xffffffff80000000
    NOT_SIZABLE = 0x00
    MIN_X_MARGIN = 0x01
    WIDTH_SIZABLE = 0x02
    MAX_X_MARGIN = 0x04
    MIN_Y_MARGIN = 0x08
    HEIGHT_SIZABLE = 0x10
    MAX_Y_MARGIN = 0x20

    DEFAULT_VFLAGS = AUTORESIZES_SUBVIEWS | MIN_Y_MARGIN | MAX_Y_MARGIN
    DEFAULT_VFLAGS_AUTOLAYOUT = AUTORESIZES_SUBVIEWS | MAX_X_MARGIN | MIN_Y_MARGIN

class cvFlags(IntEnum):
    DRAW_BACKGROUND = 0x4

class sFlagsScroller(IntEnum):
    HORIZONTAL = 0x01

class sFlagsScrollView(IntEnum):
    BORDER_NONE = 0x0
    BORDER_LINE = 0x1
    BORDER_BEZEL = 0x2
    BORDER_GROOVE = 0x3
    HAS_VERTICAL_SCROLLER = 0x10
    HAS_HORIZONTAL_SCROLLER = 0x20
    COPY_ON_SCROLL = 0x80
    AUTOHIDES_SCROLLERS = 0x200
    USES_PREDOMINANT_AXIS_SCROLLING = 0x10000

class ButtonFlags(IntEnum):
    IMAGE_ONLY = 0x00400000
    IMAGE_OVERLAPS = 0x00480000
    IMAGE_LEFT = 0x00380000
    IMAGE_RIGHT = 0x00280000
    IMAGE_BELOW = 0x00180000
    IMAGE_ABOVE = 0x00080000

    HIGHLIGHT_PUSH_IN_CELL = 0x80000000
    STATE_CONTENTS_CELL = 0x40000000
    STATE_CHANGE_BACKGROUND_CELL = 0x20000000
    STATE_CHANGE_GRAY_CELL = 0x10000000
    HIGHLIGHT_CONTENTS_CELL = 0x08000000
    HIGHLIGHT_CHANGE_BACKGROUND_CELL = 0x04000000
    HIGHLIGHT_CHANGE_GRAY_CELL = 0x02000000

    BORDERED = 0x00800000
    TRANSPARENT = 0x00008000
    IMAGE_DIMS_WHEN_DISABLED = 0x00002000

    TYPE_RADIO = 0x100

    INSET_1 = 0x2000
    INSET_2 = 0x4000

class ButtonFlags2(IntEnum):
    BORDER_ONLY_WHILE_MOUSE_INSIDE = 0x8
    IMAGE_SCALING_PROPORTIONALLY_DOWN = 0x80


class CellFlags(IntEnum):
    STATE_ON = 0xffffffff80000000
    HIGHLIGHTED = 0x40000000
    ENABLED = 0x20000000
    EDITABLE = 0x10000000
    UNKNOWN_TEXT_FIELD = 0x04000000
    BORDERED = 0x00800000
    BEZELED = 0x00400000
    SELECTABLE = 0x00200000
    SCROLLABLE = 0x00100000
    CONTINUOUS = 0x00080000
    ACTION_ON_MOUSE_DOWN = 0x00040000
    IS_LEAF = 0x00020000
    INVALID_FONT = 0x00008000
    RESERVED1 = 0x00001800
    SINGLE_LINE_MODE = 0x00000400
    ACTION_ON_MOUSE_DRAG = 0x00000100
    IS_LOADED = 0x00000080
    TRUNCATE_LAST_LINE = 0x00000040
    DONT_ACT_ON_MOUSE_UP = 0x00000020
    IS_WHITE = 0x00000010
    USER_KEY_EQUIV = 0x00000008
    SHOWS_FIRST_RESPONSE = 0x00000004
    FOCUS_RING_TYPE = 0x00000003

class CellFlags2(IntEnum):
    SELECTABLE = 0x80000000
    RICH_TEXT = 0x40000000
    IMPORTS_GRAPH = 0x10000000

    TEXT_ALIGN_NONE = 0x10000000
    TEXT_ALIGN_LEFT = 0x0
    TEXT_ALIGN_CENTER = 0x8000000
    TEXT_ALIGN_RIGHT = 0x4000000

    LAYOUT_DIRECTION_RTL = 0x01000000
    REFUSES_FIRST_RESPONDER = 0x02000000
    ALLOWS_MIXED_STATE = 0x01000000
    IN_MIXED_STATE = 0x00800000
    SENDS_ACTION_ON_END_EDITING = 0x00400000

    LINE_BREAK_MODE_WORD_WRAPPING = 0x0
    LINE_BREAK_MODE_CHAR_WRAPPING = 0x200
    LINE_BREAK_MODE_CLIPPING = 0x400
    LINE_BREAK_MODE_TRUNCATING_HEAD = 0x600
    LINE_BREAK_MODE_TRUNCATING_TAIL = 0x800
    LINE_BREAK_MODE_TRUNCATING_MIDDLE = 0xa00
    CONTROL_SIZE_MASK = 0x000E0000

class LineBreakMode(Enum):
    BY_WORD_WRAPPING = 0
    BY_CHAR_WRAPPING = 1
    BY_CLIPPING = 2
    BY_TRUNCATING_HEAD = 3
    BY_TRUNCATING_TAIL = 4
    BY_TRUNCATING_MIDDLE = 5


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


class ArchiveContext:
    def __init__(self, useAutolayout: bool=False, customObjectInstantitationMethod: Optional[str]=None) -> None:
        self.useAutolayout = useAutolayout
        self.customObjectInstantitationMethod = customObjectInstantitationMethod
        self.connections: list[NibObject] = []

        # We need the list of constraints to be able to set the NSDoNotTranslateAutoresizingMask prop correctly
        self.constraints: list[XibObject] = []

        # When parsing a storyboard, this doesn't include the main view or any of its descendant objects.
        self.objects: dict[XibId, NibObject] = {} # should be int
        self.toplevel: list[NibObject] = []

        self.extraNibObjects: list[NibObject] = []
        self.isStoryboard = False

        # These are used only for storyboards.
        self.storyboardViewController: Optional[XibViewController] = None
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
            self._add_translation_flag(constraint.get("NSSecondItem"))

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

            print("Resolving standalone xib connection with id", dst)
            if dst in self.objects:
                con["NSDestination"] = self.objects[dst]
                result.append(con)
                continue
            phid = makePlaceholderIdentifier()
            con["NSDestination"] = NibProxyObject(phid)
            self.upstreamPlaceholders[phid] = dst
            result.append(con)

        self.connections = result


# Parses xml Xib data and returns a NibObject that can be used as the root
# object in a compiled NIB archive.
# element: The element containing the objects to be included in the nib.
#          For standalone XIBs, this is typically document->objects
#          For storyboards, this is typically document->scenes->scene->objects
def ParseXIBObjects(root: Element, context: Optional[ArchiveContext]=None, resolveConnections: bool=True, parent: Optional[NibObject]=None) -> NibObject:
    objects = next(root.iter("objects"))
    toplevel: list[XibObject] = []

    context = context or ArchiveContext(
        useAutolayout=(root.attrib.get("useAutolayout") == "YES"),
        customObjectInstantitationMethod=root.attrib.get("customObjectInstantitationMethod")
        )

    for nib_object_element in objects:
        obj = __xibparser_ParseXIBObject(context, nib_object_element, parent)
        if isinstance(obj, XibObject):
            toplevel.append(obj)

    if resolveConnections:
        context.resolveConnections()

    context.processConstraints()

    return createTopLevel(toplevel, context)

def createTopLevel(toplevelObjects: list["XibObject"], context) -> NibObject:
    #for obj in toplevelObjects:
    #    print('---', obj, obj.xibid)
    #    for t in obj.getKeyValuePairs():
    #        print(t)
    #print('+++')
    #for obj in context.extraNibObjects:
    #    print('---', obj, obj.xibid)
    #    for t in obj.getKeyValuePairs():
    #        print(t)

    applicationObject = context.objects[XibId("-3")]
    filesOwner = context.objects[XibId("-2")]

    rootData = NibObject("NSIBObjectData")
    rootData["NSRoot"] = toplevelObjects[0]
    rootData["NSVisibleWindows"] = NibMutableSet(context.visibleWindows)
    rootData["NSConnections"] = NibMutableList(
        [conn for conn in context.connections if conn.classname() == "NSNibOutletConnector"] +
        [conn for conn in context.connections if conn.classname() != "NSNibOutletConnector"]
        )
    rootData["NSObjectsKeys"] = NibList([applicationObject] + context.extraNibObjects)
    # parents of XibObjects should be listed here with filesOwner as the highest parent

    parent_objects = [(o.xib_parent() or filesOwner) for o in context.extraNibObjects if o.xibid is None or not o.xibid.is_negative_id()]
    rootData["NSObjectsValues"] = NibList([filesOwner] + parent_objects)

    oid_objects = [filesOwner, applicationObject] + \
        [o for o in context.extraNibObjects if o.xibid is None or not o.xibid.is_negative_id()] + \
        [o for o in context.connections if o.classname() == "NSNibOutletConnector"] + \
        [o for o in context.connections if o.classname() != "NSNibOutletConnector"]
    rootData["NSOidsKeys"] = NibList(oid_objects)
    rootData["NSOidsValues"] = NibList([NibNSNumber(x+1) for x,_ in enumerate(oid_objects)])
    rootData["NSAccessibilityConnectors"] = NibMutableList()
    emptyList = NibList()
    rootData["NSAccessibilityOidsKeys"] = emptyList
    rootData["NSAccessibilityOidsValues"] = emptyList
    return NibObject("NSObject", None, {
        "IB.objectdata": rootData,
        "IB.systemFontUpdateVersion": 1,
    })


def makexibid() -> str:
    import random

    chars = random.sample(
        "0123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM", 10
    )
    chars[3] = "-"
    chars[6] = "-"
    return "".join(chars)


def makePlaceholderIdentifier() -> str:
    return "UpstreamPlaceholder-" + makexibid()


def classSwapper(func: Callable):
    def inner(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], *args, **kwargs) -> NibObject:
        obj = func(ctx, elem, parent, *args, **kwargs)
        if obj:
            if customClass := elem.attrib.get("customClass"):
                obj.extraContext["original_class"] = obj.originalclassname()
                obj.setclassname(customClass)

        return obj

    return inner


def __xibparser_ParseXIBObject(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> NibObject:
    tag = elem.tag
    fnname = "_xibparser_parse_" + tag
    parsefn = globals().get(fnname)
    # print("----- PARSETHING:", tag, parsefn)
    if parsefn:
        obj = parsefn(ctx, elem, parent)
        if obj and isinstance(obj, XibObject):
            if elem.attrib.get("id") == None:
                raise Exception(f"Unknown id for {elem} (parent {parent})")
            ctx.addObject(obj.xibid, obj)
        return obj
    else:
        raise Exception(f"Unknown type {tag}")


def __xibparser_ParseChildren(ctx: ArchiveContext, elem: Element, obj: Optional[NibObject]) -> list[NibObject]:
    assert obj is not None
    # Constraints are always added after other elements. It may not matter, but that's what Apple's tool does and it helps in comparisons
    children = [
        __xibparser_ParseXIBObject(ctx, child_element, obj) for child_element in elem if child_element.tag != "constraints"
    ] + [
        __xibparser_ParseXIBObject(ctx, child_element, obj) for child_element in elem if child_element.tag == "constraints"
    ]
    return [c for c in children if c]


def _xibparser_parse_placeholder(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> NibProxyObject:
    placeholderid = elem.attrib["placeholderIdentifier"]
    obj = NibProxyObject(placeholderid)
    __xibparser_ParseChildren(ctx, elem, obj)
    ctx.addObject(XibId(elem.attrib["id"]), obj)
    return obj


def _xibparser_parse_interfacebuilder_properties(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], obj: NibObject) -> None:
    rid = elem.attrib.get("restorationIdentifier")
    if rid:
        obj["UIRestorationIdentifier"] = rid

    ibid = elem.attrib.get("id")
    if ibid:
        ctx.addObject(XibId(ibid), obj)


class XibObject(NibObject):
    def __init__(self, classname: str, parent: Optional["NibObject"], xibid: Optional[str]) -> None:
        NibObject.__init__(self, classname, parent)
        self.xibid: Optional[XibId] = None
        if xibid is not None:
            self.xibid = XibId(xibid)
        self.extraContext: dict[str,Any] = {}

    def originalclassname(self) -> Optional[str]:
        name = self.extraContext.get("original_class")
        if name is None:
            return self.classname()
        assert isinstance(name, str)
        return name
    
    def xib_parent(self) -> Optional["XibObject"]:
        parent = self.parent()
        while parent is not None and not isinstance(parent, XibObject):
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
        if auto_resizing := self.extraContext.get("parsed_autoresizing"):
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
            return tuple(result)
        else:
            if frame := self.extraContext.get("NSFrame"):
                return frame
            elif frame_size := self.extraContext.get("NSFrameSize"):
                return (0, 0, frame_size[0], frame_size[1])
            else:
                return None

class XibViewController(XibObject):
    def __init__(self, classname: str, parent: Optional[NibObject] = None) -> None:
        XibObject.__init__(self, classname, parent)
        self.xibattributes: dict[str,str] = {}

        # For storyboards:
        self.relationshipsegue = None
        self.sceneConnections: list[NibObject] = [] # Populated in ArchiveContext.resolveConnections()


@classSwapper
def _xibparser_parse_viewController(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], **kwargs) -> XibViewController:
    obj = XibViewController(kwargs.get("uikit_class") or "UIViewController")
    ctx.extraNibObjects.append(obj)

    if elem.attrib.get("sceneMemberID") == "viewController":
        ctx.storyboardViewController = obj

    obj.xibattributes = elem.attrib or {}
    __xibparser_ParseChildren(ctx, elem, obj)
    _xibparser_parse_interfacebuilder_properties(ctx, elem, parent, obj)
    obj["UIStoryboardIdentifier"] = elem.attrib.get("storyboardIdentifier")

    return obj


"""
List of attributes I've seen on 'view' elements

Unhandled

adjustsFontSizeToFit
baselineAdjustment
clipsSubviews
horizontalHuggingPriority
lineBreakMode
opaque
text
userInteractionEnabled
verticalHuggingPriority

contentHorizontalAlignment="center"
contentVerticalAlignment="center"
buttonType="roundedRect"


Started
    key  -  'view' (for view controllers)

Done
    contentMode - TODO: Make sure the string values we check are correct.
    customClass
    restorationIdentifier
    translatesAutoresizingMaskIntoConstraints

WontDo
    fixedFrame - I think this is only for interface builder. (it gets set on UISearchBar)
    id - Not arhived in nib.
"""


def _xibparser_parse_view(ctx: ArchiveContext, elem: Element, parent: XibObject, **kwargs) -> XibObject:
    obj = XibObject("NSView", parent, elem.attrib["id"])
    ctx.extraNibObjects.append(obj)
    obj.setrepr(elem)

    key = elem.get("key")
    if key == "contentView":
        if parent.originalclassname() == "NSWindowTemplate":
            parent["NSWindowView"] = obj
            obj["NSFrameSize"] = NibString.intern("{0, 0}")
        else:
            raise Exception(
                "Unhandled class '%s' to take NSView with key 'contentView'"
                % (parent.originalclassname())
            )
    else:
        raise Exception(f"view in unknown key {key} (parent {parent.repr()})")

    isMainView = key == "view"  # and isinstance(parent, XibViewController)?
    
    # Parse these props first, in case any of our children point to us.
    _xibparser_parse_interfacebuilder_properties(ctx, elem, parent, obj)
    __xibparser_ParseChildren(ctx, elem, obj)

    _xibparser_common_view_attributes(ctx, elem, parent, obj, topLevelView=(key == "contentView"))
    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if isMainView:
        ctx.isParsingStoryboardView = False

    return obj


def _xibparser_common_view_attributes(_ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], obj: XibObject, topLevelView: bool = False) -> None:
    assert parent is not None

    obj["IBNSSafeAreaLayoutGuide"] = NibNil()
    obj["IBNSLayoutMarginsGuide"] = NibNil()
    obj["IBNSClipsToBounds"] = 0
    if elem.attrib.get("hidden", "NO") == "YES":
        obj.flagsOr("NSvFlags", vFlags.HIDDEN)
    obj.flagsOr("NSvFlags", vFlags.AUTORESIZES_SUBVIEWS)
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    if not topLevelView:
        obj.setIfEmpty("NSNextResponder", parent.get("NSNextResponder") or parent)
    else:
        obj.setIfEmpty("NSNextResponder", NibNil())
    obj["NSNibTouchBar"] = NibNil()
    obj.extraContext["verticalHuggingPriority"] = elem.attrib.get("verticalHuggingPriority")
    obj.extraContext["horizontalHuggingPriority"] = elem.attrib.get("horizontalHuggingPriority")

    if elem.attrib.get('translatesAutoresizingMaskIntoConstraints', "YES") == "NO":
        obj.extraContext["NSDoNotTranslateAutoresizingMask"] = True


def make_xib_object(ctx: ArchiveContext, classname: str, elem: Element, parent: Optional[NibObject], view_attributes: bool = True) -> XibObject:
    obj = XibObject(classname, parent, elem.attrib.get("id"))
    if obj.xibid is not None:
        ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    if view_attributes:
        _xibparser_common_view_attributes(ctx, elem, parent, obj)
    return obj

def _xibparser_parse_button(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSButton", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    __xibparser_ParseChildren(ctx, elem, obj)
    obj.setIfEmpty("NSFrame", NibNil())
    obj["NSEnabled"] = True
    obj.setIfEmpty("NSCell", NibNil())
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 4
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    return obj


def __parse_size(size: str) -> tuple[int, int]:
    return tuple(int(x) for x in re.findall(r'-?\d+', size))

def __parse_pos_size(size: str) -> tuple[int, int, int, int]:
    return tuple(int(x) for x in re.findall(r'-?\d+', size))

def _xibparser_parse_textView(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTextView", elem, parent)
    
    editable = 0x2 if elem.attrib.get("editable", "YES") == "YES" else 0
    imports_graphics = 0x8 if elem.attrib.get("importsGraphics") == "YES" else 0
    spelling_correction = 0x4000000 if elem.attrib.get("spellingCorrection") == "YES" else 0
    rich_text = 0x4 if elem.attrib.get("richText") == "YES" else 0
    smart_insert_delete = 0x200 if elem.attrib.get("smartInsertDelete") == "YES" else 0
    horizontally_resizable = TVFlags.HORIZONTALLY_RESIZABLE if elem.attrib.get("horizontallyResizable") == "YES" else 0
    vertically_resizable = TVFlags.VERTICALLY_RESIZABLE if elem.attrib.get("verticallyResizable") == "YES" else 0
    preferred_find_style = {
        None: None,
        "panel": 1,
        "bar": 2,
    }[elem.attrib.get("findStyle")]

    shared_data = XibObject("NSTextViewSharedData", obj, None)
    shared_data["NSAutomaticTextCompletionDisabled"] = False
    shared_data["NSBackgroundColor"] = NibNil()
    shared_data["NSDefaultParagraphStyle"] = NibNil()
    shared_data["NSFlags"] = 0x901 | spelling_correction | editable | imports_graphics | rich_text | smart_insert_delete
    shared_data["NSInsertionColor"] = makeSystemColor('textInsertionPointColor')
    shared_data["NSLinkAttributes"] = NibDictionary([NibString.intern("NSColor")])
    shared_data["NSMarkedAttributes"] = NibNil()
    shared_data["NSMoreFlags"] = 0x1
    shared_data["NSPreferredTextFinderStyle"] = 0
    shared_data["NSSelectedAttributes"] = NibDictionary([NibString.intern("NSBackgroundColor")])
    shared_data["NSTextCheckingTypes"] = 0
    shared_data["NSTextFinder"] = NibNil()
    if preferred_find_style is not None:
        shared_data["NSPreferredTextFinderStyle"] = preferred_find_style
    obj["NSSharedData"] = shared_data
    obj["NSSuperview"] = obj.xib_parent()

    with __handle_view_chain(ctx, obj):
        __xibparser_ParseChildren(ctx, elem, obj)
    obj["NSDelegate"] = NibNil()
    obj["NSTVFlags"] = 132 | horizontally_resizable | vertically_resizable
    obj["NSNextResponder"] = obj.xib_parent()
    obj.setIfNotDefault("NSViewIsLayerTreeHost", elem.attrib.get("wantsLayer") == "YES", False)

    text_container = NibObject("NSTextContainer", obj)
    text_container["NSLayoutManager"] = NibNil()
    text_container["NSMinWidth"] = 15.0
    text_container["NSTCFlags"] = 0x1

    layout_manager = NibObject("NSLayoutManager", text_container)
    layout_manager["NSTextContainers"] = NibMutableList([text_container])
    layout_manager["NSLMFlags"] = 0x66
    layout_manager["NSDelegate"] = NibNil()
    layout_manager["NSTextStorage"] = NibObject("NSTextStorage", layout_manager, {
        "NSDelegate": NibNil(),
        "NSString": NibMutableString(""),
    })
    text_container["NSLayoutManager"] = layout_manager
    text_container["NSTextLayoutManager"] = NibNil()

    text_container["NSTextView"] = obj
    if frame_size := obj.get("NSFrameSize"):
        text_container["NSWidth"] = float(__parse_size(frame_size._text)[0])
    elif frame := obj.get("NSFrame"):
        text_container["NSWidth"] = float(__parse_pos_size(frame._text)[2])
    else:
        text_container["NSWidth"] = 1.0

    obj["NSTextContainer"] = text_container

    obj["NSTextViewTextColor"] = makeSystemColor("textColor")

    return obj


def _xibparser_parse_imageView(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSImageView", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    with __handle_view_chain(ctx, obj):
        __xibparser_ParseChildren(ctx, elem, obj)
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlContinuous"] = False
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = -1
    obj["NSDragTypes"] = default_drag_types()
    obj["NSEditable"] = True
    obj["NSEnabled"] = True
    obj["NSImageViewPlaceholderPrecedence"] = 0
    obj["NSControlSendActionMask"] = 4
    obj.setIfEmpty("NSSubviews", NibMutableList([]))
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    return obj


def default_drag_types() -> NibMutableSet:
    return NibMutableSet([
        NibString.intern('Apple PDF pasteboard type'),
        NibString.intern('Apple PICT pasteboard type'),
        NibString.intern('Apple PNG pasteboard type'),
        NibString.intern('NSFilenamesPboardType'),
        NibString.intern('NeXT TIFF v4.0 pasteboard type'),
        NibString.intern('com.apple.NSFilePromiseItemMetaData'),
        NibString.intern('com.apple.pasteboard.promised-file-content-type'),
        NibString.intern('dyn.ah62d4rv4gu8yc6durvwwa3xmrvw1gkdusm1044pxqyuha2pxsvw0e55bsmwca7d3sbwu')
        ])


def _xibparser_parse_constraints(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    __xibparser_ParseChildren(ctx, elem, parent)


ATTRIBUTE_MAP = {
    "left": 1,
    "right": 2,
    "top": 3,
    "bottom": 4,
    "leading": 5,
    "trailing": 6,
    "width": 7,
    "height": 8,
    "centerX": 9,
    "centerY": 10,
    "baseline": 11,
}


def _xibparser_parse_constraint(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    first_attribute = elem.attrib["firstAttribute"]

    obj = XibObject("NSLayoutConstraint", parent, elem.attrib["id"])
    ctx.extraNibObjects.append(obj)
    obj["NSFirstAttribute"] = ATTRIBUTE_MAP[first_attribute]
    obj["NSFirstAttributeV2"] = ATTRIBUTE_MAP[first_attribute]
    if (second_attribute := elem.attrib.get("secondAttribute")) is not None:
        obj["NSSecondAttribute"] = ATTRIBUTE_MAP[second_attribute]
        obj["NSSecondAttributeV2"] = ATTRIBUTE_MAP[second_attribute]
    if (first_item := elem.attrib.get("firstItem")) is not None:
        obj["NSFirstItem"] = XibId(first_item)
    else:
        obj["NSFirstItem"] = parent
    if (second_item := elem.attrib.get("secondItem")) is not None:
        obj["NSSecondItem"] = XibId(second_item)
    if (relation := elem.attrib.get("relation")) is not None:
        obj["NSRelation"] = {"greaterThanOrEqual": 1}[relation]
    if (priority := elem.attrib.get("priority")) is not None:
        obj["NSPriority"] = int(priority)

    symbolic = elem.attrib.get("symbolic") == "YES"
    if (constant := elem.attrib.get("constant")) is not None and symbolic is False:
        obj["NSConstant"] = float(constant)
        obj["NSConstantV2"] = float(constant)
    if symbolic:
        obj["NSSymbolicConstant"] = NibString.intern("NSSpace")
    obj["NSShouldBeArchived"] = True
    parent.setIfEmpty("NSViewConstraints", NibList())
    ctx.constraints.append(obj)
    cast(NibList, parent["NSViewConstraints"]).addItem(obj)


def _xibparser_parse_imageCell(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None
    assert parent.originalclassname() == "NSImageView"
    obj = XibObject("NSImageCell", parent, elem.attrib.get("id"))
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    __xibparser_ParseChildren(ctx, elem, obj)
    __xibparser_cell_flags(elem, obj, parent)

    alignment_value = {None: 4, "left": 0, "center": 1, "right": 2}[elem.attrib.get("alignment")]
    obj["NSAlign"] = alignment_value
    obj["NSAnimates"] = elem.attrib.get("animates", "NO") == "YES"
    obj["NSContents"] = NibNil()
    obj["NSControlView"] = parent
    obj["NSScale"] = {
        "proportionallyDown": 0,
        "axesIndependently": 1,
        "none": 2,
        "proportionallyUpOrDown": 3,
    }[elem.attrib.get("imageScaling", "none")]
    obj["NSStyle"] = 0
    obj["NSControlSize2"] = 0
    if image_name := elem.attrib.get("image"):
        obj["NSContents"] = make_system_image(image_name, obj)
    parent["NSCell"] = obj

    return obj


def make_system_image(name: str, parent: NibObject) -> NibObject:
    obj = NibObject("NSCustomResource", parent)
    obj["NSResourceName"] = NibString.intern(name)
    obj["NSClassName"] = NibString.intern("NSImage")
    obj["IBNamespaceID"] = NibString.intern("system")
    design_size = NibObject("NSValue", obj)
    design_size["NS.sizeval"] = NibString.intern("{32, 32}")
    design_size["NS.special"] = 2
    obj["IBDesignSize"] = design_size
    obj["IBDesignImageConfiguration"] = NibNil()
    return obj


def _xibparser_parse_scrollView(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSScrollView", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    obj.extraContext["fixedFrame"] = elem.attrib.get("fixedFrame", "YES") == "YES"
    with __handle_view_chain(ctx, obj):
        __xibparser_ParseChildren(ctx, elem, obj)
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    obj["NSGestureRecognizers"] = NibList([default_pan_recognizer(obj)])
    obj["NSMagnification"] = 1.0
    obj["NSMaxMagnification"] = 4.0
    obj["NSMinMagnification"] = 0.25
    obj["NSSubviews"] = NibMutableList([
        obj["NSContentView"],
        obj["NSHScroller"],
        obj["NSVScroller"],
        ])

    border_type = {
        "none": sFlagsScrollView.BORDER_NONE,
        "line": sFlagsScrollView.BORDER_LINE,
        "bezel": sFlagsScrollView.BORDER_BEZEL,
        "groove": sFlagsScrollView.BORDER_GROOVE,
    }[elem.attrib.get("borderType", "bezel")]
    has_horizontal_scroller = sFlagsScrollView.HAS_HORIZONTAL_SCROLLER if elem.attrib.get("hasHorizontalScroller") == "YES" else 0
    has_vertical_scroller = sFlagsScrollView.HAS_VERTICAL_SCROLLER if elem.attrib.get("hasVerticalScroller", "YES") == "YES" else 0
    uses_predominant_axis_scrolling = sFlagsScrollView.USES_PREDOMINANT_AXIS_SCROLLING if elem.attrib.get("usesPredominantAxisScrolling", "YES") == "YES" else 0
    obj["NSsFlags"] = 0x20800 | has_horizontal_scroller | has_vertical_scroller | uses_predominant_axis_scrolling | border_type

    horizontal_line_scroll = int(elem.attrib.get("horizontalLineScroll", "10"))
    vertical_line_scroll = int(elem.attrib.get("verticalLineScroll", "10"))
    horizontal_page_scroll = int(elem.attrib.get("horizontalPageScroll", "10"))
    vertical_page_scroll = int(elem.attrib.get("verticalPageScroll", "10"))
    if (horizontal_line_scroll, vertical_line_scroll, horizontal_page_scroll, vertical_page_scroll) != (10, 10, 10, 10):
        raise Exception("TODO: NSScrollAmts")
        # TODO figure out the encoding
        obj["NSScrollAmts"] = NibInlineString("...")

    return obj

def default_pan_recognizer(scrollView: XibObject) -> NibObject:
    obj = NibObject("NSPanGestureRecognizer", None)
    obj["NSGestureRecognizer.action"] = NibString.intern("_panWithGestureRecognizer:")
    obj["NSGestureRecognizer.allowedTouchTypes"] = 1
    obj["NSGestureRecognizer.delegate"] = scrollView
    obj["NSGestureRecognizer.target"] = scrollView
    obj["NSPanGestureRecognizer.buttonMask"] = 0
    obj["NSPanGestureRecognizer.numberOfTouchesRequired"] = 1
    return obj


def _xibparser_parse_clipView(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSClipView", elem, parent)
    
    key = elem.get("key")
    if key == "contentView":
        if parent.originalclassname() == "NSScrollView":
            parent["NSContentView"] = obj
            is_main_view = False
        elif parent.originalclassname() == "NSWindowTemplate":
            parent["NSWindowView"] = obj
            is_main_view = True
        else:
            raise Exception(
                "Unhandled class '%s' to take UIView with key 'contentView'"
                % (parent.originalclassname())
            )
    else:
        raise Exception(f"view in unknown key {key} (parent {parent.repr()})")
    
    with __handle_view_chain(ctx, obj):
        __xibparser_ParseChildren(ctx, elem, obj)
    if not is_main_view:
        obj["NSSuperview"] = obj.xib_parent()
    
    obj["NSAutomaticallyAdjustsContentInsets"] = True
    if not is_main_view:
        obj["NSvFlags"] = vFlags.AUTORESIZES_SUBVIEWS # clearing the values from elem - they don't seem to matter
    if elem.attrib.get("drawsBackground", "YES") == "YES":
        obj.flagsOr("NScvFlags", cvFlags.DRAW_BACKGROUND)
    cursor = NibObject("NSCursor", obj)
    cursor["NSCursorType"] = 0
    cursor["NSHotSpot"] = NibString.intern("{1, -1}")
    obj["NSCursor"] = cursor
    obj["NSNextResponder"] = NibNil() if is_main_view else obj.xib_parent()
    if obj.get("NSSubviews") and len(obj["NSSubviews"]) > 0:
        obj["NSDocView"] = obj["NSSubviews"][0]
    else:
        obj["NSDocView"] = NibNil()
    obj.setIfEmpty("NSBGColor", makeSystemColor("controlBackgroundColor"))
    return obj


def _xibparser_parse_subviews(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    views = __xibparser_ParseChildren(ctx, elem, parent)
    parent["NSSubviews"] = NibMutableList(views)


# Types of connections: outlet, action, segue, *outletConnection (any more?)
def _xibparser_parse_connections(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    __xibparser_ParseChildren(ctx, elem, parent)


def _xibparser_parse_outlet(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    obj = XibObject("NSNibOutletConnector", parent, elem.attrib["id"])
    obj["NSSource"] = parent
    obj["NSDestination"] = XibId(elem.attrib.get("destination"))
    obj["NSLabel"] = elem.attrib.get("property")
    obj["NSChildControllerCreationSelectorName"] = NibNil()

    # Add this to the list of connections we'll have to resolve later.
    ctx.connections.append(obj)


def _xibparser_parse_action(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    etype = elem.attrib.get("eventType")

    maskmap = {
        None: None,
        "touchDown": 1 << 0,
        "touchDownRepeat": 1 << 1,
        "touchDragInside": 1 << 2,
        "touchDragOutside": 1 << 3,
        "touchDragEnter": 1 << 4,
        "touchDragExit": 1 << 5,
        "touchUpInside": 1 << 6,
        "touchUpOutside": 1 << 7,
        "touchCancel": 1 << 8,
        "valueChanged": 1 << 12,
        "editingDidBegin": 1 << 16,
        "editingChanged": 1 << 17,
        "editingDidEnd": 1 << 18,
        "editingDidEndOnExit": 1 << 19,
    }

    mask = maskmap[etype]

    obj = NibObject("NSNibControlConnector", parent)
    obj["NSLabel"] = elem.attrib["selector"]
    obj["NSSource"] = parent
    obj["NSDestination"] = XibId(elem.attrib.get("target"))
    obj["NSEventMask"] = mask # TODO

    ctx.connections.append(obj)


# TODO: I think this function might need more logic when the bounds aren't set at 0, 0
def _xibparser_parse_rect(ctx: ArchiveContext, elem: Element, parent: XibObject) -> None:
    key = elem.attrib.get("key")
    w = int(elem.attrib["width"])
    h = int(elem.attrib["height"])
    if key == "contentRect":
        assert parent.originalclassname() == "NSWindowTemplate"
        x = int(elem.attrib["x"])
        y = int(elem.attrib["y"])
        parent.extraContext["NSWindowRect"] = (x, y, w, h)
    elif key == "screenRect":
        assert parent.originalclassname() == "NSWindowTemplate"
        x = int(float(elem.attrib["x"]))
        y = int(float(elem.attrib["y"]))
        parent.extraContext["NSScreenRect"] = (x, y, w, h)
    elif key == "frame":
        x = int(float(elem.attrib["x"]))
        y = int(float(elem.attrib["y"]))
        if x == 0 and y == 0:
            parent["NSFrameSize"] = "{" + str(w) + ", " + str(h) + "}"
            parent.extraContext["NSFrameSize"] = (w, h)
        else:
            parent["NSFrame"] = "{{" + str(x) + ", " + str(y) + "}, {" + str(w) + ", " + str(h) + "}}"
            parent.extraContext["NSFrame"] = (x, y, w, h)
    else:
        raise Exception(f"unknown rect key {key}")


def _xibparser_parse_autoresizingMask(_ctx: ArchiveContext, elem: Element, parent: XibObject) -> None:
    flexibleMaxX = vFlags.MAX_X_MARGIN if elem.attrib.get("flexibleMaxX", "NO") == "YES" else 0
    flexibleMaxY = vFlags.MAX_Y_MARGIN if elem.attrib.get("flexibleMaxY", "NO") == "YES" else 0
    flexibleMinX = vFlags.MIN_X_MARGIN if elem.attrib.get("flexibleMinX", "NO") == "YES" else 0
    flexibleMinY = vFlags.MIN_Y_MARGIN if elem.attrib.get("flexibleMinY", "NO") == "YES" else 0
    widthSizable = vFlags.WIDTH_SIZABLE if elem.attrib.get("widthSizable", "NO") == "YES" else 0
    heightSizable = vFlags.HEIGHT_SIZABLE if elem.attrib.get("heightSizable", "NO") == "YES" else 0
    parent.flagsOr("NSvFlags", flexibleMaxX | flexibleMaxY | flexibleMinX | flexibleMinY | widthSizable | heightSizable)
    parent.extraContext["parsed_autoresizing"] = {
        "flexibleMaxX": bool(flexibleMaxX),
        "flexibleMaxY": bool(flexibleMaxY),
        "flexibleMinX": bool(flexibleMinX),
        "flexibleMinY": bool(flexibleMinY),
        "widthSizable": bool(widthSizable),
        "heightSizable": bool(heightSizable),
    }


def _xibparser_parse_point(_ctx: ArchiveContext, elem: Element, _parent: NibObject) -> None:
    point = (float(elem.attrib["x"]), float(elem.attrib["y"]))
    if elem.attrib.get("key") == "canvasLocation":
        pass # only useful for the designer
    else:
        raise Exception(f"unknown point key {elem.attrib.get('key')}")


def _xibparser_parse_window(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    item = XibObject("NSWindowTemplate", parent, elem.attrib["id"])
    ctx.extraNibObjects.append(item)
    item.flagsOr("NSWTFlags", 0x780000) # default initial position mask, can be overriden by children

    __xibparser_ParseChildren(ctx, elem, item)
    item["NSWindowBacking"] = 2
    if not item.extraContext.get("NSWindowRect"):
        item.extraContext["NSWindowRect"] = (0, 0, 0, 0)

    item.flagsOr("NSWTFlags", WTFlags.DEFER)
    if elem.attrib.get("allowsToolTipsWhenApplicationIsInactive", "YES") == "YES":
        item.flagsOr("NSWTFlags", WTFlags.ALLOWS_TOOL_TIPS_WHEN_APPLICATION_IS_INACTIVE)
    if elem.attrib.get("autorecalculatesKeyViewLoop", "YES") == "YES":
        item.flagsOr("NSWTFlags", WTFlags.AUTORECALCULATES_KEY_VIEW_LOOP)
    if elem.attrib.get("releasedWhenClosed", "YES") == "NO":
        item.flagsOr("NSWTFlags", WTFlags.RELEASED_WHEN_CLOSED)

    item["NSWindowTitle"] = NibString.intern(elem.attrib.get("title", ''))
    item["NSWindowSubtitle"] = ""
    item["NSWindowClass"] = NibString.intern("NSWindow")
    item["NSViewClass"] = NibNil() # TODO
    item["NSUserInterfaceItemIdentifier"] = NibNil() # TODO
    if not item.get("NSWindowView"):
        item["NSWindowView"] = NibNil()
    if not item.extraContext.get("NSScreenRect"):
        item.extraContext["NSScreenRect"] = (0, 0, 0, 0)
    item.setIfEmpty("NSMaxSize", '{10000000000000, 10000000000000}')
    item["NSWindowIsRestorable"] = elem.attrib.get("restorable", "YES") == "YES"
    item["NSMinFullScreenContentSize"] = NibString.intern('{0, 0}')
    item["NSMaxFullScreenContentSize"] = NibString.intern('{0, 0}')
    if elem.attrib.get("tabbingMode"):
        item["NSWindowTabbingMode"] = {"disallowed": 2}[elem.attrib["tabbingMode"]]
    if elem.attrib.get("visibleAtLaunch", "YES") == "YES":
        ctx.visibleWindows.append(item)
    if custom_class := elem.attrib.get("customClass"):
        item["IBClassReference"] = make_class_reference(custom_class)
        item["NSWindowClass"] = custom_class

    # fixup the rects
    if item.extraContext.get("NSWindowRect"):
        content_rect = item.extraContext["NSWindowRect"]
        screen_rect = item.extraContext["NSScreenRect"]
        item.extraContext["NSWindowRect"] = calculate_window_rect(item.extraContext.get("initialPositionMask", {}), content_rect, screen_rect)
        item["NSWindowRect"] = "{{" + str(item.extraContext["NSWindowRect"][0]) + ", " + str(item.extraContext["NSWindowRect"][1]) + "}, {" + str(item.extraContext["NSWindowRect"][2]) + ", " + str(item.extraContext["NSWindowRect"][3]) + "}}"
    if item.extraContext.get("NSScreenRect"):
        item["NSScreenRect"] = "{{" + str(item.extraContext["NSScreenRect"][0]) + ", " + str(item.extraContext["NSScreenRect"][1]) + "}, {" + str(item.extraContext["NSScreenRect"][2]) + ", " + str(item.extraContext["NSScreenRect"][3]) + "}}"

    return item

def calculate_window_rect(struts: dict[str, bool], content_rect: tuple[int, int, int, int], screen_rect: tuple[int, int, int, int]) -> tuple[Union[int,float], ...]:
    if screen_rect == (0, 0, 0, 0):
        return content_rect
    res = (
        content_rect[0] if struts.get("left") else screen_rect[2]/2 - content_rect[2]/2,
        content_rect[1] if struts.get("bottom") else screen_rect[3]/2 - content_rect[3]/2,
        content_rect[2],
        content_rect[3],
        )
    return tuple(int(x) if x==int(x) else x for x in res)

def make_class_reference(class_name: str, module_name: Optional[str]=None, module_provider: Optional[str]=None) -> NibObject:
    return NibObject("IBClassReference", None, {
        "IBClassName": NibString(class_name),
        "IBModuleName": NibNil() if module_name is None else NibString(module_name),
        "IBModuleProvider": NibNil() if module_provider is None else NibString(module_provider),
    })


def _xibparser_parse_customObject(ctx, elem, parent):
    obj = XibObject("NSCustomObject", parent, elem.attrib["id"])
    if obj.xibid is not None:
        ctx.addObject(obj.xibid, obj)
    if not obj.xibid.is_negative_id():
        ctx.extraNibObjects.append(obj)
    custom_module = elem.attrib.get("customModule")
    custom_class = elem.attrib.get("customClass")
    custom_module_provider = elem.attrib.get("customModuleProvider")

    if custom_class:
        if ctx.customObjectInstantitationMethod == "direct" and custom_module:
            obj["NSClassName"] = NibString.intern(f"_TtC{len(custom_module)}{custom_module}{len(custom_class)}{custom_class}")
            obj["NSInitializeWithInit"] = True
            obj["NSOriginalClassName"] = NibString.intern("NSObject")
            obj.setclassname("NSClassSwapper")
        else:
            obj["IBClassReference"] = make_class_reference(custom_class, custom_module, custom_module_provider)
            if obj.xibid == XibId("-3"):
                obj["NSClassName"] = NibString.intern("NSApplication")
            else:
                obj["NSClassName"] = NibString.intern(f"_TtC{len(custom_module)}{custom_module}{len(custom_class)}{custom_class}" if custom_module else custom_class)

    elif obj.xibid.is_negative_id():
        obj["NSClassName"] = NibString.intern("NSApplication")
    else:
        obj["NSClassName"] = NibString.intern("NSObject")
    __xibparser_ParseChildren(ctx, elem, obj)
    return obj

def _xibparser_parse_windowStyleMask(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    maskmap = {
        "titled": 1 << 0,
        "closable": 1 << 1,
        "miniaturizable": 1 << 2,
        "resizable": 1 << 3,
    }
    value = sum((elem.attrib.get(attr, "NO") == "YES") * val for attr, val in maskmap.items())
    parent["NSWindowStyleMask"] = value

def _xibparser_parse_windowPositionMask(_ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert isinstance(parent, XibObject)
    assert elem.attrib.get("key") == "initialPositionMask"

    struts = {
        "left": elem.attrib.get("leftStrut", "NO") == "YES",
        "right": elem.attrib.get("rightStrut", "NO") == "YES",
        "bottom": elem.attrib.get("bottomStrut", "NO") == "YES",
        "top": elem.attrib.get("topStrut", "NO") == "YES",
    }
    if struts["bottom"] and struts["left"] and struts["top"] and struts["right"]:
        flags = WTFlags.STRUTS_ALL
    elif struts["bottom"] and struts["left"]:
        flags = WTFlags.STRUTS_BOTTOM_LEFT
    elif struts["bottom"] and struts["right"]:
        flags = WTFlags.STRUTS_BOTTOM_RIGHT
    elif struts["top"] and struts["left"]:
        flags = WTFlags.STRUTS_TOP_LEFT
    elif struts["top"] and struts["right"]:
        flags = WTFlags.STRUTS_TOP_RIGHT
    elif struts["left"]:
        flags = WTFlags.STRUTS_LEFT
    elif struts["right"]:
        flags = WTFlags.STRUTS_RIGHT
    elif struts["bottom"]:
        flags = WTFlags.STRUTS_BOTTOM
    elif struts["top"]:
        flags = WTFlags.STRUTS_TOP
    else:
        flags = WTFlags.STRUTS_MASK

    parent.flagsAnd("NSWTFlags", ~WTFlags.STRUTS_MASK) # clear the default
    parent.flagsOr("NSWTFlags", flags)
    parent.extraContext["initialPositionMask"] = struts
    #parent["NSWindowPositionMask"] = value


def _xibparser_parse_textField(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSTextField", elem, parent)

    obj["NSSuperview"] = obj.xib_parent()
    __xibparser_ParseChildren(ctx, elem, obj)
    obj.setIfEmpty("NSFrame", NibNil())
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    obj["NSEnabled"] = True
    obj.setIfEmpty("NSCell", NibNil())
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    obj["NSControlUsesSingleLineMode"] = False
    obj.setIfEmpty("NSControlLineBreakMode", 0)
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 4
    obj["NSTextFieldAlignmentRectInsetsVersion"] = 2
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    horizontal_compression_prio = elem.attrib.get('horizontalCompressionResistancePriority')
    vertical_compression_prio = elem.attrib.get('verticalCompressionResistancePriority')
    if horizontal_compression_prio is not None or vertical_compression_prio is not None:
        if horizontal_compression_prio is None:
            horizontal_compression_prio = "750"
        if vertical_compression_prio is None:
            vertical_compression_prio = "750"
        obj["NSAntiCompressionPriority"] = f"{{{horizontal_compression_prio}, {vertical_compression_prio}}}"

    return obj

def __xibparser_cell_flags(elem: Element, obj: NibObject, parent: NibObject) -> None:
    sendsAction = elem.attrib.get("sendsActionOnEndEditing", "NO") == "YES"
    sendsActionMask = CellFlags2.SENDS_ACTION_ON_END_EDITING if sendsAction else 0
    lineBreakMode = elem.attrib.get("lineBreakMode")
    lineBreakModeMask = {
        None: 0,
        "wordWrapping": 0,
        "charWrapping": 0,
        "truncatingTail": CellFlags.TRUNCATE_LAST_LINE,
        "truncatingHead": CellFlags.TRUNCATE_LAST_LINE,
        "truncatingMiddle": CellFlags.TRUNCATE_LAST_LINE,
        "clipping": CellFlags.TRUNCATE_LAST_LINE,
    }[lineBreakMode]
    lineBreakModeMask2 = {
        None: 0,
        "wordWrapping": CellFlags2.LINE_BREAK_MODE_WORD_WRAPPING,
        "charWrapping": CellFlags2.LINE_BREAK_MODE_CHAR_WRAPPING,
        "clipping": CellFlags2.LINE_BREAK_MODE_CLIPPING,
        "truncatingHead": CellFlags2.LINE_BREAK_MODE_TRUNCATING_HEAD,
        "truncatingTail": CellFlags2.LINE_BREAK_MODE_TRUNCATING_TAIL,
        "truncatingMiddle": CellFlags2.LINE_BREAK_MODE_TRUNCATING_MIDDLE,
    }[lineBreakMode]
    textAlignment = elem.attrib.get("alignment")
    textAlignmentMask = {None: CellFlags2.TEXT_ALIGN_NONE, "left": CellFlags2.TEXT_ALIGN_LEFT, "center": CellFlags2.TEXT_ALIGN_CENTER, "right": CellFlags2.TEXT_ALIGN_RIGHT}[textAlignment]
    selectable = (CellFlags.SELECTABLE + 1) if elem.attrib.get("selectable", "NO") == "YES" else 0
    state_on = CellFlags.STATE_ON if (elem.attrib.get("state") == "on") else 0
    text_field_flag = CellFlags.UNKNOWN_TEXT_FIELD if obj.originalclassname() in ["NSTextFieldCell", "NSButtonCell"] else 0
    refuses_first_responder = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    refuses_first_responder_mask = CellFlags2.REFUSES_FIRST_RESPONDER if refuses_first_responder else 0
    scrollable = CellFlags.SCROLLABLE if elem.attrib.get("scrollable", "NO") == "YES" else 0

    obj.flagsOr("NSCellFlags", lineBreakModeMask | text_field_flag | selectable | state_on | scrollable)
    obj.flagsOr("NSCellFlags2", textAlignmentMask | sendsActionMask | lineBreakModeMask2 | refuses_first_responder_mask)
    parent["NSControlRefusesFirstResponder"] = refuses_first_responder
    parent["NSControlLineBreakMode"] = {
        None: LineBreakMode.BY_WORD_WRAPPING,
        "wordWrapping": LineBreakMode.BY_WORD_WRAPPING,
        "charWrapping": LineBreakMode.BY_CHAR_WRAPPING,
        "clipping": LineBreakMode.BY_CLIPPING,
        "truncatingHead": LineBreakMode.BY_TRUNCATING_HEAD,
        "truncatingTail": LineBreakMode.BY_TRUNCATING_TAIL,
        "truncatingMiddle": LineBreakMode.BY_TRUNCATING_MIDDLE,
    }[lineBreakMode].value
    if obj.originalclassname() in ['NSButtonCell', 'NSTextFieldCell', 'NSImageCell']:
        textAlignmentValue = {None: 4, "left": 0, "center": 1, "right": 2}[textAlignment]
        parent["NSControlTextAlignment"] = textAlignmentValue

def _xibparser_parse_textFieldCell(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSTextFieldCell", parent, elem.attrib["id"])
    ctx.extraNibObjects.append(obj)
    __xibparser_cell_flags(elem, obj, parent)

    obj["NSControlSize2"] = 0
    obj["NSContents"] = elem.attrib.get("title", NibString.intern(''))
    obj["NSSupport"] = NibNil() # TODO
    obj["NSControlView"] = obj.xib_parent()
    obj["NSCharacterPickerEnabled"] = True
    __xibparser_ParseChildren(ctx, elem, obj)

    parent["NSCell"] = obj
    return obj


def _xibparser_parse_progressIndicator(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSProgressIndicator", elem, parent)

    bezeled_value = elem.attrib.get("bezeled", "YES") == "YES"
    bezeled = 0x1 if bezeled_value else 0
    indeterminate_value = elem.attrib.get("indeterminate", "NO") == "YES"
    indeterminate = 0x2 if indeterminate_value else 0
    style_value = elem.attrib.get("style", "bar")
    style = {"bar": 0, "spinning": 0x1000}[style_value]

    _xibparser_common_view_attributes(ctx, elem, parent, obj)
    obj["NSSuperview"] = obj.xib_parent()
    __xibparser_ParseChildren(ctx, elem, obj)
    if elem.attrib.get("maxValue"):
        obj["NSMaxValue"] = float(elem.attrib["maxValue"])
    if elem.attrib.get("minValue"):
        obj["NSMinValue"] = float(elem.attrib["minValue"])
    obj.flagsOr("NSpiFlags", 0x4004 | bezeled | indeterminate | style)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj


def _xibparser_parse_buttonCell(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSButtonCell", parent, elem.attrib["id"])
    ctx.extraNibObjects.append(obj)

    inset = int(elem.attrib.get("inset", "0"))
    inset = min(max(inset, 0), 3)
    inset = {0: 0, 1: ButtonFlags.INSET_1, 2: ButtonFlags.INSET_2, 3: (ButtonFlags.INSET_1|ButtonFlags.INSET_2)}[inset]
    buttonType = elem.attrib.get("type", "push")
    buttonTypeMask = {"push": 0, "radio": ButtonFlags.TYPE_RADIO}[buttonType]
    bezelStyleName = elem.attrib.get("bezelStyle")
    bezelStyle = {None: 0, "rounded": 1}[bezelStyleName]
    borderStyle = elem.attrib.get("borderStyle")
    borderStyleMask = {None: 0, "border": ButtonFlags.BORDERED}[borderStyle]
    imageScaling = elem.attrib.get("imageScaling")
    imageScalingMask = {None: 0, "proportionallyDown": ButtonFlags2.IMAGE_SCALING_PROPORTIONALLY_DOWN}[imageScaling]

    __xibparser_ParseChildren(ctx, elem, obj)
    __xibparser_cell_flags(elem, obj, parent)
    obj["NSControlSize2"] = 0
    obj["NSContents"] = elem.attrib["title"]
    obj["NSSupport"] = NibObject("NSFont", obj, {
        "NSName": ".AppleSystemUIFont",
        "NSSize": 13.0,
        "NSfFlags": 1044,
        })
    obj["NSControlView"] = parent
    obj.flagsOr("NSButtonFlags", inset | buttonTypeMask | borderStyleMask | 0xffffffff00000000)
    obj.flagsOr("NSButtonFlags2", 0x1 | imageScalingMask)
    if buttonType == "radio":
        obj["NSAlternateContents"] = NibObject("NSButtonImageSource", None, {
            "NSImageName": "NSRadioButton"
            })
    obj["NSBezelStyle"] = bezelStyle
    obj["NSAlternateContents"] = NibString.intern('')
    obj["NSKeyEquivalent"] = NibString.intern('')
    obj["NSPeriodicDelay"] = 400
    obj["NSPeriodicInterval"] = 75
    obj["NSAuxButtonType"] = 7
    parent["NSCell"] = obj

    if borderStyle == "border":
        v, h = parent.extraContext.get("verticalHuggingPriority", 250), parent.extraContext.get("horizontalHuggingPriority", 250)
        #parent["NSHuggingPriority"] = "{" + str(h) + ", " + str(v) + "}"

    return obj

def _xibparser_parse_font(ctx: ArchiveContext, elem: Element, parent: NibObject) -> NibObject:
    item = NibObject("NSFont")
    meta_font = elem.attrib.get("metaFont")
    assert meta_font in ["system", "systemBold", "smallSystem"], f"metaFont: {meta_font}" # other options unknown

    if meta_font == 'system':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = 13.0
        item["NSfFlags"] = 1044
    elif meta_font == 'systemBold':
        item["NSName"] = NibString.intern(".AppleSystemUIFontBold")
        item["NSSize"] = float(elem.attrib.get("size", 24.0))
        item["NSfFlags"] = 2072
    elif meta_font == 'smallSystem':
        item["NSName"] = NibString.intern(".AppleSystemUIFont")
        item["NSSize"] = 11.0
        item["NSfFlags"] = 3100
    else:
        raise Exception(f"missing font {meta_font}")
    parent["NSSupport"] = item
    return item

def _xibparser_parse_behavior(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.originalclassname() == "NSButtonCell"
    maskmap = {
        "pushIn": 1<<31,
        "lightByBackground": 1<<26,
        "lightByGray": 1<<25,
    }
    value = sum((elem.attrib[attr] == "YES") * val for attr, val in maskmap.items())
    if value == sum(maskmap.values()):
        parent["NSAuxButtonType"] = 7
    else:
        parent["NSAuxButtonType"] = 0
    parent.flagsOr("NSButtonFlags", value)

def _xibparser_parse_string(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.originalclassname() == "NSButtonCell"
    parent["NSContents"] = NibString.intern(elem.attrib.get("", ""))

def _xibparser_parse_color(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert isinstance(parent, XibObject), type(parent)
    assert elem.attrib["colorSpace"] in ["catalog", "calibratedWhite"], elem.attrib["colorSpace"]

    key = elem.attrib["key"]

    special_target_attributes = { # weird and standard attributes
        "NSView": {
            "backgroundColor": None,
        },
        "NSClipView": {
            "backgroundColor": ["NSBGColor"],
        },
        "NSTextView": {
            "backgroundColor": ["NSSharedData", "NSBackgroundColor"],
            "insertionPointColor": ["NSSharedData", "NSInsertionColor"],
            "textColor": ["NSTextViewTextColor"],
        },
        None: {
            "textColor": ["NSTextColor"],
            "backgroundColor": ["NSBackgroundColor"],
            "insertionPointColor": ["NSInsertionPointColor"],
        }
    }

    target_path = special_target_attributes.get(parent.originalclassname(), special_target_attributes[None])[key]
    if target_path is None:
        return
    target_obj = parent
    for step in target_path[:-1]:
        target_obj = target_obj[step]
    target_attribute = target_path[-1]

    if elem.attrib["colorSpace"] == "catalog":
        assert elem.attrib["catalog"] == "System", elem.attrib["catalog"]

        color = makeSystemColor(elem.attrib["name"])
        target_obj[target_attribute] = color
    elif elem.attrib["colorSpace"] == "calibratedWhite":
        white = f'{elem.attrib["white"]:.12} {elem.attrib["alpha"]:.12}\x00' if 'alpha' in elem.attrib else f'{elem.attrib["white"]:.12}\x00'
        if parent.originalclassname() == "NSClipView":
            color = NibObject("NSColor", None, {
                "NSColorSpace": 3,
                "NSWhite": NibInlineString(white)
            })
        else:
            color = NibObject("NSColor", None, {
                "NSColorSpace": 6,
                "NSCatalogName": "System",
                "NSColorName": {
                    "NSClipView": "controlBackgroundColor",
                    "NSTextView": "textBackgroundColor",
                }[parent.originalclassname()],
                "NSColor": NibObject("NSColor", None, {
                    "NSColorSpace": 3,
                    "NSComponents": NibInlineString(b'1 1'),
                    "NSCustomColorSpace": GENERIC_GREY_COLOR_SPACE,
                    "NSWhite": NibInlineString(white),
                }),
            })
        target_obj[target_attribute] = color
    else:
        raise Exception(f"unknown colorSpace {elem.attrib['colorSpace']}")


def _xibparser_parse_size(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    if elem.attrib["key"] == "maxSize":
        parent["NSMaxSize"] = f'{{{elem.attrib["width"]}, {elem.attrib["height"]}}}'
    parent.extraContext[elem.attrib["key"]] = (elem.attrib["width"], elem.attrib["height"])

def _xibparser_parse_scroller(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSScroller", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    __xibparser_ParseChildren(ctx, elem, obj)
    obj["NSNextResponder"] = obj.xib_parent()
    obj["NSAction"] = NibString.intern("_doScroller:")
    obj["NSControlAction"] = NibString.intern("_doScroller:")
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlContinuous"] = False
    obj["NSControlSendActionMask"] = 4
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlTarget"] = parent
    obj["NSTarget"] = parent
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = 0
    obj["NSControlTextAlignment"] = 0
    obj["NSControlLineBreakMode"] = 0
    obj["NSViewIsLayerTreeHost"] = True
    obj["NSControlRefusesFirstResponder"] = elem.attrib.get("refusesFirstResponder", "NO") == "YES"
    if (cur_value := elem.attrib.get("doubleValue")) is not None:
        obj["NSCurValue"] = float(cur_value)
    if elem.attrib["horizontal"] == "YES":
        parent["NSHScroller"] = obj
        obj["NSsFlags"] = sFlagsScroller.HORIZONTAL
    else:
        parent["NSVScroller"] = obj
    return obj

def _xibparser_parse_menu(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSMenu", elem, parent, view_attributes=False)
    __xibparser_ParseChildren(ctx, elem, obj)
    obj["NSTitle"] = elem.attrib.get("title", NibNil())
    if elem.attrib.get("key") == "submenu":
        parent["NSAction"] = NibString.intern("submenuAction:")
    if parent and parent.originalclassname() == "NSMenuItem":
        parent["NSTarget"] = obj
        parent["NSSubmenu"] = obj
    system_menu = elem.attrib.get("systemMenu")
    if system_menu == "apple":
        obj["NSName"] = NibString.intern("_NSAppleMenu")
    elif system_menu == "main":
        obj["NSName"] = NibString.intern("_NSMainMenu")
    return obj

MENU_MIXED_IMAGE = NibObject("NSCustomResource", None, {
    "IBDesignImageConfiguration": NibNil(),
    "IBDesignSize": NibObject("NSValue", None, {
        "NS.sizeval": NibString.intern("{18, 4}"),
        "NS.special": 2,
    }),
    "IBNamespaceID": NibNil(),
    "NSClassName": NibString.intern("NSImage"),
    "NSResourceName": NibString.intern("NSMenuMixedState"),
})

MENU_ON_IMAGE = NibObject("NSCustomResource", None, {
    "IBDesignImageConfiguration": NibNil(),
    "IBDesignSize": NibObject("NSValue", None, {
        "NS.sizeval": NibString.intern("{18, 16}"),
        "NS.special": 2,
    }),
    "IBNamespaceID": NibNil(),
    "NSClassName": NibString.intern("NSImage"),
    "NSResourceName": NibString.intern("NSMenuCheckmark"),
})

def _xibparser_parse_menuItem(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSMenuItem", elem, parent, view_attributes=False)
    __xibparser_ParseChildren(ctx, elem, obj)
    if parent and parent.originalclassname() == "NSMenu":
        obj["NSMenu"] = parent
    obj["NSAllowsKeyEquivalentLocalization"] = True
    obj["NSAllowsKeyEquivalentMirroring"] = True
    obj["NSHiddenInRepresentation"] = False
    if (key_equiv := elem.attrib.get("keyEquivalent")) is not None:
        obj["NSKeyEquiv"] = NibString.intern(key_equiv)
    else:
        obj["NSKeyEquiv"] = NibString.intern('')
    if elem.attrib.get("keyEquivalentModifierMask") is not None or key_equiv:
        obj["NSKeyEquivModMask"] = 0x100000
    obj["NSMixedImage"] = MENU_MIXED_IMAGE
    obj["NSMnemonicLoc"] = 0x7fffffff
    obj["NSOnImage"] = MENU_ON_IMAGE
    obj["NSTitle"] = NibString.intern(elem.attrib.get("title", ""))
    if elem.attrib.get("isSeparatorItem") == "YES":
        obj["NSIsSeparator"] = True
        obj["NSIsDisabled"] = True
    return obj

def _xibparser_parse_items(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.originalclassname() == "NSMenu"
    children = __xibparser_ParseChildren(ctx, elem, parent)
    parent["NSMenuItems"] = NibMutableList(children)

def _xibparser_parse_modifierMask(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    pass

def makeSystemColor(name):
    def systemGrayColorTemplate(name, components, white):
        return NibObject('NSColor', None, {
            'NSCatalogName': 'System',
            'NSColor': NibObject('NSColor', None, {
                'NSColorSpace': 3,
                'NSComponents': NibInlineString(components),
                'NSCustomColorSpace': GENERIC_GREY_COLOR_SPACE,
                'NSWhite': NibInlineString(white),
                }),
            'NSColorName': NibString.intern(name),
            'NSColorSpace': 6,
            })

    def systemRGBColorTemplate(name, sub_name, components, rgb):
        return NibObject("NSColor", None, {
            "NSCatalogName": NibString.intern("System"),
            "NSColorName": NibString.intern(name),
            "NSColorSpace": 6,
            "NSColor": NibObject("NSColor", None, {
                "NSCatalogName": NibString.intern("System"),
                "NSColorSpace": 6,
                "NSColorName": NibString.intern(sub_name),
                "NSColor": NibObject("NSColor", None, {
                    "NSComponents": NibInlineString(components),
                    "NSColorSpace": 1,
                    "NSRGB": NibInlineString(rgb),
                    "NSCustomColorSpace": RGB_COLOR_SPACE,
                }),
            })
    })


    if name == 'controlColor':
        return systemGrayColorTemplate(name, b'0.6666666667 1', b'0.602715373\x00')
    elif name == 'controlTextColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'controlBackgroundColor':
        return systemGrayColorTemplate(name, b'0.6666666667 1', b'0.602715373\x00')
    elif name == 'textColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'textBackgroundColor':
        return systemGrayColorTemplate(name, b'1 1', b'1\x00')
    elif name == 'labelColor':
        return systemGrayColorTemplate(name, b'0 1', b'0\x00')
    elif name == 'textInsertionPointColor':
        return systemRGBColorTemplate(name, 'systemBlueColor', '0 0 1 1', b'0 0 0.9981992245\x00')
    else:
        raise Exception(f"unknown name {name}")


@contextmanager
def __handle_view_chain(ctx: ArchiveContext, obj: XibObject):
    if ctx.viewKeyList:
        ctx.viewKeyList[-1]["NSNextKeyView"] = obj
    ctx.viewKeyList.append(obj)
    yield object()
    ctx.viewKeyList.pop(-1)

    x, y, w, h = obj.frame()
    if x == 0 and y == 0:
        obj["NSFrameSize"] = NibString.intern(f"{{{w}, {h}}}")
    else:
        obj["NSFrame"] = NibString.intern(f"{{{{{x}, {y}}}, {{{w}, {h}}}}}")


# is it default? TODO
GENERIC_GREY_COLOR_SPACE_NSICC = NibData.intern(b'\x00\x00\x11\x9cappl\x02\x00\x00\x00mntrGRAYXYZ \x07\xdc\x00\x08\x00\x17\x00\x0f\x00.\x00\x0facspAPPL\x00\x00\x00\x00none\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-appl\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05desc\x00\x00\x00\xc0\x00\x00\x00ydscm\x00\x00\x01<\x00\x00\x08\x1acprt\x00\x00\tX\x00\x00\x00#wtpt\x00\x00\t|\x00\x00\x00\x14kTRC\x00\x00\t\x90\x00\x00\x08\x0cdesc\x00\x00\x00\x00\x00\x00\x00\x1fGeneric Gray Gamma 2.2 Profile\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00mluc\x00\x00\x00\x00\x00\x00\x00\x1f\x00\x00\x00\x0cskSK\x00\x00\x00.\x00\x00\x01\x84daDK\x00\x00\x00:\x00\x00\x01\xb2caES\x00\x00\x008\x00\x00\x01\xecviVN\x00\x00\x00@\x00\x00\x02$ptBR\x00\x00\x00J\x00\x00\x02dukUA\x00\x00\x00,\x00\x00\x02\xaefrFU\x00\x00\x00>\x00\x00\x02\xdahuHU\x00\x00\x004\x00\x00\x03\x18zhTW\x00\x00\x00\x1a\x00\x00\x03LkoKR\x00\x00\x00"\x00\x00\x03fnbNO\x00\x00\x00:\x00\x00\x03\x88csCZ\x00\x00\x00(\x00\x00\x03\xc2heIL\x00\x00\x00$\x00\x00\x03\xearoRO\x00\x00\x00*\x00\x00\x04\x0edeDE\x00\x00\x00N\x00\x00\x048itIT\x00\x00\x00N\x00\x00\x04\x86svSE\x00\x00\x008\x00\x00\x04\xd4zhCN\x00\x00\x00\x1a\x00\x00\x05\x0cjaJP\x00\x00\x00&\x00\x00\x05&elGR\x00\x00\x00*\x00\x00\x05LptPO\x00\x00\x00R\x00\x00\x05vnlNL\x00\x00\x00@\x00\x00\x05\xc8esES\x00\x00\x00L\x00\x00\x06\x08thTH\x00\x00\x002\x00\x00\x06TtrTR\x00\x00\x00$\x00\x00\x06\x86fiFI\x00\x00\x00F\x00\x00\x06\xaahrHR\x00\x00\x00>\x00\x00\x06\xf0plPL\x00\x00\x00J\x00\x00\x07.arEG\x00\x00\x00,\x00\x00\x07xruRU\x00\x00\x00:\x00\x00\x07\xa4enUS\x00\x00\x00<\x00\x00\x07\xde\x00V\x01a\x00e\x00o\x00b\x00e\x00c\x00n\x00\xe1\x00 \x00s\x00i\x00v\x00\xe1\x00 \x00g\x00a\x00m\x00a\x00 \x002\x00,\x002\x00G\x00e\x00n\x00e\x00r\x00i\x00s\x00k\x00 \x00g\x00r\x00\xe5\x00 \x002\x00,\x002\x00 \x00g\x00a\x00m\x00m\x00a\x00-\x00p\x00r\x00o\x00f\x00i\x00l\x00G\x00a\x00m\x00m\x00a\x00 \x00d\x00e\x00 \x00g\x00r\x00i\x00s\x00o\x00s\x00 \x00g\x00e\x00n\x00\xe8\x00r\x00i\x00c\x00a\x00 \x002\x00.\x002\x00C\x1e\xa5\x00u\x00 \x00h\x00\xec\x00n\x00h\x00 \x00M\x00\xe0\x00u\x00 \x00x\x00\xe1\x00m\x00 \x00C\x00h\x00u\x00n\x00g\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x00P\x00e\x00r\x00f\x00i\x00l\x00 \x00G\x00e\x00n\x00\xe9\x00r\x00i\x00c\x00o\x00 \x00d\x00a\x00 \x00G\x00a\x00m\x00a\x00 \x00d\x00e\x00 \x00C\x00i\x00n\x00z\x00a\x00s\x00 \x002\x00,\x002\x04\x17\x040\x043\x040\x04;\x04L\x04=\x040\x00 \x00G\x00r\x00a\x00y\x00-\x043\x040\x04<\x040\x00 \x002\x00.\x002\x00P\x00r\x00o\x00f\x00i\x00l\x00 \x00g\x00\xe9\x00n\x00\xe9\x00r\x00i\x00q\x00u\x00e\x00 \x00g\x00r\x00i\x00s\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00\xc1\x00l\x00t\x00a\x00l\x00\xe1\x00n\x00o\x00s\x00 \x00s\x00z\x00\xfc\x00r\x00k\x00e\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x90\x1au(pp\x96\x8eQI^\xa6\x002\x00.\x002\x82r_ic\xcf\x8f\xf0\xc7|\xbc\x18\x00 \xd6\x8c\xc0\xc9\x00 \xac\x10\xb9\xc8\x00 \x002\x00.\x002\x00 \xd5\x04\xb8\\\xd3\x0c\xc7|\x00G\x00e\x00n\x00e\x00r\x00i\x00s\x00k\x00 \x00g\x00r\x00\xe5\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00-\x00p\x00r\x00o\x00f\x00i\x00l\x00O\x00b\x00e\x00c\x00n\x00\xe1\x00 \x01a\x00e\x00d\x00\xe1\x00 \x00g\x00a\x00m\x00a\x00 \x002\x00.\x002\x05\xd2\x05\xd0\x05\xde\x05\xd4\x00 \x05\xd0\x05\xe4\x05\xd5\x05\xe8\x00 \x05\xdb\x05\xdc\x05\xdc\x05\xd9\x00 \x002\x00.\x002\x00G\x00a\x00m\x00a\x00 \x00g\x00r\x00i\x00 \x00g\x00e\x00n\x00e\x00r\x00i\x00c\x01\x03\x00 \x002\x00,\x002\x00A\x00l\x00l\x00g\x00e\x00m\x00e\x00i\x00n\x00e\x00s\x00 \x00G\x00r\x00a\x00u\x00s\x00t\x00u\x00f\x00e\x00n\x00-\x00P\x00r\x00o\x00f\x00i\x00l\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00P\x00r\x00o\x00f\x00i\x00l\x00o\x00 \x00g\x00r\x00i\x00g\x00i\x00o\x00 \x00g\x00e\x00n\x00e\x00r\x00i\x00c\x00o\x00 \x00d\x00e\x00l\x00l\x00a\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00G\x00e\x00n\x00e\x00r\x00i\x00s\x00k\x00 \x00g\x00r\x00\xe5\x00 \x002\x00,\x002\x00 \x00g\x00a\x00m\x00m\x00a\x00p\x00r\x00o\x00f\x00i\x00lfn\x90\x1app^\xa6|\xfbep\x002\x00.\x002c\xcf\x8f\xf0e\x87N\xf6N\x00\x82,0\xb00\xec0\xa40\xac0\xf30\xde\x00 \x002\x00.\x002\x00 0\xd70\xed0\xd50\xa10\xa40\xeb\x03\x93\x03\xb5\x03\xbd\x03\xb9\x03\xba\x03\xcc\x00 \x03\x93\x03\xba\x03\xc1\x03\xb9\x00 \x03\x93\x03\xac\x03\xbc\x03\xbc\x03\xb1\x00 \x002\x00.\x002\x00P\x00e\x00r\x00f\x00i\x00l\x00 \x00g\x00e\x00n\x00\xe9\x00r\x00i\x00c\x00o\x00 \x00d\x00e\x00 \x00c\x00i\x00n\x00z\x00e\x00n\x00t\x00o\x00s\x00 \x00d\x00a\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00A\x00l\x00g\x00e\x00m\x00e\x00e\x00n\x00 \x00g\x00r\x00i\x00j\x00s\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00-\x00p\x00r\x00o\x00f\x00i\x00e\x00l\x00P\x00e\x00r\x00f\x00i\x00l\x00 \x00g\x00e\x00n\x00\xe9\x00r\x00i\x00c\x00o\x00 \x00d\x00e\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x00d\x00e\x00 \x00g\x00r\x00i\x00s\x00e\x00s\x00 \x002\x00,\x002\x0e#\x0e1\x0e\x07\x0e*\x0e5\x0eA\x0e\x01\x0e!\x0e!\x0e2\x0e@\x0e\x01\x0e#\x0e"\x0eL\x0e\x17\x0e1\x0eH\x0e\'\x0eD\x0e\x1b\x00 \x002\x00.\x002\x00G\x00e\x00n\x00e\x00l\x00 \x00G\x00r\x00i\x00 \x00G\x00a\x00m\x00a\x00 \x002\x00,\x002\x00Y\x00l\x00e\x00i\x00n\x00e\x00n\x00 \x00h\x00a\x00r\x00m\x00a\x00a\x00n\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00 \x00-\x00p\x00r\x00o\x00f\x00i\x00i\x00l\x00i\x00G\x00e\x00n\x00e\x00r\x00i\x01\r\x00k\x00i\x00 \x00G\x00r\x00a\x00y\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x00 \x00p\x00r\x00o\x00f\x00i\x00l\x00U\x00n\x00i\x00w\x00e\x00r\x00s\x00a\x00l\x00n\x00y\x00 \x00p\x00r\x00o\x00f\x00i\x00l\x00 \x00s\x00z\x00a\x00r\x00o\x01[\x00c\x00i\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x06:\x06\'\x06E\x06\'\x00 \x002\x00.\x002\x00 \x06D\x06H\x06F\x00 \x061\x06E\x06\'\x06/\x06J\x00 \x069\x06\'\x06E\x04\x1e\x041\x04I\x040\x04O\x00 \x04A\x045\x04@\x040\x04O\x00 \x043\x040\x04<\x04<\x040\x00 \x002\x00,\x002\x00-\x04?\x04@\x04>\x04D\x048\x04;\x04L\x00G\x00e\x00n\x00e\x00r\x00i\x00c\x00 \x00G\x00r\x00a\x00y\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x00 \x00P\x00r\x00o\x00f\x00i\x00l\x00e\x00\x00text\x00\x00\x00\x00Copyright Apple Inc., 2012\x00\x00XYZ \x00\x00\x00\x00\x00\x00\xf3Q\x00\x01\x00\x00\x00\x01\x16\xcccurv\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x05\x00\n\x00\x0f\x00\x14\x00\x19\x00\x1e\x00#\x00(\x00-\x002\x007\x00;\x00@\x00E\x00J\x00O\x00T\x00Y\x00^\x00c\x00h\x00m\x00r\x00w\x00|\x00\x81\x00\x86\x00\x8b\x00\x90\x00\x95\x00\x9a\x00\x9f\x00\xa4\x00\xa9\x00\xae\x00\xb2\x00\xb7\x00\xbc\x00\xc1\x00\xc6\x00\xcb\x00\xd0\x00\xd5\x00\xdb\x00\xe0\x00\xe5\x00\xeb\x00\xf0\x00\xf6\x00\xfb\x01\x01\x01\x07\x01\r\x01\x13\x01\x19\x01\x1f\x01%\x01+\x012\x018\x01>\x01E\x01L\x01R\x01Y\x01`\x01g\x01n\x01u\x01|\x01\x83\x01\x8b\x01\x92\x01\x9a\x01\xa1\x01\xa9\x01\xb1\x01\xb9\x01\xc1\x01\xc9\x01\xd1\x01\xd9\x01\xe1\x01\xe9\x01\xf2\x01\xfa\x02\x03\x02\x0c\x02\x14\x02\x1d\x02&\x02/\x028\x02A\x02K\x02T\x02]\x02g\x02q\x02z\x02\x84\x02\x8e\x02\x98\x02\xa2\x02\xac\x02\xb6\x02\xc1\x02\xcb\x02\xd5\x02\xe0\x02\xeb\x02\xf5\x03\x00\x03\x0b\x03\x16\x03!\x03-\x038\x03C\x03O\x03Z\x03f\x03r\x03~\x03\x8a\x03\x96\x03\xa2\x03\xae\x03\xba\x03\xc7\x03\xd3\x03\xe0\x03\xec\x03\xf9\x04\x06\x04\x13\x04 \x04-\x04;\x04H\x04U\x04c\x04q\x04~\x04\x8c\x04\x9a\x04\xa8\x04\xb6\x04\xc4\x04\xd3\x04\xe1\x04\xf0\x04\xfe\x05\r\x05\x1c\x05+\x05:\x05I\x05X\x05g\x05w\x05\x86\x05\x96\x05\xa6\x05\xb5\x05\xc5\x05\xd5\x05\xe5\x05\xf6\x06\x06\x06\x16\x06\'\x067\x06H\x06Y\x06j\x06{\x06\x8c\x06\x9d\x06\xaf\x06\xc0\x06\xd1\x06\xe3\x06\xf5\x07\x07\x07\x19\x07+\x07=\x07O\x07a\x07t\x07\x86\x07\x99\x07\xac\x07\xbf\x07\xd2\x07\xe5\x07\xf8\x08\x0b\x08\x1f\x082\x08F\x08Z\x08n\x08\x82\x08\x96\x08\xaa\x08\xbe\x08\xd2\x08\xe7\x08\xfb\t\x10\t%\t:\tO\td\ty\t\x8f\t\xa4\t\xba\t\xcf\t\xe5\t\xfb\n\x11\n\'\n=\nT\nj\n\x81\n\x98\n\xae\n\xc5\n\xdc\n\xf3\x0b\x0b\x0b"\x0b9\x0bQ\x0bi\x0b\x80\x0b\x98\x0b\xb0\x0b\xc8\x0b\xe1\x0b\xf9\x0c\x12\x0c*\x0cC\x0c\\\x0cu\x0c\x8e\x0c\xa7\x0c\xc0\x0c\xd9\x0c\xf3\r\r\r&\r@\rZ\rt\r\x8e\r\xa9\r\xc3\r\xde\r\xf8\x0e\x13\x0e.\x0eI\x0ed\x0e\x7f\x0e\x9b\x0e\xb6\x0e\xd2\x0e\xee\x0f\t\x0f%\x0fA\x0f^\x0fz\x0f\x96\x0f\xb3\x0f\xcf\x0f\xec\x10\t\x10&\x10C\x10a\x10~\x10\x9b\x10\xb9\x10\xd7\x10\xf5\x11\x13\x111\x11O\x11m\x11\x8c\x11\xaa\x11\xc9\x11\xe8\x12\x07\x12&\x12E\x12d\x12\x84\x12\xa3\x12\xc3\x12\xe3\x13\x03\x13#\x13C\x13c\x13\x83\x13\xa4\x13\xc5\x13\xe5\x14\x06\x14\'\x14I\x14j\x14\x8b\x14\xad\x14\xce\x14\xf0\x15\x12\x154\x15V\x15x\x15\x9b\x15\xbd\x15\xe0\x16\x03\x16&\x16I\x16l\x16\x8f\x16\xb2\x16\xd6\x16\xfa\x17\x1d\x17A\x17e\x17\x89\x17\xae\x17\xd2\x17\xf7\x18\x1b\x18@\x18e\x18\x8a\x18\xaf\x18\xd5\x18\xfa\x19 \x19E\x19k\x19\x91\x19\xb7\x19\xdd\x1a\x04\x1a*\x1aQ\x1aw\x1a\x9e\x1a\xc5\x1a\xec\x1b\x14\x1b;\x1bc\x1b\x8a\x1b\xb2\x1b\xda\x1c\x02\x1c*\x1cR\x1c{\x1c\xa3\x1c\xcc\x1c\xf5\x1d\x1e\x1dG\x1dp\x1d\x99\x1d\xc3\x1d\xec\x1e\x16\x1e@\x1ej\x1e\x94\x1e\xbe\x1e\xe9\x1f\x13\x1f>\x1fi\x1f\x94\x1f\xbf\x1f\xea \x15 A l \x98 \xc4 \xf0!\x1c!H!u!\xa1!\xce!\xfb"\'"U"\x82"\xaf"\xdd#\n#8#f#\x94#\xc2#\xf0$\x1f$M$|$\xab$\xda%\t%8%h%\x97%\xc7%\xf7&\'&W&\x87&\xb7&\xe8\'\x18\'I\'z\'\xab\'\xdc(\r(?(q(\xa2(\xd4)\x06)8)k)\x9d)\xd0*\x02*5*h*\x9b*\xcf+\x02+6+i+\x9d+\xd1,\x05,9,n,\xa2,\xd7-\x0c-A-v-\xab-\xe1.\x16.L.\x82.\xb7.\xee/$/Z/\x91/\xc7/\xfe050l0\xa40\xdb1\x121J1\x821\xba1\xf22*2c2\x9b2\xd43\r3F3\x7f3\xb83\xf14+4e4\x9e4\xd85\x135M5\x875\xc25\xfd676r6\xae6\xe97$7`7\x9c7\xd78\x148P8\x8c8\xc89\x059B9\x7f9\xbc9\xf9:6:t:\xb2:\xef;-;k;\xaa;\xe8<\'<e<\xa4<\xe3="=a=\xa1=\xe0> >`>\xa0>\xe0?!?a?\xa2?\xe2@#@d@\xa6@\xe7A)AjA\xacA\xeeB0BrB\xb5B\xf7C:C}C\xc0D\x03DGD\x8aD\xceE\x12EUE\x9aE\xdeF"FgF\xabF\xf0G5G{G\xc0H\x05HKH\x91H\xd7I\x1dIcI\xa9I\xf0J7J}J\xc4K\x0cKSK\x9aK\xe2L*LrL\xbaM\x02MJM\x93M\xdcN%NnN\xb7O\x00OIO\x93O\xddP\'PqP\xbbQ\x06QPQ\x9bQ\xe6R1R|R\xc7S\x13S_S\xaaS\xf6TBT\x8fT\xdbU(UuU\xc2V\x0fV\\V\xa9V\xf7WDW\x92W\xe0X/X}X\xcbY\x1aYiY\xb8Z\x07ZVZ\xa6Z\xf5[E[\x95[\xe5\\5\\\x86\\\xd6]\']x]\xc9^\x1a^l^\xbd_\x0f_a_\xb3`\x05`W`\xaa`\xfcaOa\xa2a\xf5bIb\x9cb\xf0cCc\x97c\xebd@d\x94d\xe9e=e\x92e\xe7f=f\x92f\xe8g=g\x93g\xe9h?h\x96h\xeciCi\x9ai\xf1jHj\x9fj\xf7kOk\xa7k\xfflWl\xafm\x08m`m\xb9n\x12nkn\xc4o\x1eoxo\xd1p+p\x86p\xe0q:q\x95q\xf0rKr\xa6s\x01s]s\xb8t\x14tpt\xccu(u\x85u\xe1v>v\x9bv\xf8wVw\xb3x\x11xnx\xccy*y\x89y\xe7zFz\xa5{\x04{c{\xc2|!|\x81|\xe1}A}\xa1~\x01~b~\xc2\x7f#\x7f\x84\x7f\xe5\x80G\x80\xa8\x81\n\x81k\x81\xcd\x820\x82\x92\x82\xf4\x83W\x83\xba\x84\x1d\x84\x80\x84\xe3\x85G\x85\xab\x86\x0e\x86r\x86\xd7\x87;\x87\x9f\x88\x04\x88i\x88\xce\x893\x89\x99\x89\xfe\x8ad\x8a\xca\x8b0\x8b\x96\x8b\xfc\x8cc\x8c\xca\x8d1\x8d\x98\x8d\xff\x8ef\x8e\xce\x8f6\x8f\x9e\x90\x06\x90n\x90\xd6\x91?\x91\xa8\x92\x11\x92z\x92\xe3\x93M\x93\xb6\x94 \x94\x8a\x94\xf4\x95_\x95\xc9\x964\x96\x9f\x97\n\x97u\x97\xe0\x98L\x98\xb8\x99$\x99\x90\x99\xfc\x9ah\x9a\xd5\x9bB\x9b\xaf\x9c\x1c\x9c\x89\x9c\xf7\x9dd\x9d\xd2\x9e@\x9e\xae\x9f\x1d\x9f\x8b\x9f\xfa\xa0i\xa0\xd8\xa1G\xa1\xb6\xa2&\xa2\x96\xa3\x06\xa3v\xa3\xe6\xa4V\xa4\xc7\xa58\xa5\xa9\xa6\x1a\xa6\x8b\xa6\xfd\xa7n\xa7\xe0\xa8R\xa8\xc4\xa97\xa9\xa9\xaa\x1c\xaa\x8f\xab\x02\xabu\xab\xe9\xac\\\xac\xd0\xadD\xad\xb8\xae-\xae\xa1\xaf\x16\xaf\x8b\xb0\x00\xb0u\xb0\xea\xb1`\xb1\xd6\xb2K\xb2\xc2\xb38\xb3\xae\xb4%\xb4\x9c\xb5\x13\xb5\x8a\xb6\x01\xb6y\xb6\xf0\xb7h\xb7\xe0\xb8Y\xb8\xd1\xb9J\xb9\xc2\xba;\xba\xb5\xbb.\xbb\xa7\xbc!\xbc\x9b\xbd\x15\xbd\x8f\xbe\n\xbe\x84\xbe\xff\xbfz\xbf\xf5\xc0p\xc0\xec\xc1g\xc1\xe3\xc2_\xc2\xdb\xc3X\xc3\xd4\xc4Q\xc4\xce\xc5K\xc5\xc8\xc6F\xc6\xc3\xc7A\xc7\xbf\xc8=\xc8\xbc\xc9:\xc9\xb9\xca8\xca\xb7\xcb6\xcb\xb6\xcc5\xcc\xb5\xcd5\xcd\xb5\xce6\xce\xb6\xcf7\xcf\xb8\xd09\xd0\xba\xd1<\xd1\xbe\xd2?\xd2\xc1\xd3D\xd3\xc6\xd4I\xd4\xcb\xd5N\xd5\xd1\xd6U\xd6\xd8\xd7\\\xd7\xe0\xd8d\xd8\xe8\xd9l\xd9\xf1\xdav\xda\xfb\xdb\x80\xdc\x05\xdc\x8a\xdd\x10\xdd\x96\xde\x1c\xde\xa2\xdf)\xdf\xaf\xe06\xe0\xbd\xe1D\xe1\xcc\xe2S\xe2\xdb\xe3c\xe3\xeb\xe4s\xe4\xfc\xe5\x84\xe6\r\xe6\x96\xe7\x1f\xe7\xa9\xe82\xe8\xbc\xe9F\xe9\xd0\xea[\xea\xe5\xebp\xeb\xfb\xec\x86\xed\x11\xed\x9c\xee(\xee\xb4\xef@\xef\xcc\xf0X\xf0\xe5\xf1r\xf1\xff\xf2\x8c\xf3\x19\xf3\xa7\xf44\xf4\xc2\xf5P\xf5\xde\xf6m\xf6\xfb\xf7\x8a\xf8\x19\xf8\xa8\xf98\xf9\xc7\xfaW\xfa\xe7\xfbw\xfc\x07\xfc\x98\xfd)\xfd\xba\xfeK\xfe\xdc\xffm\xff\xff')
RGB_COLOR_SPACE_NSICC = NibData.intern(b'\x00\x00\x0cHLino\x02\x10\x00\x00mntrRGB XYZ \x07\xce\x00\x02\x00\t\x00\x06\x001\x00\x00acspMSFT\x00\x00\x00\x00IEC sRGB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-HP  \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11cprt\x00\x00\x01P\x00\x00\x003desc\x00\x00\x01\x84\x00\x00\x00lwtpt\x00\x00\x01\xf0\x00\x00\x00\x14bkpt\x00\x00\x02\x04\x00\x00\x00\x14rXYZ\x00\x00\x02\x18\x00\x00\x00\x14gXYZ\x00\x00\x02,\x00\x00\x00\x14bXYZ\x00\x00\x02@\x00\x00\x00\x14dmnd\x00\x00\x02T\x00\x00\x00pdmdd\x00\x00\x02\xc4\x00\x00\x00\x88vued\x00\x00\x03L\x00\x00\x00\x86view\x00\x00\x03\xd4\x00\x00\x00$lumi\x00\x00\x03\xf8\x00\x00\x00\x14meas\x00\x00\x04\x0c\x00\x00\x00$tech\x00\x00\x040\x00\x00\x00\x0crTRC\x00\x00\x04<\x00\x00\x08\x0cgTRC\x00\x00\x04<\x00\x00\x08\x0cbTRC\x00\x00\x04<\x00\x00\x08\x0ctext\x00\x00\x00\x00Copyright (c) 1998 Hewlett-Packard Company\x00\x00desc\x00\x00\x00\x00\x00\x00\x00\x12sRGB IEC61966-2.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12sRGB IEC61966-2.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00XYZ \x00\x00\x00\x00\x00\x00\xf3Q\x00\x01\x00\x00\x00\x01\x16\xccXYZ \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00XYZ \x00\x00\x00\x00\x00\x00o\xa2\x00\x008\xf5\x00\x00\x03\x90XYZ \x00\x00\x00\x00\x00\x00b\x99\x00\x00\xb7\x85\x00\x00\x18\xdaXYZ \x00\x00\x00\x00\x00\x00$\xa0\x00\x00\x0f\x84\x00\x00\xb6\xcfdesc\x00\x00\x00\x00\x00\x00\x00\x16IEC http://www.iec.ch\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x16IEC http://www.iec.ch\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00desc\x00\x00\x00\x00\x00\x00\x00.IEC 61966-2.1 Default RGB colour space - sRGB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.IEC 61966-2.1 Default RGB colour space - sRGB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00desc\x00\x00\x00\x00\x00\x00\x00,Reference Viewing Condition in IEC61966-2.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00,Reference Viewing Condition in IEC61966-2.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00view\x00\x00\x00\x00\x00\x13\xa4\xfe\x00\x14_.\x00\x10\xcf\x14\x00\x03\xed\xcc\x00\x04\x13\x0b\x00\x03\\\x9e\x00\x00\x00\x01XYZ \x00\x00\x00\x00\x00L\tV\x00P\x00\x00\x00W\x1f\xe7meas\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x8f\x00\x00\x00\x02sig \x00\x00\x00\x00CRT curv\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x05\x00\n\x00\x0f\x00\x14\x00\x19\x00\x1e\x00#\x00(\x00-\x002\x007\x00;\x00@\x00E\x00J\x00O\x00T\x00Y\x00^\x00c\x00h\x00m\x00r\x00w\x00|\x00\x81\x00\x86\x00\x8b\x00\x90\x00\x95\x00\x9a\x00\x9f\x00\xa4\x00\xa9\x00\xae\x00\xb2\x00\xb7\x00\xbc\x00\xc1\x00\xc6\x00\xcb\x00\xd0\x00\xd5\x00\xdb\x00\xe0\x00\xe5\x00\xeb\x00\xf0\x00\xf6\x00\xfb\x01\x01\x01\x07\x01\r\x01\x13\x01\x19\x01\x1f\x01%\x01+\x012\x018\x01>\x01E\x01L\x01R\x01Y\x01`\x01g\x01n\x01u\x01|\x01\x83\x01\x8b\x01\x92\x01\x9a\x01\xa1\x01\xa9\x01\xb1\x01\xb9\x01\xc1\x01\xc9\x01\xd1\x01\xd9\x01\xe1\x01\xe9\x01\xf2\x01\xfa\x02\x03\x02\x0c\x02\x14\x02\x1d\x02&\x02/\x028\x02A\x02K\x02T\x02]\x02g\x02q\x02z\x02\x84\x02\x8e\x02\x98\x02\xa2\x02\xac\x02\xb6\x02\xc1\x02\xcb\x02\xd5\x02\xe0\x02\xeb\x02\xf5\x03\x00\x03\x0b\x03\x16\x03!\x03-\x038\x03C\x03O\x03Z\x03f\x03r\x03~\x03\x8a\x03\x96\x03\xa2\x03\xae\x03\xba\x03\xc7\x03\xd3\x03\xe0\x03\xec\x03\xf9\x04\x06\x04\x13\x04 \x04-\x04;\x04H\x04U\x04c\x04q\x04~\x04\x8c\x04\x9a\x04\xa8\x04\xb6\x04\xc4\x04\xd3\x04\xe1\x04\xf0\x04\xfe\x05\r\x05\x1c\x05+\x05:\x05I\x05X\x05g\x05w\x05\x86\x05\x96\x05\xa6\x05\xb5\x05\xc5\x05\xd5\x05\xe5\x05\xf6\x06\x06\x06\x16\x06\'\x067\x06H\x06Y\x06j\x06{\x06\x8c\x06\x9d\x06\xaf\x06\xc0\x06\xd1\x06\xe3\x06\xf5\x07\x07\x07\x19\x07+\x07=\x07O\x07a\x07t\x07\x86\x07\x99\x07\xac\x07\xbf\x07\xd2\x07\xe5\x07\xf8\x08\x0b\x08\x1f\x082\x08F\x08Z\x08n\x08\x82\x08\x96\x08\xaa\x08\xbe\x08\xd2\x08\xe7\x08\xfb\t\x10\t%\t:\tO\td\ty\t\x8f\t\xa4\t\xba\t\xcf\t\xe5\t\xfb\n\x11\n\'\n=\nT\nj\n\x81\n\x98\n\xae\n\xc5\n\xdc\n\xf3\x0b\x0b\x0b"\x0b9\x0bQ\x0bi\x0b\x80\x0b\x98\x0b\xb0\x0b\xc8\x0b\xe1\x0b\xf9\x0c\x12\x0c*\x0cC\x0c\\\x0cu\x0c\x8e\x0c\xa7\x0c\xc0\x0c\xd9\x0c\xf3\r\r\r&\r@\rZ\rt\r\x8e\r\xa9\r\xc3\r\xde\r\xf8\x0e\x13\x0e.\x0eI\x0ed\x0e\x7f\x0e\x9b\x0e\xb6\x0e\xd2\x0e\xee\x0f\t\x0f%\x0fA\x0f^\x0fz\x0f\x96\x0f\xb3\x0f\xcf\x0f\xec\x10\t\x10&\x10C\x10a\x10~\x10\x9b\x10\xb9\x10\xd7\x10\xf5\x11\x13\x111\x11O\x11m\x11\x8c\x11\xaa\x11\xc9\x11\xe8\x12\x07\x12&\x12E\x12d\x12\x84\x12\xa3\x12\xc3\x12\xe3\x13\x03\x13#\x13C\x13c\x13\x83\x13\xa4\x13\xc5\x13\xe5\x14\x06\x14\'\x14I\x14j\x14\x8b\x14\xad\x14\xce\x14\xf0\x15\x12\x154\x15V\x15x\x15\x9b\x15\xbd\x15\xe0\x16\x03\x16&\x16I\x16l\x16\x8f\x16\xb2\x16\xd6\x16\xfa\x17\x1d\x17A\x17e\x17\x89\x17\xae\x17\xd2\x17\xf7\x18\x1b\x18@\x18e\x18\x8a\x18\xaf\x18\xd5\x18\xfa\x19 \x19E\x19k\x19\x91\x19\xb7\x19\xdd\x1a\x04\x1a*\x1aQ\x1aw\x1a\x9e\x1a\xc5\x1a\xec\x1b\x14\x1b;\x1bc\x1b\x8a\x1b\xb2\x1b\xda\x1c\x02\x1c*\x1cR\x1c{\x1c\xa3\x1c\xcc\x1c\xf5\x1d\x1e\x1dG\x1dp\x1d\x99\x1d\xc3\x1d\xec\x1e\x16\x1e@\x1ej\x1e\x94\x1e\xbe\x1e\xe9\x1f\x13\x1f>\x1fi\x1f\x94\x1f\xbf\x1f\xea \x15 A l \x98 \xc4 \xf0!\x1c!H!u!\xa1!\xce!\xfb"\'"U"\x82"\xaf"\xdd#\n#8#f#\x94#\xc2#\xf0$\x1f$M$|$\xab$\xda%\t%8%h%\x97%\xc7%\xf7&\'&W&\x87&\xb7&\xe8\'\x18\'I\'z\'\xab\'\xdc(\r(?(q(\xa2(\xd4)\x06)8)k)\x9d)\xd0*\x02*5*h*\x9b*\xcf+\x02+6+i+\x9d+\xd1,\x05,9,n,\xa2,\xd7-\x0c-A-v-\xab-\xe1.\x16.L.\x82.\xb7.\xee/$/Z/\x91/\xc7/\xfe050l0\xa40\xdb1\x121J1\x821\xba1\xf22*2c2\x9b2\xd43\r3F3\x7f3\xb83\xf14+4e4\x9e4\xd85\x135M5\x875\xc25\xfd676r6\xae6\xe97$7`7\x9c7\xd78\x148P8\x8c8\xc89\x059B9\x7f9\xbc9\xf9:6:t:\xb2:\xef;-;k;\xaa;\xe8<\'<e<\xa4<\xe3="=a=\xa1=\xe0> >`>\xa0>\xe0?!?a?\xa2?\xe2@#@d@\xa6@\xe7A)AjA\xacA\xeeB0BrB\xb5B\xf7C:C}C\xc0D\x03DGD\x8aD\xceE\x12EUE\x9aE\xdeF"FgF\xabF\xf0G5G{G\xc0H\x05HKH\x91H\xd7I\x1dIcI\xa9I\xf0J7J}J\xc4K\x0cKSK\x9aK\xe2L*LrL\xbaM\x02MJM\x93M\xdcN%NnN\xb7O\x00OIO\x93O\xddP\'PqP\xbbQ\x06QPQ\x9bQ\xe6R1R|R\xc7S\x13S_S\xaaS\xf6TBT\x8fT\xdbU(UuU\xc2V\x0fV\\V\xa9V\xf7WDW\x92W\xe0X/X}X\xcbY\x1aYiY\xb8Z\x07ZVZ\xa6Z\xf5[E[\x95[\xe5\\5\\\x86\\\xd6]\']x]\xc9^\x1a^l^\xbd_\x0f_a_\xb3`\x05`W`\xaa`\xfcaOa\xa2a\xf5bIb\x9cb\xf0cCc\x97c\xebd@d\x94d\xe9e=e\x92e\xe7f=f\x92f\xe8g=g\x93g\xe9h?h\x96h\xeciCi\x9ai\xf1jHj\x9fj\xf7kOk\xa7k\xfflWl\xafm\x08m`m\xb9n\x12nkn\xc4o\x1eoxo\xd1p+p\x86p\xe0q:q\x95q\xf0rKr\xa6s\x01s]s\xb8t\x14tpt\xccu(u\x85u\xe1v>v\x9bv\xf8wVw\xb3x\x11xnx\xccy*y\x89y\xe7zFz\xa5{\x04{c{\xc2|!|\x81|\xe1}A}\xa1~\x01~b~\xc2\x7f#\x7f\x84\x7f\xe5\x80G\x80\xa8\x81\n\x81k\x81\xcd\x820\x82\x92\x82\xf4\x83W\x83\xba\x84\x1d\x84\x80\x84\xe3\x85G\x85\xab\x86\x0e\x86r\x86\xd7\x87;\x87\x9f\x88\x04\x88i\x88\xce\x893\x89\x99\x89\xfe\x8ad\x8a\xca\x8b0\x8b\x96\x8b\xfc\x8cc\x8c\xca\x8d1\x8d\x98\x8d\xff\x8ef\x8e\xce\x8f6\x8f\x9e\x90\x06\x90n\x90\xd6\x91?\x91\xa8\x92\x11\x92z\x92\xe3\x93M\x93\xb6\x94 \x94\x8a\x94\xf4\x95_\x95\xc9\x964\x96\x9f\x97\n\x97u\x97\xe0\x98L\x98\xb8\x99$\x99\x90\x99\xfc\x9ah\x9a\xd5\x9bB\x9b\xaf\x9c\x1c\x9c\x89\x9c\xf7\x9dd\x9d\xd2\x9e@\x9e\xae\x9f\x1d\x9f\x8b\x9f\xfa\xa0i\xa0\xd8\xa1G\xa1\xb6\xa2&\xa2\x96\xa3\x06\xa3v\xa3\xe6\xa4V\xa4\xc7\xa58\xa5\xa9\xa6\x1a\xa6\x8b\xa6\xfd\xa7n\xa7\xe0\xa8R\xa8\xc4\xa97\xa9\xa9\xaa\x1c\xaa\x8f\xab\x02\xabu\xab\xe9\xac\\\xac\xd0\xadD\xad\xb8\xae-\xae\xa1\xaf\x16\xaf\x8b\xb0\x00\xb0u\xb0\xea\xb1`\xb1\xd6\xb2K\xb2\xc2\xb38\xb3\xae\xb4%\xb4\x9c\xb5\x13\xb5\x8a\xb6\x01\xb6y\xb6\xf0\xb7h\xb7\xe0\xb8Y\xb8\xd1\xb9J\xb9\xc2\xba;\xba\xb5\xbb.\xbb\xa7\xbc!\xbc\x9b\xbd\x15\xbd\x8f\xbe\n\xbe\x84\xbe\xff\xbfz\xbf\xf5\xc0p\xc0\xec\xc1g\xc1\xe3\xc2_\xc2\xdb\xc3X\xc3\xd4\xc4Q\xc4\xce\xc5K\xc5\xc8\xc6F\xc6\xc3\xc7A\xc7\xbf\xc8=\xc8\xbc\xc9:\xc9\xb9\xca8\xca\xb7\xcb6\xcb\xb6\xcc5\xcc\xb5\xcd5\xcd\xb5\xce6\xce\xb6\xcf7\xcf\xb8\xd09\xd0\xba\xd1<\xd1\xbe\xd2?\xd2\xc1\xd3D\xd3\xc6\xd4I\xd4\xcb\xd5N\xd5\xd1\xd6U\xd6\xd8\xd7\\\xd7\xe0\xd8d\xd8\xe8\xd9l\xd9\xf1\xdav\xda\xfb\xdb\x80\xdc\x05\xdc\x8a\xdd\x10\xdd\x96\xde\x1c\xde\xa2\xdf)\xdf\xaf\xe06\xe0\xbd\xe1D\xe1\xcc\xe2S\xe2\xdb\xe3c\xe3\xeb\xe4s\xe4\xfc\xe5\x84\xe6\r\xe6\x96\xe7\x1f\xe7\xa9\xe82\xe8\xbc\xe9F\xe9\xd0\xea[\xea\xe5\xebp\xeb\xfb\xec\x86\xed\x11\xed\x9c\xee(\xee\xb4\xef@\xef\xcc\xf0X\xf0\xe5\xf1r\xf1\xff\xf2\x8c\xf3\x19\xf3\xa7\xf44\xf4\xc2\xf5P\xf5\xde\xf6m\xf6\xfb\xf7\x8a\xf8\x19\xf8\xa8\xf98\xf9\xc7\xfaW\xfa\xe7\xfbw\xfc\x07\xfc\x98\xfd)\xfd\xba\xfeK\xfe\xdc\xffm\xff\xff')

GENERIC_GREY_COLOR_SPACE = NibObject("NSColorSpace", None, {
    'NSICC': GENERIC_GREY_COLOR_SPACE_NSICC,
    'NSID': 9,
    'NSModel': int(NSColorSpaceModels.NSGrayColorSpaceModel),
    })

RGB_COLOR_SPACE = NibObject("NSColorSpace", None, {
    'NSICC': RGB_COLOR_SPACE_NSICC,
    'NSID': 7,
    })
