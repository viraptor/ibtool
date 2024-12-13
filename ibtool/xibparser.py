import re
from .models import (
    NibNSNumber,
    NibObject,
    NibList,
    NibMutableList,
    NibMutableSet,
    XibId,
    ArchiveContext,
    XibObject,
)
from xml.etree.ElementTree import Element
from typing import Optional
from .parsers_base import __xibparser_ParseXIBObject


# Parses xml Xib data and returns a NibObject that can be used as the root
# object in a compiled NIB archive.
# element: The element containing the objects to be included in the nib.
#          For standalone XIBs, this is typically document->objects
#          For storyboards, this is typically document->scenes->scene->objects
def ParseXIBObjects(root: Element, context: Optional[ArchiveContext]=None, resolveConnections: bool=True, parent: Optional[NibObject]=None) -> tuple[ArchiveContext, NibObject]:
    objects = next(root.iter("objects"))
    toplevel: list[XibObject] = []

    context = context or ArchiveContext(
        useAutolayout=(root.attrib.get("useAutolayout") == "YES"),
        customObjectInstantitationMethod=root.attrib.get("customObjectInstantitationMethod"),
        toolsVersion=int(root.attrib.get("toolsVersion", "0")),
        )
    
    dependencies = [x for x in root.iter("dependencies")]
    if not dependencies:
        deployment = [x for x in dependencies[0].iter("deployment")]
        if deployment:
            context.deployment = True

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

