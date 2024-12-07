from ..models import ArchiveContext, NibObject, XibObject, NibString, NibMutableList, NibList, NibInlineString, NibFloatToWord
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain
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
    has_horizontal_scroller = sFlagsScrollView.HAS_HORIZONTAL_SCROLLER if elem.attrib.get("hasHorizontalScroller") == "YES" else 0
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

    if not obj.extraContext.get("parsed_autoresizing"):
        obj.flagsOr("NSvFlags", vFlags.DEFAULT_VFLAGS_AUTOLAYOUT if ctx.useAutolayout else vFlags.DEFAULT_VFLAGS)
    obj["NSGestureRecognizers"] = NibList([default_pan_recognizer(obj)])
    obj["NSMagnification"] = 1.0
    obj["NSMaxMagnification"] = 4.0
    obj["NSMinMagnification"] = 0.25
    obj["NSSubviews"] = NibMutableList([
        obj["NSContentView"],
        obj["NSHScroller"],
        obj["NSVScroller"],
        ])

    horizontal_line_scroll = int(elem.attrib.get("horizontalLineScroll", "10"))
    vertical_line_scroll = int(elem.attrib.get("verticalLineScroll", "10"))
    horizontal_page_scroll = 0 if elem.attrib.get("horizontalPageScroll") == "0.0" else int(elem.attrib.get("horizontalPageScroll", "10"))
    vertical_page_scroll = 0 if elem.attrib.get("verticalPageScroll") == "0.0" else int(elem.attrib.get("verticalPageScroll", "10"))
    if (horizontal_line_scroll, vertical_line_scroll, horizontal_page_scroll, vertical_page_scroll) != (10, 10, 10, 10):
        obj["NSScrollAmts"] = NibInlineString(NibFloatToWord(vertical_page_scroll) + NibFloatToWord(horizontal_page_scroll) + NibFloatToWord(vertical_line_scroll) + NibFloatToWord(horizontal_line_scroll))

    if (content_view := obj.get("NSContentView")) is not None:
        if (doc_view := content_view.get("NSDocView")) is not None:
            if doc_view.originalclassname() == "NSTableView":
                obj["NSHScroller"]["NSEnabled"] = True

    return obj
