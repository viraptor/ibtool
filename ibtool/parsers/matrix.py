from ..models import ArchiveContext, NibObject, XibObject, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_view_attributes, makeSystemColor, __xibparser_cell_options
from ..parsers_base import parse_children
from ..constants import CellFlags, CellFlags2, CONTROL_SIZE_MAP2

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSMatrix", elem, parent, view_attributes=False)
    _xibparser_common_view_attributes(ctx, elem, parent, obj, topLevelView=(parent is None))
    parse_children(ctx, elem, obj)
    obj["NSCellClass"] = NibString.intern("NSActionCell")
    obj["NSCellIsDiscardable"] = True
    obj["NSCellBackgroundColor"] = makeSystemColor("controlColor")
    obj["NSControlContinuous"] = False
    obj["NSControlLineBreakMode"] = 0
    obj["NSAllowsLogicalLayoutDirection"] = False
    obj["NSControlUsesSingleLineMode"] = False
    obj["NSControlSize"] = 0
    obj["NSControlSize2"] = 0
    obj["NSControlTextAlignment"] = 0
    obj["NSControlWritingDirection"] = 0
    obj["NSEnabled"] = True
    obj["NSMatrixFlags"] = 0x44000000 # todo
    obj["NSControlSendActionMask"] = 0
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSSelectedCol"] = -1
    obj["NSSelectedRow"] = -1
    obj["NSSuperview"] = parent
    obj["NSCell"] = NibObject("NSActionCell", None, {
        "NSCellFlags": CellFlags.DONT_ACT_ON_MOUSE_UP,
        "NSCellFlags2": CellFlags2.UNKNOWN_MATRIX_CELL,
        "NSControlSize2": CONTROL_SIZE_MAP2[None],
    })
    return obj
