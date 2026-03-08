from ..models import ArchiveContext, NibObject, NibMutableList, NibMutableDictionary, XibObject, NibNil, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_flags, __handle_view_chain, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children
from ..constants import vFlags
from enum import IntEnum

class TVFLAGS(IntEnum):
    ALLOWS_COLUMN_REORDERING = 0xffffffff00000000
    AUTORESIZE_ALL_COLUMNS_TO_FIT =       0x8000
    AUTORESIZE_STYLE_BIT0 =            0x200000
    AUTORESIZE_STYLE_BIT1 =            0x400000
    ALTERNATING_ROW_BACKGROUND_COLORS = 0x800000
    AUTOSAVE_COLUMNS =                 0x1000000
    UNKNOWN_2 =                        0x2000000
    ALLOWS_COLUMN_SELECTION =          0x4000000
    ALLOWS_MULTIPLE_SELECTION =        0x8000000
    ALLOWS_EMPTY_SELECTION =          0x10000000
    AUTORESIZE_STYLE_BIT2 =          0x20000000
    ALLOWS_COLUMN_RESIZING =          0x40000000
    UNKNOWN_1 =                       0x80000000

COLUMN_AUTORESIZE_STYLE_MAP = {
    "none": 0,
    "uniform": 1,
    "sequential": 2,
    "reverseSequential": 3,
    "lastColumnOnly": 4,
    "firstColumnOnly": 5,
}

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None

    obj = make_xib_object(ctx, "NSTableView", elem, parent)

    obj["NSSuperview"] = parent

    if elem.attrib.get("viewBased") == "YES":
        obj["NSSubviews"] = NibMutableList([])
        obj["NSTableViewArchivedReusableViewsKey"] = NibMutableDictionary([])

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    
    if obj.get("NSNextKeyView") is not None:
        del obj["NSNextKeyView"]

    obj["NSAllowsLogicalLayoutDirection"] = False
    cas_str = elem.attrib.get("columnAutoresizingStyle")
    cas_val = COLUMN_AUTORESIZE_STYLE_MAP.get(cas_str, 1)  # default is uniform (1)
    obj["NSColumnAutoresizingStyle"] = cas_val
    obj.setIfNotDefault("NSControlAllowsExpansionToolTips", elem.attrib.get("allowsExpansionToolTips") == "YES", False)
    obj["NSControlContinuous"] = False
    obj["NSControlLineBreakMode"] = 0
    obj["NSControlRefusesFirstResponder"] = False
    obj["NSControlSendActionMask"] = 0
    obj["NSControlSize"] = 0
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
        "NSvFlags": 0x100,
    })
    obj["NSDataSource"] = NibNil()
    obj["NSDelegate"] = NibNil()
    obj["NSDraggingSourceMaskForLocal"] = -1
    obj["NSDraggingSourceMaskForNonLocal"] = 0
    obj["NSEnabled"] = True
    obj["NSTableViewDraggingDestinationStyle"] = 0
    obj["NSTableViewGroupRowStyle"] = 1

    MAP_TABLE_STYLE = {
        None: None,
        "fullWidth": 1,
        "inset": 2,
        "sourceList": 3,
        "plain": 4,
    }
    MAP_TABLE_HIGHLIGHT_STYLE = {
        None: None,
        "sourceList": 1,
    }
    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSTvFlags", const=TVFLAGS.ALLOWS_COLUMN_RESIZING | TVFLAGS.AUTORESIZE_STYLE_BIT2 | TVFLAGS.UNKNOWN_2 | TVFLAGS.AUTORESIZE_STYLE_BIT1),
        PropSchema(prop="NSTvFlags", attrib="alternatingRowBackgroundColors", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALTERNATING_ROW_BACKGROUND_COLORS),
        PropSchema(prop="NSTvFlags", attrib="autosaveColumns", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.AUTOSAVE_COLUMNS),
        PropSchema(prop="NSTvFlags", attrib="columnSelection", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_SELECTION),
        PropSchema(prop="NSTvFlags", attrib="multipleSelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_MULTIPLE_SELECTION),
        PropSchema(prop="NSTvFlags", attrib="columnReordering", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_REORDERING | TVFLAGS.UNKNOWN_1),
        PropSchema(prop="NSTvFlags", attrib="emptySelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_EMPTY_SELECTION),
        PropSchema(prop="NSTableViewShouldFloatGroupRows", attrib="floatsGroupRows", default="YES", map=MAP_YES_NO),
        PropSchema(prop="NSTableViewStyle", attrib="tableStyle", map=MAP_TABLE_STYLE, skip_default=True),
        PropSchema(prop="NSTableViewSelectionHighlightStyle", attrib="selectionHighlightStyle", map=MAP_TABLE_HIGHLIGHT_STYLE, skip_default=True),
        PropSchema(prop="NSAllowsTypeSelect", attrib="typeSelect", default="YES", map=MAP_YES_NO, skip_default=False),
        PropSchema(prop="NSAutosaveName", attrib="autosaveName", skip_default=True),
        PropSchema(prop="NSRowHeight", attrib="rowHeight", default="17", filter=float, skip_default=False),
    ])

    # Set AUTOSAVE_COLUMNS when autosaveName is present
    if elem.attrib.get("autosaveName"):
        obj.flagsOr("NSTvFlags", TVFLAGS.AUTOSAVE_COLUMNS)

    # Uniform autoresize style → AUTORESIZE_ALL_COLUMNS_TO_FIT
    if cas_val == 1:
        obj.flagsOr("NSTvFlags", TVFLAGS.AUTORESIZE_ALL_COLUMNS_TO_FIT)

    # Table views always get WIDTH_SIZABLE | HEIGHT_SIZABLE
    obj.flagsOr("NSvFlags", vFlags.WIDTH_SIZABLE | vFlags.HEIGHT_SIZABLE)

    focus_ring = {"none": 0x1000, "exterior": 0x2000}.get(obj.extraContext.get("focusRingType"), 0)
    if focus_ring:
        obj.flagsOr("NSvFlags", focus_ring)

    return obj
