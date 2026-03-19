from ..models import ArchiveContext, NibObject, NibString, XibObject, XibId
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSCustomObject", elem, parent)
    ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    obj["NSClassName"] = NibString.intern("NSApplication")

    menu_elem = elem.find("menu[@key='mainMenu']")
    # Parse children with parent=None for menu so it gets filesOwner as parent in NSObjectsValues
    for child_elem in elem:
        if child_elem.tag == "menu" and child_elem.get("key") == "mainMenu":
            from ..parsers_base import __xibparser_ParseXIBObject
            __xibparser_ParseXIBObject(ctx, child_elem, None)
        else:
            from ..parsers_base import __xibparser_ParseXIBObject
            __xibparser_ParseXIBObject(ctx, child_elem, obj)

    if menu_elem is not None:
        menu_obj = ctx.findObject(XibId(menu_elem.get("id")))
        obj["IBMainMenu"] = menu_obj

    return obj
