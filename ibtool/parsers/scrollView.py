import math
import re
import struct
from dataclasses import dataclass, field
from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord
from xml.etree.ElementTree import Element
from typing import Optional, Any
from .helpers import make_xib_object, __handle_view_chain, frame_string, size_string, parse_frame_string
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
        old_w = col["NSWidth"]
        col["NSWidth"] = old_w - r
        _adjust_cell_views_for_column_change(doc_view, col, old_w, old_w - r)

def _reduce_column_widths(doc_view, reduction):
    table_columns = doc_view.get("NSTableColumns")
    if not table_columns or len(table_columns) == 0:
        return
    cas = doc_view.get("NSColumnAutoresizingStyle")
    if cas == 4:  # lastColumnOnly
        col = table_columns[-1]
        old_w = col["NSWidth"]
        col["NSWidth"] = old_w - reduction
        _adjust_cell_views_for_column_change(doc_view, col, old_w, old_w - reduction)
    elif cas == 5:  # firstColumnOnly
        col = table_columns[0]
        old_w = col["NSWidth"]
        col["NSWidth"] = old_w - reduction
        _adjust_cell_views_for_column_change(doc_view, col, old_w, old_w - reduction)
    elif cas == 1:  # uniform
        n = len(table_columns)
        per_col = math.ceil(reduction / n)
        for i, col in enumerate(table_columns):
            r = per_col if i < n - 1 else reduction - per_col * (n - 1)
            old_w = col["NSWidth"]
            col["NSWidth"] = old_w - r
            _adjust_cell_views_for_column_change(doc_view, col, old_w, old_w - r)

def _adjust_cell_views_for_column_change(doc_view, col, old_width, new_width):
    """Adjust prototype cell view frames when column width changes."""
    delta = new_width - old_width
    if delta == 0:
        return
    pcv = col.extraContext.get("prototypeCellView")
    if not pcv:
        return
    pcv_nib_frame = pcv.get("NSFrame")
    if pcv_nib_frame and hasattr(pcv_nib_frame, '_text'):
        f = parse_frame_string(pcv_nib_frame)
        if f:
            pcv["NSFrame"] = frame_string(f[0], f[1], f[2] + delta, f[3])
            for child in (pcv.get("NSSubviews") or []):
                cf = child.get("NSFrame")
                if cf and hasattr(cf, '_text'):
                    cf_parsed = parse_frame_string(cf)
                    if cf_parsed:
                        child["NSFrame"] = frame_string(cf_parsed[0], cf_parsed[1], cf_parsed[2] + delta, cf_parsed[3])

def default_pan_recognizer(scrollView: XibObject) -> NibObject:
    obj = NibObject("NSPanGestureRecognizer", None)
    obj["NSGestureRecognizer.action"] = NibString.intern("_panWithGestureRecognizer:")
    obj["NSGestureRecognizer.allowedTouchTypes"] = 1
    obj["NSGestureRecognizer.delegate"] = scrollView
    obj["NSGestureRecognizer.target"] = scrollView
    obj["NSPanGestureRecognizer.buttonMask"] = 0
    obj["NSPanGestureRecognizer.numberOfTouchesRequired"] = 1
    return obj

@dataclass
class _SVState:
    """Computed geometry state for scroll view post-processing."""
    obj: Any
    cv: Any  # content clip view
    doc_view: Any
    sv_w: int
    sv_h: int
    border: int
    insets: tuple
    auto_hiding: int
    has_horizontal_scroller: int
    uses_predominant_axis_scrolling: int
    vs_offscreen: bool
    vs_hidden: bool
    vs_standard_w: int
    vs_frame_w: int
    is_regular_scroller: bool
    is_small_offscreen: bool
    hs_offscreen: bool
    hs_hidden: bool
    hs_h_for_table: int
    is_table_dv: bool
    has_header: bool
    sv_w_raw: int
    cv_already_accounts_for_scroller: bool
    small_scroller_should_expand: bool
    border_col_reduced: bool = False

