import re
import os
import plistlib
import uuid
from .models import (
    NibNSNumber,
    NibObject,
    NibList,
    NibMutableList,
    NibDictionary,
    NibMutableDictionary,
    NibMutableSet,
    NibString,
    NibLocalizableString,
    NibMutableString,
    NibNil,
    XibId,
    ArchiveContext,
    XibObject,
)
from xml.etree.ElementTree import Element
from typing import Optional
import base64
from .parsers_base import __xibparser_ParseXIBObject

def replace_string_attribures(elem: Element):
    string_elements = [child for child in elem if child.tag == "string" and child.get("key")]

    for string_elem in string_elements:
        key = string_elem.attrib["key"]
        if string_elem.attrib.get("base64-UTF8") == "YES":
            text = (string_elem.text or '').strip()
            value = base64.b64decode(text + ((4 - (len(text) % 4)) * '=')).decode('utf-8')
            if key == "toolTip":
                elem.set("_base64ToolTip", "YES")
        else:
            value = (string_elem.text or '')
        elem.set(key, value)
        elem.remove(string_elem)

    for child in elem:
        replace_string_attribures(child)

# Parses xml Xib data and returns a NibObject that can be used as the root
# object in a compiled NIB archive.
# element: The element containing the objects to be included in the nib.
#          For standalone XIBs, this is typically document->objects
#          For storyboards, this is typically document->scenes->scene->objects
def ParseXIBObjects(root: Element, context: Optional[ArchiveContext]=None, resolveConnections: bool=True, parent: Optional[NibObject]=None) -> tuple[ArchiveContext, NibObject]:
    replace_string_attribures(root)

    objects = next(root.iter("objects"))
    toplevel: list[XibObject] = []

    context = context or ArchiveContext(
        useAutolayout=(root.attrib.get("useAutolayout") == "YES"),
        customObjectInstantitationMethod=root.attrib.get("customObjectInstantitationMethod"),
        toolsVersion=int(root.attrib.get("toolsVersion", "0").split(".")[0]),
        )
    
    dependencies = [x for x in root.iter("dependencies")]
    if not dependencies:
        deployment = [x for x in dependencies[0].iter("deployment")]
        if deployment:
            context.deployment = True

    for res_elem in root.iter("resources"):
        for img in res_elem.iter("image"):
            name = img.get("name")
            w = img.get("width")
            h = img.get("height")
            if name and w and h:
                context.imageResources[name] = (w, h)
            catalog = img.get("catalog")
            if name and catalog:
                context.imageCatalog[name] = catalog
            mutable_data = img.find("mutableData")
            if name and mutable_data is not None and mutable_data.text:
                import base64, plistlib
                raw = ''.join(mutable_data.text.split())
                remainder = len(raw) % 4
                if remainder == 1:
                    raw = raw[:-1]
                raw += '=' * ((4 - len(raw) % 4) % 4)
                plist_data = base64.b64decode(raw)
                try:
                    plist = plistlib.loads(plist_data)
                    plist_objects = plist.get("$objects", [])
                    tiff_list = []
                    for o in plist_objects:
                        if isinstance(o, bytes) and len(o) > 4 and o[:2] in (b'MM', b'II'):
                            tiff_list.append(o)
                    if tiff_list:
                        context.imageData[name] = tiff_list[0]
                        context.imagePlistData[name] = {
                            "tiff_reps": tiff_list,
                            "plist_objects": plist_objects,
                        }
                except Exception:
                    pass

    for nib_object_element in objects:
        obj = __xibparser_ParseXIBObject(context, nib_object_element, parent)
        if isinstance(obj, XibObject):
            toplevel.append(obj)

    if resolveConnections:
        context.resolveConnections()

    context.processConstraints()

    return context, createTopLevel(toplevel, context)


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
    rootData["NSObjectsKeys"] = NibList(context.extraNibObjects)
    # parents of XibObjects should be listed here with filesOwner as the highest parent

    extra_set = set(id(o) for o in context.extraNibObjects)
    def _get_parent(o):
        if hasattr(o, 'parent') and callable(o.parent):
            p = o.parent()
            if id(p) in extra_set:
                return p
        if hasattr(o, 'xib_parent'):
            return o.xib_parent()
        if hasattr(o, 'parent') and callable(o.parent):
            p = o.parent()
            if isinstance(p, XibObject):
                return p
        return None
    parent_objects = [_get_parent(o) or filesOwner for o in context.extraNibObjects]
    rootData["NSObjectsValues"] = NibList(parent_objects)

    oid_objects = [filesOwner] + \
        [o for o in context.extraNibObjects] + \
        [o for o in context.connections if o.classname() == "NSNibOutletConnector"] + \
        [o for o in context.connections if o.classname() not in ("NSNibOutletConnector", "NSNibConnector")]
    rootData["NSOidsKeys"] = NibList(oid_objects)
    rootData["NSOidsValues"] = NibList([NibNSNumber(x+1) for x,_ in enumerate(oid_objects)])
    ax_connectors = []
    for dest, description in context.accessibilityConnections:
        conn = NibObject("NSNibAXAttributeConnector")
        conn["AXDestinationArchiveKey"] = dest
        conn["AXAttributeTypeArchiveKey"] = NibMutableString("AXDescription")
        conn["AXAttributeValueArchiveKey"] = NibString.intern(description)
        ax_connectors.append(conn)
    rootData["NSAccessibilityConnectors"] = NibMutableList(ax_connectors)
    if ax_connectors:
        rootData["NSAccessibilityOidsKeys"] = NibList(ax_connectors)
        rootData["NSAccessibilityOidsValues"] = NibList([NibNSNumber(len(oid_objects) + 1 + i) for i in range(len(ax_connectors))])
    else:
        emptyList = NibList()
        rootData["NSAccessibilityOidsKeys"] = emptyList
        rootData["NSAccessibilityOidsValues"] = emptyList
    return NibObject("NSObject", None, {
        "IB.objectdata": rootData,
        "IB.systemFontUpdateVersion": 1,
    })


_STORYBOARD_BOOL_TRUE_PROPS = frozenset({"NSAnimates"})

