from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString, NibInlineString
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain, makeSystemColor
from ..parsers_base import parse_children
from ..constants import vFlags, cvFlags

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSClipView", elem, parent)
    
    key = elem.get("key")
    if key == "contentView":
        if parent.originalclassname() == "NSScrollView":
            parent["NSContentView"] = obj
            is_main_view = False
        elif parent.originalclassname() == "NSWindowTemplate":
            parent["NSWindowView"] = obj
            is_main_view = True
        else:
            raise Exception(
                "Unhandled class '%s' to take UIView with key 'contentView'"
                % (parent.originalclassname())
            )
    else:
        raise Exception(f"view in unknown key {key} (parent {parent.repr()})")
    
    obj.extraContext["is_window_content_view"] = is_main_view
    if is_main_view:
        # Store window content rect size so frame() uses it
        win_rect = parent.extraContext.get("NSWindowRect")
        if win_rect:
            obj.extraContext["window_content_size"] = (win_rect[2], win_rect[3])
    if not is_main_view:
        # ClipView fills scrollView's full inner area regardless of XIB rect.
        # Store scrollView dimensions so frame() uses them instead of XIB rect.
        sv = parent.extraContext
        if "NSFrame" in sv:
            obj.extraContext["scrollview_size"] = (sv["NSFrame"][2], sv["NSFrame"][3])
        elif "NSFrameSize" in sv:
            obj.extraContext["scrollview_size"] = sv["NSFrameSize"]
    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    if not is_main_view:
        obj["NSSuperview"] = obj.xib_parent()
    
    obj["NSAutomaticallyAdjustsContentInsets"] = True
    if not is_main_view:
        obj["NSvFlags"] = vFlags.AUTORESIZES_SUBVIEWS # clearing the values from elem - they don't seem to matter
    if elem.attrib.get("copiesOnScroll", "YES") == "NO":
        obj.flagsOr("NScvFlags", 0x2)
    if is_main_view:
        obj.flagsOr("NScvFlags", cvFlags.DRAW_BACKGROUND)
    elif elem.attrib.get("drawsBackground", "YES" if ctx.toolsVersion >= 20037 else "NO") == "YES":
        obj.flagsOr("NScvFlags", cvFlags.DRAW_BACKGROUND)
    # catalog/System backgroundColor color implies DRAW_BACKGROUND (unless drawsBackground is explicitly NO)
    elif elem.attrib.get("drawsBackground") != "NO" and any(child.tag == "color" and child.attrib.get("key") == "backgroundColor" and child.attrib.get("colorSpace") == "catalog" for child in elem):
        obj.flagsOr("NScvFlags", cvFlags.DRAW_BACKGROUND)
    obj["NSNextResponder"] = NibNil() if is_main_view else obj.xib_parent()
    if obj.get("NSSubviews") and len(obj["NSSubviews"]) > 0:
        obj["NSDocView"] = obj["NSSubviews"][0]
    else:
        obj["NSDocView"] = NibNil()
    if not is_main_view and not isinstance(obj.get("NSDocView"), NibNil):
        obj["NSNextKeyView"] = obj["NSDocView"]
    # Only clip views containing text views get a cursor
    doc_view = obj.get("NSDocView")
    if doc_view is not None and not isinstance(doc_view, NibNil) and doc_view.originalclassname() == "NSTextView":
        cursor = NibObject("NSCursor", obj)
        cursor["NSCursorType"] = 0
        cursor["NSHotSpot"] = NibString.intern("{1, -1}")
        obj["NSCursor"] = cursor
    # Table/outline view doc views imply DRAW_BACKGROUND on clip view
    doc_view = obj.get("NSDocView")
    if not is_main_view and doc_view is not None and not isinstance(doc_view, NibNil):
        if doc_view.originalclassname() in ("NSTableView", "NSOutlineView"):
            obj.flagsOr("NScvFlags", cvFlags.DRAW_BACKGROUND)
    obj.setIfEmpty("NSBGColor", makeSystemColor("controlBackgroundColor"))
    return obj
