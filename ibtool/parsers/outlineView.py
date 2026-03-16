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

    if elem.attrib.get("viewBased") == "YES":
        obj["NSSubviews"] = NibMutableList([])
        obj["NSTableViewArchivedReusableViewsKey"] = NibMutableDictionary([])

    if outline_col_id := elem.attrib.get("outlineTableColumn"):
        obj.extraContext["outlineTableColumnId"] = outline_col_id

    # Pre-compute expected column expansion for cell view width calculation
    # Expansion happens when parent doesn't use autolayout and scroller is small
    clip_view = obj.xib_parent()
    if clip_view and clip_view.extraContext.get("scrollview_size"):
        sv_parent = clip_view.xib_parent()  # scrollView
        if sv_parent:
            sv_parent_parent = sv_parent.xib_parent()  # parent of scrollView
            parent_autolayout = sv_parent_parent and sv_parent_parent.extraContext.get("NSDoNotTranslateAutoresizingMask")
            if not parent_autolayout:
                cv_frame = clip_view.frame()
                rect_elem = elem.find("rect[@key='frame']")
                if cv_frame and rect_elem is not None:
                    raw_w = int(rect_elem.attrib.get("width", "0"))
                    clip_w = int(cv_frame[2])
                    if clip_w > raw_w:
                        obj.extraContext["expected_column_expansion"] = clip_w - raw_w

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
        # Outline view width is managed by the scroll view, not frame() autoresizing.
        # Keep only heightSizable so the outline fills the clip view vertically.
        obj.extraContext["parsed_autoresizing"] = {
            "flexibleMaxX": False, "flexibleMaxY": False,
            "flexibleMinX": False, "flexibleMinY": False,
            "widthSizable": False, "heightSizable": True,
        }

    # Update extraContext to match computed frame (used by scrollView.py)
    computed = obj.frame()
    obj.extraContext["NSFrameSize"] = (computed[2], computed[3])
    obj.extraContext.pop("NSFrame", None)

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
    obj.setIfEmpty("NSIntercellSpacingHeight", 0.0)
    obj.setIfEmpty("NSIntercellSpacingWidth", 0.0)
    obj["NSOutineViewStronglyReferencesItems"] = True
    if elem.attrib.get("autoresizesOutlineColumn") != "YES":
        obj["NSOutlineViewAutoresizesOutlineColumnKey"] = False
    indent = elem.attrib.get("indentationPerLevel")
    obj["NSOutlineViewIndentationPerLevelKey"] = NibFloat(float(indent) if indent else 0.0)
    obj["NSTableViewDraggingDestinationStyle"] = 0
    obj["NSTableViewGroupRowStyle"] = 1

    handle_props(ctx, elem, obj, [
        PropSchema(prop="NSTvFlags", const=TVFLAGS.UNKNOWN_2 | TVFLAGS.GRID_STYLE_BIT0),
        PropSchema(prop="NSTvFlags", attrib="columnResizing", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_RESIZING),
        PropSchema(prop="NSTvFlags", attrib="alternatingRowBackgroundColors", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALTERNATING_ROW_BACKGROUND_COLORS),
        PropSchema(prop="NSTvFlags", attrib="columnSelection", default="NO", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_SELECTION),
        PropSchema(prop="NSTvFlags", attrib="multipleSelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_MULTIPLE_SELECTION),
        PropSchema(prop="NSTvFlags", attrib="columnReordering", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_COLUMN_REORDERING | TVFLAGS.UNKNOWN_1),
        PropSchema(prop="NSTvFlags", attrib="emptySelection", default="YES", map=MAP_YES_NO, or_mask=TVFLAGS.ALLOWS_EMPTY_SELECTION),
        PropSchema(prop="NSTableViewShouldFloatGroupRows", attrib="floatsGroupRows", default="YES", map=MAP_YES_NO),
        PropSchema(prop="NSAllowsTypeSelect", attrib="typeSelect", default="YES", map=MAP_YES_NO, skip_default=False),
        PropSchema(prop="NSAutosaveName", attrib="autosaveName", skip_default=True),
        PropSchema(prop="NSRowHeight", attrib="rowHeight", default="17", filter=float, skip_default=False),
    ])

    # GRID_STYLE_BIT1 when multipleSelection=YES AND (columnResizing=YES OR 3+ columns)
    columns = obj.get("NSTableColumns")
    num_cols = len(columns) if columns else 0
    if elem.attrib.get("multipleSelection", "YES") == "YES":
        if elem.attrib.get("columnResizing", "YES") == "YES" or num_cols >= 3:
            obj.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)
    # Clear BIT0 when columnResizing=NO and any column has resizeWithTable
    if elem.attrib.get("columnResizing", "YES") == "NO" and columns:
        for col in columns:
            if col.get("NSIsResizeable"):
                obj.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT0)
                break

    # UNKNOWN_4 when columnReordering=YES and autosaveColumns is not explicitly "NO"
    if elem.attrib.get("columnReordering", "YES") == "YES" and "autosaveColumns" not in elem.attrib:
        obj.flagsOr("NSTvFlags", TVFLAGS.UNKNOWN_4)

    if cas_val == 1:  # uniform → AUTORESIZE_ALL_COLUMNS_TO_FIT
        obj.flagsOr("NSTvFlags", TVFLAGS.AUTORESIZE_ALL_COLUMNS_TO_FIT)

    # Grid lines → HAS_GRID_LINES flag
    if obj.get("NSGridStyleMask"):
        obj.flagsOr("NSTvFlags", TVFLAGS.HAS_GRID_LINES)

    # Outline views always get WIDTH_SIZABLE | HEIGHT_SIZABLE
    obj.flagsOr("NSvFlags", vFlags.WIDTH_SIZABLE | vFlags.HEIGHT_SIZABLE)

    return obj
