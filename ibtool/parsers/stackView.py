from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibNSNumber, NibString, NibMutableList, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags
from ..text_measure import compute_intrinsic_width, _available, _is_hidden
import ctypes

def _build_visibility_map(obj, children):
    """Build NSMapTable for stack view container visibility priorities.
    Returns NibNil if no visibility data needed, or NSMapTable with entries
    for children whose explicitly-set priority differs from 1000."""
    vis_prios = obj.extraContext.get("visibility_priorities")
    def _child_hidden(c):
        flags = c.get("NSvFlags") if hasattr(c, 'get') else None
        if flags is None or not isinstance(flags, int):
            return False
        return bool(ctypes.c_uint32(flags).value & 0x80000000)
    has_hidden = any(_child_hidden(c) for c in children)
    if not has_hidden:
        return NibNil()
    # Build map entries: explicit non-1000 priorities + hidden children
    map_entries = []
    seen = set()
    if vis_prios is not None:
        for i, child in enumerate(children):
            prio = vis_prios[i] if i < len(vis_prios) else 1000
            if prio != 1000:
                map_entries.append(child)
                map_entries.append(NibNSNumber(prio))
                seen.add(id(child))
    # Add hidden stack view children not already in the map
    for child in children:
        cn = child.originalclassname() if hasattr(child, 'originalclassname') else (child.classname() if hasattr(child, 'classname') else '')
        if id(child) not in seen and _child_hidden(child) and cn == "NSStackView":
            map_entries.append(child)
            map_entries.append(NibNSNumber(0))
            seen.add(id(child))
    map_table = NibObject("NSMapTable")
    map_table["$0"] = 517
    map_table["$1"] = 0
    if map_entries:
        for j in range(0, len(map_entries), 2):
            map_table[f"${j+2}"] = map_entries[j]
            map_table[f"${j+3}"] = map_entries[j+1]
        map_table[f"${len(map_entries)+2}"] = NibNil()
    else:
        map_table["$2"] = NibNil()
    map_table["NS.count"] = len(map_entries) // 2
    return map_table


def _relayout_children(ctx, elem, obj):
    """In storyboard mode, recalculate child frames based on intrinsic content sizes.
    Only applies when all visible children have computable intrinsic widths."""
    if not _available or not ctx.isStoryboard:
        return

    distribution = elem.attrib.get("distribution")
    if distribution is None:
        return

    orientation = elem.attrib.get("orientation", "horizontal")
    spacing = float(elem.attrib.get("spacing", 8.0))
    detaches = elem.attrib.get("detachesHiddenViews", "NO") == "YES"

    subviews_elem = None
    for child in elem:
        if child.tag == "subviews":
            subviews_elem = child
            break
    if subviews_elem is None:
        return

    child_elems = [c for c in subviews_elem if c.tag not in ("constraint", "constraints")]
    subview_items = obj.get("NSSubviews")
    if subview_items is None:
        return
    nib_children = subview_items._items
    if len(child_elems) != len(nib_children):
        return

    is_horizontal = orientation == "horizontal"
    sv_frame = obj.frame()
    total_size = sv_frame[2] if is_horizontal else sv_frame[3]

    visible = []
    all_known = True
    any_changed = False
    for i, ce in enumerate(child_elems):
        hidden = _is_hidden(ce)
        if hidden and detaches:
            continue
        if hidden:
            continue
        iw = compute_intrinsic_width(ce)
        if iw is None:
            all_known = False
        else:
            xib_w = nib_children[i].frame()[2]
            if iw != xib_w:
                any_changed = True
        visible.append((i, ce, nib_children[i], iw))

    if not visible or not any_changed:
        return

    if is_horizontal and all_known and distribution == "equalSpacing":
        _relayout_horizontal(visible, distribution, spacing, total_size)
    elif is_horizontal and distribution == "fillProportionally":
        _relayout_fill_proportionally(visible, spacing, total_size)


def _relayout_horizontal(visible, distribution, spacing, total_width):
    n = len(visible)
    intrinsic = [iw for (i, ce, nc, iw) in visible]
    total_content = sum(intrinsic)
    remaining = total_width - total_content
    if n > 1:
        gap = remaining / (n - 1)
    else:
        gap = 0
    pos = 0
    for vi, (i, ce, nib_child, iw) in enumerate(visible):
        old_w = nib_child.frame()[2]
        nib_child.set_nib_frame(int(pos), 0, intrinsic[vi], nib_child.frame()[3])
        if ce.tag == "stackView" and intrinsic[vi] != old_w:
            _cascade_fill_relayout(ce, nib_child, intrinsic[vi])
        pos += intrinsic[vi] + gap


