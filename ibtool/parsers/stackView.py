from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibMutableList, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSStackView", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)

    obj["NSStackViewAlignment"] = 10
    obj["NSStackViewBeginningContainer"] = NibObject("NSStackViewContainer", obj, {
        "IBNSClipsToBounds": 0,
        "IBNSLayoutMarginsGuide": NibNil(),
        "IBNSSafeAreaLayoutGuide": NibNil(),
        "NSDoNotTranslateAutoresizingMask": True,
        "NSFrameSize": NibString.intern("{0, 0}"),
        "NSNextResponder": NibNil(),
        "NSNibTouchBar": NibNil(),
        "NSStackViewContainerNonDroppedViews": NibMutableList(obj["NSSubviews"]._items),
        "NSStackViewContainerStackView": obj,
        "NSStackViewContainerVisibilityPriorities": NibNil(),
        "NSStackViewContainerViewToCustomAfterSpaceMap": NibNil(),
        "NSViewWantsBestResolutionOpenGLSurface": True,
        "NSvFlags": vFlags.AUTORESIZES_SUBVIEWS,
    })
    obj["NSStackViewDetachesHiddenViews"] = True
    obj["NSStackViewEdgeInsets.bottom"] = NibFloat(0.0)
    obj["NSStackViewEdgeInsets.left"] = NibFloat(0.0)
    obj["NSStackViewEdgeInsets.right"] = NibFloat(0.0)
    obj["NSStackViewEdgeInsets.top"] = NibFloat(0.0)
    obj["NSStackViewHasFlatViewHierarchy"] = True
    obj["NSStackViewHorizontalClippingResistance"] = NibFloat(float(elem.attrib.get("horizontalClippingResistancePriority", 0)))
    obj["NSStackViewHorizontalHugging"] = NibFloat(float(elem.attrib.get("horizontalStackHuggingPriority", 0)))
    obj["NSStackViewVerticalClippingResistance"] = NibFloat(float(elem.attrib.get("verticalClippingResistancePriority", "1000")))
    obj["NSStackViewVerticalHugging"] = NibFloat(float(elem.attrib.get("verticalStackHuggingPriority")))
    obj["NSStackViewOrientation"] = 0
    obj["NSStackViewSecondaryAlignment"] = 3
    obj["NSStackViewSpacing"] = NibFloat(1.0)
    obj["NSStackViewdistribution"] = {
        "fillProportionally": 2,
        "fill": 9999,
    }[elem.attrib.get("distribution")]

    return obj