def _storyboard_fixups(root: NibObject) -> None:
    visited: set[int] = set()
    _storyboard_walk(root, visited)

def _storyboard_walk(obj: NibObject, visited: set[int]) -> None:
    obj_id = id(obj)
    if obj_id in visited:
        return
    visited.add(obj_id)

    from .models import ArrayLike, NibDictionaryImpl

    for key, val in list(obj.properties.items()):
        if key in _STORYBOARD_BOOL_TRUE_PROPS and val is False:
            obj.properties[key] = True
        elif isinstance(val, NibObject):
            _storyboard_walk(val, visited)

    if isinstance(obj, NibDictionaryImpl):
        for item in obj._objects:
            if isinstance(item, NibObject):
                _storyboard_walk(item, visited)
    elif isinstance(obj, ArrayLike):
        for item in obj._items:
            if isinstance(item, NibObject):
                _storyboard_walk(item, visited)


def _compile_storyboard_nib(genlib, nibroot):
    _storyboard_fixups(nibroot)
    return genlib.CompileNibObjects([nibroot])


def CompileStoryboard(tree, outpath):
    from . import genlib

    root = tree.getroot()
    replace_string_attribures(root)

    initial_vc_id = root.get("initialViewController")
    use_autolayout = root.get("useAutolayout") == "YES"
    tools_version = int(root.get("toolsVersion", "0").split(".")[0])
    custom_instantiation = root.get("customObjectInstantitationMethod")

    os.makedirs(outpath, exist_ok=True)

    scenes = root.findall(".//scene")
    nib_names = {}  # scene identifier -> nib name
    vc_identifiers_to_uuids = {}  # scene identifier -> UUID
    main_menu_nib = None
    has_app_scene = any(
        child.tag == "application"
        for s in scenes if (objs := s.find("objects")) is not None
        for child in objs
    )

    for scene_elem in scenes:
        objects_elem = scene_elem.find("objects")
        if objects_elem is None:
            continue

        vc_elem = None
        first_responder_elem = None
        for child in objects_elem:
            if child.get("sceneMemberID") == "viewController":
                vc_elem = child
            elif child.get("sceneMemberID") == "firstResponder":
                first_responder_elem = child

        if vc_elem is None:
            continue

        scene_type = vc_elem.tag  # "application", "windowController", "viewController"
        vc_id = vc_elem.get("id")

        if scene_type == "application":
            nib_name = "MainMenu"
            main_menu_nib = nib_name
            nib_names[nib_name] = nib_name
            nibroot = _compile_application_scene(
                root, objects_elem, vc_elem, first_responder_elem,
                use_autolayout, tools_version, custom_instantiation,
            )
            outbytes = _compile_storyboard_nib(genlib, nibroot)
            with open(os.path.join(outpath, nib_name + ".nib"), "wb") as f:
                f.write(outbytes)

        elif scene_type == "windowController":
            storyboard_id = vc_elem.get("storyboardIdentifier")
            nib_name = storyboard_id or f"NSWindowController-{vc_id}"
            nib_names[nib_name] = nib_name
            wc_uuid = str(uuid.uuid4()).upper()
            vc_identifiers_to_uuids[nib_name] = wc_uuid

            segue_elems = vc_elem.findall(".//segue")
            content_vc_id = None
            for seg in segue_elems:
                if seg.get("kind") == "relationship" and "ContentViewController" in (seg.get("relationship") or ""):
                    content_vc_id = seg.get("destination")

            view_nib_name = None
            view_nib_bytes = None
            if content_vc_id:
                vc_scene = _find_scene_for_vc(scenes, content_vc_id)
                if vc_scene is not None:
                    vc_scene_objects = vc_scene.find("objects")
                    vc_scene_vc_elem = None
                    for child in vc_scene_objects:
                        if child.get("sceneMemberID") == "viewController":
                            vc_scene_vc_elem = child
                    if vc_scene_vc_elem is not None:
                        # tabViewControllers are embedded directly in the WC nib
                        if vc_scene_vc_elem.tag != "tabViewController":
                            view_elem = vc_scene_vc_elem.find("view") or vc_scene_vc_elem.find("tabView")
                            if view_elem is not None:
                                view_id = view_elem.get("id")
                                view_nib_name = f"{content_vc_id}-view-{view_id}"
                                view_nib_root = _compile_view_nib(
                                    root, vc_scene_vc_elem, view_elem,
                                    use_autolayout, tools_version, custom_instantiation,
                                )
                                view_nib_bytes = _compile_storyboard_nib(genlib, view_nib_root)

            nibroot = _compile_window_controller_scene(
                root, objects_elem, vc_elem, first_responder_elem,
                use_autolayout, tools_version, custom_instantiation,
                wc_uuid, content_vc_id, view_nib_name, scenes,
                has_app_scene=has_app_scene,
            )
            outbytes = _compile_storyboard_nib(genlib, nibroot)
            with open(os.path.join(outpath, nib_name + ".nib"), "wb") as f:
                f.write(outbytes)

            if view_nib_name and view_nib_bytes:
                with open(os.path.join(outpath, view_nib_name + ".nib"), "wb") as f:
                    f.write(view_nib_bytes)

        elif scene_type in ("viewController", "tabViewController"):
            storyboard_id = vc_elem.get("storyboardIdentifier")
            if storyboard_id:
                view_elem = vc_elem.find("view") or vc_elem.find("tabView")
                if view_elem is not None:
                    view_id = view_elem.get("id")
                    view_nib_name = f"{vc_id}-view-{view_id}"
                    nib_names[view_nib_name] = view_nib_name
                    vc_uuid = str(uuid.uuid4()).upper()
                    vc_identifiers_to_uuids[view_nib_name] = vc_uuid

                    view_nib_root = _compile_view_nib(
                        root, vc_elem, view_elem,
                        use_autolayout, tools_version, custom_instantiation,
                    )
                    view_nib_bytes = _compile_storyboard_nib(genlib, view_nib_root)
                    with open(os.path.join(outpath, view_nib_name + ".nib"), "wb") as f:
                        f.write(view_nib_bytes)

                    nib_names[storyboard_id] = storyboard_id
                    vc_identifiers_to_uuids[storyboard_id] = vc_uuid
                    ctrl_nib_root = _compile_viewcontroller_scene(
                        root, vc_elem, view_nib_name, storyboard_id,
                        vc_uuid, use_autolayout, tools_version, custom_instantiation,
                    )
                    ctrl_nib_bytes = _compile_storyboard_nib(genlib, ctrl_nib_root)
                    with open(os.path.join(outpath, storyboard_id + ".nib"), "wb") as f:
                        f.write(ctrl_nib_bytes)

    # Generate Info.plist
    info = {
        "NSStoryboardMainMenu": main_menu_nib or "MainMenu",
        "NSViewControllerIdentifiersToNibNames": nib_names,
        **({"NSStoryboardDesignatedEntryPointIdentifier": f"NSWindowController-{initial_vc_id}"} if initial_vc_id else {}),
        "NSViewControllerIdentifiersToUUIDs": vc_identifiers_to_uuids,
        "NSStoryboardVersion": 1,
    }
    with open(os.path.join(outpath, "Info.plist"), "wb") as f:
        plistlib.dump(info, f)


