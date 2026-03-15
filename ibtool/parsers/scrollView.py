import math
import re
import struct
from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain
from ..parsers_base import parse_children
from ..constants import sFlagsScrollView, vFlags
from .tableView import TVFLAGS

def _is_table_or_outline(obj):
    return obj and hasattr(obj, 'originalclassname') and obj.originalclassname() in ("NSTableView", "NSOutlineView")

def _get_ics_w(doc_view):
    ics_w = doc_view.get("NSIntercellSpacingWidth")
    return ics_w if ics_w is not None else 3.0

def _reduce_resizable_column_widths(doc_view, reduction):
    table_columns = doc_view.get("NSTableColumns")
    if not table_columns or len(table_columns) == 0:
        return
    resizable = [col for col in table_columns if (col.get("NSResizingMask") or 0) & 1]
    if not resizable:
        return
    n = len(resizable)
    per_col = math.ceil(reduction / n)
    for i, col in enumerate(resizable):
        r = per_col if i < n - 1 else reduction - per_col * (n - 1)
        col["NSWidth"] = col["NSWidth"] - r

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

    # GRID_STYLE_BIT1 for table/outline scroll views when usesPredominantAxisScrolling or hasHorizontalScroller is active
    if uses_predominant_axis_scrolling or has_horizontal_scroller:
        content_cv = obj.get("NSContentView")
        if content_cv:
            dv = content_cv.get("NSDocView")
            if _is_table_or_outline(dv):
                dv.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)

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
    # Compute VScroller offscreen status and scroller size early (needed by border_deficit logic)
    vs_orig_frame = obj["NSVScroller"].extraContext.get("NSFrame")
    sv_frame_for_offscreen = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
    sv_w_raw = (sv_frame_for_offscreen[2] if len(sv_frame_for_offscreen) == 4 else sv_frame_for_offscreen[0]) if sv_frame_for_offscreen else 0
    vs_offscreen = vs_orig_frame and len(vs_orig_frame) == 4 and (vs_orig_frame[0] < 0 or vs_orig_frame[0] >= sv_w_raw)
    vs_standard_w = obj["NSVScroller"].extraContext.get("standard_scroller_width", 17)
    vs_frame_w = obj["NSVScroller"].extraContext.get("scroller_width", 17)
    is_regular_scroller = vs_standard_w == 17 and vs_frame_w != 16
    is_small_offscreen = vs_offscreen and not is_regular_scroller
    hs_orig_frame_early = obj["NSHScroller"].extraContext.get("NSFrame")
    hs_offscreen = hs_orig_frame_early and len(hs_orig_frame_early) == 4 and hs_orig_frame_early[0] < 0

    # Adjust table flags when clip view y doesn't account for border
    insets = obj.extraContext.get("insets", (0, 0))
    border = insets[0] // 2
    cv = obj["NSContentView"]
    cv_frame = cv.extraContext.get("NSFrame")
    clip_y = cv_frame[1] if cv_frame and len(cv_frame) == 4 else border
    border_deficit = border - clip_y
    doc_view = cv.get("NSDocView")
    if border_deficit > 0 and _is_table_or_outline(doc_view):
        # Height adjustment is handled by heightSizable autoresizing in the table/outline parser.
        # When grid lines are present and clip_y < border, swap GRID_STYLE_BIT0 → BIT1
        # and reduce autoresizable column width by ics * 3
        if doc_view.get("NSGridStyleMask"):
            doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT0)
            doc_view.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)
            reduction = _get_ics_w(doc_view) * 3
            _reduce_column_widths(doc_view, reduction)
        elif auto_hiding and obj.get("NSHeaderClipView") is not None and not is_small_offscreen:
            # Autohiding scroll views with headers and no grid lines:
            # reduce column widths by scroller_width + ics * 4
            # (skipped for small offscreen scrollers which expand doc view instead)
            reduction = 17 + _get_ics_w(doc_view) * 4
            _reduce_column_widths(doc_view, reduction)
    # Autohiding scroll views without headers: reduce column widths when VScroller is not offscreen
    doc_view = cv.get("NSDocView")
    # COPY_ON_SCROLL: only when VScroller is not offscreen
    if not vs_offscreen and (uses_predominant_axis_scrolling or has_horizontal_scroller):
        if _is_table_or_outline(doc_view):
            obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)
    has_header = obj.get("NSHeaderClipView") is not None
    if auto_hiding and not has_header and not vs_offscreen and _is_table_or_outline(doc_view):
        reduction = 17 + _get_ics_w(doc_view) * 4
        _reduce_column_widths(doc_view, reduction)
    if _is_table_or_outline(doc_view) and not vs_offscreen and is_regular_scroller and (has_horizontal_scroller or not auto_hiding):
        scroller_w = 17
        ics_w = _get_ics_w(doc_view)
        if has_header:
            expansion = int(scroller_w + 3)
        else:
            expansion = int(scroller_w + ics_w * 3)
        # Compute clip view computed dimensions to determine if table extends beyond it
        cv_computed = cv.frame()
        clip_computed_w = int(cv_computed[2]) if cv_computed else None
        clip_computed_h = int(cv_computed[3]) if cv_computed else None
        # Get header height for height correction
        header_h = 0
        if has_header:
            header_clip = obj["NSHeaderClipView"]
            hv = header_clip.get("NSDocView")
            if hv:
                hv_f = hv.extraContext.get("NSFrame") or hv.extraContext.get("NSFrameSize")
                if hv_f:
                    header_h = int(hv_f[3]) if len(hv_f) == 4 else int(hv_f[1])
        # Expand doc view (table/outline) frame width
        dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
        if dv_frame:
            raw_w = int(dv_frame[2]) if len(dv_frame) == 4 else int(dv_frame[0])
            new_h = int(dv_frame[3]) if len(dv_frame) == 4 else int(dv_frame[1])
            if not has_horizontal_scroller and clip_computed_w is not None and raw_w <= clip_computed_w and (clip_computed_w - raw_w) >= vs_standard_w:
                new_w = clip_computed_w
                col_expansion = new_w - raw_w
                if col_expansion > 0:
                    _reduce_resizable_column_widths(doc_view, -col_expansion)
            else:
                new_w = raw_w + expansion
            elastic_h = doc_view.extraContext.get("elastic_row_height")
            if elastic_h is not None:
                new_h = elastic_h
            elif has_header and clip_computed_h is not None:
                new_h = clip_computed_h - header_h
            doc_view["NSFrameSize"] = NibString.intern(f"{{{new_w}, {new_h}}}")
        # Expand header view width to match
        if has_header:
            header_clip = obj["NSHeaderClipView"]
            header_view = header_clip.get("NSDocView")
            if header_view:
                hv_frame = header_view.extraContext.get("NSFrame") or header_view.extraContext.get("NSFrameSize")
                if hv_frame:
                    hv_raw_w = int(hv_frame[2]) if len(hv_frame) == 4 else int(hv_frame[0])
                    hv_new_h = int(hv_frame[3]) if len(hv_frame) == 4 else int(hv_frame[1])
                    if not has_horizontal_scroller and clip_computed_w is not None and hv_raw_w <= clip_computed_w:
                        hv_new_w = clip_computed_w
                    else:
                        hv_new_w = hv_raw_w + expansion
                    header_view["NSFrameSize"] = NibString.intern(f"{{{hv_new_w}, {hv_new_h}}}")

    # Horizontal scroller gets NSEnabled for table/outline scroll views (regular size, not autohiding)
    is_table_sv = _is_table_or_outline(doc_view)
    if is_table_sv and is_regular_scroller and not vs_offscreen and (has_horizontal_scroller or not auto_hiding):
        # Check if doc view was expanded beyond clip width (meaning horizontal scrolling is needed)
        dv_frame_check = doc_view.get("NSFrameSize")
        cv_computed_check = cv.frame()
        dv_expanded_w = 0
        if dv_frame_check:
            m_check = re.match(r'\{(\d+),', dv_frame_check._text)
            if m_check:
                dv_expanded_w = int(m_check.group(1))
        clip_check_w = int(cv_computed_check[2]) if cv_computed_check else 0
        needs_h_scroll = dv_expanded_w > clip_check_w
        if needs_h_scroll and (has_horizontal_scroller or not has_header):
            obj["NSHScroller"]["NSEnabled"] = True
        elif needs_h_scroll:
            dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
            cv_computed = cv.frame()
            raw_dv_w = (int(dv_frame[2]) if len(dv_frame) == 4 else int(dv_frame[0])) if dv_frame else 0
            clip_w = int(cv_computed[2]) if cv_computed else 0
            if raw_dv_w > clip_w:
                obj["NSHScroller"]["NSEnabled"] = True

    # Autohiding small scroller handling for table/outline scroll views with offscreen VScroller
    if is_table_sv and vs_offscreen and not is_regular_scroller and auto_hiding:
        hs_vflags = obj["NSHScroller"].get("NSvFlags")
        hs_is_hidden = (hs_vflags or 0) & vFlags.HIDDEN
        insets_sm = obj.extraContext.get("insets", (0, 0))
        border_sm = insets_sm[0] // 2
        sv_frame_sm = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if sv_frame_sm is not None:
            sv_w_sm = sv_frame_sm[2] if len(sv_frame_sm) == 4 else sv_frame_sm[0]
            sv_h_sm = sv_frame_sm[3] if len(sv_frame_sm) == 4 else sv_frame_sm[1]
            clip_w_sm = int(sv_w_sm - 2 * border_sm)
            ics_w = _get_ics_w(doc_view)
            hs_frame = obj["NSHScroller"].extraContext.get("NSFrame")
            hs_frame_h = int(hs_frame[3]) if hs_frame and len(hs_frame) == 4 else 14
            table_columns = doc_view.get("NSTableColumns") or []
            ncols = len(table_columns)
            sum_cols = sum(col["NSWidth"] for col in table_columns)
            natural_w = int(sum_cols + ncols * ics_w + vs_standard_w + hs_frame_h)
            has_grid_lines = doc_view.get("NSGridStyleMask")
            if hs_is_hidden and not has_grid_lines and has_header:
                # No grid lines: expand doc view and enable HScroller
                # Expansion amount depends on border deficit
                expansion = int(17 + ics_w * 4) if border_deficit > 0 else int(17 + 3)
                new_w = clip_w_sm + expansion
                dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
                if dv_frame:
                    new_h = int(dv_frame[3]) if len(dv_frame) == 4 else int(dv_frame[1])
                    doc_view["NSFrameSize"] = NibString.intern(f"{{{new_w}, {new_h}}}")
                if has_header:
                    header_clip = obj["NSHeaderClipView"]
                    header_view = header_clip.get("NSDocView")
                    if header_view:
                        hv_frame = header_view.extraContext.get("NSFrame") or header_view.extraContext.get("NSFrameSize")
                        if hv_frame:
                            hv_new_h = int(hv_frame[3]) if len(hv_frame) == 4 else int(hv_frame[1])
                            header_view["NSFrameSize"] = NibString.intern(f"{{{new_w}, {hv_new_h}}}")
                hs_standard_h = obj["NSHScroller"].extraContext.get("standard_scroller_width", 17)
                hs_x = border_sm
                hs_y = int(sv_h_sm) - border_sm - hs_standard_h
                hs_w = clip_w_sm
                obj["NSHScroller"]["NSFrame"] = NibString.intern(f"{{{{{hs_x}, {hs_y}}}, {{{hs_w}, {hs_standard_h}}}}}")
                obj["NSHScroller"].flagsAnd("NSvFlags", ~vFlags.HIDDEN)
                obj["NSHScroller"]["NSEnabled"] = True
                obj["NSHScroller"]["NSPercent"] = clip_w_sm / new_w
                if has_horizontal_scroller:
                    obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)
            elif hs_is_hidden and not has_grid_lines and natural_w > clip_w_sm:
                dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
                if dv_frame:
                    new_h = int(dv_frame[3]) if len(dv_frame) == 4 else int(dv_frame[1])
                    doc_view["NSFrameSize"] = NibString.intern(f"{{{natural_w}, {new_h}}}")
                if has_header:
                    header_clip = obj["NSHeaderClipView"]
                    header_view = header_clip.get("NSDocView")
                    if header_view:
                        hv_frame = header_view.extraContext.get("NSFrame") or header_view.extraContext.get("NSFrameSize")
                        if hv_frame:
                            hv_new_h = int(hv_frame[3]) if len(hv_frame) == 4 else int(hv_frame[1])
                            header_view["NSFrameSize"] = NibString.intern(f"{{{natural_w}, {hv_new_h}}}")
                hs_standard_h = obj["NSHScroller"].extraContext.get("standard_scroller_width", 17)
                hs_x = border_sm
                hs_y = int(sv_h_sm) - border_sm - hs_standard_h
                hs_w = clip_w_sm
                obj["NSHScroller"]["NSFrame"] = NibString.intern(f"{{{{{hs_x}, {hs_y}}}, {{{hs_w}, {hs_standard_h}}}}}")
                obj["NSHScroller"].flagsAnd("NSvFlags", ~vFlags.HIDDEN)
                obj["NSHScroller"]["NSEnabled"] = True
                obj["NSHScroller"]["NSPercent"] = clip_w_sm / natural_w
                obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)
            elif not hs_is_hidden:
                if natural_w > clip_w_sm:
                    reduction = 17 + ics_w * 4
                    _reduce_resizable_column_widths(doc_view, reduction)
                dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
                if dv_frame:
                    new_h = int(dv_frame[3] if len(dv_frame) == 4 else dv_frame[1])
                    doc_view["NSFrameSize"] = NibString.intern(f"{{{clip_w_sm}, {new_h}}}")
                if has_header:
                    header_clip = obj["NSHeaderClipView"]
                    header_view = header_clip.get("NSDocView")
                    if header_view:
                        hv_frame = header_view.extraContext.get("NSFrame") or header_view.extraContext.get("NSFrameSize")
                        if hv_frame:
                            hv_new_h = int(hv_frame[3] if len(hv_frame) == 4 else hv_frame[1])
                            header_view["NSFrameSize"] = NibString.intern(f"{{{clip_w_sm}, {hv_new_h}}}")
                doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT1)
                obj["NSHScroller"].flagsOr("NSvFlags", vFlags.HIDDEN)

    # Small scroller handling for table/outline scroll views with offscreen VScroller (non-autohiding)
    if is_table_sv and vs_offscreen and not is_regular_scroller and not auto_hiding:
        hs_vflags = obj["NSHScroller"].get("NSvFlags")
        hs_is_hidden = (hs_vflags or 0) & vFlags.HIDDEN
        insets_sm = obj.extraContext.get("insets", (0, 0))
        border_sm = insets_sm[0] // 2
        sv_frame_sm = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if sv_frame_sm is not None:
            sv_w_sm = sv_frame_sm[2] if len(sv_frame_sm) == 4 else sv_frame_sm[0]
            sv_h_sm = sv_frame_sm[3] if len(sv_frame_sm) == 4 else sv_frame_sm[1]
            clip_w_sm = int(sv_w_sm - 2 * border_sm)
            if hs_is_hidden:
                expansion = 20
                dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
                if dv_frame:
                    if len(dv_frame) == 4:
                        new_w = int(dv_frame[2]) + expansion
                        new_h = int(dv_frame[3])
                    else:
                        new_w = int(dv_frame[0]) + expansion
                        new_h = int(dv_frame[1])
                    doc_view["NSFrameSize"] = NibString.intern(f"{{{new_w}, {new_h}}}")
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
                hs_standard_h = obj["NSHScroller"].extraContext.get("standard_scroller_width", 17)
                hs_x = border_sm
                hs_y = int(sv_h_sm) - border_sm - hs_standard_h
                hs_w = clip_w_sm
                obj["NSHScroller"]["NSFrame"] = NibString.intern(f"{{{{{hs_x}, {hs_y}}}, {{{hs_w}, {hs_standard_h}}}}}")
                obj["NSHScroller"].flagsAnd("NSvFlags", ~vFlags.HIDDEN)
                obj["NSHScroller"]["NSEnabled"] = True
                dv_frame_str = doc_view.get("NSFrameSize")
                if dv_frame_str:
                    m = re.match(r'\{(\d+),', dv_frame_str._text)
                    if m:
                        table_w = int(m.group(1))
                        if table_w > 0:
                            obj["NSHScroller"]["NSPercent"] = clip_w_sm / table_w
            else:
                reduction = 17 + _get_ics_w(doc_view) * 4
                _reduce_resizable_column_widths(doc_view, reduction)
                dv_frame = doc_view.extraContext.get("NSFrame") or doc_view.extraContext.get("NSFrameSize")
                if dv_frame:
                    new_h = int(dv_frame[3] if len(dv_frame) == 4 else dv_frame[1])
                    doc_view["NSFrameSize"] = NibString.intern(f"{{{clip_w_sm}, {new_h}}}")
                if has_header:
                    header_clip = obj["NSHeaderClipView"]
                    header_view = header_clip.get("NSDocView")
                    if header_view:
                        hv_frame = header_view.extraContext.get("NSFrame") or header_view.extraContext.get("NSFrameSize")
                        if hv_frame:
                            hv_new_h = int(hv_frame[3] if len(hv_frame) == 4 else hv_frame[1])
                            header_view["NSFrameSize"] = NibString.intern(f"{{{clip_w_sm}, {hv_new_h}}}")
                obj.flagsAnd("NSsFlags", ~sFlagsScrollView.COPY_ON_SCROLL)
                doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT1)
                obj["NSHScroller"].flagsOr("NSvFlags", vFlags.HIDDEN)

    obj["NSSubviews"].addItem(obj["NSHScroller"])
    obj["NSSubviews"].addItem(obj["NSVScroller"])

    obj["NSNextKeyView"] = obj["NSContentView"]

    horizontal_line_scroll = int(elem.attrib.get("horizontalLineScroll", "10"))
    vertical_line_scroll = int(elem.attrib.get("verticalLineScroll", "10"))
    horizontal_page_scroll = 0 if elem.attrib.get("horizontalPageScroll") == "0.0" else int(elem.attrib.get("horizontalPageScroll", "10"))
    vertical_page_scroll = 0 if elem.attrib.get("verticalPageScroll") == "0.0" else int(elem.attrib.get("verticalPageScroll", "10"))
    # For table/outline doc views, line scroll = rowHeight + intercellSpacingHeight
    if _is_table_or_outline(doc_view):
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

    # Recompute scroller frames for table/outline scroll views
    hs_orig_frame = obj["NSHScroller"].extraContext.get("NSFrame")
    hs_offscreen = hs_orig_frame and len(hs_orig_frame) == 4 and hs_orig_frame[0] < 0
    if not vs_offscreen and is_table_sv:
        insets = obj.extraContext.get("insets", (0, 0))
        border = insets[0] // 2  # total inset / 2 = per-side border
        sv_frame = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if sv_frame is not None:
            sv_w = sv_frame[2] if len(sv_frame) == 4 else sv_frame[0]
            sv_h = sv_frame[3] if len(sv_frame) == 4 else sv_frame[1]
            vs_w = vs_standard_w
            hs_h = 17
            # Get header height if present
            header_h = 0
            if has_header:
                header_clip = obj["NSHeaderClipView"]
                hv = header_clip.get("NSDocView")
                if hv:
                    hv_f = hv.extraContext.get("NSFrame") or hv.extraContext.get("NSFrameSize")
                    if hv_f:
                        header_h = hv_f[3] if len(hv_f) == 4 else hv_f[1]
            # Vertical scroller (only for non-autohiding)
            if not auto_hiding:
                vs_x = sv_w - border - vs_w
                vs_y = border + header_h
                vs_h = sv_h - 2 * border - header_h
                obj["NSVScroller"]["NSFrame"] = NibString.intern(f"{{{{{vs_x}, {vs_y}}}, {{{vs_w}, {vs_h}}}}}")
                obj["NSVScroller"].flagsAnd("NSvFlags", ~vFlags.HIDDEN)
            # For elastic tables with content taller than visible area, enable VScroller
            elastic_h = doc_view.extraContext.get("elastic_row_height")
            if auto_hiding and elastic_h is not None:
                visible_h = sv_h - 2 * border - header_h
                if elastic_h > visible_h:
                    clip_h = sv_h - 2 * border
                    obj["NSVScroller"]["NSEnabled"] = True
                    obj["NSVScroller"]["NSPercent"] = clip_h / (elastic_h + header_h)
                    # Encode line scroll into NSsFlags upper bits
                    vline_f32 = struct.pack(">f", float(doc_view.get("NSRowHeight") or 0))
                    byte1 = vline_f32[1]
                    byte1_ceil = (byte1 + 0x0F) & 0xF0
                    obj.flagsOr("NSsFlags", (byte1_ceil << 8) | 0x40)
            # Horizontal scroller (only when not offscreen)
            if not hs_offscreen:
                hs_x = border
                hs_y = sv_h - border - hs_h
                hs_w = sv_w - 2 * border
                obj["NSHScroller"]["NSFrame"] = NibString.intern(f"{{{{{hs_x}, {hs_y}}}, {{{hs_w}, {hs_h}}}}}")
                obj["NSHScroller"].flagsAnd("NSvFlags", ~vFlags.HIDDEN)
                # NSPercent = visible ratio (clip width / table width)
                clip_w = sv_w - 2 * border
                dv_frame_str = doc_view.get("NSFrameSize")
                if dv_frame_str:
                    m = re.match(r'\{(\d+),', dv_frame_str._text)
                    if m:
                        table_w = int(m.group(1))
                        if table_w > 0:
                            obj["NSHScroller"]["NSPercent"] = clip_w / table_w
    elif not vs_offscreen and not has_header and not is_table_sv:
        insets = obj.extraContext.get("insets", (0, 0))
        border = insets[0] // 2
        sv_frame = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if sv_frame is not None:
            sv_w = sv_frame[2] if len(sv_frame) == 4 else sv_frame[0]
            sv_h = sv_frame[3] if len(sv_frame) == 4 else sv_frame[1]
            vs_w = obj["NSVScroller"].extraContext.get("scroller_width", 15)
            vs_x = sv_w - border - vs_w
            vs_y = border
            vs_h = sv_h - 2 * border
            obj["NSVScroller"]["NSFrame"] = NibString.intern(f"{{{{{vs_x}, {vs_y}}}, {{{vs_w}, {vs_h}}}}}")

    h = obj.extraContext.get("horizontalHuggingPriority", "250")
    v = obj.extraContext.get("verticalHuggingPriority", "250")
    if h != "250" or v != "250":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    return obj
