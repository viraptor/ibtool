import math
from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import sFlagsScrollView, vFlags
from .tableView import TVFLAGS

def _get_ics_w(doc_view):
    ics_w = doc_view.get("NSIntercellSpacingWidth")
    return ics_w if ics_w is not None else 3.0

def _reduce_column_widths(doc_view, reduction):
    table_columns = doc_view.get("NSTableColumns")
    if not table_columns or len(table_columns) == 0:
        return
    cas = doc_view.get("NSColumnAutoresizingStyle")
    if cas == 4:  # lastColumnOnly
        table_columns[-1]["NSWidth"] = table_columns[-1]["NSWidth"] - reduction
    elif cas == 5:  # firstColumnOnly
        table_columns[0]["NSWidth"] = table_columns[0]["NSWidth"] - reduction
    elif cas == 1:  # uniform
        n = len(table_columns)
        per_col = math.ceil(reduction / n)
        for i, col in enumerate(table_columns):
            r = per_col if i < n - 1 else reduction - per_col * (n - 1)
            col["NSWidth"] = col["NSWidth"] - r

def default_pan_recognizer(scrollView: XibObject) -> NibObject:
    obj = NibObject("NSPanGestureRecognizer", None)
    obj["NSGestureRecognizer.action"] = NibString.intern("_panWithGestureRecognizer:")
    obj["NSGestureRecognizer.allowedTouchTypes"] = 1
    obj["NSGestureRecognizer.delegate"] = scrollView
    obj["NSGestureRecognizer.target"] = scrollView
    obj["NSPanGestureRecognizer.buttonMask"] = 0
    obj["NSPanGestureRecognizer.numberOfTouchesRequired"] = 1
    return obj

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSScrollView", elem, parent)
    obj["NSSuperview"] = obj.xib_parent()
    obj.extraContext["fixedFrame"] = elem.attrib.get("fixedFrame", "YES") == "YES"

    border_type = {
        "none": sFlagsScrollView.BORDER_NONE,
        "line": sFlagsScrollView.BORDER_LINE,
        "bezel": sFlagsScrollView.BORDER_BEZEL,
        "groove": sFlagsScrollView.BORDER_GROOVE,
    }[elem.attrib.get("borderType", "bezel")]
    has_horizontal_scroller = sFlagsScrollView.HAS_HORIZONTAL_SCROLLER if elem.attrib.get("hasHorizontalScroller", "YES") == "YES" else 0
    has_vertical_scroller = sFlagsScrollView.HAS_VERTICAL_SCROLLER if elem.attrib.get("hasVerticalScroller", "YES") == "YES" else 0
    uses_predominant_axis_scrolling = sFlagsScrollView.USES_PREDOMINANT_AXIS_SCROLLING if elem.attrib.get("usesPredominantAxisScrolling", "YES") == "YES" else 0
    auto_hiding = sFlagsScrollView.AUTOHIDES_SCROLLERS if elem.attrib.get("autohidesScrollers") == "YES" else 0
    # COPY_ON_SCROLL is deferred until after children parsed (only for table/outline doc views)
    obj["NSsFlags"] = 0x20800 | has_horizontal_scroller | has_vertical_scroller | uses_predominant_axis_scrolling | border_type | auto_hiding
    if border_type in [sFlagsScrollView.BORDER_LINE, sFlagsScrollView.BORDER_BEZEL]:
        obj.extraContext["insets"] = (2, 2)
    if border_type == sFlagsScrollView.BORDER_GROOVE:
        obj.extraContext["insets"] = (4, 4)

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)

    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

    # Add COPY_ON_SCROLL for table/outline scroll views when usesPredominantAxisScrolling is active
    if uses_predominant_axis_scrolling:
        content_cv = obj.get("NSContentView")
        if content_cv:
            dv = content_cv.get("NSDocView")
            if dv and dv.originalclassname() in ("NSTableView", "NSOutlineView"):
                obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    obj["NSGestureRecognizers"] = NibList([default_pan_recognizer(obj)])
    obj["NSMagnification"] = 1.0
    obj["NSMaxMagnification"] = 4.0
    obj["NSMinMagnification"] = 0.25
    obj["NSSubviews"] = NibMutableList([])
    obj["NSSubviews"].addItem(obj["NSContentView"])
    if obj.get("NSHeaderClipView"):
        obj["NSSubviews"].addItem(obj["NSHeaderClipView"])
        # Content clip view gets NSBounds with y offset for header height
        cv = obj["NSContentView"]
        cv_computed = cv.frame()
        if cv_computed:
            cv_w = int(cv_computed[2])
            cv_h = int(cv_computed[3])
            # Get header height from header clip view's doc view
            header_clip = obj["NSHeaderClipView"]
            header_view = header_clip.get("NSDocView")
            header_h = 23  # default
            if header_view:
                hv_frame = header_view.extraContext.get("NSFrame") or header_view.extraContext.get("NSFrameSize")
                if hv_frame:
                    header_h = hv_frame[3] if len(hv_frame) == 4 else hv_frame[1]
            cv["NSBounds"] = NibString.intern(f"{{{{{0}, {-header_h}}}, {{{cv_w}, {cv_h}}}}}")
    # Adjust table flags when clip view y doesn't account for border
    insets = obj.extraContext.get("insets", (0, 0))
    border = insets[0] // 2
    cv = obj["NSContentView"]
    cv_frame = cv.extraContext.get("NSFrame")
    clip_y = cv_frame[1] if cv_frame and len(cv_frame) == 4 else border
    border_deficit = border - clip_y
    doc_view = cv.get("NSDocView")
    if border_deficit > 0 and doc_view and doc_view.originalclassname() in ("NSTableView", "NSOutlineView"):
        # Height adjustment is handled by heightSizable autoresizing in the table/outline parser.
        # When grid lines are present and clip_y < border, swap GRID_STYLE_BIT0 → BIT1
        # and reduce autoresizable column width by ics * 3
        if doc_view.get("NSGridStyleMask"):
            doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT0)
            doc_view.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)
            reduction = _get_ics_w(doc_view) * 3
            _reduce_column_widths(doc_view, reduction)
        elif auto_hiding and obj.get("NSHeaderClipView") is not None:
            # Autohiding scroll views with headers and no grid lines:
            # reduce column widths by scroller_width + ics * 4
            reduction = 17 + _get_ics_w(doc_view) * 4
            _reduce_column_widths(doc_view, reduction)
    # Expand table/outline view and header view widths for visible vertical scroller
    doc_view = cv.get("NSDocView")
    vs_orig_frame = obj["NSVScroller"].extraContext.get("NSFrame")
    vs_offscreen = vs_orig_frame and len(vs_orig_frame) == 4 and vs_orig_frame[0] < 0
    has_header = obj.get("NSHeaderClipView") is not None
    if doc_view and doc_view.originalclassname() in ("NSTableView", "NSOutlineView") and not vs_offscreen and not auto_hiding:
        scroller_w = 17  # standard scroller width for regular control size
        ics_w = doc_view.get("NSIntercellSpacingWidth")
        if ics_w is None:
            ics_w = 3.0
        if has_header:
            expansion = int(scroller_w + ics_w)
        else:
            expansion = int(scroller_w + ics_w * 3)
        # Expand doc view (table/outline) frame width
        dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
        if dv_frame:
            if len(dv_frame) == 4:
                new_w = int(dv_frame[2]) + expansion
                new_h = int(dv_frame[3])
            else:
                new_w = int(dv_frame[0]) + expansion
                new_h = int(dv_frame[1])
            doc_view["NSFrameSize"] = NibString.intern(f"{{{new_w}, {new_h}}}")
        # Expand header view width to match
        if has_header:
            header_clip = obj["NSHeaderClipView"]
            header_view = header_clip.get("NSDocView")
            if header_view:
                hv_frame = header_view.extraContext.get("NSFrame") or header_view.extraContext.get("NSFrameSize")
                if hv_frame:
                    if len(hv_frame) == 4:
                        hv_new_w = int(hv_frame[2]) + expansion
                        hv_new_h = int(hv_frame[3])
                    else:
                        hv_new_w = int(hv_frame[0]) + expansion
                        hv_new_h = int(hv_frame[1])
                    header_view["NSFrameSize"] = NibString.intern(f"{{{hv_new_w}, {hv_new_h}}}")

    # Horizontal scroller gets NSEnabled for table/outline scroll views (not autohiding)
    is_table_sv = doc_view and doc_view.originalclassname() in ("NSTableView", "NSOutlineView")
    if is_table_sv and not auto_hiding:
        obj["NSHScroller"]["NSEnabled"] = True
    obj["NSSubviews"].addItem(obj["NSHScroller"])
    obj["NSSubviews"].addItem(obj["NSVScroller"])

    obj["NSNextKeyView"] = obj["NSContentView"]

    horizontal_line_scroll = int(elem.attrib.get("horizontalLineScroll", "10"))
    vertical_line_scroll = int(elem.attrib.get("verticalLineScroll", "10"))
    horizontal_page_scroll = 0 if elem.attrib.get("horizontalPageScroll") == "0.0" else int(elem.attrib.get("horizontalPageScroll", "10"))
    vertical_page_scroll = 0 if elem.attrib.get("verticalPageScroll") == "0.0" else int(elem.attrib.get("verticalPageScroll", "10"))
    # For table/outline doc views, line scroll = rowHeight + intercellSpacingHeight
    if doc_view and doc_view.originalclassname() in ("NSTableView", "NSOutlineView"):
        row_h = doc_view.get("NSRowHeight")
        if row_h is None:
            row_h = 17.0
        ics_h = doc_view.get("NSIntercellSpacingHeight")
        if ics_h is None:
            ics_h = 2.0
        line_scroll = int(row_h + ics_h)
        horizontal_line_scroll = line_scroll
        vertical_line_scroll = line_scroll
    if (horizontal_line_scroll, vertical_line_scroll, horizontal_page_scroll, vertical_page_scroll) != (10, 10, 10, 10):
        obj["NSScrollAmts"] = NibInlineString(NibFloatToWord(vertical_page_scroll) + NibFloatToWord(horizontal_page_scroll) + NibFloatToWord(vertical_line_scroll) + NibFloatToWord(horizontal_line_scroll))

    # Recompute vertical scroller frame from scrollView dimensions, but only if
    # the scroller isn't already positioned off-screen (hidden auto-hiding scrollers)
    # and there's no header (header scroll views keep raw XIB scroller frames)
    if not vs_offscreen and not has_header:
        insets = obj.extraContext.get("insets", (0, 0))
        border = insets[0] // 2  # total inset / 2 = per-side border
        sv_frame = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if sv_frame is not None:
            sv_w = sv_frame[2] if len(sv_frame) == 4 else sv_frame[0]
            sv_h = sv_frame[3] if len(sv_frame) == 4 else sv_frame[1]
            vs_w = 17 if is_table_sv else obj["NSVScroller"].extraContext.get("scroller_width", 15)
            vs_x = sv_w - border - vs_w
            vs_y = border
            vs_h = sv_h - 2 * border
            obj["NSVScroller"]["NSFrame"] = NibString.intern(f"{{{{{vs_x}, {vs_y}}}, {{{vs_w}, {vs_h}}}}}")

    return obj