def _find_scene_for_vc(scenes, vc_id):
    for scene in scenes:
        objects_elem = scene.find("objects")
        if objects_elem is None:
            continue
        for child in objects_elem:
            if child.get("sceneMemberID") == "viewController" and child.get("id") == vc_id:
                return scene
    return None


def _make_scene_context(root, use_autolayout, tools_version, custom_instantiation):
    ctx = ArchiveContext(
        useAutolayout=use_autolayout,
        customObjectInstantitationMethod=custom_instantiation or "direct",
        toolsVersion=tools_version,
    )
    ctx.isStoryboard = True

    for res_elem in root.iter("resources"):
        for img in res_elem.iter("image"):
            name = img.get("name")
            w = img.get("width")
            h = img.get("height")
            if name and w and h:
                ctx.imageResources[name] = (w, h)
            catalog = img.get("catalog")
            if name and catalog:
                ctx.imageCatalog[name] = catalog

    return ctx


def _inject_synthetic_objects(ctx):
    files_owner = XibObject(ctx, "NSCustomObject", None, None)
    files_owner.xibid = XibId("-2")
    files_owner["NSClassName"] = NibString.intern("NSObject")
    ctx.addObject(files_owner.xibid, files_owner)

    app_object = XibObject(ctx, "NSCustomObject", None, None)
    app_object.xibid = XibId("-3")
    app_object["NSClassName"] = NibString.intern("NSApplication")
    ctx.addObject(app_object.xibid, app_object)
    ctx.extraNibObjects.append(app_object)

    return files_owner, app_object


def _reverse_menu_children(child_objs):
    if not child_objs:
        return
    # Build tree: for each menu, find its items; for each item, find its submenu
    # Then rebuild the list with reverse DFS ordering
    menu_items = {}  # menu obj id -> list of (item, submenu_or_none)
    item_submenu = {}  # item obj id -> submenu obj

    for obj in child_objs:
        cn = obj.classname() if hasattr(obj, 'classname') else ""
        if cn in ("NSMenu",):
            items_list = obj.get("NSMenuItems")
            if items_list and hasattr(items_list, '_items'):
                menu_items[id(obj)] = items_list._items[:]
        if cn in ("NSMenuItem",):
            submenu = obj.get("NSSubmenu")
            if submenu is not None:
                item_submenu[id(obj)] = submenu

    if not menu_items:
        return

    # Rebuild child_objs in reverse DFS order
    visited = set()
    result = []

    def visit_menu(menu):
        if id(menu) in visited:
            return
        visited.add(id(menu))
        result.append(menu)
        items = menu_items.get(id(menu), [])
        for item in reversed(items):
            if id(item) in visited:
                continue
            visited.add(id(item))
            result.append(item)
            submenu = item_submenu.get(id(item))
            if submenu:
                visit_menu(submenu)

    # Find the root menu (first menu in the list)
    for obj in child_objs:
        cn = obj.classname() if hasattr(obj, 'classname') else ""
        if cn == "NSMenu" and id(obj) in menu_items:
            visit_menu(obj)
            break

    # Add any remaining non-menu objects
    for obj in child_objs:
        if id(obj) not in visited:
            result.append(obj)

    child_objs[:] = result


def _resolve_storyboard_connections(ctx, first_responder_id=None):
    from .models import NibProxyObject
    fr_xibid = XibId(first_responder_id) if first_responder_id else None
    result = []
    for con in ctx.connections:
        if con.classname() == "NSIBUserDefinedRuntimeAttributesConnector":
            result.append(con)
            continue
        dst = con.get("NSDestination")
        if dst is None:
            result.append(con)
            continue
        if isinstance(dst, NibProxyObject) or isinstance(dst, NibObject):
            result.append(con)
            continue
        assert isinstance(dst, XibId)
        # First responder: drop destination entirely
        if fr_xibid and dst == fr_xibid:
            del con.properties["NSDestination"]
            result.append(con)
            continue
        if dst in ctx.objects:
            con["NSDestination"] = ctx.objects[dst]
            result.append(con)
            continue
        if dst in ctx.viewObjects:
            con["NSDestination"] = ctx.viewObjects[dst]
            result.append(con)
            continue
        phid = ctx.makePlaceholderIdentifier()
        con["NSDestination"] = NibProxyObject(phid)
        ctx.upstreamPlaceholders[phid] = dst
        result.append(con)
    ctx.connections = result
    ctx._resolveViewReferences()


