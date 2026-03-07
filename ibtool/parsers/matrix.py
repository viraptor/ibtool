from ..models import ArchiveContext, NibObject, XibObject, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_view_attributes, makeSystemColor, __xibparser_cell_options
from ..parsers_base import parse_children
from ..constants import CellFlags, CellFlags2, cvFlags

MATRIX_MODE_MAP = {
    None: 2,       # default is radio
    "track": 0,
    "highlight": 1,
    "radio": 2,
    "list": 3,
}

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
    obj["NSControlTextAlignment"] = 0
    obj["NSControlWritingDirection"] = 0
    obj["NSEnabled"] = True

    # Compute NSMatrixFlags
    mode = MATRIX_MODE_MAP.get(elem.attrib.get("mode"), 2)
    matrix_flags = 0
    if mode & 2:
        matrix_flags |= 0x40000000
    if mode & 1:
        matrix_flags |= 0x01000000
    if elem.attrib.get("selectionByRect", "YES") != "NO":
        matrix_flags |= 0x04000000
    if elem.attrib.get("drawsBackground") == "YES":
        matrix_flags |= 0x80000000
        # Propagate drawsBackground to parent clip view
        if parent.originalclassname() == "NSClipView":
            parent.flagsOr("NScvFlags", cvFlags.DRAW_BACKGROUND)
    # Sign-extend to match signed 32-bit storage
    if matrix_flags >= 0x80000000:
        matrix_flags -= 0x100000000
    obj["NSMatrixFlags"] = matrix_flags

    obj["NSControlSendActionMask"] = 0
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSSelectedCol"] = -1
    obj["NSSelectedRow"] = -1
    obj["NSSuperview"] = parent
    obj["NSCell"] = NibObject("NSActionCell", None, {
        "NSCellFlags": CellFlags.DONT_ACT_ON_MOUSE_UP,
        "NSCellFlags2": CellFlags2.UNKNOWN_MATRIX_CELL,
    })
    return obj
