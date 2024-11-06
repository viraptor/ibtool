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

"""
TODO:
- Translate autoresizing masks into layout constraints.
"""


class ArchiveContext:
    def __init__(self) -> None:
        self.connections: list[NibObject] = []
        # When parsing a storyboard, this doesn't include the main view or any of its descendant objects.
        self.objects: dict[str, NibObject] = {} # should be int
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

    def getObject(self, objid: str) -> Optional[NibObject]:
        if not objid:
            return None
        if objid in self.viewObjects:
            return self.viewObjects[objid]
        if objid in self.objects:
            return self.objects[objid]
        return None

    # Kinda ugly. If we ever use a separate ArchiveContext for storyboard scenes and their views, we can use just use getObject.
    # Basically this is like getObject, but only searches in the right one of 'objects' or 'viewObjects'
    def getObjectInCurrentContext(self, objid) -> Optional[NibObject]:
        if objid is None:
            return None
        if self.isParsingStoryboardView:
            return self.viewObjects.get(objid)
        else:
            return self.objects[objid]
        return None

    def resolveConnections(self) -> None:
        if not self.isStoryboard:
            self._resolveConnections_xib()
        else:
            self._resolveConnections_storyboard()
        self._resolveViewReferences()

    def _resolveViewReferences(self) -> None:
        for ref in self.viewReferences:
            view_id, obj, key = ref
            obj[key] = self.findObject(view_id)

    def _resolveConnections_xib(self) -> None:
        result = []
        for con in self.connections:
            dst = con["UIDestination"]
            if isinstance(dst, NibProxyObject):
                result.append(con)
                continue

            # How does this happen?
            if isinstance(dst, XibObject):
                result.append(con)
                continue
            # I think this resolution code will be obsolete when we start using UpstreamPlaceholder's.
            assert isinstance(dst, str), "%r is not a string ID" % dst
            print("Resolving standalone xib connection with id", dst)
            if dst in self.objects:
                con["UIDestination"] = self.objects[dst]
                result.append(con)
                continue
            phid = makePlaceholderIdentifier()
            con["UIDestination"] = NibProxyObject(phid)
            self.upstreamPlaceholders[phid] = dst
            result.append(con)

        self.connections = result

    def _resolveConnections_storyboard(self) -> None:
        view_cons: list[NibObject] = []
        scene_cons: list[NibObject] = []

        upstreamPlaceholderTable: dict[int,tuple[str,NibObject]] = {}  # src serial -> tuple( phid, src object )
        cachedProxyObjects: dict[str,NibProxyObject] = {}

        def placeholderIDForObject(obj: NibObject) -> str:
            if obj.serial() in upstreamPlaceholderTable:
                phid = upstreamPlaceholderTable[obj.serial()][0]
            else:
                phid = "UpstreamPlaceholder-" + makexibid()
                upstreamPlaceholderTable[obj.serial()] = (phid, obj)
            return phid

        def proxyObjectForObject(obj: NibObject) -> Optional[NibProxyObject]:
            phid = placeholderIDForObject(obj)
            if cachedProxyObjects.get(phid):
                return cachedProxyObjects.get(phid)
            prox = NibProxyObject(phid)
            cachedProxyObjects[phid] = prox
            return prox

        for con in self.connections:
            label = con["UILabel"]
            src = cast(XibObject, con["UISource"])
            dst = cast(XibObject, con["UIDestination"])  # Get the object ID.
            if not isinstance(dst, NibObject):
                dst = self.objects.get(dst) or self.viewObjects.get(dst)
            assert dst, "Can't find connection destination id %r" % (
                con["UIDestination"]
            )
            con["UIDestination"] = dst

            src_top = src.xibid in self.objects
            dst_top = dst.xibid in self.objects

            if not src_top:
                assert src.xibid in self.viewObjects

            # Something outside the view (typically the view controller) pointing to something in the view.
            if (src_top, dst_top) == (True, False):
                con["UISource"] = proxyObjectForObject(src)
                view_cons.append(con)

            # Something in the view pointing to something not in the view.
            elif (src_top, dst_top) == (False, True):
                con["UIDestination"] = proxyObjectForObject(dst)
                view_cons.append(con)

            elif (src_top, dst_top) == (True, True):
                scene_cons.append(con)

            elif (src_top, dst_top) == (False, False):
                view_cons.append(con)

        externObjects = dict(list(upstreamPlaceholderTable.values()))

        for ph_id, obj_id in self.upstreamPlaceholders.items():
            obj = self.objects[obj_id]
            externObjects[ph_id] = obj

        assert self.storyboardViewController is not None
        if externObjects:
            self.storyboardViewController["UIExternalObjectsTableForViewLoading"] = (
                externObjects
            )

        scene_cons.extend(self.segueConnections)

        self.viewConnections = view_cons
        self.sceneConnections = scene_cons

        self.storyboardViewController.sceneConnections = scene_cons


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

    applicationObject = [o for o in rootObject if int(o.xibid)==-3][0]
    filesOwner = [o for o in rootObject if int(o.xibid)==-2][0]

    rootData = NibObject("NSIBObjectData")
    rootData["NSRoot"] = rootObject[0]
    rootData["NSVisibleWindows"] = NibMutableSet(context.visibleWindows)
    rootData["NSConnections"] = NibMutableList()
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