def _compile_application_scene(root, objects_elem, vc_elem, first_responder_elem,
                                use_autolayout, tools_version, custom_instantiation):
    ctx = _make_scene_context(root, use_autolayout, tools_version, custom_instantiation)

    first_responder_id = first_responder_elem.get("id") if first_responder_elem is not None else None

    # Create synthetic files owner (-2) and application (-3) but don't add -3 yet
    files_owner = XibObject(ctx, "NSCustomObject", None, None)
    files_owner.xibid = XibId("-2")
    files_owner["NSClassName"] = NibString.intern("NSObject")
    ctx.addObject(files_owner.xibid, files_owner)

    toplevel = []
    for child in objects_elem:
        obj = __xibparser_ParseXIBObject(ctx, child, None)
        if isinstance(obj, XibObject):
            toplevel.append(obj)

    # Remove first responder from extraNibObjects (storyboard first responders are not serialized)
    if first_responder_id:
        fr_xibid = XibId(first_responder_id)
        ctx.extraNibObjects = [o for o in ctx.extraNibObjects
                               if not (hasattr(o, 'xibid') and o.xibid == fr_xibid)]

    # Reorder extraNibObjects: top-level scene objects first, then synthetic -3, then children (reversed)
    toplevel_xibids = set()
    for child in objects_elem:
        cid = child.get("id")
        if cid:
            toplevel_xibids.add(cid)

    top_level_objs = []
    child_objs = []
    for o in ctx.extraNibObjects:
        xid = getattr(o, 'xibid', None)
        if xid and xid.val() in toplevel_xibids:
            top_level_objs.append(o)
        else:
            child_objs.append(o)

    app_object = XibObject(ctx, "NSCustomObject", None, None)
    app_object.xibid = XibId("-3")
    app_object["NSClassName"] = NibString.intern("NSApplication")
    ctx.addObject(app_object.xibid, app_object)

    # In storyboard compilation, menu children are in reverse DFS order
    _reverse_menu_children(child_objs)

    ctx.extraNibObjects = top_level_objs + [app_object] + child_objs

    _resolve_storyboard_connections(ctx, first_responder_id)
    ctx.processConstraints()
    return createTopLevel([files_owner] + toplevel, ctx)