def _rewrite_nib_frame(obj):
    """Recompute frame via frame() and write to NIB property (not extraContext)."""
    f = obj.frame()
    if f:
        x, y, w, h = int(f[0]), int(f[1]), int(f[2]), int(f[3])
        if x == 0 and y == 0:
            obj["NSFrameSize"] = size_string(w, h)
        else:
            obj["NSFrame"] = frame_string(x, y, w, h)

def _get_header_h(obj):
    """Get header view height from header clip view's doc view."""
    hcv = obj.get("NSHeaderClipView")
    if not hcv:
        return 0
    hv = hcv.get("NSDocView")
    if not hv:
        return 0
    hv_raw = hv.raw_frame()
    return hv_raw[3] if hv_raw else 0

def _set_header_view_width(obj, new_w):
    """Set header view NSFrameSize width, preserving height."""
    hcv = obj.get("NSHeaderClipView")
    if not hcv:
        return
    hv = hcv.get("NSDocView")
    if not hv:
        return
    hv_raw = hv.raw_frame()
    if hv_raw:
        hv["NSFrameSize"] = size_string(new_w, hv_raw[3])

def _setup_hscroller_frame(obj, border, sv_h, clip_w):
    """Position and show HScroller at bottom of scroll view."""
    hs = obj["NSHScroller"]
    hs_standard_h = hs.extraContext.get("standard_scroller_width", 17)
    hs_raw = hs.raw_frame()
    hs_frame_h = hs_raw[3] if hs_raw else 0
    hs_h = max(hs_standard_h, hs_frame_h + 1)
    hs["NSFrame"] = frame_string(border, int(sv_h) - border - hs_h, clip_w, hs_h)
    hs.flagsAnd("NSvFlags", ~vFlags.HIDDEN)
    hs["NSEnabled"] = True