# original, not sure which version/type uses it
#def old_top_level():
#    root = NibObject("NSObject")
#    root["UINibTopLevelObjectsKey"] = toplevel
#    # __xibparser_resolveConnections(ib_connections, ib_objects)
#    root["UINibConnectionsKey"] = context.connections
#    root["UINibObjectsKey"] = list(toplevel)
#    root["UINibObjectsKey"].extend(context.extraNibObjects)

def CompileStoryboard(tree: ElementTree, foldername: str) -> None:
    import os

    if os.path.isdir(foldername):
        import shutil

        shutil.rmtree(foldername)

    os.mkdir(foldername)

    root = tree.getroot()
    init = root.attrib.get("initialViewController")

    scenesNode = next(root.iter("scenes"))

    identifierMap: dict[str,str] = {}
    idToNibNameMap: dict[str,str] = {}
    idToViewControllerMap: dict[str,XibViewController] = {}

    # Make some constants before

    fowner = NibProxyObject("IBFilesOwner")
    sbplaceholder = NibProxyObject("UIStoryboardPlaceholder")

    # A list of tuples containing:
    #  - The view controller of the scene.
    #  - The root objects for the scene.
    #  - The view controller nib name.
    # We can't write the scene nibs as we read the scenes, because some things might depend on having
    # seen all the scenes. (e.g. Segues, which need to know how to translate ID into storyboardIdentifier)
    scenesToWrite: list[tuple[XibViewController,NibObject,str]] = []

    for sceneNode in scenesNode:
        toplevel = []

        sceneID = sceneNode.attrib["sceneID"]
        objects = next(sceneNode.iter("objects"))
        viewController = None
        viewControllerNibName = None

        context = ArchiveContext()
        context.isStoryboard = True

        for elem in objects:
            obj = __xibparser_ParseXIBObject(context, elem, None)
            if not obj:
                continue
            viewNibFilename = None

            toplevel.append(obj)
            context.toplevel.append(obj)

        viewController = context.storyboardViewController
        if not viewController:
            raise Exception("Storyboard scene did not have associated view controller.")
        assert viewController.sceneConnections is not None

        context.resolveConnections()

        viewControllerNibName = (
            viewController.xibattributes.get("storyboardIdentifier")
            or "UIViewController-" + viewController.xibattributes["id"]
        )
        identifierMap[viewControllerNibName] = viewControllerNibName
        idToNibNameMap[viewController.xibattributes["id"]] = viewControllerNibName
        idToViewControllerMap[viewController.xibattributes["id"]] = viewController
        view = viewController.properties.get("UIView")
        if view:
            del viewController.properties["UIView"]
            # Don't encode the view in the scene nib's objects.
            assert isinstance(view, NibObject)
            context.extraNibObjects.remove(view)

            view.extend("UISubviews", context.viewControllerLayoutGuides)

            ViewConnection = NibObject("UIRuntimeOutletConnection")
            ViewConnection["UILabel"] = "view"
            ViewConnection["UISource"] = fowner
            ViewConnection["UIDestination"] = view

            view_repr = view.repr()
            assert view_repr is not None
            viewNibFilename = "{}-view-{}".format(
                viewController.xibattributes.get("id"),
                view_repr.attrib.get("id"),
            )

            root = NibObject("NSObject")
            root["UINibTopLevelObjectsKey"] = [view]  # + context.viewConnections
            root["UINibObjectsKey"] = [view]  # + context.viewConnections
            root["UINibConnectionsKey"] = [ViewConnection] + context.viewConnections
            # root['UINibConnectionsKey']

            with open(
                "{}/{}{}".format(foldername, viewNibFilename, ".nib"), "wb"
            ) as fl:
                fl.write(CompileNibObjects([root]))

        # Not setting the UINibName key is acceptable.
        # I'm guessing things like UINavigationController scenes do that.
        print("viewNibFilename:", viewNibFilename)
        viewController["UINibName"] = viewNibFilename

        toplevel.append(fowner)
        toplevel.append(sbplaceholder)

        FilesOwnerConnection = NibObject("UIRuntimeOutletConnection")
        FilesOwnerConnection["UILabel"] = "sceneViewController"
        FilesOwnerConnection["UISource"] = fowner
        FilesOwnerConnection["UIDestination"] = viewController

        StoryboardConnection = NibObject("UIRuntimeOutletConnection")
        StoryboardConnection["UILabel"] = "storyboard"
        StoryboardConnection["UISource"] = viewController
        StoryboardConnection["UIDestination"] = sbplaceholder
        viewController.sceneConnections.append(StoryboardConnection)

        nibconnections = [
            FilesOwnerConnection,
            StoryboardConnection,
        ] + context.sceneConnections

        root = NibObject("NSObject")
        root["UINibTopLevelObjectsKey"] = toplevel
        root["UINibConnectionsKey"] = nibconnections
        objectsKeys = list(toplevel)
        objectsKeys.extend(context.extraNibObjects)
        root["UINibObjectsKey"] = objectsKeys

        scenesToWrite.append((viewController, root, viewControllerNibName))

    # Do some additional processing before the scenes are written.
    # This includes resolving references for storyboard segues and assigning
    # all the appropriate values for relationship segues in the storyboard.
    for finalScene in scenesToWrite:
        viewController, root, viewControllerNibName = finalScene

        assert isinstance(viewController, NibObject)
        templates = viewController.get("UIStoryboardSegueTemplates")
        assert isinstance(templates, list)
        for segue in templates or []:
            assert isinstance(segue, NibObject)
            dest = segue["UIDestinationViewControllerIdentifier"]
            if isinstance(dest, NibString):
                dest = dest._text
            if isinstance(dest, str):
                segue["UIDestinationViewControllerIdentifier"] = idToNibNameMap[dest]

        # This is kinda ugly. It's inspired by the need to set certain properties on the view controller,
        # like UIParentViewController, which we only want set when we're including the view controller
        # inside another view controller's nib. We make a copy of the properties array, add what we need,
        # then put the dict back when we're done.
        resetProperties: list[tuple[XibViewController,dict[str,PropValue]]] = []

        if viewController.relationshipsegue is not None:
            segue = viewController.relationshipsegue
            relationship = segue.attrib["relationship"]
            if relationship == "rootViewController":
                rootViewController = idToViewControllerMap[segue.attrib["destination"]]
                viewController["UIChildViewControllers"] = [rootViewController]
                viewController["UIViewControllers"] = [rootViewController]

                if viewController.sceneConnections:
                    root["UINibConnectionsKey"].extend(
                        rootViewController.sceneConnections
                    )

                resetProperties.append(
                    (rootViewController, dict(rootViewController.properties))
                )

                rootViewController["UIParentViewController"] = viewController
                # Maybe also set a default UINavigationItem?

        b = CompileNibObjects([root])
        with open(
            "{}/{}{}".format(foldername, viewControllerNibName, ".nib"), "wb"
        ) as fl:
            fl.write(b)

        for viewController, oldProperties in resetProperties:
            assert viewController is not None
            viewController.properties = oldProperties

    storyboard_info = {
        "UIViewControllerIdentifiersToNibNames": identifierMap,
        "UIStoryboardVersion": 1,
    }

    if init:
        init = idToNibNameMap.get(init) or init
        storyboard_info["UIStoryboardDesignatedEntryPointIdentifier"] = init

    print("INIT:", init)

    import plistlib

    with open(foldername + "/Info.plist", "wb") as f:
        plistlib.dump(storyboard_info, f)


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
            obj.xibid = elem.attrib["id"]
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
    def __init__(self, classname: str) -> None:
        NibObject.__init__(self, classname)
        self.xibid: Optional[str] = None

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
    if key == "view":
        parent["UIView"] = obj
    elif key == "tableFooterView":
        parent["UITableFooterView"] = obj
        parent.append("UISubviews", obj)
    elif key == "tableHeaderView":
        parent["UITableHeaderView"] = obj
        parent.append("UISubviews", obj)
    elif key == "contentView":
        if parent.originalclassname() == "UIVisualEffectView":
            parent["UIVisualEffectViewContentView"] = obj
            obj.setclassname("_UIVisualEffectContentView")
        elif parent.originalclassname() == "NSWindowTemplate":
            parent["NSWindowView"] = obj
        else:
            raise Exception(
                "Unhandled class '%s' to take UIView with key 'contentView'"
                % (parent.originalclassname())
            )
    else:
        raise Exception(f"view in unknown key {key} (parent {parent.repr()})")

    isMainView = key == "view"  # and isinstance(parent, XibViewController)?

    if elem.attrib.get("translatesAutoresizingMaskIntoConstraints") == "NO":
        obj["UIViewDoesNotTranslateAutoresizingMaskIntoConstraints"] = True

    if "contentMode" in list(elem.attrib.keys()):
        mode = elem.attrib["contentMode"]
        enum = [
            "scaleToFill",
            "scaleAspectFit",
            "scaleAspectFill",
            "redraw",
            "center",
            "top",
            "bottom",
            "left",
            "right",
            "topLeft",
            "topRight",
            "bottomLeft",
            "bottomRight",
        ]
        idx = enum.index(mode)
        if idx:  # It doesn't encode the default value.
            obj["UIContentMode"] = NibByte(idx)

    obj["UIClipsToBounds"] = elem.attrib.get("clipsSubviews") == "YES"

    # Default Values?
    obj["UIAutoresizingMask"] = NibByte(36)  # Flexible right + bottom margin.
    obj["UIAutoresizeSubviews"] = True

    val = elem.attrib.get("text")
    if val:
        obj["UIText"] = val

    if isMainView:
        ctx.isParsingStoryboardView = True

    ctx.extraNibObjects.append(obj)

    # Parse these props first, in case any of our children point to us.
    _xibparser_parse_interfacebuilder_properties(ctx, elem, parent, obj)
    __xibparser_ParseChildren(ctx, elem, obj)

    if isMainView:
        ctx.isParsingStoryboardView = False

    return obj