def _build_tab_view_controller_for_wc(ctx, vc_elem, scenes, parent,
                                       vc_tag_to_class, extra_objects,
                                       extra_connections, extra_placeholders):
    """Build a full NSTabViewController with tab items and child VC swappers
    for embedding in a window controller NIB."""
    from .parsers.helpers import makeSystemColor

    tab_style_map = {"toolbar": 2, "segmentedControlOnTop": 1, "segmentedControlOnBottom": 1}
    tab_style = vc_elem.get("tabStyle", "")
    transition_elem = vc_elem.find("viewControllerTransitionOptions")

    tab_vc = NibObject("NSTabViewController", parent)
    tab_vc["NSSelectedTabViewItemIndex"] = int(vc_elem.get("selectedTabViewItemIndex", "0"))
    tab_vc["NSViewControllerTabStyle"] = tab_style_map.get(tab_style, 0)
    if transition_elem is not None and transition_elem.get("allowUserInteraction") == "YES":
        tab_vc["NSViewControllerTransitionOption"] = 4096
    tab_vc["showSeguePresentationStyle"] = 0
    tab_vc["uniqueIdentifierForStoryboardCompilation"] = NibString.intern(str(uuid.uuid4()).upper())

    # Create the NSTabView
    tab_view_elem = vc_elem.find("tabView")
    tab_view = NibObject("NSTabView")
    tab_view["NSNextResponder"] = NibNil()
    tab_view["NSNibTouchBar"] = NibNil()
    tab_view["NSvFlags"] = 0x100
    tab_view["NSAllowTruncatedLabels"] = True
    tab_view["NSDrawsBackground"] = True
    tab_view["NSTvFlags"] = 0x6
    tab_view["NSViewWantsBestResolutionOpenGLSurface"] = True
    tab_view["IBNSSafeAreaLayoutGuide"] = NibNil()
    tab_view["IBNSLayoutMarginsGuide"] = NibNil()
    tab_view["IBNSClipsToBounds"] = 0
    tab_view["NSSubviews"] = NibMutableList([])
    tab_view["NSTabViewItems"] = NibMutableList([])
    # System font 13
    font = NibObject("NSFont")
    font["NSName"] = NibString.intern(".AppleSystemUIFont")
    font["NSSize"] = 13.0
    font["NSfFlags"] = 0x414
    tab_view["NSFont"] = font

    if tab_view_elem is not None:
        frame_elem = tab_view_elem.find("rect[@key='frame']")
        if frame_elem is not None:
            from .parsers.helpers import frame_string as _frame_string
            x = int(float(frame_elem.get("x", "0")))
            y_f = float(frame_elem.get("y", "0"))
            y = int(y_f) if y_f == int(y_f) else y_f
            w = int(frame_elem.get("width", "453"))
            h = int(frame_elem.get("height", "261"))
            tab_view["NSFrame"] = _frame_string(x, y, w, h)

    tab_vc["NSTabView"] = tab_view

    # Gather tab items and their segue destinations
    tab_item_segues = [
        seg for seg in vc_elem.findall(".//segue")
        if seg.get("kind") == "relationship" and seg.get("relationship") == "tabItems"
    ]
    tab_view_items_elem = vc_elem.find("tabViewItems")
    tab_items_list = list(tab_view_items_elem) if tab_view_items_elem is not None else []

    tab_item_objs = []
    child_swapper_objs = []

    for tab_item_elem, tab_seg in zip(tab_items_list, tab_item_segues):
        child_vc_id = tab_seg.get("destination")
        child_scene = _find_scene_for_vc(scenes, child_vc_id)
        if child_scene is None:
            continue
        child_objects = child_scene.find("objects")
        child_vc_elem = None
        for ch in child_objects:
            if ch.get("sceneMemberID") == "viewController":
                child_vc_elem = ch
        if child_vc_elem is None:
            continue

        child_view = child_vc_elem.find("view") or child_vc_elem.find("tabView")
        if child_view is None:
            continue
        child_view_id = child_view.get("id")
        child_view_nib = f"{child_vc_id}-view-{child_view_id}"

        # Swift mangled name if customModule is set
        child_default_class = vc_tag_to_class.get(child_vc_elem.tag, "NSViewController")
        child_custom_class = child_vc_elem.get("customClass")
        child_module = child_vc_elem.get("customModule")
        if child_custom_class and child_module:
            class_name = f"_TtC{len(child_module)}{child_module}{len(child_custom_class)}{child_custom_class}"
        elif child_custom_class:
            class_name = child_custom_class
        else:
            class_name = child_default_class

        # NSClassSwapper for child VC
        child_swapper = NibObject("NSClassSwapper", tab_vc)
        child_swapper["NSClassName"] = NibString.intern(class_name)
        child_swapper["NSOriginalClassName"] = NibString.intern("NSViewController")
        child_swapper["NSNibName"] = NibString.intern(child_view_nib)
        child_swapper["NSExternalObjectsTableForViewLoading"] = NibMutableDictionary([
            NibString.intern("UpstreamPlaceholder-1"), child_swapper,
        ])
        child_swapper["connectionsRequireClassSwapperForStoryboardCompilation"] = True

        show_segue = child_vc_elem.get("showSeguePresentationStyle")
        child_swapper["showSeguePresentationStyle"] = 1 if show_segue == "single" else 0
        child_uuid = str(uuid.uuid4()).upper()
        child_swapper["uniqueIdentifierForStoryboardCompilation"] = NibString.intern(child_uuid)
        if show_segue == "single":
            child_swapper["NSStoryboardSegueDestinationOptions"] = NibDictionary([
                NibString.intern("NSSingleInstancePresentationIdentifier"),
                NibString.intern(child_uuid),
            ])

        sb_id = child_vc_elem.get("storyboardIdentifier")
        if sb_id:
            child_swapper["NSStoryboardIdentifier"] = NibString.intern(sb_id)

        # NSTabViewItem
        tab_item = NibObject("NSTabViewItem")
        label = tab_item_elem.get("label", "")
        tab_item["NSLabel"] = NibString.intern(label)
        tab_item["NSColor"] = makeSystemColor("controlColor")

        img_name = tab_item_elem.get("image")
        img_obj = None
        if img_name:
            from .parsers.helpers import make_image
            img_obj = make_image(img_name, tab_item, ctx)
            tab_item["NSImage"] = img_obj

        # Outlet: tab item -> child swapper (viewController)
        conn = NibObject("NSNibOutletConnector")
        conn["NSSource"] = tab_item
        conn["NSDestination"] = child_swapper
        conn["NSLabel"] = NibString.intern("viewController")
        extra_connections.append(conn)

        # Runtime attribute: tab item image
        if img_obj:
            rt = NibObject("NSIBUserDefinedRuntimeAttributesConnector")
            rt["NSObject"] = tab_item
            rt["NSValues"] = NibList([img_obj])
            rt["NSKeyPaths"] = NibList([NibString.intern("image")])
            extra_connections.append(rt)

        # Storyboard placeholder for child swapper
        placeholder = NibObject("NSNibExternalObjectPlaceholder")
        placeholder["NSExternalObjectPlaceholderIdentifier"] = NibString.intern("NSStoryboardPlaceholder")
        extra_placeholders.append(placeholder)
        conn_sb = NibObject("NSNibOutletConnector")
        conn_sb["NSSource"] = child_swapper
        conn_sb["NSDestination"] = placeholder
        conn_sb["NSLabel"] = NibString.intern("storyboard")
        conn_sb["NSChildControllerCreationSelectorName"] = NibNil()
        extra_connections.append(conn_sb)

        tab_item_objs.append(tab_item)
        child_swapper_objs.append(child_swapper)
        extra_objects.append(tab_item)
        extra_objects.append(child_swapper)

    tab_vc["privateRelationshipSegueTrackingItems"] = NibList(tab_item_objs)

    # Outlet: tabView.delegate -> tabVC
    conn_tv_delegate = NibObject("NSNibOutletConnector")
    conn_tv_delegate["NSSource"] = tab_view
    conn_tv_delegate["NSDestination"] = tab_vc
    conn_tv_delegate["NSLabel"] = NibString.intern("delegate")
    conn_tv_delegate["NSChildControllerCreationSelectorName"] = NibNil()
    extra_connections.append(conn_tv_delegate)

    # Storyboard placeholder for tabVC
    tab_vc_placeholder = NibObject("NSNibExternalObjectPlaceholder")
    tab_vc_placeholder["NSExternalObjectPlaceholderIdentifier"] = NibString.intern("NSStoryboardPlaceholder")
    extra_placeholders.append(tab_vc_placeholder)
    conn_tvc_sb = NibObject("NSNibOutletConnector")
    conn_tvc_sb["NSSource"] = tab_vc
    conn_tvc_sb["NSDestination"] = tab_vc_placeholder
    conn_tvc_sb["NSLabel"] = NibString.intern("storyboard")
    conn_tvc_sb["NSChildControllerCreationSelectorName"] = NibNil()
    extra_connections.append(conn_tvc_sb)

    # Outlet: tabVC -> tabView
    conn_tvc_tv = NibObject("NSNibOutletConnector")
    conn_tvc_tv["NSSource"] = tab_vc
    conn_tvc_tv["NSDestination"] = tab_view
    conn_tvc_tv["NSLabel"] = NibString.intern("tabView")
    conn_tvc_tv["NSChildControllerCreationSelectorName"] = NibNil()
    extra_connections.append(conn_tvc_tv)

    # Runtime attribute: tabVC.tabViewItems
    rt_items = NibObject("NSIBUserDefinedRuntimeAttributesConnector")
    rt_items["NSObject"] = tab_vc
    rt_items["NSValues"] = NibList([NibList(tab_item_objs)])
    rt_items["NSKeyPaths"] = NibList([NibString.intern("tabViewItems")])
    extra_connections.append(rt_items)

    extra_objects.insert(0, tab_view)

    return tab_vc



    walk(toolbar)
    return result


