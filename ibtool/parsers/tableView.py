from ..models import ArchiveContext, NibObject, NibMutableList, NibMutableDictionary, XibObject, NibNil, NibString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __xibparser_cell_flags, __handle_view_chain, handle_props, PropSchema, MAP_YES_NO, MAP_FOCUS_RING, MAP_TABLE_STYLE, MAP_TABLE_HIGHLIGHT_STYLE
from ..parsers_base import parse_children
from ..constants import vFlags
from enum import IntEnum

class TVFLAGS(IntEnum):
    ALLOWS_COLUMN_REORDERING = 0xffffffff00000000
    AUTORESIZE_ALL_COLUMNS_TO_FIT =       0x8000
    GRID_STYLE_DASHED =                0x200000
    GRID_STYLE_SOLID =                 0x400000
    ALTERNATING_ROW_BACKGROUND_COLORS = 0x800000
    NO_AUTOSAVE_COLUMNS =              0x1000000
    ALLOWS_TYPE_SELECT =               0x2000000
    ALLOWS_COLUMN_SELECTION =          0x4000000
    ALLOWS_MULTIPLE_SELECTION =        0x8000000
    ALLOWS_EMPTY_SELECTION =          0x10000000
    HAS_GRID_LINES =                 0x20000000
    ALLOWS_COLUMN_RESIZING =          0x40000000
    COLUMN_REORDERING_LEGACY =        0x80000000

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

    is_elastic = elem.attrib.get("rowSizeStyle") == "automatic"
    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
        # Sort reusable views dictionary by identifier to match Apple's ordering
        reusable = obj.get("NSTableViewArchivedReusableViewsKey")
        if reusable and len(reusable._items) >= 2:
            pairs = [(reusable._items[i], reusable._items[i+1]) for i in range(0, len(reusable._items), 2)]
            pairs.sort(key=lambda p: p[0]._text if hasattr(p[0], '_text') else str(p[0]))
            reusable._items = [item for pair in pairs for item in pair]
        # Table view width is managed by the scroll view, not frame() autoresizing.
        # Keep only heightSizable so the table fills the clip view vertically.
        # For elastic/automatic row sizing, don't use heightSizable - height is cell-based.
        obj.extraContext["parsed_autoresizing"] = {
            "flexibleMaxX": False, "flexibleMaxY": False,
            "flexibleMinX": False, "flexibleMinY": False,
            "widthSizable": False, "heightSizable": not is_elastic,
        }

    # Update extraContext to match computed frame (used by scrollView.py)
    computed = obj.frame()
    obj.extraContext["NSFrameSize"] = (computed[2], computed[3])
    obj.extraContext.pop("NSFrame", None)

    if obj.get("NSNextKeyView") is not None:
        del obj["NSNextKeyView"]

    obj["NSAllowsLogicalLayoutDirection"] = ctx.isBaseLocalization
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
    obj["NSTableViewDraggingDestinationStyle"] = 1 if elem.attrib.get("selectionHighlightStyle") == "sourceList" else 0
    obj["NSTableViewGroupRowStyle"] = 1

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSTvFlags", const=TVFLAGS.ALLOWS_TYPE_SELECT | TVFLAGS.GRID_STYLE_DASHED),
        PropSchema(prop="NSTvFlags", attrib="columnResizing", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_RESIZING),
        PropSchema(prop="NSTvFlags", attrib="alternatingRowBackgroundColors", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALTERNATING_ROW_BACKGROUND_COLORS),
        PropSchema(prop="NSTvFlags", attrib="columnSelection", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_SELECTION),
        PropSchema(prop="NSTvFlags", attrib="multipleSelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_MULTIPLE_SELECTION),
        PropSchema(prop="NSTvFlags", attrib="columnReordering", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_REORDERING | TVFLAGS.COLUMN_REORDERING_LEGACY),
        PropSchema(prop="NSTvFlags", attrib="emptySelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_EMPTY_SELECTION),
        PropSchema(prop="NSTableViewShouldFloatGroupRows", attrib="floatsGroupRows", default="YES", map=MAP_YES_NO),
        PropSchema(prop="NSTableViewStyle", attrib="tableStyle", map=MAP_TABLE_STYLE, skip_default=True),
        PropSchema(prop="NSTvFlags", attrib="selectionHighlightStyle", default=None, map={None: False, "sourceList": True}, or_mask=TVFLAGS.GRID_STYLE_SOLID),
        PropSchema(prop="NSTableViewSelectionHighlightStyle", attrib="selectionHighlightStyle", map=MAP_TABLE_HIGHLIGHT_STYLE, skip_default=True),
        PropSchema(prop="NSAllowsTypeSelect", attrib="typeSelect", default="YES", map=MAP_YES_NO, skip_default=False),
        PropSchema(prop="NSAutosaveName", attrib="autosaveName", skip_default=True),
        PropSchema(prop="NSRowHeight", attrib="rowHeight", default="17", filter=float, skip_default=False),
    ])

    if elem.attrib.get("selectionHighlightStyle") == "sourceList":
        obj.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_DASHED)

    # Tables with alternating row backgrounds, 3+ columns, no column reordering
    # and lastColumnOnly autoresize swap from DASHED to SOLID grid style.
    columns = obj.get("NSTableColumns")
    num_cols = len(columns) if columns else 0
    if (num_cols >= 3
            and elem.attrib.get("alternatingRowBackgroundColors") == "YES"
            and elem.attrib.get("columnReordering") == "NO"
            and elem.attrib.get("columnAutoresizingStyle") == "lastColumnOnly"):
        obj.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_DASHED)
        obj.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_SOLID)

    if is_elastic:
        columns_for_height = obj.get("NSTableColumns")
        if columns_for_height:
            max_cell_h = 0
            for col in columns_for_height:
                pcv = col.extraContext.get("prototypeCellView")
                if pcv:
                    ec = pcv.extraContext.get("NSFrame") or pcv.extraContext.get("NSFrameSize")
                    if ec:
                        h = ec[3] if len(ec) == 4 else ec[1]
                        max_cell_h = max(max_cell_h, h)
            if max_cell_h > 0:
                obj["NSRowHeight"] = float(max_cell_h)
                cur_fs = obj.extraContext.get("NSFrameSize")
                if cur_fs:
                    new_h = max(max_cell_h, cur_fs[1])
                    obj.extraContext["NSFrameSize"] = (cur_fs[0], new_h)
                    obj.extraContext["elastic_row_height"] = new_h

    columns = obj.get("NSTableColumns")

    if "autosaveColumns" not in elem.attrib:
        obj.flagsOr("NSTvFlags", TVFLAGS.NO_AUTOSAVE_COLUMNS)

    # Uniform autoresize style → AUTORESIZE_ALL_COLUMNS_TO_FIT
    if cas_val == 1:
        obj.flagsOr("NSTvFlags", TVFLAGS.AUTORESIZE_ALL_COLUMNS_TO_FIT)

    # Grid lines → HAS_GRID_LINES flag
    if obj.get("NSGridStyleMask"):
        obj.flagsOr("NSTvFlags", TVFLAGS.HAS_GRID_LINES)

    # Table views always get WIDTH_SIZABLE | HEIGHT_SIZABLE
    obj.flagsOr("NSvFlags", vFlags.WIDTH_SIZABLE | vFlags.HEIGHT_SIZABLE)

    focus_ring = MAP_FOCUS_RING.get(obj.extraContext.get("focusRingType"), 0)
    if focus_ring:
        obj.flagsOr("NSvFlags", focus_ring)

    h = obj.extraContext.get("horizontalHuggingPriority", "250")
    v = obj.extraContext.get("verticalHuggingPriority", "250")
    if h != "250" or v != "750":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    return obj
