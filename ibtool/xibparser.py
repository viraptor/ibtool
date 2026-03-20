import re
import os
import plistlib
import uuid
from .models import (
    NibNSNumber,
    NibObject,
    NibList,
    NibMutableList,
    NibMutableDictionary,
    NibMutableSet,
    NibString,
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

    def _get_parent(o):
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
            outbytes = genlib.CompileNibObjects([nibroot])
            with open(os.path.join(outpath, nib_name + ".nib"), "wb") as f:
                f.write(outbytes)

        elif scene_type == "windowController":
            nib_name = f"NSWindowController-{vc_id}"
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
                        view_elem = vc_scene_vc_elem.find("view")
                        if view_elem is not None:
                            view_id = view_elem.get("id")
                            view_nib_name = f"{content_vc_id}-view-{view_id}"
                            view_nib_root = _compile_view_nib(
                                root, vc_scene_vc_elem, view_elem,
                                use_autolayout, tools_version, custom_instantiation,
                            )
                            view_nib_bytes = genlib.CompileNibObjects([view_nib_root])

            nibroot = _compile_window_controller_scene(
                root, objects_elem, vc_elem, first_responder_elem,
                use_autolayout, tools_version, custom_instantiation,
                wc_uuid, content_vc_id, view_nib_name, scenes,
            )
            outbytes = genlib.CompileNibObjects([nibroot])
            with open(os.path.join(outpath, nib_name + ".nib"), "wb") as f:
                f.write(outbytes)

            if view_nib_name and view_nib_bytes:
                with open(os.path.join(outpath, view_nib_name + ".nib"), "wb") as f:
                    f.write(view_nib_bytes)

    # Generate Info.plist
    info = {
        "NSStoryboardMainMenu": main_menu_nib or "MainMenu",
        "NSViewControllerIdentifiersToNibNames": nib_names,
        "NSStoryboardDesignatedEntryPointIdentifier": f"NSWindowController-{initial_vc_id}" if initial_vc_id else "",
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


def _compile_window_controller_scene(root, objects_elem, vc_elem, first_responder_elem,
                                      use_autolayout, tools_version, custom_instantiation,
                                      wc_uuid, content_vc_id, view_nib_name, scenes):
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

    wc_obj["uniqueIdentifierForStoryboardCompilation"] = NibString.intern(wc_uuid)

    window_template = wc_obj.get("IBWindowTemplate")

    # Ensure window template has a content view
    if window_template and (not window_template.get("NSWindowView") or isinstance(window_template.get("NSWindowView"), NibNil)):
        content_view = NibObject("NSView", window_template)
        content_view["NSNextResponder"] = NibNil()
        content_view["NSNibTouchBar"] = NibNil()
        content_view["NSvFlags"] = 0x100
        frame_size = window_template.get("NSWindowContentMinSize") or NibString.intern("{0, 0}")
        content_view["NSFrameSize"] = frame_size
        content_view["NSViewWantsBestResolutionOpenGLSurface"] = True
        content_view["IBNSSafeAreaLayoutGuide"] = NibNil()
        content_view["IBNSLayoutMarginsGuide"] = NibNil()
        content_view["IBNSClipsToBounds"] = 0
        window_template["NSWindowView"] = content_view

    # Create content view controller as NSClassSwapper
    content_vc_swapper = None
    if content_vc_id and view_nib_name:
        vc_scene = _find_scene_for_vc(scenes, content_vc_id)
        if vc_scene is not None:
            vc_objects = vc_scene.find("objects")
            vc_elem_in_scene = None
            for child in vc_objects:
                if child.get("sceneMemberID") == "viewController":
                    vc_elem_in_scene = child
            if vc_elem_in_scene is not None:
                custom_class = vc_elem_in_scene.get("customClass", "NSViewController")
                original_class = "NSViewController"

                content_vc_swapper = NibObject("NSClassSwapper", window_template)
                content_vc_swapper["NSClassName"] = NibString.intern(custom_class)
                content_vc_swapper["NSOriginalClassName"] = NibString.intern(original_class)
                content_vc_swapper["NSNibName"] = NibString.intern(view_nib_name)
                content_vc_swapper["NSExternalObjectsTableForViewLoading"] = NibMutableDictionary()
                content_vc_swapper["showSeguePresentationStyle"] = 0
                vc_uuid = str(uuid.uuid4()).upper()
                content_vc_swapper["uniqueIdentifierForStoryboardCompilation"] = NibString.intern(vc_uuid)

                wc_obj["IBWindowTemplateContentViewController"] = content_vc_swapper

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

    # Reorder extraNibObjects to match reference:
    # [placeholder1, wc, wt, view, vcSwapper, NSApp, placeholder2]
    content_view_obj = window_template.get("NSWindowView") if window_template else None
    ordered = [placeholder1, wc_obj]
    if window_template:
        ordered.append(window_template)
    if content_view_obj:
        ordered.append(content_view_obj)
    if content_vc_swapper:
        ordered.append(content_vc_swapper)
    ordered.append(app_object)
    ordered.append(placeholder2)
    ctx.extraNibObjects = ordered

    # Add storyboard-specific connections
    conn_scene = NibObject("NSNibOutletConnector")
    conn_scene["NSSource"] = files_owner
    conn_scene["NSDestination"] = wc_obj
    conn_scene["NSLabel"] = NibString.intern("sceneController")
    conn_scene["NSChildControllerCreationSelectorName"] = NibNil()
    ctx.connections.insert(0, conn_scene)

    if content_vc_swapper:
        conn_vc_sb = NibObject("NSNibOutletConnector")
        conn_vc_sb["NSSource"] = content_vc_swapper
        conn_vc_sb["NSDestination"] = placeholder1
        conn_vc_sb["NSLabel"] = NibString.intern("storyboard")
        conn_vc_sb["NSChildControllerCreationSelectorName"] = NibNil()
        ctx.connections.append(conn_vc_sb)

    if window_template:
        conn_delegate = NibObject("NSNibOutletConnector")
        conn_delegate["NSSource"] = window_template
        conn_delegate["NSDestination"] = wc_obj
        conn_delegate["NSLabel"] = NibString.intern("delegate")
        conn_delegate["NSChildControllerCreationSelectorName"] = NibNil()
        ctx.connections.append(conn_delegate)

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

    if content_vc_swapper and window_template:
        runtime_conn = NibObject("NSIBUserDefinedRuntimeAttributesConnector")
        runtime_conn["NSObject"] = window_template
        runtime_conn["NSValues"] = NibList([content_vc_swapper])
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

    custom_class = view_elem.get("customClass")
    original_class = "NSView"

    if custom_class:
        view_obj = XibObject(ctx, "NSView", view_elem, None)
        view_obj.setclassname("NSClassSwapper")
        view_obj["NSClassName"] = NibString.intern(custom_class)
        view_obj["NSOriginalClassName"] = NibString.intern(original_class)
    else:
        view_obj = XibObject(ctx, "NSView", view_elem, None)

    ctx.addObject(view_obj.xibid, view_obj)
    ctx.extraNibObjects.append(view_obj)

    app_object = XibObject(ctx, "NSCustomObject", None, None)
    app_object.xibid = XibId("-3")
    app_object["NSClassName"] = NibString.intern("NSApplication")
    ctx.addObject(app_object.xibid, app_object)
    ctx.extraNibObjects.append(app_object)

    view_obj["NSNextResponder"] = NibNil()
    view_obj["NSNibTouchBar"] = NibNil()
    view_obj.flagsOr("NSvFlags", 0x100)

    frame_elem = view_elem.find("rect[@key='frame']")
    if frame_elem is not None:
        w = frame_elem.get("width", "0")
        h = frame_elem.get("height", "0")
        w = int(float(w)) if float(w) == int(float(w)) else float(w)
        h = int(float(h)) if float(h) == int(float(h)) else float(h)
        view_obj["NSFrameSize"] = NibString.intern(f"{{{w}, {h}}}")

    view_obj["NSViewWantsBestResolutionOpenGLSurface"] = True
    view_obj["IBNSSafeAreaLayoutGuide"] = NibNil()
    view_obj["IBNSLayoutMarginsGuide"] = NibNil()
    view_obj["IBNSClipsToBounds"] = 0

    # Connection: root -> view
    conn = NibObject("NSNibOutletConnector")
    conn["NSSource"] = files_owner
    conn["NSDestination"] = view_obj
    conn["NSLabel"] = NibString.intern("view")
    conn["NSChildControllerCreationSelectorName"] = NibNil()
    ctx.connections.append(conn)

    ctx.resolveConnections()
    ctx.processConstraints()
    return createTopLevel([files_owner], ctx)