def _compile_window_controller_scene(root, objects_elem, vc_elem, first_responder_elem,
                                      use_autolayout, tools_version, custom_instantiation,
                                      wc_uuid, content_vc_id, view_nib_name, scenes,
                                      has_app_scene=False):
    ctx = _make_scene_context(root, use_autolayout, tools_version, custom_instantiation)

    first_responder_id = first_responder_elem.get("id") if first_responder_elem is not None else None

    # Create files owner (-2) but defer -3
    files_owner = XibObject(ctx, "NSCustomObject", None, None)
    files_owner.xibid = XibId("-2")
    files_owner["NSClassName"] = NibString.intern("NSObject")
    ctx.addObject(files_owner.xibid, files_owner)

    toplevel = []
    wc_obj = None
    for child in objects_elem:
        obj = __xibparser_ParseXIBObject(ctx, child, None)
        if isinstance(obj, XibObject):
            toplevel.append(obj)
            if child.get("sceneMemberID") == "viewController" and child.tag == "windowController":
                wc_obj = obj

    # Remove first responder from extraNibObjects
    if first_responder_id:
        fr_xibid = XibId(first_responder_id)
        ctx.extraNibObjects = [o for o in ctx.extraNibObjects
                               if not (hasattr(o, 'xibid') and o.xibid == fr_xibid)]

    if wc_obj is None:
        app_object = XibObject(ctx, "NSCustomObject", None, None)
        app_object.xibid = XibId("-3")
        app_object["NSClassName"] = NibString.intern("NSApplication")
        ctx.addObject(app_object.xibid, app_object)
        ctx.extraNibObjects.append(app_object)
        _resolve_storyboard_connections(ctx, first_responder_id)
        ctx.processConstraints()
        return createTopLevel([files_owner] + toplevel, ctx)

    wc_uuid_str = NibString.intern(wc_uuid)
    wc_obj["uniqueIdentifierForStoryboardCompilation"] = wc_uuid_str

    if wc_obj.get("showSeguePresentationStyle") == 1:
        wc_obj["NSStoryboardSegueDestinationOptions"] = NibDictionary([
            NibString.intern("NSSingleInstancePresentationIdentifier"),
            wc_uuid_str,
        ])

    window_template = wc_obj.get("IBWindowTemplate")

    # Ensure window template has a content view
    if window_template and (not window_template.get("NSWindowView") or isinstance(window_template.get("NSWindowView"), NibNil)):
        content_view = NibObject("NSView", window_template)
        content_view["NSNextResponder"] = NibNil()
        content_view["NSNibTouchBar"] = NibNil()
        content_view["NSvFlags"] = 0x100
        frame_size_str = "{0, 0}"
        win_rect = window_template.get("NSWindowRect")
        if isinstance(win_rect, NibString):
            m = re.search(r'\{([\d.]+),\s*([\d.]+)\}\}$', win_rect._text)
            if m:
                w = int(float(m.group(1))) if float(m.group(1)) == int(float(m.group(1))) else float(m.group(1))
                h = int(float(m.group(2))) if float(m.group(2)) == int(float(m.group(2))) else float(m.group(2))
                frame_size_str = f"{{{w}, {h}}}"
        content_view["NSFrameSize"] = NibString.intern(frame_size_str)
        content_view["NSViewWantsBestResolutionOpenGLSurface"] = True
        content_view["IBNSSafeAreaLayoutGuide"] = NibNil()
        content_view["IBNSLayoutMarginsGuide"] = NibNil()
        content_view["IBNSClipsToBounds"] = 0
        window_template["NSWindowView"] = content_view

    # Create content view controller
    content_vc_obj = None  # either NSClassSwapper or NSTabViewController
    tab_vc_extra_objects = []  # additional objects for tabViewController embedding
    tab_vc_extra_connections = []  # additional connections for tabViewController
    tab_vc_extra_placeholders = []  # storyboard placeholders for child VC swappers

    _vc_tag_to_class = {
        "viewController": "NSViewController",
        "tabViewController": "NSTabViewController",
        "splitViewController": "NSSplitViewController",
        "pageController": "NSPageController",
    }

    vc_elem_in_scene = None
    if content_vc_id:
        vc_scene = _find_scene_for_vc(scenes, content_vc_id)
        if vc_scene is not None:
            vc_objects = vc_scene.find("objects")
            for child in vc_objects:
                if child.get("sceneMemberID") == "viewController":
                    vc_elem_in_scene = child

    if vc_elem_in_scene is not None and vc_elem_in_scene.tag == "tabViewController":
        content_vc_obj = _build_tab_view_controller_for_wc(
            ctx, vc_elem_in_scene, scenes, window_template, _vc_tag_to_class,
            tab_vc_extra_objects, tab_vc_extra_connections, tab_vc_extra_placeholders,
        )
        wc_obj["IBWindowTemplateContentViewController"] = content_vc_obj
    elif vc_elem_in_scene is not None and view_nib_name:
        original_class = _vc_tag_to_class.get(vc_elem_in_scene.tag, "NSViewController")
        custom_class = vc_elem_in_scene.get("customClass")
        custom_module = vc_elem_in_scene.get("customModule")
        if custom_class:
            if custom_module:
                class_name = f"_TtC{len(custom_module)}{custom_module}{len(custom_class)}{custom_class}"
            else:
                class_name = custom_class
            content_vc_obj = NibObject("NSClassSwapper", window_template)
            content_vc_obj["NSClassName"] = NibString.intern(class_name)
            content_vc_obj["NSOriginalClassName"] = NibString.intern(original_class)
            content_vc_obj["NSNibName"] = NibString.intern(view_nib_name)
            sb_id = vc_elem_in_scene.get("storyboardIdentifier")
            if sb_id:
                content_vc_obj["NSStoryboardIdentifier"] = NibString.intern(sb_id)
            vc_has_connections = vc_elem_in_scene.find("connections") is not None
            if sb_id or vc_has_connections:
                content_vc_obj["NSExternalObjectsTableForViewLoading"] = NibMutableDictionary([
                    NibString.intern("UpstreamPlaceholder-1"), content_vc_obj,
                ])
            else:
                content_vc_obj["NSExternalObjectsTableForViewLoading"] = NibMutableDictionary()
            content_vc_obj["showSeguePresentationStyle"] = 0
            vc_uuid = str(uuid.uuid4()).upper()
            content_vc_obj["uniqueIdentifierForStoryboardCompilation"] = NibString.intern(vc_uuid)
            if sb_id:
                content_vc_obj["connectionsRequireClassSwapperForStoryboardCompilation"] = True
        else:
            content_vc_obj = NibObject(original_class, window_template)
            content_vc_obj["NSNibName"] = NibString.intern(view_nib_name)
            content_vc_obj["NSExternalObjectsTableForViewLoading"] = NibMutableDictionary()
            content_vc_obj["showSeguePresentationStyle"] = 0
            vc_uuid = str(uuid.uuid4()).upper()
            content_vc_obj["uniqueIdentifierForStoryboardCompilation"] = NibString.intern(vc_uuid)
        wc_obj["IBWindowTemplateContentViewController"] = content_vc_obj

    # Create storyboard external placeholder objects
    placeholder1 = NibObject("NSNibExternalObjectPlaceholder")
    placeholder1["NSExternalObjectPlaceholderIdentifier"] = NibString.intern("NSStoryboardPlaceholder")

    placeholder2 = NibObject("NSNibExternalObjectPlaceholder")
    placeholder2["NSExternalObjectPlaceholderIdentifier"] = NibString.intern("NSStoryboardPlaceholder")

    # Add synthetic -3
    app_object = XibObject(ctx, "NSCustomObject", None, None)
    app_object.xibid = XibId("-3")
    app_object["NSClassName"] = NibString.intern("NSApplication")
    ctx.addObject(app_object.xibid, app_object)

    # Reorder extraNibObjects to match reference
    content_view_obj = window_template.get("NSWindowView") if window_template else None
    ordered = [placeholder1, wc_obj]
    if window_template:
        ordered.append(window_template)
    if content_view_obj:
        ordered.append(content_view_obj)
    if content_vc_obj:
        ordered.append(content_vc_obj)
    ordered.extend(tab_vc_extra_objects)
    # Include remaining parsed objects (e.g. toolbar items) not yet in ordered
    ordered_set = set(id(o) for o in ordered)
    ordered_set.add(id(app_object))
    remaining = [o for o in ctx.extraNibObjects if id(o) not in ordered_set]
    ordered.extend(remaining)
    ordered.append(app_object)
    ordered.append(placeholder2)
    ordered.extend(tab_vc_extra_placeholders)
    ctx.extraNibObjects = ordered

    # Remove parsed connections - they'll be replaced with storyboard-specific ones
    # But preserve action connections from parsed elements (e.g. toolbar items)
    parsed_connections = ctx.connections[:]
    preserved_connections = [c for c in parsed_connections
                             if c.classname() == "NSNibControlConnector"]
    ctx.connections.clear()

    # Add tab VC connections before storyboard connections
    ctx.connections.extend(tab_vc_extra_connections)

    # Add storyboard-specific connections in Apple's order
    conn_scene = NibObject("NSNibOutletConnector")
    conn_scene["NSSource"] = files_owner
    conn_scene["NSDestination"] = wc_obj
    conn_scene["NSLabel"] = NibString.intern("sceneController")
    conn_scene["NSChildControllerCreationSelectorName"] = NibNil()
    ctx.connections.append(conn_scene)

    conn_wc_sb = NibObject("NSNibOutletConnector")
    conn_wc_sb["NSSource"] = wc_obj
    conn_wc_sb["NSDestination"] = placeholder2
    conn_wc_sb["NSLabel"] = NibString.intern("storyboard")
    conn_wc_sb["NSChildControllerCreationSelectorName"] = NibNil()
    ctx.connections.append(conn_wc_sb)

    if window_template:
        conn_window = NibObject("NSNibOutletConnector")
        conn_window["NSSource"] = wc_obj
        conn_window["NSDestination"] = window_template
        conn_window["NSLabel"] = NibString.intern("window")
        conn_window["NSChildControllerCreationSelectorName"] = NibNil()
        ctx.connections.append(conn_window)

    has_explicit_delegate = any(
        c.classname() == "NSNibOutletConnector"
        and isinstance(c.get("NSLabel"), NibString) and c.get("NSLabel")._text == "delegate"
        for c in parsed_connections
    )
    auto_delegate = has_app_scene and tools_version <= 13147
    if window_template and (auto_delegate or has_explicit_delegate):
        conn_delegate = NibObject("NSNibOutletConnector")
        conn_delegate["NSSource"] = window_template
        conn_delegate["NSDestination"] = wc_obj
        conn_delegate["NSLabel"] = NibString.intern("delegate")
        conn_delegate["NSChildControllerCreationSelectorName"] = NibNil()
        ctx.connections.append(conn_delegate)

    if not tab_vc_extra_connections and content_vc_obj:
        conn_vc_sb = NibObject("NSNibOutletConnector")
        conn_vc_sb["NSSource"] = content_vc_obj
        conn_vc_sb["NSDestination"] = placeholder1
        conn_vc_sb["NSLabel"] = NibString.intern("storyboard")
        conn_vc_sb["NSChildControllerCreationSelectorName"] = NibNil()
        ctx.connections.append(conn_vc_sb)

    # Add preserved parsed connections (e.g. toolbar actions)
    ctx.connections.extend(preserved_connections)

    if content_vc_obj and window_template:
        runtime_conn = NibObject("NSIBUserDefinedRuntimeAttributesConnector")
        runtime_conn["NSObject"] = window_template
        runtime_conn["NSValues"] = NibList([content_vc_obj])
        runtime_conn["NSKeyPaths"] = NibList([NibString.intern("contentViewController")])
        ctx.connections.append(runtime_conn)

    _resolve_storyboard_connections(ctx, first_responder_id)
    ctx.processConstraints()
    return createTopLevel([files_owner] + toplevel, ctx)


