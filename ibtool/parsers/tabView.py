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

    # Auto-generate NSNextKeyView chain for each tab view item
    for _item_elem, tab_item in tab_item_objects:
        _build_key_view_loop(tab_item, obj)

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


def _collect_leaf_views(view):
    """Collect interactive leaf views from a view hierarchy with their positions."""
    leaves = []
    subviews = view.get("NSSubviews")
    if not subviews:
        return leaves
    for sv in subviews:
        cls = sv.originalclassname()
        if cls in ("NSCustomView",):
            leaves.extend(_collect_leaf_views(sv))
        elif cls in ("NSButton", "NSTextField", "NSPopUpButton", "NSSecureTextField",
                      "NSComboBox", "NSDatePicker", "NSSlider", "NSColorWell",
                      "NSStepper", "NSSegmentedControl", "NSSearchField",
                      "NSClassSwapper"):
            frame = sv.extraContext.get("NSFrame") or sv.extraContext.get("NSFrameSize")
            if frame:
                x = frame[0] if len(frame) == 4 else 0
                y = frame[1] if len(frame) == 4 else 0
            else:
                x, y = 0, 0
            leaves.append((sv, x, y))
    return leaves


def _build_key_view_loop(tab_item, tab_view):
    """Build auto-generated NSNextKeyView chain for a tab view item."""
    item_view = tab_item.get("NSView")
    if not item_view:
        return

    # Find the content container (first subview, usually a customView)
    container = None
    subviews = item_view.get("NSSubviews")
    if subviews and len(subviews) > 0:
        container = subviews[0] if len(subviews) == 1 else None

    if container is None:
        return

    leaves = _collect_leaf_views(container)
    if not leaves:
        return

    # Skip if any leaf already has NSNextKeyView from explicit connections
    if any(v[0].get("NSNextKeyView") for v in leaves):
        return

    # Sort: Y-descending, X-ascending (top-to-bottom, left-to-right in standard coords)
    leaves.sort(key=lambda v: (-v[2], v[1]))

    # Build chain: tabView → item_view → container → first → ... → last → tabView
    tab_view["NSNextKeyView"] = item_view
    item_view["NSNextKeyView"] = container
    container["NSNextKeyView"] = leaves[0][0]
    for i in range(len(leaves) - 1):
        leaves[i][0]["NSNextKeyView"] = leaves[i + 1][0]
    leaves[-1][0]["NSNextKeyView"] = tab_view


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
