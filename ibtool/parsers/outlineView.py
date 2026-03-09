from ..models import ArchiveContext, NibObject, NibMutableList, NibMutableDictionary, XibObject, NibNil, NibString, NibFloat
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children
from ..constants import vFlags
from .tableView import TVFLAGS, COLUMN_AUTORESIZE_STYLE_MAP

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSOutlineView", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
        # Outline view width is managed by the scroll view, not frame() autoresizing.
        if "parsed_autoresizing" in obj.extraContext:
            del obj.extraContext["parsed_autoresizing"]

    if obj.get("NSNextKeyView") is not None:
        del obj["NSNextKeyView"]

    obj["NSAllowsLogicalLayoutDirection"] = False
    cas_str = elem.attrib.get("columnAutoresizingStyle")
    cas_val = COLUMN_AUTORESIZE_STYLE_MAP.get(cas_str, 1)  # default is uniform (1)
    obj["NSColumnAutoresizingStyle"] = cas_val
    # Note: AUTORESIZE_ALL_COLUMNS_TO_FIT is set after handle_props below
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
        "NSFrameSize": NibString.intern("{17, 28}"),
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
    obj["NSIntercellSpacingHeight"] = 2.0
    obj["NSIntercellSpacingWidth"] = 3.0
    obj["NSOutineViewStronglyReferencesItems"] = True
    obj["NSOutlineViewAutoresizesOutlineColumnKey"] = False
    obj["NSOutlineViewIndentationPerLevelKey"] = NibFloat(0.0)
    obj["NSTableViewDraggingDestinationStyle"] = 0
    obj["NSTableViewGroupRowStyle"] = 1

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSTvFlags", const=TVFLAGS.ALLOWS_COLUMN_RESIZING | TVFLAGS.UNKNOWN_4 | TVFLAGS.UNKNOWN_2 | TVFLAGS.UNKNOWN_3),
        PropSchema(prop="NSTvFlags", attrib="alternatingRowBackgroundColors", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALTERNATING_ROW_BACKGROUND_COLORS),
        PropSchema(prop="NSTvFlags", attrib="columnSelection", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_SELECTION),
        PropSchema(prop="NSTvFlags", attrib="multipleSelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_MULTIPLE_SELECTION | TVFLAGS.ALLOWS_MULTIPLE_SELECTION_2),
        PropSchema(prop="NSTvFlags", attrib="columnReordering", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_REORDERING | TVFLAGS.UNKNOWN_1),
        PropSchema(prop="NSTvFlags", attrib="emptySelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_EMPTY_SELECTION),
        PropSchema(prop="NSTableViewShouldFloatGroupRows", attrib="floatsGroupRows", default="YES", map=MAP_YES_NO),
        PropSchema(prop="NSAllowsTypeSelect", attrib="typeSelect", default="YES", map=MAP_YES_NO, skip_default=False),
        PropSchema(prop="NSAutosaveName", attrib="autosaveName", skip_default=True),
        PropSchema(prop="NSRowHeight", attrib="rowHeight", default="17", filter=float, skip_default=False),
    ])

    if cas_val == 1:  # uniform → AUTORESIZE_ALL_COLUMNS_TO_FIT
        obj.flagsOr("NSTvFlags", TVFLAGS.AUTORESIZE_ALL_COLUMNS_TO_FIT)

    # Outline views always get WIDTH_SIZABLE | HEIGHT_SIZABLE
    obj.flagsOr("NSvFlags", vFlags.WIDTH_SIZABLE | vFlags.HEIGHT_SIZABLE)

    return obj
