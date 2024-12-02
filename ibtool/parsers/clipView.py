from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibString
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
    
    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)
    if not is_main_view:
        obj["NSSuperview"] = obj.xib_parent()
    
    obj["NSAutomaticallyAdjustsContentInsets"] = True
    if not is_main_view:
        obj["NSvFlags"] = vFlags.AUTORESIZES_SUBVIEWS # clearing the values from elem - they don't seem to matter
    if elem.attrib.get("drawsBackground", "YES" if ctx.toolsVersion >= 20037 else "NO") == "YES":
        obj.flagsOr("NScvFlags", cvFlags.DRAW_BACKGROUND)
    cursor = NibObject("NSCursor", obj)
    cursor["NSCursorType"] = 0
    cursor["NSHotSpot"] = NibString.intern("{1, -1}")
    obj["NSCursor"] = cursor
    obj["NSNextResponder"] = NibNil() if is_main_view else obj.xib_parent()
    if obj.get("NSSubviews") and len(obj["NSSubviews"]) > 0:
        obj["NSDocView"] = obj["NSSubviews"][0]
    else:
        obj["NSDocView"] = NibNil()
    obj.setIfEmpty("NSBGColor", makeSystemColor("controlBackgroundColor"))
    return obj
