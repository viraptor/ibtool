from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain
from ..parsers_base import parse_children
from ..constants import vFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSOutlineView", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    
    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSAllowsTypeSelect"] = True
    obj["NSColumnAutoresizingStyle"] = 1
    obj["NSControlAllowsExpansionToolTips"] = True
    obj["NSControlContinuous"] = False
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlTextAlignment"] = 0
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = 0
    obj["NSCornerView"] = NibObject("_NSCornerView", obj, {
        "IBNSClipsToBounds": 0,
        "IBNSLayoutMarginsGuide": NibNil(),
        "IBNSSafeAreaLayoutGuide": NibNil(),
        "NSFrameSize": NibString.intern("{15, 28}"),
        "NSNextResponder": NibNil(),
        "NSNibTouchBar": NibNil(),
        "NSViewWantsBestResolutionOpenGLSurface": True,
        "NSvFlags": 256,
    })
    obj["NSDataSource"] = NibNil()
    obj["NSDelegate"] = NibNil()
    obj["NSDraggingSourceMaskForLocal"] = -1
    obj["NSDraggingSourceMaskForNonLocal"] = 0
    obj["NSEnabled"] = True
    obj["NSControlSendActionMask"] = 0
    obj["NSIntercellSpacingHeight"] = 2.0
    obj["NSIntercellSpacingWidth"] = 3.0
    obj["NSOutineViewStronglyReferencesItems"] = True
    obj["NSOutlineViewIndentationPerLevelKey"] = NibFloat(16.0)
    obj["NSRowHeight"] = 34.0
    obj["NSTableViewDraggingDestinationStyle"] = 0
    obj["NSTableViewGroupRowStyle"] = 1
    obj["NSTvFlags"] = 440434688

    return obj
