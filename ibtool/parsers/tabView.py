from ..models import ArchiveContext, NibObject, NibMutableList, XibObject, NibNil, NibString, NibLocalizableString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, parse_interfacebuilder_properties, __handle_view_chain, _xibparser_common_view_attributes, _xibparser_common_translate_autoresizing, makeSystemColor
from ..parsers_base import parse_children
from ..constants import vFlags
from . import view as view_parser


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

        if selected_item is None and tab_item_objects:
            selected_item = tab_item_objects[0][1]

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
    _build_scrollview_chain(obj, tab_item_objects, selected_item)

    obj["NSTabViewItems"] = tab_view_items
    if selected_item:
        obj["NSSelectedTabViewItem"] = selected_item
    obj["NSAllowTruncatedLabels"] = True
    if elem.attrib.get("drawsBackground", "YES") != "NO":
        obj["NSDrawsBackground"] = True
    tab_view_type = {
        None: 0,
        "topTabsBezelBorder": 0,
        "leftTabsBezelBorder": 1,
        "bottomTabsBezelBorder": 2,
        "rightTabsBezelBorder": 3,
        "noTabsBezelBorder": 4,
        "noTabsLineBorder": 5,
        "noTabsNoBorder": 6,
    }[elem.attrib.get("type")]
    obj.setIfEmpty("NSTvFlags", tab_view_type)
    if not obj.get("NSFont"):
        from .font import to_flags_val
        font = NibObject("NSFont")
        font["NSName"] = NibString.intern(".AppleSystemUIFont")
        font["NSSize"] = 11.0
        font["NSfFlags"] = to_flags_val(0x1c)
        obj["NSFont"] = font

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
                h = frame[3] if len(frame) == 4 else frame[1]
            else:
                x, y, h = 0, 0, 0
            leaves.append((sv, x, y, h))
    return leaves


