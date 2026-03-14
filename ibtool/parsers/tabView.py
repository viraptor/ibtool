from ..models import ArchiveContext, NibObject, NibMutableList, XibObject, NibNil, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, parse_interfacebuilder_properties, __handle_view_chain, _xibparser_common_view_attributes, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTabView", elem, parent)
    obj["NSSuperview"] = parent

    parse_interfacebuilder_properties(ctx, elem, parent, obj)

    tab_view_items = NibMutableList([])
    initial_item_id = elem.attrib.get("initialItem")
    selected_item = None

    # Parse tabViewItems first to create the tab items
    tvi_elem = elem.find("tabViewItems")
    tab_item_objects = []
    if tvi_elem is not None:
        for item_elem in tvi_elem:
            if item_elem.tag == "tabViewItem":
                tab_item = _parse_tab_view_item(ctx, item_elem, obj)
                tab_item_objects.append((item_elem, tab_item))
                tab_view_items.addItem(tab_item)
                if item_elem.attrib.get("id") == initial_item_id:
                    selected_item = tab_item

    # The content view of the selected (initial) tab becomes the tab view's subview
    content_views = []
    for item_elem, tab_item in tab_item_objects:
        view = tab_item.get("NSView")
        if view is not None:
            content_views.append(view)

    if content_views:
        obj["NSSubviews"] = NibMutableList(content_views)
    else:
        obj["NSSubviews"] = NibMutableList([])

    # Parse remaining children (constraints, connections, etc.)
    for child in elem:
        if child.tag in ("tabViewItems", "rect", "autoresizingMask"):
            continue
        if child.tag == "constraints":
            from ..parsers_base import parse_children as pc
            pc(ctx, child, obj)

    obj["NSTabViewItems"] = tab_view_items
    if selected_item:
        obj["NSSelectedTabViewItem"] = selected_item
    obj["NSAllowTruncatedLabels"] = True
    obj["NSDrawsBackground"] = True
    obj.setIfEmpty("NSTvFlags", 0x0)

    font = NibObject("NSFont")
    font["NSName"] = NibString.intern(".AppleSystemUIFont")
    font["NSSize"] = 13.0
    font["NSfFlags"] = 0x414
    obj["NSFont"] = font

    obj["NSDoNotTranslateAutoresizingMask"] = True

    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    return obj


def _parse_tab_view_item(ctx, elem, tab_view):
    obj = XibObject(ctx, "NSTabViewItem", elem, tab_view)
    ctx.extraNibObjects.append(obj)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)

    obj["NSLabel"] = NibString.intern(elem.attrib.get("label", ""))
    obj["NSTabView"] = tab_view
    obj["NSIdentifier"] = NibString.intern(elem.attrib.get("identifier", ""))

    from .helpers import makeSystemColor
    obj["NSColor"] = makeSystemColor("controlColor")

    # Parse the view child
    view_elem = elem.find("view")
    if view_elem is not None:
        from . import view as view_parser
        view_obj = view_parser.parse(ctx, view_elem, tab_view)
        obj["NSView"] = view_obj

    return obj