def _init_sv_state(obj, auto_hiding, has_horizontal_scroller, uses_predominant_axis_scrolling):
    vs = obj["NSVScroller"]
    hs = obj["NSHScroller"]
    sv_raw = obj.raw_frame()
    sv_w_raw = sv_raw[2] if sv_raw else 0
    sv_h = sv_raw[3] if sv_raw else 0

    vs_orig = vs.raw_frame()
    vs_offscreen = vs_orig is not None and (vs_orig[0] < 0 or vs_orig[0] >= sv_w_raw)
    vs_standard_w = vs.extraContext.get("standard_scroller_width", 17)
    vs_frame_w = vs.extraContext.get("scroller_width", 17)
    is_regular_scroller = vs_standard_w == 17 and (vs_frame_w != 16 or vs_offscreen)
    is_small_offscreen = vs_offscreen and not is_regular_scroller
    vs_hidden = bool((vs.get("NSvFlags") or 0) & vFlags.HIDDEN)

    hs_orig = hs.raw_frame()
    hs_offscreen = hs_orig is not None and (hs_orig[0] < 0 or hs_orig[1] < 0 or hs_orig[1] + hs_orig[3] > sv_h)
    hs_hidden = bool((hs.get("NSvFlags") or 0) & vFlags.HIDDEN)

    cv = obj.get("NSContentView")
    doc_view = cv.get("NSDocView") if cv else None
    is_table_dv = _is_table_or_outline(doc_view)

    hs_h_for_table = 0
    if is_table_dv and not hs_offscreen and hs_hidden:
        hs_h_for_table = hs.extraContext.get("standard_scroller_width", 17)

    insets = obj.extraContext.get("insets", (0, 0))
    border = insets[0] // 2
    sv_inner_w = (sv_w_raw - insets[0]) if sv_w_raw else 0
    cv_raw = cv.raw_frame() if cv else None
    cv_already_accounts_for_scroller = cv_raw is not None and cv_raw[2] < sv_inner_w

    sv_parent = obj.xib_parent()
    parent_uses_autolayout = sv_parent and sv_parent.extraContext.get("NSDoNotTranslateAutoresizingMask")
    small_scroller_should_expand = (not vs_offscreen and not is_regular_scroller
                                     and not auto_hiding and not parent_uses_autolayout
                                     and _is_table_or_outline(cv.get("NSDocView") if cv else None))

    return _SVState(
        obj=obj, cv=cv, doc_view=doc_view,
        sv_w=sv_w_raw, sv_h=sv_h, border=border, insets=insets,
        auto_hiding=auto_hiding,
        has_horizontal_scroller=has_horizontal_scroller,
        uses_predominant_axis_scrolling=uses_predominant_axis_scrolling,
        vs_offscreen=vs_offscreen, vs_hidden=vs_hidden,
        vs_standard_w=vs_standard_w, vs_frame_w=vs_frame_w,
        is_regular_scroller=is_regular_scroller,
        is_small_offscreen=is_small_offscreen,
        hs_offscreen=hs_offscreen, hs_hidden=hs_hidden,
        hs_h_for_table=hs_h_for_table,
        is_table_dv=is_table_dv,
        has_header=obj.get("NSHeaderClipView") is not None,
        sv_w_raw=sv_w_raw,
        cv_already_accounts_for_scroller=cv_already_accounts_for_scroller,
        small_scroller_should_expand=small_scroller_should_expand,
    )

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

    # Pre-compute expected scroller reduction for child parsers (outlineView.py)
    if not auto_hiding:
        vs_elem = elem.find("scroller[@key='verticalScroller']")
        if vs_elem is not None:
            vs_rect = vs_elem.find("rect[@key='frame']")
            vs_cs = vs_elem.attrib.get("controlSize")
            vs_std_w = {"small": 13, "mini": 11}.get(vs_cs, 17)
            sv_frame_elem = elem.find("rect[@key='frame']")
            sv_w_pre = int(sv_frame_elem.attrib.get("width", "0")) if sv_frame_elem is not None else 0
            vs_x_pre = int(float(vs_rect.attrib.get("x", "0"))) if vs_rect is not None else 0
            vs_offscreen_pre = vs_x_pre < 0 or vs_x_pre >= sv_w_pre
            vs_hidden_pre = (vs_elem.attrib.get("hidden") == "YES")
            if not vs_offscreen_pre and not vs_hidden_pre:
                obj.extraContext["expected_vs_reduction"] = vs_std_w

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
    focus_ring = {"none": 0x1000, "exterior": 0x2000}.get(obj.extraContext.get("focusRingType"), 0)
    if focus_ring:
        obj.flagsOr("NSvFlags", focus_ring)
    obj["NSGestureRecognizers"] = NibList([default_pan_recognizer(obj)])
    obj["NSMagnification"] = 1.0
    obj["NSMaxMagnification"] = 4.0
    obj["NSMinMagnification"] = 0.25
    obj["NSSubviews"] = NibMutableList([])
    obj["NSSubviews"].addItem(obj["NSContentView"])
    st = _init_sv_state(obj, auto_hiding, has_horizontal_scroller, uses_predominant_axis_scrolling)
    vs_offscreen = st.vs_offscreen
    vs_standard_w = st.vs_standard_w
    vs_frame_w = st.vs_frame_w
    is_regular_scroller = st.is_regular_scroller
    is_small_offscreen = st.is_small_offscreen
    hs_offscreen = st.hs_offscreen
    vs_hidden = st.vs_hidden
    hs_hidden = st.hs_hidden
    content_cv_tmp = st.cv
    dv_tmp = st.doc_view
    is_table_dv = st.is_table_dv
    hs_h_for_table = st.hs_h_for_table
    sv_w_raw = st.sv_w_raw

    # Note: autohiding scroll views with hidden HScroller do not reduce clip height.

    # Post-processing: reduce clip view scrollview_size for visible scrollers
    if not auto_hiding and content_cv_tmp:
        sv_size = content_cv_tmp.extraContext.get("scrollview_size")
        if sv_size:
            new_w, new_h = sv_size
            if not vs_offscreen and not vs_hidden:
                vs_reduction = vs_standard_w if (vs_standard_w != 17 and is_table_dv) else 17
                new_w -= vs_reduction
            if not hs_offscreen and not hs_hidden:
                hs_standard_w = obj["NSHScroller"].extraContext.get("standard_scroller_width", 17)
                hs_reduction = hs_standard_w if (hs_standard_w != 17 and is_table_dv) else 17
                new_h -= hs_reduction
            if (new_w, new_h) != sv_size:
                content_cv_tmp.extraContext["scrollview_size"] = (new_w, new_h)
                _rewrite_nib_frame(content_cv_tmp)
                if dv_tmp and not is_table_dv:
                    dv_frame = dv_tmp.frame()
                    if dv_frame:
                        dv_tmp["NSFrameSize"] = size_string(dv_frame[2], dv_frame[3])
                        dv_tmp.extraContext["_has_computed_size"] = True
                        for child_obj in (dv_tmp.get("NSSubviews") or []):
                            if hasattr(child_obj, 'frame') and hasattr(child_obj, 'extraContext'):
                                _rewrite_nib_frame(child_obj)

    # Adjust header clip view frame width for non-autohiding with visible VScroller
    if not auto_hiding and not vs_offscreen and not vs_hidden:
        hcv = obj.get("NSHeaderClipView")
        if hcv:
            hcv_f = parse_frame_string(hcv.get("NSFrame")) if hcv.get("NSFrame") else None
            if hcv_f:
                hcv["NSFrame"] = frame_string(hcv_f[0], hcv_f[1], hcv_f[2] - vs_standard_w, hcv_f[3])

    if obj.get("NSHeaderClipView"):
        obj["NSSubviews"].addItem(obj["NSHeaderClipView"])
        cv = obj["NSContentView"]
        cv_computed = cv.frame()
        if cv_computed:
            cv_w, cv_h = int(cv_computed[2]), int(cv_computed[3])
            header_h = _get_header_h(obj) or 23
            cv["NSBounds"] = frame_string(0, -header_h, cv_w, cv_h)

    content_cv = st.cv
    cv_already_accounts_for_scroller = st.cv_already_accounts_for_scroller
    small_scroller_should_expand = st.small_scroller_should_expand
    cv_raw = content_cv.raw_frame() if content_cv else None
    if not small_scroller_should_expand and not vs_offscreen and not is_regular_scroller and cv_already_accounts_for_scroller and content_cv:
        content_cv["NSFrame"] = frame_string(*cv_raw)

    border = st.border
    cv = st.cv
    cv_frame = cv.extraContext.get("NSFrame")
    clip_y = cv_frame[1] if cv_frame and len(cv_frame) == 4 else border
    border_deficit = border - clip_y
    doc_view = st.doc_view
    border_col_reduced = False
    if border_deficit > 0 and _is_table_or_outline(doc_view):
        if doc_view.get("NSGridStyleMask"):
            doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT0)
            doc_view.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)
            _reduce_column_widths(doc_view, _get_ics_w(doc_view) * 3)
            border_col_reduced = True
        elif auto_hiding and obj.get("NSHeaderClipView") is not None and not is_small_offscreen:
            reduction = 17 + _get_ics_w(doc_view) * 4
            _reduce_column_widths(doc_view, reduction)
            border_col_reduced = True
    elif border > 0 and _is_table_or_outline(doc_view) and not obj.get("NSHeaderClipView") and (vs_offscreen or (auto_hiding and is_regular_scroller and has_horizontal_scroller)):
        doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT0)
        doc_view.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)
        _reduce_column_widths(doc_view, _get_ics_w(doc_view) * 3)
        border_col_reduced = True
    # Autohiding scroll views without headers: reduce column widths when VScroller is not offscreen
    doc_view = cv.get("NSDocView")
    # COPY_ON_SCROLL: only when VScroller is not offscreen
    if not vs_offscreen and (uses_predominant_axis_scrolling or has_horizontal_scroller):
        if _is_table_or_outline(doc_view):
            obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)
    has_header = obj.get("NSHeaderClipView") is not None
    if auto_hiding and not has_header and not vs_offscreen and not border_col_reduced and not is_regular_scroller and _is_table_or_outline(doc_view):
        reduction = 17 + _get_ics_w(doc_view) * 4
        _reduce_column_widths(doc_view, reduction)
    # Small-scroller expansion: expand doc view to clip computed width
    if small_scroller_should_expand:
        cv_computed = cv.frame()
        clip_computed_w = int(cv_computed[2]) if cv_computed else None
        dv_raw = doc_view.raw_frame()
        if dv_raw and clip_computed_w is not None:
            raw_w, new_h = dv_raw[2], dv_raw[3]
            if raw_w < clip_computed_w:
                _reduce_resizable_column_widths(doc_view, -(clip_computed_w - raw_w))
                doc_view.set_nib_size(clip_computed_w, new_h)
            elif raw_w > clip_computed_w:
                if vs_standard_w != 17:
                    _reduce_resizable_column_widths(doc_view, raw_w - clip_computed_w)
                doc_view.set_nib_size(clip_computed_w, new_h)
        # 16px frame with 17px standard: apply BIT0→BIT1 swap and column expansion
        if vs_standard_w == 17 and _is_table_or_outline(doc_view):
            ics_w = _get_ics_w(doc_view)
            table_columns = doc_view.get("NSTableColumns") or []
            n_cols = len(table_columns)
            sum_cols = sum(col["NSWidth"] for col in table_columns)
            total_content = sum_cols + n_cols * ics_w
            target_sum = clip_computed_w - (n_cols + 3) * ics_w
            if total_content > clip_computed_w - ics_w * 3 - vs_standard_w:
                doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT0)
                doc_view.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)
                col_change = int(target_sum - sum_cols)
                if col_change > 0:
                    _reduce_column_widths(doc_view, -col_change)
            if has_header:
                hv_h = _get_header_h(obj)
                if hv_h:
                    hcv = obj.get("NSHeaderClipView")
                    hcv.get("NSDocView")["NSFrameSize"] = size_string(clip_computed_w, hv_h)
    if _is_table_or_outline(doc_view) and not vs_offscreen and is_regular_scroller and (has_horizontal_scroller or not auto_hiding):
        scroller_w = 17
        ics_w = _get_ics_w(doc_view)
        expansion = int(scroller_w + 3) if has_header else int(scroller_w + ics_w * 3)
        cv_computed = cv.frame()
        clip_computed_w = int(cv_computed[2]) if cv_computed else None
        clip_computed_h = int(cv_computed[3]) if cv_computed else None
        header_h = _get_header_h(obj)
        dv_raw = doc_view.raw_frame()
        if dv_raw:
            raw_w, new_h = dv_raw[2], dv_raw[3]
            if clip_computed_w is not None and raw_w > clip_computed_w:
                new_w = raw_w + expansion
            elif not has_horizontal_scroller and clip_computed_w is not None and raw_w <= clip_computed_w and (clip_computed_w - raw_w) >= vs_standard_w:
                new_w = clip_computed_w
                if new_w - raw_w > 0:
                    _reduce_resizable_column_widths(doc_view, -(new_w - raw_w))
            elif clip_computed_w is not None and raw_w <= clip_computed_w:
                new_w = raw_w + expansion if has_horizontal_scroller else raw_w
            else:
                new_w = raw_w + expansion
            elastic_h = doc_view.extraContext.get("elastic_row_height")
            if auto_hiding and hs_h_for_table > 0 and clip_computed_h:
                original_visible_h = clip_computed_h + hs_h_for_table - header_h
            elif clip_computed_h:
                original_visible_h = clip_computed_h - header_h
            else:
                original_visible_h = None
            if elastic_h is not None and original_visible_h is not None and elastic_h > original_visible_h:
                new_h = elastic_h
            elif has_header and clip_computed_h is not None:
                new_h = clip_computed_h - header_h
            doc_view["NSFrameSize"] = size_string(new_w, new_h)
        # Expand header view width to match
        if has_header:
            hcv = obj.get("NSHeaderClipView")
            hv = hcv.get("NSDocView") if hcv else None
            if hv:
                hv_raw = hv.raw_frame()
                if hv_raw:
                    hv_raw_w, hv_new_h = hv_raw[2], hv_raw[3]
                    if clip_computed_w is not None and hv_raw_w > clip_computed_w:
                        hv_new_w = hv_raw_w + expansion
                    elif not has_horizontal_scroller and clip_computed_w is not None and hv_raw_w <= clip_computed_w:
                        hv_new_w = clip_computed_w
                    elif clip_computed_w is not None and hv_raw_w <= clip_computed_w:
                        hv_new_w = hv_raw_w + expansion if has_horizontal_scroller else hv_raw_w
                    else:
                        hv_new_w = hv_raw_w + expansion
                    hv["NSFrameSize"] = size_string(hv_new_w, hv_new_h)

    # For hasHorizontalScroller=NO with autohiding, expand doc view to fit column content
    if _is_table_or_outline(doc_view) and not vs_offscreen and not has_horizontal_scroller and auto_hiding:
        table_columns = doc_view.get("NSTableColumns") or []
        if table_columns:
            ics_w = _get_ics_w(doc_view)
            ncols = len(table_columns)
            sum_cols = sum(col["NSWidth"] for col in table_columns)
            content_w = int(sum_cols + ncols * ics_w)
            cv_computed = cv.frame()
            clip_w_val = int(cv_computed[2]) if cv_computed else 0
            if content_w > clip_w_val:
                expansion = int(vs_standard_w + ics_w * (ncols + 4))
                new_w = int(sum_cols) + expansion
                clip_h_val = int(cv_computed[3]) if cv_computed else 0
                header_h_val = _get_header_h(obj) or 0
                new_h = clip_h_val - header_h_val
                doc_view["NSFrameSize"] = size_string(new_w, new_h)
                obj["NSHScroller"]["NSEnabled"] = True
                obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)
                doc_view.flagsOr("NSTvFlags", TVFLAGS.GRID_STYLE_BIT1)

    # Horizontal scroller gets NSEnabled for table/outline scroll views (regular size, not autohiding)
    is_table_sv = _is_table_or_outline(doc_view)
    if is_table_sv and is_regular_scroller and not vs_offscreen and (has_horizontal_scroller or not auto_hiding):
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
            dv_raw = doc_view.raw_frame()
            raw_dv_w = dv_raw[2] if dv_raw else 0
            clip_w = int(cv.frame()[2]) if cv.frame() else 0
            if raw_dv_w > clip_w:
                obj["NSHScroller"]["NSEnabled"] = True

    # Autohiding small scroller handling for table/outline scroll views with offscreen VScroller
    if is_table_sv and vs_offscreen and not is_regular_scroller and auto_hiding:
        hs_vflags = obj["NSHScroller"].get("NSvFlags")
        hs_is_hidden = (hs_vflags or 0) & vFlags.HIDDEN
        border_sm = st.border
        sv_raw = obj.raw_frame()
        if sv_raw:
            sv_w_sm, sv_h_sm = sv_raw[2], sv_raw[3]
            clip_w_sm = int(sv_w_sm - 2 * border_sm)
            ics_w = _get_ics_w(doc_view)
            hs_raw = obj["NSHScroller"].raw_frame()
            hs_frame_h = hs_raw[3] if hs_raw else 14
            table_columns = doc_view.get("NSTableColumns") or []
            ncols = len(table_columns)
            sum_cols = sum(col["NSWidth"] for col in table_columns)
            natural_w = int(sum_cols + ncols * ics_w + vs_standard_w + hs_frame_h)
            has_grid_lines = doc_view.get("NSGridStyleMask")
            if hs_is_hidden and not has_grid_lines and has_header:
                expansion = int(17 + ics_w * 4) if border_deficit > 0 else int(17 + 3)
                new_w = clip_w_sm + expansion
                dv_raw = doc_view.raw_frame()
                if dv_raw:
                    new_h = dv_raw[3]
                    if hs_h_for_table > 0 and has_header:
                        cv_tmp = obj.get("NSContentView")
                        if cv_tmp:
                            cv_computed_tmp = cv_tmp.frame()
                            if cv_computed_tmp:
                                header_h_tmp = _get_header_h(obj)
                                visible_h = int(cv_computed_tmp[3]) - header_h_tmp
                                if new_h > visible_h:
                                    new_h = visible_h
                    doc_view["NSFrameSize"] = size_string(new_w, new_h)
                _set_header_view_width(obj, new_w)
                _setup_hscroller_frame(obj, border_sm, sv_h_sm, clip_w_sm)
                obj["NSHScroller"]["NSPercent"] = clip_w_sm / new_w
                if has_horizontal_scroller:
                    obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)
            elif hs_is_hidden and not has_grid_lines and natural_w > clip_w_sm:
                dv_raw = doc_view.raw_frame()
                if dv_raw:
                    doc_view["NSFrameSize"] = size_string(natural_w, dv_raw[3])
                _set_header_view_width(obj, natural_w)
                _setup_hscroller_frame(obj, border_sm, sv_h_sm, clip_w_sm)
                obj["NSHScroller"]["NSPercent"] = clip_w_sm / natural_w
                obj.flagsOr("NSsFlags", sFlagsScrollView.COPY_ON_SCROLL)
            elif not hs_is_hidden:
                if natural_w > clip_w_sm:
                    _reduce_resizable_column_widths(doc_view, 17 + ics_w * 4)
                dv_raw = doc_view.raw_frame()
                if dv_raw:
                    doc_view["NSFrameSize"] = size_string(clip_w_sm, dv_raw[3])
                _set_header_view_width(obj, clip_w_sm)
                doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT1)
                obj["NSHScroller"].flagsOr("NSvFlags", vFlags.HIDDEN)

    # Small scroller handling for table/outline scroll views with offscreen VScroller (non-autohiding)
    if is_table_sv and vs_offscreen and not is_regular_scroller and not auto_hiding:
        hs_vflags = obj["NSHScroller"].get("NSvFlags")
        hs_is_hidden = (hs_vflags or 0) & vFlags.HIDDEN
        border_sm = st.border
        sv_raw = obj.raw_frame()
        if sv_raw:
            sv_w_sm, sv_h_sm = sv_raw[2], sv_raw[3]
            clip_w_sm = int(sv_w_sm - 2 * border_sm)
            if hs_is_hidden:
                expansion = 20
                dv_raw = doc_view.raw_frame()
                if dv_raw:
                    doc_view["NSFrameSize"] = size_string(dv_raw[2] + expansion, dv_raw[3])
                if has_header:
                    hv_raw = obj.get("NSHeaderClipView").get("NSDocView").raw_frame()
                    if hv_raw:
                        obj.get("NSHeaderClipView").get("NSDocView")["NSFrameSize"] = size_string(hv_raw[2] + expansion, hv_raw[3])
                _setup_hscroller_frame(obj, border_sm, sv_h_sm, clip_w_sm)
                dv_frame_str = doc_view.get("NSFrameSize")
                if dv_frame_str:
                    m = re.match(r'\{(\d+),', dv_frame_str._text)
                    if m:
                        table_w = int(m.group(1))
                        if table_w > 0:
                            obj["NSHScroller"]["NSPercent"] = clip_w_sm / table_w
            else:
                _reduce_resizable_column_widths(doc_view, 17 + _get_ics_w(doc_view) * 4)
                dv_raw = doc_view.raw_frame()
                if dv_raw:
                    doc_view["NSFrameSize"] = size_string(clip_w_sm, dv_raw[3])
                _set_header_view_width(obj, clip_w_sm)
                obj.flagsAnd("NSsFlags", ~sFlagsScrollView.COPY_ON_SCROLL)
                doc_view.flagsAnd("NSTvFlags", ~TVFLAGS.GRID_STYLE_BIT1)
                obj["NSHScroller"].flagsOr("NSvFlags", vFlags.HIDDEN)

    obj["NSSubviews"].addItem(obj["NSHScroller"])

    # Corner view handling for table/outline scroll views
    if is_table_sv:
        corner_view = doc_view.get("NSCornerView")
        if corner_view:
            border_cv = st.border
            sv_w_cv = st.sv_w
            if auto_hiding:
                corner_view["NSvFlags"] = 0x100 | vFlags.HIDDEN
            elif not vs_offscreen:
                header_h_cv = _get_header_h(obj)
                corner_h = header_h_cv if has_header else 28
                corner_w = 18
                corner_x = int(sv_w_cv) - corner_w
                if "NSFrameSize" in corner_view.properties:
                    del corner_view.properties["NSFrameSize"]
                corner_view["NSFrame"] = frame_string(corner_x, border_cv, corner_w, corner_h)
            if has_header:
                corner_view["NSSuperview"] = obj
                corner_view["NSNextResponder"] = obj
                obj["NSCornerView"] = corner_view
                obj["NSSubviews"].addItem(corner_view)

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
    hs_orig_raw = obj["NSHScroller"].raw_frame()
    hs_offscreen = hs_orig_raw is not None and hs_orig_raw[0] < 0
    if not vs_offscreen and is_table_sv and (is_regular_scroller or small_scroller_should_expand or not cv_already_accounts_for_scroller):
        border = st.border
        sv_w, sv_h = st.sv_w, st.sv_h
        vs_w = vs_standard_w
        hs_h = 17
        header_h = _get_header_h(obj)
        if not auto_hiding:
            vs_x = sv_w - border - vs_w
            vs_y = border + header_h
            vs_h_val = sv_h - 2 * border - header_h
            obj["NSVScroller"]["NSFrame"] = frame_string(vs_x, vs_y, vs_w, vs_h_val)
            obj["NSVScroller"].flagsAnd("NSvFlags", ~vFlags.HIDDEN)
        elastic_h = doc_view.extraContext.get("elastic_row_height")
        if auto_hiding and elastic_h is not None:
            visible_h = sv_h - 2 * border - header_h
            if elastic_h > visible_h:
                clip_h = sv_h - 2 * border - hs_h_for_table
                obj["NSVScroller"]["NSEnabled"] = True
                obj["NSVScroller"]["NSPercent"] = clip_h / (elastic_h + header_h)
                vline_f32 = struct.pack(">f", float(doc_view.get("NSRowHeight") or 0))
                byte1 = vline_f32[1]
                byte1_ceil = (byte1 + 0x0F) & 0xF0
                obj.flagsOr("NSsFlags", (byte1_ceil << 8) | 0x40)
        if not hs_offscreen and has_horizontal_scroller:
            hs_x = border
            hs_y = sv_h - border - hs_h
            hs_w = sv_w - 2 * border
            obj["NSHScroller"]["NSFrame"] = frame_string(hs_x, hs_y, hs_w, hs_h)
            obj["NSHScroller"].flagsAnd("NSvFlags", ~vFlags.HIDDEN)
            clip_w = sv_w - 2 * border
            dv_frame_str = doc_view.get("NSFrameSize")
            if dv_frame_str:
                m = re.match(r'\{(\d+),', dv_frame_str._text)
                if m:
                    table_w = int(m.group(1))
                    if table_w > 0:
                        obj["NSHScroller"]["NSPercent"] = clip_w / table_w
    elif not vs_offscreen and not has_header and not is_table_sv:
        border = st.border
        sv_w, sv_h = st.sv_w, st.sv_h
        vs_w = obj["NSVScroller"].extraContext.get("scroller_width", 15)
        obj["NSVScroller"]["NSFrame"] = frame_string(sv_w - border - vs_w, border, vs_w, sv_h - 2 * border)

    # Expand text view doc views to fill the clip view width
    if not is_table_sv and doc_view and doc_view.originalclassname() == "NSTextView":
        auto_resizing = doc_view.extraContext.get("parsed_autoresizing")
        if auto_resizing and auto_resizing.get("widthSizable"):
            cv_computed = cv.frame()
            if cv_computed:
                clip_w = int(cv_computed[2])
                dv_raw = doc_view.raw_frame()
                if dv_raw:
                    doc_view["NSFrameSize"] = size_string(clip_w, dv_raw[3])
                    tc = doc_view.get("NSTextContainer")
                    if tc:
                        tc["NSWidth"] = float(clip_w)

    h = obj.extraContext.get("horizontalHuggingPriority", "250")
    v = obj.extraContext.get("verticalHuggingPriority", "250")
    if h != "250" or v != "250":
        obj["NSHuggingPriority"] = NibString.intern(f"{{{h}, {v}}}")

    return obj
