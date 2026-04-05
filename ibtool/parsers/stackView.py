from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibNSNumber, NibString, NibMutableList, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def _build_visibility_map(obj, children):
    """Build NSMapTable for stack view container visibility priorities.
    Returns NibNil if no visibility data needed, or NSMapTable with entries
    for children whose explicitly-set priority differs from 1000."""
    from ..constants import vFlags as _vFlags
    vis_prios = obj.extraContext.get("visibility_priorities")
    # Check if any child is hidden
    import ctypes as _ctypes
    def _is_hidden(c):
        flags = c.get("NSvFlags") if hasattr(c, 'get') else None
        if flags is None or not isinstance(flags, int):
            return False
        return bool(_ctypes.c_uint32(flags).value & 0x80000000)
    has_hidden = any(_is_hidden(c) for c in children)
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
        if id(child) not in seen and _is_hidden(child) and cn == "NSStackView":
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


def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSStackView", elem, parent)
    distribution = elem.attrib.get("distribution")

    obj["NSSuperview"] = obj.xib_parent()

    parse_children(ctx, elem, obj)
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
