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

    # Auto-generate NSNextKeyView chain for the selected tab only — Apple
    # leaves background tabs without a chain.
    if selected_item is not None:
        _build_key_view_loop(selected_item, obj)
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


def _collect_leaf_views(view, offset_x=0, offset_y=0):
    """Collect interactive leaf views with their positions in the original view's coords.

    NSBox is collected as a leaf, and its NSContentView children are recursively
    collected with an added offset so their coordinates remain comparable to
    sibling leaves at the outer level.
    """
    leaves = []
    subviews = view.get("NSSubviews")
    if not subviews:
        return leaves
    for sv in subviews:
        cls = sv.originalclassname()
        if cls == "NSCustomView":
            leaves.extend(_collect_leaf_views(sv, offset_x, offset_y))
            continue
        if cls not in ("NSButton", "NSTextField", "NSPopUpButton", "NSSecureTextField",
                       "NSComboBox", "NSDatePicker", "NSSlider", "NSColorWell",
                       "NSStepper", "NSSegmentedControl", "NSSearchField",
                       "NSClassSwapper", "NSBox", "NSProgressIndicator"):
            continue
        frame = sv.extraContext.get("NSFrame") or sv.extraContext.get("NSFrameSize")
        if frame:
            x = frame[0] if len(frame) == 4 else 0
            y = frame[1] if len(frame) == 4 else 0
            w = frame[2] if len(frame) == 4 else frame[0]
            h = frame[3] if len(frame) == 4 else frame[1]
        else:
            x, y, w, h = 0, 0, 0, 0
        leaves.append((sv, x + offset_x, y + offset_y, h, w))
        if cls == "NSBox":
            content = sv.get("NSContentView")
            if content is not None and not isinstance(content, NibNil):
                cv_frame = content.extraContext.get("NSFrame") or content.extraContext.get("NSFrameSize")
                cv_x = cv_frame[0] if cv_frame and len(cv_frame) == 4 else 1
                cv_y = cv_frame[1] if cv_frame and len(cv_frame) == 4 else 1
                leaves.extend(_collect_leaf_views(content, offset_x + x + cv_x, offset_y + y + cv_y))
    return leaves


def _sort_views_for_key_loop(leaves):
    """Sort views into Apple's NSNextKeyView reading order.

    Two-level grouping:
      Row groups — views whose Y-ranges [y, y+h] overlap belong to the same
        row. Rows are ordered by max top edge (y+h) descending.
      Column subgroups — within a row, views whose X-ranges [x, x+w] overlap
        belong to the same column. Columns are ordered by min x ascending,
        and views inside a column are ordered top-down (y descending).
    """
    if len(leaves) <= 1:
        return leaves

    n = len(leaves)

    def group_by_overlap(indices, axis_low, axis_size):
        """Union-find groups of indices whose [axis_low, axis_low+axis_size]
        ranges overlap (open interval — touching edges don't count)."""
        parent = list(range(len(indices)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i, j):
            pi, pj = find(i), find(j)
            if pi != pj:
                parent[pi] = pj

        for ii in range(len(indices)):
            a, sa = axis_low(indices[ii]), axis_size(indices[ii])
            for jj in range(ii + 1, len(indices)):
                b, sb = axis_low(indices[jj]), axis_size(indices[jj])
                if a < b + sb and b < a + sa:
                    union(ii, jj)

        buckets: dict[int, list[int]] = {}
        for ii in range(len(indices)):
            buckets.setdefault(find(ii), []).append(indices[ii])
        return list(buckets.values())

    rows = group_by_overlap(list(range(n)),
                            lambda i: leaves[i][2],
                            lambda i: leaves[i][3])
    rows.sort(key=lambda g: max(leaves[i][2] + leaves[i][3] for i in g), reverse=True)

    def _is_box(i):
        return leaves[i][0].originalclassname() == "NSBox"

    result = []
    for row in rows:
        cols = group_by_overlap(row,
                                lambda i: leaves[i][1],
                                lambda i: leaves[i][4])
        cols.sort(key=lambda g: min(leaves[i][1] for i in g))
        for col in cols:
            # When a column contains an NSBox it's almost always a wide row
            # anchor that x-overlaps every neighbouring control. Apple places
            # the box first then walks the rest left-to-right rather than
            # top-down — the controls inside the row band read left-to-right.
            if any(_is_box(i) for i in col):
                boxes = sorted([i for i in col if _is_box(i)], key=lambda i: -leaves[i][2])
                others = sorted([i for i in col if not _is_box(i)], key=lambda i: (leaves[i][1], -leaves[i][2]))
                result.extend(boxes + others)
            else:
                col.sort(key=lambda i: -leaves[i][2])
                result.extend(col)

    return [leaves[i] for i in result]


def _build_key_view_loop(tab_item, tab_view):
    """Build auto-generated NSNextKeyView chain for a tab view item."""
    item_view = tab_item.get("NSView")
    if not item_view:
        return

    subviews = item_view.get("NSSubviews")
    if not subviews:
        return

    if len(subviews) == 1:
        container = subviews[0]
    else:
        container = item_view

    leaves = _collect_leaf_views(container)
    if not leaves:
        return

    if any(v[0].get("NSNextKeyView") for v in leaves):
        return

    leaves = _sort_views_for_key_loop(leaves)

    tab_view["NSNextKeyView"] = item_view
    if container is not item_view:
        item_view["NSNextKeyView"] = container
    container["NSNextKeyView"] = leaves[0][0]

    def _set_next(view, target):
        # NSBox keeps its own NSNextKeyView=nil; the chain continuation lives
        # on its NSContentView so the box acts as a transparent waypoint.
        if view.originalclassname() == "NSBox":
            view["NSNextKeyView"] = NibNil()
            content = view.get("NSContentView")
            if content is not None:
                content["NSNextKeyView"] = target
        else:
            view["NSNextKeyView"] = target

    for i in range(len(leaves) - 1):
        _set_next(leaves[i][0], leaves[i + 1][0])
    _set_next(leaves[-1][0], tab_view)
    # Sliders don't continue the key view chain — predecessors still point at
    # them but their own next is nil.
    for leaf in leaves:
        if leaf[0].originalclassname() == "NSSlider":
            leaf[0]["NSNextKeyView"] = NibNil()


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
