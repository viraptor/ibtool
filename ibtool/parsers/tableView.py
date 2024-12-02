from ..models import ArchiveContext, NibObject, NibMutableList, NibMutableDictionary, XibObject, NibNil
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_flags, __handle_view_chain
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None

    obj = make_xib_object(ctx, "NSTableView", elem, parent)

    obj["NSSuperview"] = parent

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)

    obj["NSSubviews"] = NibMutableList([])
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSAllowsTypeSelect"] = True
    obj["NSColumnAutoresizingStyle"] = 4
    obj["NSControlAllowsExpansionToolTips"] = True
    obj["NSControlContinuous"] = False
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlSendActionMask"] = 0
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlTextAlignment"] = 0
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlWritingDirection"] = 0
    obj["NSCornerView"] = NibObject("_NSCornerView", obj, {
    })
    obj["NSDataSource"] = NibNil()
    obj["NSDelegate"] = NibNil()
    obj["NSDraggingSourceMaskForLocal"] = -1
    obj["NSDraggingSourceMaskForNonLocal"] = 0
    obj["NSEnabled"] = True
    obj["NSIntercellSpacingHeight"] = 0.0
    obj["NSIntercellSpacingWidth"] = 17.0
    obj["NSRowHeight"] = 24.0
    obj["NSTableViewArchivedReusableViewsKey"] = NibMutableDictionary([])
    obj["NSTableViewDraggingDestinationStyle"] = 0
    obj["NSTableViewGroupRowStyle"] = 1
    obj["NSTvFlags"] = 0xffffffffd2600000

    return obj