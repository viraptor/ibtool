from genlib import (
    CompileNibObjects,
    NibByte,
    NibData,
    NibInlineString,
    NibNSNumber,
    NibObject,
    NibProxyObject,
    NibString,
    NibNil,
    NibList,
    NibMutableList,
    NibMutableSet,
    PropValue,
    PropPair,
)
from xml.etree.ElementTree import Element, ElementTree
from typing import Optional, Any, Union, cast, TypeAlias


class XibId:
    def __init__(self, val: Union[str,int]) -> None:
        if isinstance(val, str):
            val = int(val)
        assert isinstance(val, int), f"id reference {val}"
        self._val = val

    def val(self) -> int:
        return self._val

    def __repr__(self) -> str:
        return f"XibId({self._val})"

    def __eq__(self, other: Union[int,"XibId"]) -> bool:
        if isinstance(other, int):
            return self._val == other
        elif isinstance(other, XibId):
            return self._val == other._val
        else:
            return False

    def __hash__(self) -> int:
        return hash(self._val)


class ArchiveContext:
    def __init__(self) -> None:
        self.connections: list[NibObject] = []
        # When parsing a storyboard, this doesn't include the main view or any of its descendant objects.
        self.objects: dict[XibId, NibObject] = {} # should be int
        self.toplevel: list[NibObject] = []

        self.extraNibObjects: list[NibObject] = []
        self.isStoryboard = False

        # These are used only for storyboards.
        self.storyboardViewController: Optional[XibViewController] = None
        self.isParsingStoryboardView = False
        self.viewObjects: dict[str, NibObject] = {}
        self.viewConnections: list[NibObject] = []
        self.sceneConnections: list[NibObject] = []
        self.segueConnections: list[NibObject] = []

        self.isPrototypeList = False
        self.visibleWindows: list[NibObject] = []

        # What I plan on using after the context revision:

        self.upstreamPlaceholders: dict[str,str] = {}
        self.parentContext: Optional[ArchiveContext] = None
        # List of tuples (view id, referencing object, referencing key)
        self.viewReferences: list[tuple[str,NibObject,str]] = []
        self.viewControllerLayoutGuides: list = []
        # self.view = None
        # self.viewController = None

    def contextForSegues(self) -> 'ArchiveContext':
        if self.isPrototypeList:
            assert self.parentContext is not None
            return self.parentContext
        return self

    def addObject(self, objid: str, obj: NibObject, forceSceneObject: Any =None) -> None:
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
    def findObject(self, objid: str) -> NibObject:
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
def ParseXIBObjects(element: Element, context: Optional[ArchiveContext]=None, resolveConnections: bool=True, parent: Optional[NibObject]=None) -> NibObject:
    toplevel = []

    context = context or ArchiveContext()

    for nib_object_element in element:
        obj = __xibparser_ParseXIBObject(context, nib_object_element, parent)
        if obj:
            toplevel.append(obj)

    if resolveConnections:
        context.resolveConnections()

    return createTopLevel(toplevel, context, context.extraNibObjects)

def createTopLevel(rootObject, context, extraObjects) -> NibObject:
    #for obj in rootObject:
    #    print('---', obj, obj.xibid)
    #    for t in obj.getKeyValuePairs():
    #        print(t)
    #print('+++')
    #for obj in extraObjects:
    #    print('---', obj, obj.xibid)
    #    for t in obj.getKeyValuePairs():
    #        print(t)

    applicationObject = [o for o in rootObject if o.xibid==-3][0]
    filesOwner = [o for o in rootObject if o.xibid==-2][0]

    rootData = NibObject("NSIBObjectData")
    rootData["NSRoot"] = rootObject[0]
    rootData["NSVisibleWindows"] = NibMutableSet(context.visibleWindows)
    rootData["NSConnections"] = NibMutableList(context.connections)
    rootData["NSObjectsKeys"] = NibList([applicationObject] + rootObject[3:] + extraObjects)
    rootData["NSObjectsValues"] = NibList([filesOwner])
    oid_objects = [filesOwner, applicationObject] + rootObject[3:]
    rootData["NSOidsKeys"] = NibList(oid_objects)
    rootData["NSOidsValues"] = NibList([NibNSNumber(x+1) for x,_ in enumerate(oid_objects)])
    rootData["NSAccessibilityConnectors"] = NibMutableList()
    emptyList = NibList()
    rootData["NSAccessibilityOidsKeys"] = emptyList
    rootData["NSAccessibilityOidsValues"] = emptyList
    return NibObject("NSObject", {
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


def classSwapper(func: Any):
    def inner(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], *args, **kwargs) -> NibObject:
        obj = func(ctx, elem, parent, *args, **kwargs)
        if obj:
            customClass = elem.attrib.get("customClass")
            if customClass:
                obj["UIOriginalClassName"] = obj.classname()
                obj["UIClassName"] = customClass
                obj.setclassname("UIClassSwapper")

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
            obj.xibid = XibId(elem.attrib["id"])
        return obj
    else:
        raise Exception(f"Unknown type {tag}")


def __xibparser_ParseChildren(ctx: ArchiveContext, elem: Element, obj: Optional[NibObject]) -> list[NibObject]:
    assert obj is not None
    children = [
        __xibparser_ParseXIBObject(ctx, child_element, obj) for child_element in elem
    ]
    return [c for c in children if c]


def _xibparser_parse_placeholder(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> NibProxyObject:
    placeholderid = elem.attrib["placeholderIdentifier"]
    obj = NibProxyObject(placeholderid)
    __xibparser_ParseChildren(ctx, elem, obj)
    ctx.addObject(elem.attrib["id"], obj)
    return obj


def _xibparser_parse_interfacebuilder_properties(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], obj: NibObject) -> None:
    rid = elem.attrib.get("restorationIdentifier")
    if rid:
        obj["UIRestorationIdentifier"] = rid

    ibid = elem.attrib.get("id")
    if ibid:
        ctx.addObject(ibid, obj)


class XibObject(NibObject):
    def __init__(self, classname: str, xibid: Optional[Union[str,int]] = None) -> None:
        NibObject.__init__(self, classname)
        self.xibid: Optional[XibId] = None
        if xibid is not None:
            self.xibid = XibId(xibid)
        self.extraContext = {}

    def originalclassname(self) -> Optional[str]:
        if not self.classname():
            return None
        if self.classname() != "UIClassSwapper":
            return self.classname()
        oc = self["UIOriginalClassName"]
        assert isinstance(oc, str)
        return oc


class XibViewController(XibObject):
    def __init__(self, classname) -> None:
        XibObject.__init__(self, classname)
        self.xibattributes: dict[str,str] = {}

        # For storyboards:
        self.relationshipsegue = None
        self.sceneConnections: list[NibObject] = [] # Populated in ArchiveContext.resolveConnections()


@classSwapper
def _xibparser_parse_viewController(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], **kwargs) -> XibViewController:
    obj = XibViewController(kwargs.get("uikit_class") or "UIViewController")

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


