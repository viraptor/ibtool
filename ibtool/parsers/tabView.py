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

    with __handle_view_chain(ctx, obj):
        tab_view_items = NibMutableList([])
        initial_item_id = elem.attrib.get("initialItem")
        selected_item = None

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

        selected_view = selected_item.get("NSView") if selected_item else None
        for item_elem, tab_item in tab_item_objects:
            view = tab_item.get("NSView")
            if view is not None and view is not selected_view:
                view["NSNextResponder"] = NibNil()
                if view.get("NSSuperview") is not None:
                    del view["NSSuperview"]

        if selected_view:
            obj["NSSubviews"] = NibMutableList([selected_view])
        else:
            obj["NSSubviews"] = NibMutableList([])

        from ..parsers_base import _TabView_parse_children
        _TabView_parse_children(ctx, elem, obj, skip_tags={"tabViewItems"})

    obj["NSTabViewItems"] = tab_view_items
    if selected_item:
        obj["NSSelectedTabViewItem"] = selected_item
    obj["NSAllowTruncatedLabels"] = True
    obj["NSDrawsBackground"] = True
    obj.setIfEmpty("NSTvFlags", 0x0)

    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    x, y, w, h = obj.frame()
    if x == 0 and y == 0:
        obj["NSFrameSize"] = NibString.intern(f"{{{w}, {h}}}")
    else:
        obj["NSFrame"] = NibString.intern(f"{{{{{x}, {y}}}, {{{w}, {h}}}}}")

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
    identifier = elem.attrib.get("identifier", "")
    if identifier:
        obj["NSIdentifier"] = NibString.intern(identifier)

    from .helpers import makeSystemColor
    obj["NSColor"] = makeSystemColor("controlColor")

    view_elem = elem.find("view")
    if view_elem is not None:
        from . import view as view_parser
        view_obj = view_parser.parse(ctx, view_elem, tab_view)
        view_obj._parent = obj
        obj["NSView"] = view_obj

    return obj
