from ..models import ArchiveContext, NibObject, XibObject, NibString
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, _xibparser_common_view_attributes, makeSystemColor, __xibparser_cell_options
from ..parsers_base import parse_children
from ..constants import CellFlags, CellFlags2, cvFlags, MatrixFlags

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
    mode_bits = {0: 0, 1: MatrixFlags.MODE_HIGHLIGHT, 2: MatrixFlags.MODE_RADIO, 3: MatrixFlags.MODE_LIST}[mode]
    matrix_flags = mode_bits
    if elem.attrib.get("allowsEmptySelection", "YES") != "NO":
        matrix_flags |= MatrixFlags.ALLOWS_EMPTY_SELECTION
    if elem.attrib.get("selectionByRect", "YES") != "NO":
        matrix_flags |= MatrixFlags.SELECTION_BY_RECT
    if elem.attrib.get("autosizesCells", "YES") != "NO":
        matrix_flags |= MatrixFlags.AUTOSIZES_CELLS
    if elem.attrib.get("drawsBackground") == "YES":
        matrix_flags |= MatrixFlags.DRAWS_BACKGROUND
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
        "NSCellFlags2": CellFlags2.ALLOWS_EDITING_TEXT_ATTRIBUTES,
    })
    return obj