def _sort_views_for_key_loop(leaves):
    """Sort views using overlapping-row grouping for NSNextKeyView chain.

    Views whose Y-ranges [y, y+h] overlap are grouped into the same "row".
    Within each row, views are sorted by X-ascending then Y-descending.
    Rows are ordered by their maximum top edge (y+h) descending.
    """
    if len(leaves) <= 1:
        return leaves

    n = len(leaves)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pi] = pj

    for i in range(n):
        y_i, h_i = leaves[i][2], leaves[i][3]
        for j in range(i + 1, n):
            y_j, h_j = leaves[j][2], leaves[j][3]
            if y_i < y_j + h_j and y_j < y_i + h_i:
                union(i, j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    for r in groups:
        groups[r].sort(key=lambda i: (leaves[i][1], -leaves[i][2]))

    sorted_groups = sorted(groups.values(),
                           key=lambda g: max(leaves[i][2] + leaves[i][3] for i in g),
                           reverse=True)

    return [leaves[i] for g in sorted_groups for i in g]


def _build_key_view_loop(tab_item, tab_view):
    """Build auto-generated NSNextKeyView chain for a tab view item."""
    item_view = tab_item.get("NSView")
    if not item_view:
        return

    container = None
    subviews = item_view.get("NSSubviews")
    if subviews and len(subviews) > 0:
        container = subviews[0] if len(subviews) == 1 else None

    if container is None:
        return

    leaves = _collect_leaf_views(container)
    if not leaves:
        return

    if any(v[0].get("NSNextKeyView") for v in leaves):
        return

    leaves = _sort_views_for_key_loop(leaves)

    tab_view["NSNextKeyView"] = item_view
    item_view["NSNextKeyView"] = container
    container["NSNextKeyView"] = leaves[0][0]
    for i in range(len(leaves) - 1):
        leaves[i][0]["NSNextKeyView"] = leaves[i + 1][0]
    leaves[-1][0]["NSNextKeyView"] = tab_view


def _find_scrollviews(view, found=None):
    """Walk a view hierarchy and collect all NSScrollView descendants in
    document order (depth-first via NSSubviews)."""
    if found is None:
        found = []
    if view is None or isinstance(view, NibNil):
        return found
    if hasattr(view, 'originalclassname') and view.originalclassname() == "NSScrollView":
        found.append(view)
        return found
    subviews = view.get("NSSubviews") if hasattr(view, 'get') else None
    if subviews:
        for sv in subviews:
            _find_scrollviews(sv, found)
    return found


def _hscroller_offscreen(hs):
    """A horizontal scroller is treated as offscreen-only (skipped in the
    middle of the key view chain, only used as a terminal SV→HS→nil edge)
    when its frame origin has a negative coordinate. Apple keeps offscreen
    scrollers in the nib for reuse but doesn't tab through them."""
    if hs is None or isinstance(hs, NibNil):
        return True
    f = hs.get("NSFrame")
    if f is not None and hasattr(f, "_text"):
        import re as _re
        m = _re.match(r'\{\{(-?\d+),\s*(-?\d+)\}', f._text)
        if m and (int(m.group(1)) < 0 or int(m.group(2)) < 0):
            return True
    return False


def _build_scrollview_chain(tab_view, tab_item_objects, selected_item):
    """Build the per-tab-item NSNextKeyView chain that walks scroll views.

    Apple's pattern (verified empirically):
      For each scroll view SV in tab item view tree (document order):
        SV.NextKeyView = HS  (terminal nil — only emitted when HS is hidden)
        CV.NextKeyView = DocView (already set by clipView parser)
        if HS hidden:  DocView.NextKeyView = VS
        else:          DocView.NextKeyView = HS; HS.NextKeyView = VS
        VS.NextKeyView = next sibling SV (or back to tab view for the last)
      For the selected/initial tab item additionally:
        TabView.NextKeyView = item view
        item view.NextKeyView = first SV
    """
    for tab_item in tab_item_objects if False else [t for _, t in tab_item_objects]:
        item_view = tab_item.get("NSView")
        if item_view is None or isinstance(item_view, NibNil):
            continue
        scrollviews = _find_scrollviews(item_view)
        if not scrollviews:
            continue
        for i, sv in enumerate(scrollviews):
            hs = sv.get("NSHScroller")
            vs = sv.get("NSVScroller")
            cv = sv.get("NSContentView")
            dv = cv.get("NSDocView") if cv is not None and not isinstance(cv, NibNil) else None
            hs_offscreen = _hscroller_offscreen(hs)
            if hs is not None and not isinstance(hs, NibNil) and hs_offscreen:
                sv["NSNextKeyView"] = hs
                hs["NSNextKeyView"] = NibNil()
            elif "NSNextKeyView" in sv.properties:
                del sv.properties["NSNextKeyView"]
            if dv is not None and not isinstance(dv, NibNil):
                if hs is not None and not isinstance(hs, NibNil) and not hs_offscreen:
                    dv["NSNextKeyView"] = hs
                    if vs is not None and not isinstance(vs, NibNil):
                        hs["NSNextKeyView"] = vs
                elif vs is not None and not isinstance(vs, NibNil):
                    dv["NSNextKeyView"] = vs
            if vs is not None and not isinstance(vs, NibNil):
                if i + 1 < len(scrollviews):
                    vs["NSNextKeyView"] = scrollviews[i + 1]
                elif tab_item is selected_item:
                    vs["NSNextKeyView"] = tab_view
        if tab_item is selected_item:
            tab_view["NSNextKeyView"] = item_view
            # Walk down through container subviews until reaching the first
            # scroll view, chaining each intermediate. The first scroll view
            # itself terminates at nil.
            chain_path = [item_view]
            cur = item_view
            while True:
                subs = cur.get("NSSubviews") if hasattr(cur, "get") else None
                if not subs:
                    break
                first_child = subs[0] if len(subs) > 0 else None
                if first_child is None:
                    break
                chain_path.append(first_child)
                if first_child is scrollviews[0]:
                    break
                cur = first_child
            for a, b in zip(chain_path, chain_path[1:]):
                a["NSNextKeyView"] = b
            # Only force a nil terminator on the first SV when it doesn't
            # already have an outgoing SV→HS edge (set when HS is offscreen).
            if "NSNextKeyView" not in chain_path[-1].properties:
                chain_path[-1]["NSNextKeyView"] = NibNil()


def _parse_tab_view_item(ctx, elem, tab_view):
    obj = XibObject(ctx, "NSTabViewItem", elem, tab_view)
    ctx.extraNibObjects.append(obj)
    if obj.xibid:
        ctx.addObject(obj.xibid, obj)

    label = elem.attrib.get("label", "")
    if ctx.isBaseLocalization and label:
        obj["NSLabel"] = NibLocalizableString(label, key=f"{elem.attrib.get('id', '')}.label")
    else:
        obj["NSLabel"] = NibString.intern(label)
    obj["NSTabView"] = tab_view
    identifier = elem.attrib.get("identifier", "")
    if identifier:
        obj["NSIdentifier"] = NibString.intern(identifier)

    obj["NSColor"] = makeSystemColor("controlColor")

    view_elem = elem.find("view")
    if view_elem is not None:
        view_obj = view_parser.parse(ctx, view_elem, tab_view)
        view_obj._parent = obj
        obj["NSView"] = view_obj

    return obj
