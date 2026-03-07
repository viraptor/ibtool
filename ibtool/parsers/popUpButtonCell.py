from ..models import ArchiveContext, NibObject, XibObject, NibString, XibId
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_options, __xibparser_button_flags
from ..parsers_base import parse_children
from ..constants import ButtonFlags, CellFlags, BEZEL_STYLE_MAP, FontFlags
from .font import to_flags_val

PREFERRED_EDGE_MAP = {
    None: 1,
    "minX": 0,
    "minY": 1,
    "maxX": 2,
    "maxY": 3,
}

ARROW_POSITION_MAP = {
    "arrowAtCenter": 1,
    "arrowAtBottom": 2,
    "noArrow": 2,
}

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None
    obj = make_xib_object(ctx, "NSPopUpButtonCell", elem, parent, view_attributes=False)
    if obj.get("NSTag") is not None:
        del obj["NSTag"]  # tag on cells is for item selection, not NSTag
    parse_children(ctx, elem, obj)
    __xibparser_cell_options(elem, obj, parent)
    obj["NSAlternateContents"] = NibString.intern("")
    obj["NSAltersState"] = True
    obj["NSControlView"] = parent
    obj["NSKeyEquivalent"] = NibString.intern("")
    obj["NSPeriodicDelay"] = 400
    obj["NSPeriodicInterval"] = 75

    pulls_down = elem.attrib.get("pullsDown") == "YES"

    __xibparser_button_flags(elem, obj, parent)
    obj.flagsOr("NSCellFlags", CellFlags.BEZELED)

    obj["NSBezelStyle"] = BEZEL_STYLE_MAP.get(elem.attrib.get("bezelStyle"))
    # Clear BEZEL from button flags for popup button cells
    if obj.get("NSButtonFlags") is not None:
        obj["NSButtonFlags"] = obj["NSButtonFlags"] & ~ButtonFlags.BEZEL

    # For push-type popup button cells, override NSAuxButtonType to 0
    if elem.attrib.get("type", "push") == "push":
        obj["NSAuxButtonType"] = 0

    if pulls_down:
        obj["NSPullDown"] = True
        obj["NSContents"] = NibString.intern("")
        obj["NSPreferredEdge"] = 1
        obj["NSArrowPosition"] = 2
        # Hide the first menu item for pulldown buttons
        if obj.get("NSMenu"):
            menu_items = obj["NSMenu"]["NSMenuItems"]._items
            if menu_items:
                menu_items[0]["NSIsHidden"] = True
    else:
        obj["NSPreferredEdge"] = PREFERRED_EDGE_MAP.get(elem.attrib.get("preferredEdge"), 1)
        obj["NSArrowPosition"] = 2  # default for popups

        # Set selected item from menu
        selected_item_id = elem.attrib.get("selectedItem")
        if selected_item_id and obj.get("NSMenu"):
            menu_items = obj["NSMenu"]["NSMenuItems"]._items
            selected_obj = ctx.findObject(XibId(selected_item_id))
            for i, item in enumerate(menu_items):
                if item is selected_obj:
                    obj["NSMenuItem"] = item
                    if i > 0:
                        obj["NSSelectedIndex"] = i
                    obj["NSContents"] = NibString.intern(elem.attrib.get("title", ""))
                    break
        if obj.get("NSContents") is None:
            obj["NSContents"] = NibString.intern(elem.attrib.get("title", ""))

    if arrow_pos := elem.attrib.get("arrowPosition"):
        obj["NSArrowPosition"] = ARROW_POSITION_MAP[arrow_pos]

    # Popup button cells use ROLE_TITLE_BAR_FONT for their font
    if obj.get("NSSupport") is not None:
        obj["NSSupport"]["NSfFlags"] = to_flags_val(FontFlags.ROLE_TITLE_BAR_FONT.value)

    obj["NSMenuItemRespectAlignment"] = True

    parent["NSCell"] = obj
    return obj