def _relayout_fill_proportionally(visible, spacing, total_width):
    """After intrinsic width fixes by parsers, adjust the flexible child to absorb any width delta."""
    n = len(visible)
    if n <= 1:
        return
    # Compute delta: how much total children width changed from XIB values
    delta = 0
    for vi, (i, ce, nib_child, iw) in enumerate(visible):
        rect_elem = ce.find("rect[@key='frame']")
        if rect_elem is None:
            continue
        orig_w = int(rect_elem.get("width", "0"))
        cur_w = nib_child.frame()[2]
        delta += cur_w - orig_w
    if delta == 0:
        return
    # Find the flexible child (a fill stack view, or the largest non-intrinsic child)
    flex_idx = None
    for vi, (i, ce, nib_child, iw) in enumerate(visible):
        if ce.tag == "stackView" and ce.get("distribution") == "fill":
            flex_idx = vi
            break
    if flex_idx is None:
        return
    # Adjust flexible child width
    _, flex_ce, flex_child, _ = visible[flex_idx]
    fc_frame = flex_child.frame()
    new_w = fc_frame[2] - delta
    if new_w <= 0:
        return
    # Shift positions: children after any changed child need position adjustment
    shift = 0
    for vi, (i, ce, nib_child, iw) in enumerate(visible):
        f = nib_child.frame()
        rect_elem = ce.find("rect[@key='frame']")
        orig_w = int(rect_elem.get("width", "0")) if rect_elem is not None else f[2]
        child_delta = f[2] - orig_w
        if vi == flex_idx:
            nib_child.set_nib_frame(int(f[0] + shift), f[1], int(new_w), f[3])
            _cascade_fill_relayout(flex_ce, nib_child, int(new_w))
            shift += (new_w - f[2])
        elif shift != 0:
            nib_child.set_nib_frame(int(f[0] + shift), f[1], f[2], f[3])
        if vi != flex_idx:
            shift += child_delta


