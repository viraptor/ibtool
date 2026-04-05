from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibMutableList, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

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
        obj["NSStackViewBeginningContainer"] = NibObject("NSStackViewContainer", obj, {
            "IBNSClipsToBounds": 0,
            "IBNSLayoutMarginsGuide": NibNil(),
            "IBNSSafeAreaLayoutGuide": NibNil(),
            "NSDoNotTranslateAutoresizingMask": True,
            "NSFrameSize": NibString.intern("{0, 0}"),
            "NSNextResponder": NibNil(),
            "NSNibTouchBar": NibNil(),
            "NSStackViewContainerNonDroppedViews": NibMutableList([] if (distribution is None or obj.get("NSSubviews") is None) else obj["NSSubviews"]._items),
            "NSStackViewContainerStackView": obj,
            "NSStackViewContainerVisibilityPriorities": NibNil(),
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