def _compile_view_nib(root, vc_elem, view_elem,
                       use_autolayout, tools_version, custom_instantiation):
    ctx = _make_scene_context(root, use_autolayout, tools_version, custom_instantiation)

    files_owner = XibObject(ctx, "NSCustomObject", None, None)
    files_owner.xibid = XibId("-2")
    files_owner["NSClassName"] = NibString.intern("NSObject")
    ctx.addObject(files_owner.xibid, files_owner)

    # Register the VC as an external placeholder so connections targeting
    # the VC id (outlets/actions from child views to the VC) resolve correctly.
    vc_id = vc_elem.get("id")
    vc_placeholder = NibObject("NSNibExternalObjectPlaceholder")
    vc_placeholder["NSExternalObjectPlaceholderIdentifier"] = NibString.intern("UpstreamPlaceholder-1")
    if vc_id:
        ctx.addObject(XibId(vc_id), vc_placeholder)

    view_obj = __xibparser_ParseXIBObject(ctx, view_elem, None)

    # Parse the VC element's own connections (outlets from VC to subviews)
    for conn_elem in vc_elem.findall("connections/*"):
        if conn_elem.tag == "outlet":
            outlet_conn = NibObject("NSNibOutletConnector")
            outlet_conn["NSSource"] = vc_placeholder
            outlet_conn["NSDestination"] = XibId(conn_elem.get("destination"))
            outlet_conn["NSLabel"] = conn_elem.get("property")
            outlet_conn["NSChildControllerCreationSelectorName"] = NibNil()
            ctx.connections.append(outlet_conn)
        elif conn_elem.tag == "action":
            action_conn = NibObject("NSNibControlConnector")
            action_conn["NSSource"] = vc_placeholder
            action_conn["NSDestination"] = XibId(conn_elem.get("destination") or conn_elem.get("target"))
            action_conn["NSLabel"] = conn_elem.get("selector")
            ctx.connections.append(action_conn)

    app_object = XibObject(ctx, "NSCustomObject", None, None)
    app_object.xibid = XibId("-3")
    app_object["NSClassName"] = NibString.intern("NSApplication")
    ctx.addObject(app_object.xibid, app_object)
    ctx.extraNibObjects.append(app_object)

    vc_xibid = XibId(vc_id) if vc_id else None
    has_vc_connections = any(
        c.get("NSSource") is vc_placeholder or c.get("NSDestination") is vc_placeholder
        or c.get("NSSource") == vc_xibid or c.get("NSDestination") == vc_xibid
        for c in ctx.connections
    )
    if has_vc_connections:
        ctx.extraNibObjects.append(vc_placeholder)

    # Connection: root -> view
    conn = NibObject("NSNibOutletConnector")
    conn["NSSource"] = files_owner
    conn["NSDestination"] = view_obj
    conn["NSLabel"] = NibString.intern("view")
    conn["NSChildControllerCreationSelectorName"] = NibNil()
    ctx.connections.append(conn)

    ctx.resolveConnections()
    # Drop connections whose destinations couldn't be resolved (cross-scene refs).
    # resolveConnections() turns these into UIProxyObject which doesn't exist on macOS.
    from .models import NibProxyObject
    ctx.connections = [c for c in ctx.connections
                       if not isinstance(c.get("NSDestination"), NibProxyObject)]
    ctx.processConstraints()
    return createTopLevel([files_owner], ctx)