def _xibparser_parse_button(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]):
    obj = XibObject("NSButton")
    obj.xibid = elem.attrib["id"]
    ctx.addObject(obj.xibid, obj)
    __xibparser_ParseChildren(ctx, elem, obj)
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
    con = XibObject("UIRuntimeOutletConnection")
    con["UILabel"] = elem.attrib.get("property")
    con["UISource"] = parent
    con["UIDestination"] = elem.attrib.get("destination")

    # Add this to the list of connections we'll have to resolve later.
    ctx.connections.append(con)


def _xibparser_parse_action(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    etype = elem.attrib.get("eventType")

    #  @31: UIRuntimeEventConnection
    # UILabel = (10) @48  "shout:"
    # UISource = (10) @51  UIButton instance
    # UIDestination = (10) @16 UIProxyObject "UpstreamPlaceholder-cnh-Gb-aGf"
    # UIEventMask = (0) 64 UIControlEventTouchUpInside

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

    con = NibObject("UIRuntimeEventConnection")
    con["UILabel"] = elem.attrib["selector"]
    con["UISource"] = parent
    con["UIDestination"] = elem.attrib.get("destination") or elem.attrib.get("target")
    con["UIEventMask"] = mask

    ctx.connections.append(con)


# TODO: I think this function might need more logic when the bounds aren't set at 0, 0
def _xibparser_parse_rect(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    key = elem.attrib.get("key")
    if key == "contentRect":
        x = int(elem.attrib["x"])
        y = int(elem.attrib["y"])
        w = int(elem.attrib["width"])
        h = int(elem.attrib["height"])
        parent["NSWindowRect"] = "{{" + str(x) + ", " + str(y) + "}, {" + str(w) + ", " + str(h) + "}}"
    elif key == "screenRect":
        x = int(float(elem.attrib["x"]))
        y = int(float(elem.attrib["y"]))
        w = int(elem.attrib["width"])
        h = int(elem.attrib["height"])
        parent["NSScreenRect"] = "{{" + str(x) + ", " + str(y) + "}, {" + str(w) + ", " + str(h) + "}}"
    else:
        raise Exception(f"unknown rect key {key}")


def _xibparser_parse_point(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    point = (float(elem.attrib["x"]), float(elem.attrib["y"]))

def _xibparser_parse_window(ctx, elem, parent):
    item = XibObject("NSWindowTemplate")
    item.xibid = elem.attrib["id"]
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
    item = XibObject("NSCustomObject")
    item.xibid = elem.attrib["id"]
    ctx.addObject(item.xibid, item)
    if elem.attrib.get("customClass"):
        classRef = XibObject("IBClassReference")
        className = NibString(elem.attrib.get("customClass"))
        classRef["IBClassName"] = className
        classRef["IBModuleName"] = NibNil()
        classRef["IBModuleProvider"] = NibNil()
        item["IBClassReference"] = classRef
        if int(item.xibid) == -3:
            item["NSClassName"] = DEFAULT_NSAPPLICATION_STRING
        else:
            item["NSClassName"] = className
    elif int(item.xibid) < 0:
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
    obj = XibObject("NSTextField")
    obj.xibid = elem.attrib["id"]
    ctx.addObject(obj.xibid, obj)
    __xibparser_ParseChildren(ctx, elem, obj)
    obj["NSNextResponder"] = NibNil() # TODO
    obj["NSNibTouchBar"] = NibNil() # TODO
    obj["NSvFlags"] = 0x10c # TODO
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
    obj = XibObject("NSTextFieldCell")
    obj.xibid = elem.attrib["id"]
    ctx.addObject(obj.xibid, obj)
    __xibparser_ParseChildren(ctx, elem, obj)
    return obj

def _xibparser_parse_progressIndicator(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSProgressIndicator")
    obj.xibid = elem.attrib["id"]
    ctx.addObject(obj.xibid, obj)
    __xibparser_ParseChildren(ctx, elem, obj)
    return obj

def _xibparser_parse_buttonCell(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject("NSButtonCell")
    obj.xibid = elem.attrib["id"]
    ctx.addObject(obj.xibid, obj)
    __xibparser_ParseChildren(ctx, elem, obj)
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
    parent["NSButtonFlags"] = 0x804000 + value

def _xibparser_parse_string(ctx: ArchiveContext, elem: Element, parent: NibObject) -> None:
    assert parent.classname() == "NSButtonCell"
    parent["NSContents"] = NibString(elem.attrib.get("", ""))
