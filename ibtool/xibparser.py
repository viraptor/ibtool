import re
import os
import plistlib
import uuid
from .models import (
    ArrayLike,
    NibNSNumber,
    NibObject,
    NibList,
    NibMutableList,
    NibDictionary,
    NibDictionaryImpl,
    NibMutableDictionary,
    NibMutableSet,
    NibProxyObject,
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
from . import genlib
from .parsers_base import __xibparser_ParseXIBObject
from .system_images import system_image_size
from .parsers.helpers import makeSystemColor

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
def ParseXIBObjects(root: Element, context: Optional[ArchiveContext]=None, resolveConnections: bool=True, parent: Optional[NibObject]=None, module: Optional[str]=None, isBaseLocalization: bool=False) -> tuple[ArchiveContext, NibObject]:
    replace_string_attribures(root)

    objects = next(root.iter("objects"))
    toplevel: list[XibObject] = []

    context = context or ArchiveContext(
        useAutolayout=(root.attrib.get("useAutolayout") == "YES"),
        customObjectInstantitationMethod=root.attrib.get("customObjectInstantitationMethod"),
        toolsVersion=int(root.attrib.get("toolsVersion", "0").split(".")[0]),
        module=module,
        )
    if isBaseLocalization:
        context.isBaseLocalization = True
    
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
                if name.startswith("NS"):
                    sys_size = system_image_size(name)
                    if sys_size is not None:
                        w, h = str(sys_size[0]), str(sys_size[1])
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


from .storyboard import CompileStoryboard  # noqa: E402,F401