def _compile_viewcontroller_scene(root, vc_elem, view_nib_name, storyboard_id,
                                   vc_uuid, use_autolayout, tools_version, custom_instantiation):
    ctx = _make_scene_context(root, use_autolayout, tools_version, custom_instantiation)

    files_owner = XibObject(ctx, "NSCustomObject", None, None)
    files_owner.xibid = XibId("-2")
    files_owner["NSClassName"] = NibString.intern("NSObject")
    ctx.addObject(files_owner.xibid, files_owner)

    vc_tag_to_class = {
        "viewController": "NSViewController",
        "tabViewController": "NSTabViewController",
        "splitViewController": "NSSplitViewController",
        "pageController": "NSPageController",
    }
    original_class = vc_tag_to_class.get(vc_elem.tag, "NSViewController")
    custom_class = vc_elem.get("customClass")
    custom_module = vc_elem.get("customModule")
    if custom_class and custom_module:
        class_name = f"_TtC{len(custom_module)}{custom_module}{len(custom_class)}{custom_class}"
    elif custom_class:
        class_name = custom_class
    else:
        class_name = original_class

    vc_swapper = NibObject("NSClassSwapper", files_owner)
    vc_swapper["NSClassName"] = NibString.intern(class_name)
    vc_swapper["NSOriginalClassName"] = NibString.intern(original_class)
    vc_swapper["NSNibName"] = NibString.intern(view_nib_name)
    vc_swapper["NSStoryboardIdentifier"] = NibString.intern(storyboard_id)
    vc_swapper["NSExternalObjectsTableForViewLoading"] = NibMutableDictionary([
        NibString.intern("UpstreamPlaceholder-1"), vc_swapper,
    ])
    show_segue = vc_elem.get("showSeguePresentationStyle")
    if show_segue == "single":
        vc_swapper["showSeguePresentationStyle"] = 1
    else:
        vc_swapper["showSeguePresentationStyle"] = 0
    vc_swapper["uniqueIdentifierForStoryboardCompilation"] = NibString.intern(vc_uuid)
    if show_segue == "single":
        vc_swapper["NSStoryboardSegueDestinationOptions"] = NibDictionary([
            NibString.intern("NSSingleInstancePresentationIdentifier"),
            NibString.intern(vc_uuid),
        ])
    vc_swapper["connectionsRequireClassSwapperForStoryboardCompilation"] = True
    ctx.extraNibObjects.append(vc_swapper)

    app_object = XibObject(ctx, "NSCustomObject", None, None)
    app_object.xibid = XibId("-3")
    app_object["NSClassName"] = NibString.intern("NSApplication")
    ctx.addObject(app_object.xibid, app_object)
    ctx.extraNibObjects.append(app_object)

    storyboard_placeholder = NibObject("NSNibExternalObjectPlaceholder", files_owner)
    storyboard_placeholder["NSExternalObjectPlaceholderIdentifier"] = NibString.intern("NSStoryboardPlaceholder")
    ctx.extraNibObjects.append(storyboard_placeholder)

    # Connection: files_owner -> vc_swapper ("sceneController")
    conn1 = NibObject("NSNibOutletConnector")
    conn1["NSSource"] = files_owner
    conn1["NSDestination"] = vc_swapper
    conn1["NSLabel"] = NibString.intern("sceneController")
    conn1["NSChildControllerCreationSelectorName"] = NibNil()
    ctx.connections.append(conn1)

    # Connection: vc_swapper -> storyboard_placeholder ("storyboard")
    conn2 = NibObject("NSNibOutletConnector")
    conn2["NSSource"] = vc_swapper
    conn2["NSDestination"] = storyboard_placeholder
    conn2["NSLabel"] = NibString.intern("storyboard")
    conn2["NSChildControllerCreationSelectorName"] = NibNil()
    ctx.connections.append(conn2)

    ctx.resolveConnections()
    return createTopLevel([files_owner], ctx)