@classSwapper
def _xibparser_parse_view(ctx: ArchiveContext, elem: Element, parent: XibObject, **kwargs) -> XibObject:
    obj = XibObject(kwargs.get("uikit_class") or "NSView")
    obj.setrepr(elem)

    key = elem.get("key")
    if key == "contentView":
        if parent.originalclassname() == "NSWindowTemplate":
            parent["NSWindowView"] = obj
        else:
            raise Exception(
                "Unhandled class '%s' to take UIView with key 'contentView'"
                % (parent.originalclassname())
            )
    else:
        raise Exception(f"view in unknown key {key} (parent {parent.repr()})")

    isMainView = key == "view"  # and isinstance(parent, XibViewController)?

    ctx.extraNibObjects.append(obj)
    
    # Parse these props first, in case any of our children point to us.
    _xibparser_parse_interfacebuilder_properties(ctx, elem, parent, obj)
    __xibparser_ParseChildren(ctx, elem, obj)

    _xibparser_common_view_attributes(ctx, elem, parent, obj)

    if isMainView:
        ctx.isParsingStoryboardView = False

    return obj


def _xibparser_common_view_attributes(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject], obj: XibObject) -> None:
    obj["IBNSSafeAreaLayoutGuide"] = NibNil()
    obj["IBNSLayoutMarginsGuide"] = NibNil()
    obj["IBNSClipsToBounds"] = 0
    obj.setIfEmpty("NSvFlags", 0x100)
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    obj.setIfEmpty("NSNextResponder", parent.get("NSNextResponder") or parent)


