from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibMutableList, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSStackView", elem, parent)
    distribution = elem.attrib.get("distribution")

    obj["NSSuperview"] = obj.xib_parent()

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)
    
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    if obj.get("NSSubviews") is not None:
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
    obj["NSStackViewDetachesHiddenViews"] = elem.attrib.get("detachesHiddenViews", "NO") == "YES"
    obj["NSStackViewEdgeInsets.bottom"] = NibFloat(0.0)
    obj["NSStackViewEdgeInsets.left"] = NibFloat(0.0)
    obj["NSStackViewEdgeInsets.right"] = NibFloat(0.0)
    obj["NSStackViewEdgeInsets.top"] = NibFloat(0.0)
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
