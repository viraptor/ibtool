from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, _xibparser_common_translate_autoresizing
from ..parsers_base import parse_children
from ..constants import sFlagsScrollView, vFlags

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
    obj["NSsFlags"] = 0x20800 | has_horizontal_scroller | has_vertical_scroller | uses_predominant_axis_scrolling | border_type | auto_hiding
    if border_type in [sFlagsScrollView.BORDER_LINE, sFlagsScrollView.BORDER_BEZEL]:
        obj.extraContext["insets"] = (2, 2)
    if border_type == sFlagsScrollView.BORDER_GROOVE:
        obj.extraContext["insets"] = (4, 4)

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)

    _xibparser_common_translate_autoresizing(ctx, elem, parent, obj)

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
        # Content clip view gets NSBounds with y offset for header
        cv = obj["NSContentView"]
        cv_frame = cv.extraContext.get("NSFrame") or cv.extraContext.get("NSFrameSize")
        if cv_frame is not None:
            cv_w = cv_frame[2] if len(cv_frame) == 4 else cv_frame[0]
            cv_h = cv_frame[3] if len(cv_frame) == 4 else cv_frame[1]
            cv["NSBounds"] = NibString.intern(f"{{{{{0}, {-23}}}, {{{int(cv_w)}, {int(cv_h)}}}}}")
    obj["NSSubviews"].addItem(obj["NSHScroller"])
    obj["NSSubviews"].addItem(obj["NSVScroller"])

    obj["NSNextKeyView"] = obj["NSContentView"]

    horizontal_line_scroll = int(elem.attrib.get("horizontalLineScroll", "10"))
    vertical_line_scroll = int(elem.attrib.get("verticalLineScroll", "10"))
    horizontal_page_scroll = 0 if elem.attrib.get("horizontalPageScroll") == "0.0" else int(elem.attrib.get("horizontalPageScroll", "10"))
    vertical_page_scroll = 0 if elem.attrib.get("verticalPageScroll") == "0.0" else int(elem.attrib.get("verticalPageScroll", "10"))
    if (horizontal_line_scroll, vertical_line_scroll, horizontal_page_scroll, vertical_page_scroll) != (10, 10, 10, 10):
        obj["NSScrollAmts"] = NibInlineString(NibFloatToWord(vertical_page_scroll) + NibFloatToWord(horizontal_page_scroll) + NibFloatToWord(vertical_line_scroll) + NibFloatToWord(horizontal_line_scroll))

    # Recompute vertical scroller frame from scrollView dimensions, but only if
    # the scroller isn't already positioned off-screen (hidden auto-hiding scrollers)
    vs_orig_frame = obj["NSVScroller"].extraContext.get("NSFrame")
    vs_offscreen = vs_orig_frame and len(vs_orig_frame) == 4 and vs_orig_frame[0] < 0
    if not vs_offscreen:
        insets = obj.extraContext.get("insets", (0, 0))
        border = insets[0] // 2  # total inset / 2 = per-side border
        sv_frame = obj.extraContext.get("NSFrame") or obj.extraContext.get("NSFrameSize")
        if sv_frame is not None:
            sv_w = sv_frame[2] if len(sv_frame) == 4 else sv_frame[0]
            sv_h = sv_frame[3] if len(sv_frame) == 4 else sv_frame[1]
            # Get the scroller width from its extraContext (set by scroller parser)
            vs_w = obj["NSVScroller"].extraContext.get("scroller_width", 15)
            vs_x = sv_w - border - vs_w
            vs_y = border
            vs_h = sv_h - 2 * border
            obj["NSVScroller"]["NSFrame"] = NibString.intern(f"{{{{{vs_x}, {vs_y}}}, {{{vs_w}, {vs_h}}}}}")

    return obj
