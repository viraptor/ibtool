from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibMutableList
from xml.etree.ElementTree import Element
from .helpers import make_xib_object
from ..parsers_base import parse_children

SYSTEM_MENUS = {
    "apple": "_NSAppleMenu",
    "main": "_NSMainMenu",
    "font": "_NSFontMenu",
    "services": "_NSServicesMenu",
    "recentDocuments": "_NSRecentDocumentsMenu",
    "window": "_NSWindowsMenu",
    "help": "_NSHelpMenu",
}

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSMenu", elem, parent, view_attributes=False)
    parse_children(ctx, elem, obj)
    obj["NSTitle"] = elem.attrib.get("title", NibNil())
    if elem.attrib.get("key") == "submenu":
        parent["NSAction"] = NibString.intern("submenuAction:")
        obj.setIfEmpty("NSMenuItems", NibMutableList())
    if parent and parent.originalclassname() == "NSMenuItem":
        parent["NSTarget"] = obj
        parent["NSSubmenu"] = obj
    elif parent and parent.originalclassname() == "NSPopUpButtonCell":
        parent["NSMenu"] = obj
        parent["NSMenuItem"] = obj["NSMenuItems"]._items[0]
        parent["NSUsesItemFromMenu"] = True
        for item in obj["NSMenuItems"]._items:
            item["NSAction"] = NibString.intern("_popUpItemAction:")
            item["NSTarget"] = parent
            item["NSKeyEquivModMask"] = 0x100000
    obj.setIfNotDefault("NSNoAutoenable", elem.attrib.get("autoenablesItems", "YES") == "NO", False)
    if system_menu := elem.attrib.get("systemMenu"):
        if system_menu not in SYSTEM_MENUS:
            raise Exception(f"Unknown system menu: {system_menu}")
        obj["NSName"] = NibString.intern(SYSTEM_MENUS[system_menu])
    return obj