def _cascade_fill_relayout(sv_elem, sv_obj, new_width):
    """After a parent sets a fill stack child's width, update its children."""
    dist = sv_elem.get("distribution")
    if dist != "fill":
        return
    orientation = sv_elem.get("orientation", "horizontal")
    if orientation != "horizontal":
        return
    spacing = float(sv_elem.get("spacing", 8.0))
    detaches = sv_elem.get("detachesHiddenViews", "YES") == "YES"

    subviews_elem = None
    for child in sv_elem:
        if child.tag == "subviews":
            subviews_elem = child
            break
    if subviews_elem is None:
        return

    child_elems = [c for c in subviews_elem if c.tag not in ("constraint", "constraints")]
    subview_items = sv_obj.get("NSSubviews")
    if subview_items is None:
        return
    nib_children = subview_items._items
    if len(child_elems) != len(nib_children):
        return

    visible = []
    for i, ce in enumerate(child_elems):
        if _is_hidden(ce) and detaches:
            continue
        if _is_hidden(ce):
            continue
        iw = compute_intrinsic_width(ce)
        if iw is None:
            return
        visible.append((i, ce, nib_children[i], iw))

    if not visible:
        return

    n = len(visible)
    total_spacing = spacing * (n - 1)
    available = new_width - total_spacing

    fill_idx = 0
    min_hug = float('inf')
    for vi, (i, ce, nib_child, iw) in enumerate(visible):
        hug = float(ce.get("horizontalHuggingPriority", "250"))
        if hug < min_hug:
            min_hug = hug
            fill_idx = vi

    # Compute width delta from original stack width
    rect_elem = sv_elem.find("rect[@key='frame']")
    old_width = int(rect_elem.get("width", "0")) if rect_elem is not None else sv_obj.frame()[2]
    width_delta = new_width - old_width
    if width_delta == 0:
        return
    # Set non-fill children to intrinsic widths, accumulate their width changes
    non_fill_delta = 0
    for vi, (i, ce, nib_child, iw) in enumerate(visible):
        if vi == fill_idx:
            continue
        f = nib_child.frame()
        if f[2] != iw:
            non_fill_delta += iw - f[2]
            nib_child.set_nib_frame(f[0], f[1], int(iw), f[3])
    # Fill target absorbs: total delta minus what non-fill children consumed
    fill_change = width_delta - non_fill_delta
    _, _, fill_child, _ = visible[fill_idx]
    fc = fill_child.frame()
    new_fill_w = fc[2] + fill_change
    if new_fill_w < 0:
        new_fill_w = 0
    fill_child.set_nib_frame(fc[0], fc[1], int(new_fill_w), fc[3])
    # Shift positions: accumulate width changes and shift subsequent children
    shift = 0
    for vi, (i, ce, nib_child, iw) in enumerate(visible):
        f = nib_child.frame()
        if shift != 0:
            nib_child.set_nib_frame(int(f[0] + shift), f[1], f[2], f[3])
        rect_el = ce.find("rect[@key='frame']")
        orig_w = int(rect_el.get("width", "0")) if rect_el is not None else f[2]
        shift += f[2] - orig_w


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSStackView", elem, parent)
    distribution = elem.attrib.get("distribution")

    obj["NSSuperview"] = obj.xib_parent()

    parse_children(ctx, elem, obj)

    if distribution is not None:
        _relayout_children(ctx, elem, obj)

    x, y, w, h = obj.frame()
    if x == 0 and y == 0:
        obj["NSFrameSize"] = NibString.intern(f"{{{w}, {h}}}")
    else:
        obj["NSFrame"] = NibString.intern(f"{{{{{x}, {y}}}, {{{w}, {h}}}}}")
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if obj.get("NSSubviews") is not None:
        # Priority decreases by 10 for each ancestor view above the
        # immediate parent, up to the window content view or cell view root.
        ancestor_depth = 0
        immediate_parent = obj.xib_parent()
        is_in_cellview = (immediate_parent is not None and hasattr(immediate_parent, 'originalclassname')
                          and immediate_parent.originalclassname() == "NSTableCellView")
        if not is_in_cellview:
            p = immediate_parent
            if p is not None:
                p = p.xib_parent() if hasattr(p, 'xib_parent') else None
            while p is not None:
                if hasattr(p, 'extraContext') and p.extraContext.get("is_window_content_view"):
                    break
                if hasattr(p, 'originalclassname') and p.originalclassname() in ("NSWindowTemplate", "NSTableCellView"):
                    break
                ancestor_depth += 1
                p = p.xib_parent() if hasattr(p, 'xib_parent') else None
        priority = 999990 - ancestor_depth * 10
        ctx.connections.insert(0, NibObject("NSNibConnector", None, {
            "NSSource": obj,
            "NSLabel": NibString.intern(f"Encoding NSStackView requires being decoded before other connections with an early decoding order priority of {priority}."),
        }))
        if obj.extraContext.get("NSDoNotTranslateAutoresizingMask"):
            obj["NSDoNotTranslateAutoresizingMask"] = True
        for child in obj["NSSubviews"]._items:
            if hasattr(child, 'extraContext') and child.extraContext.get("NSDoNotTranslateAutoresizingMask"):
                child["NSDoNotTranslateAutoresizingMask"] = True
        children = [] if (distribution is None or obj.get("NSSubviews") is None) else obj["NSSubviews"]._items
        vis_prio = _build_visibility_map(obj, children)
        obj["NSStackViewBeginningContainer"] = NibObject("NSStackViewContainer", obj, {
            "IBNSClipsToBounds": 0,
            "IBNSLayoutMarginsGuide": NibNil(),
            "IBNSSafeAreaLayoutGuide": NibNil(),
            "NSDoNotTranslateAutoresizingMask": True,
            "NSFrameSize": NibString.intern("{0, 0}"),
            "NSNextResponder": NibNil(),
            "NSNibTouchBar": NibNil(),
            "NSStackViewContainerNonDroppedViews": NibMutableList(children),
            "NSStackViewContainerStackView": obj,
            "NSStackViewContainerVisibilityPriorities": vis_prio,
            "NSStackViewContainerViewToCustomAfterSpaceMap": NibNil(),
            "NSViewWantsBestResolutionOpenGLSurface": True,
            "NSvFlags": vFlags.AUTORESIZES_SUBVIEWS,
        })
    h = elem.attrib.get("horizontalHuggingPriority", "250")
    v = elem.attrib.get("verticalHuggingPriority", "250")
    if h != "250" or v != "250":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    if sv_identifier := elem.attrib.get("identifier"):
        obj["NSReuseIdentifierKey"] = NibString.intern(sv_identifier)
    obj["NSStackViewDetachesHiddenViews"] = elem.attrib.get("detachesHiddenViews", "NO") == "YES"
    obj.setIfEmpty("NSStackViewEdgeInsets.bottom", NibFloat(0.0))
    obj.setIfEmpty("NSStackViewEdgeInsets.left", NibFloat(0.0))
    obj.setIfEmpty("NSStackViewEdgeInsets.right", NibFloat(0.0))
    obj.setIfEmpty("NSStackViewEdgeInsets.top", NibFloat(0.0))
    obj["NSStackViewHasFlatViewHierarchy"] = True
    obj["NSStackViewHorizontalClippingResistance"] = NibFloat(float(elem.attrib.get("horizontalClippingResistancePriority", "1000")))
    obj["NSStackViewHorizontalHugging"] = NibFloat(float(elem.attrib.get("horizontalStackHuggingPriority", 0)))
    obj["NSStackViewVerticalClippingResistance"] = NibFloat(float(elem.attrib.get("verticalClippingResistancePriority", "1000")))
    obj["NSStackViewVerticalHugging"] = NibFloat(float(elem.attrib.get("verticalStackHuggingPriority")))
    obj["NSStackViewSpacing"] = NibFloat(float(elem.attrib.get("spacing", 8.0)))
        
    if alignment := elem.attrib.get("alignment"):
        obj["NSStackViewAlignment"] = {
            "top": 3,
            "bottom": 4,
            "leading": 5,
            "centerX": 9,
            "centerY": 10,
            "firstBaseline": 12,
            "baseline": 11,
            "trailing": 6,
        }[alignment]

        obj["NSStackViewSecondaryAlignment"] = {
            "top": 1,
            "bottom": 4,
            "leading": 1,
            "centerX": 3,
            "centerY": 3,
            "firstBaseline": 2,
            "baseline": 5,
            "trailing": 4,
        }[alignment]

    if distribution is not None:
        obj["NSStackViewdistribution"] = {
            "fill": 0,
            "fillEqually": 1,
            "fillProportionally": 2,
            "equalSpacing": 3,
            "equalCentering": 4,
        }[distribution]

    obj["NSStackViewOrientation"] = {
        "horizontal": 0,
        "vertical": 1,
    }[elem.attrib.get("orientation", "horizontal")]

    if distribution is None:
        obj["NSStackViewHasEqualSpacing"] = False
        obj["NSStackViewMiddleContainer"] = NibObject("NSStackViewContainer", None, {
            "IBNSClipsToBounds": 0,
            "IBNSLayoutMarginsGuide": NibNil(),
            "IBNSSafeAreaLayoutGuide": NibNil(),
            "NSDoNotTranslateAutoresizingMask": True,
            "NSFrameSize": NibString.intern("{0, 0}"),
            "NSNextResponder": NibNil(),
            "NSNibTouchBar": NibNil(),
            "NSStackViewContainerNonDroppedViews": NibMutableList([]),
            "NSStackViewContainerStackView": obj,
            "NSStackViewContainerViewToCustomAfterSpaceMap": NibNil(),
            "NSStackViewContainerVisibilityPriorities": NibNil(),
            "NSViewWantsBestResolutionOpenGLSurface": True,
            "NSvFlags": vFlags.AUTORESIZES_SUBVIEWS,
        })
        obj["NSStackViewEndContainer"] = NibObject("NSStackViewContainer", None, {
            "IBNSClipsToBounds": 0,
            "IBNSLayoutMarginsGuide": NibNil(),
            "IBNSSafeAreaLayoutGuide": NibNil(),
            "NSDoNotTranslateAutoresizingMask": True,
            "NSFrameSize": NibString.intern("{0, 0}"),
            "NSNextResponder": NibNil(),
            "NSNibTouchBar": NibNil(),
            "NSStackViewContainerNonDroppedViews": NibMutableList([]),
            "NSStackViewContainerStackView": obj,
            "NSStackViewContainerViewToCustomAfterSpaceMap": NibNil(),
            "NSStackViewContainerVisibilityPriorities": NibNil(),
            "NSViewWantsBestResolutionOpenGLSurface": True,
            "NSvFlags": vFlags.AUTORESIZES_SUBVIEWS,
        })
        obj["NSSubviews"] = NibMutableList([]) # actually empty in practice
    elif distribution == "equalSpacing":
        obj["NSStackViewHasEqualSpacing"] = True

    return obj