def _xibparser_parse_button(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = XibObject("NSButton", elem.attrib["id"])
    ctx.addObject(obj.xibid, obj)
    obj.extraContext["verticalHuggingPriority"] = elem.attrib.get("verticalHuggingPriority")

    __xibparser_ParseChildren(ctx, elem, obj)
    _xibparser_common_view_attributes(ctx, elem, parent, obj)
    obj["NSNibTouchBar"] = NibNil()
    obj.setIfEmpty("NSFrame", NibNil())
    obj.setIfEmpty("NSSuperview", parent.get("NSSuperview") or parent)
    obj["IBNSSafeAreaLayoutGuide"] = NibNil()
    obj["IBNSLayoutMarginsGuide"] = NibNil()
    obj["IBNSClipsToBounds"] = 0
    obj["NSEnabled"] = True
    obj.setIfEmpty("NSFrame", NibNil())
    obj.setIfEmpty("NSCell", NibNil())
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj.setIfEmpty("NSControlTextAlignment", 4)
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 4
    obj["IBNSShadowedSymbolConfiguration"] = NibNil()
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
    con = XibObject("NSOutletConnection", elem.attrib["id"])
    con["NSSource"] = parent
    con["NSDestination"] = XibId(elem.attrib.get("destination"))
    con["NSLabel"] = elem.attrib.get("property")
    con["NSChildControllerCreationSelectorName"] = NibNil()

    # Add this to the list of connections we'll have to resolve later.
    ctx.connections.append(con)


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

    con = NibObject("NSRuntimeEventConnection")
    con["NSLabel"] = elem.attrib["selector"]
    con["NSSource"] = parent
    con["NSDestination"] = XibId(elem.attrib.get("target"))
    con["NSEventMask"] = mask # TODO

    ctx.connections.append(con)


# TODO: I think this function might need more logic when the bounds aren't set at 0, 0
def _xibparser_parse_rect(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    key = elem.attrib.get("key")
    w = int(elem.attrib["width"])
    h = int(elem.attrib["height"])
    if key == "contentRect":
        assert parent.classname() == "NSWindowTemplate"
        x = int(elem.attrib["x"])
        y = int(elem.attrib["y"])
        parent["NSWindowRect"] = "{{" + str(x) + ", " + str(y) + "}, {" + str(w) + ", " + str(h) + "}}"
    elif key == "screenRect":
        assert parent.classname() == "NSWindowTemplate"
        x = int(float(elem.attrib["x"]))
        y = int(float(elem.attrib["y"]))
        parent["NSScreenRect"] = "{{" + str(x) + ", " + str(y) + "}, {" + str(w) + ", " + str(h) + "}}"
    elif key == "frame":
        x = int(float(elem.attrib["x"]))
        y = int(float(elem.attrib["y"]))
        parent["NSFrame"] = "{{" + str(x) + ", " + str(y) + "}, {" + str(w) + ", " + str(h) + "}}"
    else:
        raise Exception(f"unknown rect key {key}")


def _xibparser_parse_autoresizingMask(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    flexibleMaxX = elem.attrib.get("flexibleMaxX", "NO") == "YES"
    flexibleMaxY = elem.attrib.get("flexibleMaxY", "NO") == "YES"
    if flexibleMaxY:
        parent["NSvFlags"] &= ~0b100000
    if flexibleMaxX:
        parent["NSvFlags"] &= ~0b1000


def _xibparser_parse_point(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    point = (float(elem.attrib["x"]), float(elem.attrib["y"]))

def _xibparser_parse_window(ctx, elem, parent):
    item = XibObject("NSWindowTemplate", elem.attrib["id"])
    ctx.addObject(item.xibid, item)
    __xibparser_ParseChildren(ctx, elem, item)
    item["NSWindowBacking"] = 2
    if not item.get("NSWindowRect"):
        item["NSWindowRect"] = '{{0, 0}, {0, 0}}'
    flags = 0x20000000

    if elem.attrib.get("allowsToolTipsWhenApplicationIsInactive", "YES") == "YES":
        flags |= 0x2000
    if elem.attrib.get("autorecalculatesKeyViewLoop", "YES") == "YES":
        flags |= 0x800
    item["NSWTFlags"] = flags

    item["NSWindowTitle"] = NibString(elem.attrib.get("title"))
    item["NSWindowSubtitle"] = ""
    item["NSWindowClass"] = NibString("NSWindow")
    item["NSViewClass"] = NibNil() # TODO
    item["NSUserInterfaceItemIdentifier"] = NibNil() # TODO
    if not item.get("NSWindowView"):
        item["NSWindowView"] = NibNil()
    if not item.get("NSWindowRect"):
        item["NSScreenRect"] = '{{0, 0}, {0, 0}}'
    item["NSMaxSize"] = '{10000000000000, 10000000000000}'
    item["NSWindowIsRestorable"] = elem.attrib.get("restorable", "YES") == "YES"
    default_content_size = NibData('{{0, 0}, {0, 0}}')
    item["NSMinFullScreenContentSize"] = default_content_size
    item["NSMaxFullScreenContentSize"] = default_content_size
    if elem.attrib.get("tabbingMode"):
        item["NSWindowTabbingMode"] = {"disallowed": 2}[elem.attrib["tabbingMode"]]
    if elem.attrib.get("visibleAtLaunch", "YES") == "YES":
        ctx.visibleWindows.append(item)
    return item

DEFAULT_NSAPPLICATION_STRING = NibString("NSApplication")

def _xibparser_parse_customObject(ctx, elem, parent):
    item = XibObject("NSCustomObject", elem.attrib["id"])
    ctx.addObject(item.xibid, item)
    if elem.attrib.get("customClass"):
        classRef = XibObject("IBClassReference")
        className = NibString(elem.attrib.get("customClass"))
        classRef["IBClassName"] = className
        classRef["IBModuleName"] = NibNil()
        classRef["IBModuleProvider"] = NibNil()
        item["IBClassReference"] = classRef
        if item.xibid == -3:
            item["NSClassName"] = DEFAULT_NSAPPLICATION_STRING
        else:
            item["NSClassName"] = className
    elif item.xibid.val() < 0:
        item["NSClassName"] = DEFAULT_NSAPPLICATION_STRING
    else:
        item["NSClassName"] = NibString("NSObject")
    __xibparser_ParseChildren(ctx, elem, item)
    return item

def _xibparser_parse_windowStyleMask(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    maskmap = {
        "titled": 1 << 0,
        "closable": 1 << 1,
        "miniaturizable": 1 << 2,
    }
    value = sum((elem.attrib[attr] == "YES") * val for attr, val in maskmap.items())
    parent["NSWindowStyleMask"] = value

def _xibparser_parse_windowPositionMask(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    maskmap = {
        "leftStrut": 1 << 0,
        "bottomStrut": 1 << 1,
    }
    value = sum((elem.attrib[attr] == "YES") * val for attr, val in maskmap.items())
    parent["NSWindowPositionMask"] = value

def _xibparser_parse_textField(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSTextField", elem.attrib["id"])
    ctx.addObject(obj.xibid, obj)
    obj["NSvFlags"] = 0x10c
    __xibparser_ParseChildren(ctx, elem, obj)
    obj["NSNextResponder"] = NibNil() # TODO
    obj["NSNibTouchBar"] = NibNil() # TODO
    obj["NSFrame"] = NibNil() # TODO
    obj["NSSuperview"] = NibNil() # TODO
    obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    obj["IBNSSafeAreaLayoutGuide"] = NibNil()
    obj["IBNSLayoutMarginsGuide"] = NibNil()
    obj["IBNSClipsToBounds"] = 0
    obj["NSEnabled"] = True
    obj["NSCell"] = NibNil() # TODO
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlContinuous"] = False
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlTextAlignment"] = 4
    obj["NSControlLineBreakMode"] = 4
    obj["NSControlWritingDirection"] = -1
    obj["NSControlSendActionMask"] = 4
    obj["NSTextFieldAlignmentRectInsetsVersion"] = 2
    return obj

def _xibparser_parse_textFieldCell(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSTextFieldCell", elem.attrib["id"])
    ctx.addObject(obj.xibid, obj)
    obj["NSCellFlags"] = 0x4000040 # TODO
    obj["NSCellFlags2"] = 0x10400800 # TODO
    obj["NSControlSize2"] = 0
    obj["NSContents"] = NibNil() # TODO
    obj["NSSupport"] = NibNil() # TODO
    obj["NSControlView"] = NibNil() # TODO
    obj["NSCharacterPickerEnabled"] = True
    __xibparser_ParseChildren(ctx, elem, obj)
    return obj

def _xibparser_parse_progressIndicator(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSProgressIndicator", elem.attrib["id"])
    ctx.addObject(obj.xibid, obj)
    __xibparser_ParseChildren(ctx, elem, obj)
    return obj

def _xibparser_parse_buttonCell(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSButtonCell", elem.attrib["id"])
    ctx.addObject(obj.xibid, obj)

    inset = int(elem.attrib.get("inset", "0"))
    inset = min(max(inset, 0), 3)
    inset = {0: 0, 1: 0x2000, 2: 0x4000, 3: 0x6000}[inset]
    buttonType = elem.attrib.get("type", "push")
    buttonTypeMask = {"push": 0, "radio": 0x100}[buttonType]
    textAlignment = elem.attrib.get("alignment")
    textAlignmentMask = {None: 0x10000000, "left": 0, "center": 0x8000000, "right": 0x4000000}[textAlignment]
    bezelStyle = elem.attrib.get("bezelStyle")
    bezelStyle = {None: 0, "rounded": 1}[bezelStyle]
    borderStyle = elem.attrib.get("borderStyle")
    borderStyleMask = {None: 0, "border": 0x800000}[borderStyle]

    __xibparser_ParseChildren(ctx, elem, obj)
    obj["NSCellFlags"] = 67108864
    obj["NSCellFlags2"] = textAlignmentMask
    obj["NSControlSize2"] = 0
    obj["NSContents"] = elem.attrib["title"]
    obj["NSSupport"] = NibObject("NSFont", {
        "NSName": ".AppleSystemUIFont",
        "NSSize": 13.0,
        "NSfFlags": 1044,
        })
    obj["NSControlView"] = parent
    obj["NSButtonFlags"] = (obj.get("NSButtonFlags") or 0) | inset | buttonTypeMask | borderStyleMask
    obj["NSButtonFlags2"] = 0x81
    if buttonType == "radio":
        obj["NSAlternateContents"] = NibObject("NSButtonImageSource", {
            "NSImageName": "NSRadioButton"
            })
    obj["NSBezelStyle"] = bezelStyle
    unknown = NibString('')
    obj["NSAlternateContents"] = unknown
    obj["NSKeyEquivalent"] = unknown
    obj["NSPeriodicDelay"] = 400
    obj["NSPeriodicInterval"] = 75
    obj["NSAuxButtonType"] = 7
    parent["NSCell"] = obj

    parent["NSControlTextAlignment"] = {"left": 0, "center": 1, "right": 2, None: 4}[textAlignment]
    if borderStyle == "border":
        v, h = parent.extraContext.get("verticalHuggingPriority", 250), parent.extraContext.get("horizontalHuggingPriority", 250)
        parent["NSHuggingPriority"] = "{" + str(h) + ", " + str(v) + "}"

    return obj

def _xibparser_parse_font(ctx: ArchiveContext, elem: Element, parent: NibObject) -> NibObject:
    item = NibObject("NSFont")
    assert elem.attrib["metaFont"] == "system" # other options unknown
    item["NSName"] = NibString(".AppleSystemUIFont")
    item["NSSize"] = 13.0
    item["NSfFlags"] = 1044
    parent["NSSupport"] = item
    return item

def _xibparser_parse_behavior(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.classname() == "NSButtonCell"
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
    parent["NSButtonFlags"] = (parent.get("NSButtonFlags") or 0) | value

def _xibparser_parse_string(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.classname() == "NSButtonCell"
    parent["NSContents"] = NibString(elem.attrib.get("", ""))

def _xibparser_parse_color(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert isinstance(parent, XibObject), type(parent)
    
    color = NibObject("NSColor")
    colorSpaces = {"catalog": 6}
    color["NSColorSpace"] = colorSpaces[elem.attrib["colorSpace"]]
    color["NSCatalogName"] = elem.attrib["catalog"]
    color["NSColorName"] = elem.attrib["name"]

    colorObj = NibObject("NSColor")
    colorObj["NSColorSpace"] = 3 # TODO
    colorObj["NSWhite"] = b'0.602715373\x00'
    colorSpace = NibObject("NSColorSpace")
    colorSpace["NSID"] = 9
    colorSpace["NSModel"] = 0 # gray? https://developer.apple.com/documentation/appkit/nscolorspace/model/gray TODO
    colorSpace["NSICC"] = DEFAULT_COLOR_SPACE
    colorObj["NSCustomColorSpace"] = colorSpace
    colorObj["NSComponents"] = colorSpace
    color["NSColor"] = colorObj

    key = elem.attrib["key"]
    if key == "textColor":
        parent["NSTextColor"] = color
    elif key == "backgroundColor":
        parent["NSBackgroundColor"] = color
    else:
        raise Exception(f"unknown key {key}")

# is it default? TODO
DEFAULT_COLOR_SPACE = NibData(b'\x00\x00\x11\x9cappl\x02\x00\x00\x00mntrGRAYXYZ \x07\xdc\x00\x08\x00\x17\x00\x0f\x00.\x00\x0facspAPPL\x00\x00\x00\x00none\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-appl\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05desc\x00\x00\x00\xc0\x00\x00\x00ydscm\x00\x00\x01<\x00\x00\x08\x1acprt\x00\x00\tX\x00\x00\x00#wtpt\x00\x00\t|\x00\x00\x00\x14kTRC\x00\x00\t\x90\x00\x00\x08\x0cdesc\x00\x00\x00\x00\x00\x00\x00\x1fGeneric Gray Gamma 2.2 Profile\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00mluc\x00\x00\x00\x00\x00\x00\x00\x1f\x00\x00\x00\x0cskSK\x00\x00\x00.\x00\x00\x01\x84daDK\x00\x00\x00:\x00\x00\x01\xb2caES\x00\x00\x008\x00\x00\x01\xecviVN\x00\x00\x00@\x00\x00\x02$ptBR\x00\x00\x00J\x00\x00\x02dukUA\x00\x00\x00,\x00\x00\x02\xaefrFU\x00\x00\x00>\x00\x00\x02\xdahuHU\x00\x00\x004\x00\x00\x03\x18zhTW\x00\x00\x00\x1a\x00\x00\x03LkoKR\x00\x00\x00"\x00\x00\x03fnbNO\x00\x00\x00:\x00\x00\x03\x88csCZ\x00\x00\x00(\x00\x00\x03\xc2heIL\x00\x00\x00$\x00\x00\x03\xearoRO\x00\x00\x00*\x00\x00\x04\x0edeDE\x00\x00\x00N\x00\x00\x048itIT\x00\x00\x00N\x00\x00\x04\x86svSE\x00\x00\x008\x00\x00\x04\xd4zhCN\x00\x00\x00\x1a\x00\x00\x05\x0cjaJP\x00\x00\x00&\x00\x00\x05&elGR\x00\x00\x00*\x00\x00\x05LptPO\x00\x00\x00R\x00\x00\x05vnlNL\x00\x00\x00@\x00\x00\x05\xc8esES\x00\x00\x00L\x00\x00\x06\x08thTH\x00\x00\x002\x00\x00\x06TtrTR\x00\x00\x00$\x00\x00\x06\x86fiFI\x00\x00\x00F\x00\x00\x06\xaahrHR\x00\x00\x00>\x00\x00\x06\xf0plPL\x00\x00\x00J\x00\x00\x07.arEG\x00\x00\x00,\x00\x00\x07xruRU\x00\x00\x00:\x00\x00\x07\xa4enUS\x00\x00\x00<\x00\x00\x07\xde\x00V\x01a\x00e\x00o\x00b\x00e\x00c\x00n\x00\xe1\x00 \x00s\x00i\x00v\x00\xe1\x00 \x00g\x00a\x00m\x00a\x00 \x002\x00,\x002\x00G\x00e\x00n\x00e\x00r\x00i\x00s\x00k\x00 \x00g\x00r\x00\xe5\x00 \x002\x00,\x002\x00 \x00g\x00a\x00m\x00m\x00a\x00-\x00p\x00r\x00o\x00f\x00i\x00l\x00G\x00a\x00m\x00m\x00a\x00 \x00d\x00e\x00 \x00g\x00r\x00i\x00s\x00o\x00s\x00 \x00g\x00e\x00n\x00\xe8\x00r\x00i\x00c\x00a\x00 \x002\x00.\x002\x00C\x1e\xa5\x00u\x00 \x00h\x00\xec\x00n\x00h\x00 \x00M\x00\xe0\x00u\x00 \x00x\x00\xe1\x00m\x00 \x00C\x00h\x00u\x00n\x00g\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x00P\x00e\x00r\x00f\x00i\x00l\x00 \x00G\x00e\x00n\x00\xe9\x00r\x00i\x00c\x00o\x00 \x00d\x00a\x00 \x00G\x00a\x00m\x00a\x00 \x00d\x00e\x00 \x00C\x00i\x00n\x00z\x00a\x00s\x00 \x002\x00,\x002\x04\x17\x040\x043\x040\x04;\x04L\x04=\x040\x00 \x00G\x00r\x00a\x00y\x00-\x043\x040\x04<\x040\x00 \x002\x00.\x002\x00P\x00r\x00o\x00f\x00i\x00l\x00 \x00g\x00\xe9\x00n\x00\xe9\x00r\x00i\x00q\x00u\x00e\x00 \x00g\x00r\x00i\x00s\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00\xc1\x00l\x00t\x00a\x00l\x00\xe1\x00n\x00o\x00s\x00 \x00s\x00z\x00\xfc\x00r\x00k\x00e\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x90\x1au(pp\x96\x8eQI^\xa6\x002\x00.\x002\x82r_ic\xcf\x8f\xf0\xc7|\xbc\x18\x00 \xd6\x8c\xc0\xc9\x00 \xac\x10\xb9\xc8\x00 \x002\x00.\x002\x00 \xd5\x04\xb8\\\xd3\x0c\xc7|\x00G\x00e\x00n\x00e\x00r\x00i\x00s\x00k\x00 \x00g\x00r\x00\xe5\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00-\x00p\x00r\x00o\x00f\x00i\x00l\x00O\x00b\x00e\x00c\x00n\x00\xe1\x00 \x01a\x00e\x00d\x00\xe1\x00 \x00g\x00a\x00m\x00a\x00 \x002\x00.\x002\x05\xd2\x05\xd0\x05\xde\x05\xd4\x00 \x05\xd0\x05\xe4\x05\xd5\x05\xe8\x00 \x05\xdb\x05\xdc\x05\xdc\x05\xd9\x00 \x002\x00.\x002\x00G\x00a\x00m\x00a\x00 \x00g\x00r\x00i\x00 \x00g\x00e\x00n\x00e\x00r\x00i\x00c\x01\x03\x00 \x002\x00,\x002\x00A\x00l\x00l\x00g\x00e\x00m\x00e\x00i\x00n\x00e\x00s\x00 \x00G\x00r\x00a\x00u\x00s\x00t\x00u\x00f\x00e\x00n\x00-\x00P\x00r\x00o\x00f\x00i\x00l\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00P\x00r\x00o\x00f\x00i\x00l\x00o\x00 \x00g\x00r\x00i\x00g\x00i\x00o\x00 \x00g\x00e\x00n\x00e\x00r\x00i\x00c\x00o\x00 \x00d\x00e\x00l\x00l\x00a\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00G\x00e\x00n\x00e\x00r\x00i\x00s\x00k\x00 \x00g\x00r\x00\xe5\x00 \x002\x00,\x002\x00 \x00g\x00a\x00m\x00m\x00a\x00p\x00r\x00o\x00f\x00i\x00lfn\x90\x1app^\xa6|\xfbep\x002\x00.\x002c\xcf\x8f\xf0e\x87N\xf6N\x00\x82,0\xb00\xec0\xa40\xac0\xf30\xde\x00 \x002\x00.\x002\x00 0\xd70\xed0\xd50\xa10\xa40\xeb\x03\x93\x03\xb5\x03\xbd\x03\xb9\x03\xba\x03\xcc\x00 \x03\x93\x03\xba\x03\xc1\x03\xb9\x00 \x03\x93\x03\xac\x03\xbc\x03\xbc\x03\xb1\x00 \x002\x00.\x002\x00P\x00e\x00r\x00f\x00i\x00l\x00 \x00g\x00e\x00n\x00\xe9\x00r\x00i\x00c\x00o\x00 \x00d\x00e\x00 \x00c\x00i\x00n\x00z\x00e\x00n\x00t\x00o\x00s\x00 \x00d\x00a\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00A\x00l\x00g\x00e\x00m\x00e\x00e\x00n\x00 \x00g\x00r\x00i\x00j\x00s\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00-\x00p\x00r\x00o\x00f\x00i\x00e\x00l\x00P\x00e\x00r\x00f\x00i\x00l\x00 \x00g\x00e\x00n\x00\xe9\x00r\x00i\x00c\x00o\x00 \x00d\x00e\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x00d\x00e\x00 \x00g\x00r\x00i\x00s\x00e\x00s\x00 \x002\x00,\x002\x0e#\x0e1\x0e\x07\x0e*\x0e5\x0eA\x0e\x01\x0e!\x0e!\x0e2\x0e@\x0e\x01\x0e#\x0e"\x0eL\x0e\x17\x0e1\x0eH\x0e\'\x0eD\x0e\x1b\x00 \x002\x00.\x002\x00G\x00e\x00n\x00e\x00l\x00 \x00G\x00r\x00i\x00 \x00G\x00a\x00m\x00a\x00 \x002\x00,\x002\x00Y\x00l\x00e\x00i\x00n\x00e\x00n\x00 \x00h\x00a\x00r\x00m\x00a\x00a\x00n\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x00 \x00-\x00p\x00r\x00o\x00f\x00i\x00i\x00l\x00i\x00G\x00e\x00n\x00e\x00r\x00i\x01\r\x00k\x00i\x00 \x00G\x00r\x00a\x00y\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x00 \x00p\x00r\x00o\x00f\x00i\x00l\x00U\x00n\x00i\x00w\x00e\x00r\x00s\x00a\x00l\x00n\x00y\x00 \x00p\x00r\x00o\x00f\x00i\x00l\x00 \x00s\x00z\x00a\x00r\x00o\x01[\x00c\x00i\x00 \x00g\x00a\x00m\x00m\x00a\x00 \x002\x00,\x002\x06:\x06\'\x06E\x06\'\x00 \x002\x00.\x002\x00 \x06D\x06H\x06F\x00 \x061\x06E\x06\'\x06/\x06J\x00 \x069\x06\'\x06E\x04\x1e\x041\x04I\x040\x04O\x00 \x04A\x045\x04@\x040\x04O\x00 \x043\x040\x04<\x04<\x040\x00 \x002\x00,\x002\x00-\x04?\x04@\x04>\x04D\x048\x04;\x04L\x00G\x00e\x00n\x00e\x00r\x00i\x00c\x00 \x00G\x00r\x00a\x00y\x00 \x00G\x00a\x00m\x00m\x00a\x00 \x002\x00.\x002\x00 \x00P\x00r\x00o\x00f\x00i\x00l\x00e\x00\x00text\x00\x00\x00\x00Copyright Apple Inc., 2012\x00\x00XYZ \x00\x00\x00\x00\x00\x00\xf3Q\x00\x01\x00\x00\x00\x01\x16\xcccurv\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x05\x00\n\x00\x0f\x00\x14\x00\x19\x00\x1e\x00#\x00(\x00-\x002\x007\x00;\x00@\x00E\x00J\x00O\x00T\x00Y\x00^\x00c\x00h\x00m\x00r\x00w\x00|\x00\x81\x00\x86\x00\x8b\x00\x90\x00\x95\x00\x9a\x00\x9f\x00\xa4\x00\xa9\x00\xae\x00\xb2\x00\xb7\x00\xbc\x00\xc1\x00\xc6\x00\xcb\x00\xd0\x00\xd5\x00\xdb\x00\xe0\x00\xe5\x00\xeb\x00\xf0\x00\xf6\x00\xfb\x01\x01\x01\x07\x01\r\x01\x13\x01\x19\x01\x1f\x01%\x01+\x012\x018\x01>\x01E\x01L\x01R\x01Y\x01`\x01g\x01n\x01u\x01|\x01\x83\x01\x8b\x01\x92\x01\x9a\x01\xa1\x01\xa9\x01\xb1\x01\xb9\x01\xc1\x01\xc9\x01\xd1\x01\xd9\x01\xe1\x01\xe9\x01\xf2\x01\xfa\x02\x03\x02\x0c\x02\x14\x02\x1d\x02&\x02/\x028\x02A\x02K\x02T\x02]\x02g\x02q\x02z\x02\x84\x02\x8e\x02\x98\x02\xa2\x02\xac\x02\xb6\x02\xc1\x02\xcb\x02\xd5\x02\xe0\x02\xeb\x02\xf5\x03\x00\x03\x0b\x03\x16\x03!\x03-\x038\x03C\x03O\x03Z\x03f\x03r\x03~\x03\x8a\x03\x96\x03\xa2\x03\xae\x03\xba\x03\xc7\x03\xd3\x03\xe0\x03\xec\x03\xf9\x04\x06\x04\x13\x04 \x04-\x04;\x04H\x04U\x04c\x04q\x04~\x04\x8c\x04\x9a\x04\xa8\x04\xb6\x04\xc4\x04\xd3\x04\xe1\x04\xf0\x04\xfe\x05\r\x05\x1c\x05+\x05:\x05I\x05X\x05g\x05w\x05\x86\x05\x96\x05\xa6\x05\xb5\x05\xc5\x05\xd5\x05\xe5\x05\xf6\x06\x06\x06\x16\x06\'\x067\x06H\x06Y\x06j\x06{\x06\x8c\x06\x9d\x06\xaf\x06\xc0\x06\xd1\x06\xe3\x06\xf5\x07\x07\x07\x19\x07+\x07=\x07O\x07a\x07t\x07\x86\x07\x99\x07\xac\x07\xbf\x07\xd2\x07\xe5\x07\xf8\x08\x0b\x08\x1f\x082\x08F\x08Z\x08n\x08\x82\x08\x96\x08\xaa\x08\xbe\x08\xd2\x08\xe7\x08\xfb\t\x10\t%\t:\tO\td\ty\t\x8f\t\xa4\t\xba\t\xcf\t\xe5\t\xfb\n\x11\n\'\n=\nT\nj\n\x81\n\x98\n\xae\n\xc5\n\xdc\n\xf3\x0b\x0b\x0b"\x0b9\x0bQ\x0bi\x0b\x80\x0b\x98\x0b\xb0\x0b\xc8\x0b\xe1\x0b\xf9\x0c\x12\x0c*\x0cC\x0c\\\x0cu\x0c\x8e\x0c\xa7\x0c\xc0\x0c\xd9\x0c\xf3\r\r\r&\r@\rZ\rt\r\x8e\r\xa9\r\xc3\r\xde\r\xf8\x0e\x13\x0e.\x0eI\x0ed\x0e\x7f\x0e\x9b\x0e\xb6\x0e\xd2\x0e\xee\x0f\t\x0f%\x0fA\x0f^\x0fz\x0f\x96\x0f\xb3\x0f\xcf\x0f\xec\x10\t\x10&\x10C\x10a\x10~\x10\x9b\x10\xb9\x10\xd7\x10\xf5\x11\x13\x111\x11O\x11m\x11\x8c\x11\xaa\x11\xc9\x11\xe8\x12\x07\x12&\x12E\x12d\x12\x84\x12\xa3\x12\xc3\x12\xe3\x13\x03\x13#\x13C\x13c\x13\x83\x13\xa4\x13\xc5\x13\xe5\x14\x06\x14\'\x14I\x14j\x14\x8b\x14\xad\x14\xce\x14\xf0\x15\x12\x154\x15V\x15x\x15\x9b\x15\xbd\x15\xe0\x16\x03\x16&\x16I\x16l\x16\x8f\x16\xb2\x16\xd6\x16\xfa\x17\x1d\x17A\x17e\x17\x89\x17\xae\x17\xd2\x17\xf7\x18\x1b\x18@\x18e\x18\x8a\x18\xaf\x18\xd5\x18\xfa\x19 \x19E\x19k\x19\x91\x19\xb7\x19\xdd\x1a\x04\x1a*\x1aQ\x1aw\x1a\x9e\x1a\xc5\x1a\xec\x1b\x14\x1b;\x1bc\x1b\x8a\x1b\xb2\x1b\xda\x1c\x02\x1c*\x1cR\x1c{\x1c\xa3\x1c\xcc\x1c\xf5\x1d\x1e\x1dG\x1dp\x1d\x99\x1d\xc3\x1d\xec\x1e\x16\x1e@\x1ej\x1e\x94\x1e\xbe\x1e\xe9\x1f\x13\x1f>\x1fi\x1f\x94\x1f\xbf\x1f\xea \x15 A l \x98 \xc4 \xf0!\x1c!H!u!\xa1!\xce!\xfb"\'"U"\x82"\xaf"\xdd#\n#8#f#\x94#\xc2#\xf0$\x1f$M$|$\xab$\xda%\t%8%h%\x97%\xc7%\xf7&\'&W&\x87&\xb7&\xe8\'\x18\'I\'z\'\xab\'\xdc(\r(?(q(\xa2(\xd4)\x06)8)k)\x9d)\xd0*\x02*5*h*\x9b*\xcf+\x02+6+i+\x9d+\xd1,\x05,9,n,\xa2,\xd7-\x0c-A-v-\xab-\xe1.\x16.L.\x82.\xb7.\xee/$/Z/\x91/\xc7/\xfe050l0\xa40\xdb1\x121J1\x821\xba1\xf22*2c2\x9b2\xd43\r3F3\x7f3\xb83\xf14+4e4\x9e4\xd85\x135M5\x875\xc25\xfd676r6\xae6\xe97$7`7\x9c7\xd78\x148P8\x8c8\xc89\x059B9\x7f9\xbc9\xf9:6:t:\xb2:\xef;-;k;\xaa;\xe8<\'<e<\xa4<\xe3="=a=\xa1=\xe0> >`>\xa0>\xe0?!?a?\xa2?\xe2@#@d@\xa6@\xe7A)AjA\xacA\xeeB0BrB\xb5B\xf7C:C}C\xc0D\x03DGD\x8aD\xceE\x12EUE\x9aE\xdeF"FgF\xabF\xf0G5G{G\xc0H\x05HKH\x91H\xd7I\x1dIcI\xa9I\xf0J7J}J\xc4K\x0cKSK\x9aK\xe2L*LrL\xbaM\x02MJM\x93M\xdcN%NnN\xb7O\x00OIO\x93O\xddP\'PqP\xbbQ\x06QPQ\x9bQ\xe6R1R|R\xc7S\x13S_S\xaaS\xf6TBT\x8fT\xdbU(UuU\xc2V\x0fV\\V\xa9V\xf7WDW\x92W\xe0X/X}X\xcbY\x1aYiY\xb8Z\x07ZVZ\xa6Z\xf5[E[\x95[\xe5\\5\\\x86\\\xd6]\']x]\xc9^\x1a^l^\xbd_\x0f_a_\xb3`\x05`W`\xaa`\xfcaOa\xa2a\xf5bIb\x9cb\xf0cCc\x97c\xebd@d\x94d\xe9e=e\x92e\xe7f=f\x92f\xe8g=g\x93g\xe9h?h\x96h\xeciCi\x9ai\xf1jHj\x9fj\xf7kOk\xa7k\xfflWl\xafm\x08m`m\xb9n\x12nkn\xc4o\x1eoxo\xd1p+p\x86p\xe0q:q\x95q\xf0rKr\xa6s\x01s]s\xb8t\x14tpt\xccu(u\x85u\xe1v>v\x9bv\xf8wVw\xb3x\x11xnx\xccy*y\x89y\xe7zFz\xa5{\x04{c{\xc2|!|\x81|\xe1}A}\xa1~\x01~b~\xc2\x7f#\x7f\x84\x7f\xe5\x80G\x80\xa8\x81\n\x81k\x81\xcd\x820\x82\x92\x82\xf4\x83W\x83\xba\x84\x1d\x84\x80\x84\xe3\x85G\x85\xab\x86\x0e\x86r\x86\xd7\x87;\x87\x9f\x88\x04\x88i\x88\xce\x893\x89\x99\x89\xfe\x8ad\x8a\xca\x8b0\x8b\x96\x8b\xfc\x8cc\x8c\xca\x8d1\x8d\x98\x8d\xff\x8ef\x8e\xce\x8f6\x8f\x9e\x90\x06\x90n\x90\xd6\x91?\x91\xa8\x92\x11\x92z\x92\xe3\x93M\x93\xb6\x94 \x94\x8a\x94\xf4\x95_\x95\xc9\x964\x96\x9f\x97\n\x97u\x97\xe0\x98L\x98\xb8\x99$\x99\x90\x99\xfc\x9ah\x9a\xd5\x9bB\x9b\xaf\x9c\x1c\x9c\x89\x9c\xf7\x9dd\x9d\xd2\x9e@\x9e\xae\x9f\x1d\x9f\x8b\x9f\xfa\xa0i\xa0\xd8\xa1G\xa1\xb6\xa2&\xa2\x96\xa3\x06\xa3v\xa3\xe6\xa4V\xa4\xc7\xa58\xa5\xa9\xa6\x1a\xa6\x8b\xa6\xfd\xa7n\xa7\xe0\xa8R\xa8\xc4\xa97\xa9\xa9\xaa\x1c\xaa\x8f\xab\x02\xabu\xab\xe9\xac\\\xac\xd0\xadD\xad\xb8\xae-\xae\xa1\xaf\x16\xaf\x8b\xb0\x00\xb0u\xb0\xea\xb1`\xb1\xd6\xb2K\xb2\xc2\xb38\xb3\xae\xb4%\xb4\x9c\xb5\x13\xb5\x8a\xb6\x01\xb6y\xb6\xf0\xb7h\xb7\xe0\xb8Y\xb8\xd1\xb9J\xb9\xc2\xba;\xba\xb5\xbb.\xbb\xa7\xbc!\xbc\x9b\xbd\x15\xbd\x8f\xbe\n\xbe\x84\xbe\xff\xbfz\xbf\xf5\xc0p\xc0\xec\xc1g\xc1\xe3\xc2_\xc2\xdb\xc3X\xc3\xd4\xc4Q\xc4\xce\xc5K\xc5\xc8\xc6F\xc6\xc3\xc7A\xc7\xbf\xc8=\xc8\xbc\xc9:\xc9\xb9\xca8\xca\xb7\xcb6\xcb\xb6\xcc5\xcc\xb5\xcd5\xcd\xb5\xce6\xce\xb6\xcf7\xcf\xb8\xd09\xd0\xba\xd1<\xd1\xbe\xd2?\xd2\xc1\xd3D\xd3\xc6\xd4I\xd4\xcb\xd5N\xd5\xd1\xd6U\xd6\xd8\xd7\\\xd7\xe0\xd8d\xd8\xe8\xd9l\xd9\xf1\xdav\xda\xfb\xdb\x80\xdc\x05\xdc\x8a\xdd\x10\xdd\x96\xde\x1c\xde\xa2\xdf)\xdf\xaf\xe06\xe0\xbd\xe1D\xe1\xcc\xe2S\xe2\xdb\xe3c\xe3\xeb\xe4s\xe4\xfc\xe5\x84\xe6\r\xe6\x96\xe7\x1f\xe7\xa9\xe82\xe8\xbc\xe9F\xe9\xd0\xea[\xea\xe5\xebp\xeb\xfb\xec\x86\xed\x11\xed\x9c\xee(\xee\xb4\xef@\xef\xcc\xf0X\xf0\xe5\xf1r\xf1\xff\xf2\x8c\xf3\x19\xf3\xa7\xf44\xf4\xc2\xf5P\xf5\xde\xf6m\xf6\xfb\xf7\x8a\xf8\x19\xf8\xa8\xf98\xf9\xc7\xfaW\xfa\xe7\xfbw\xfc\x07\xfc\x98\xfd)\xfd\xba\xfeK\xfe\xdc\xffm\xff\xff')
