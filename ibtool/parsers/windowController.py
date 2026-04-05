from ..models import ArchiveContext, NibObject, NibString, XibObject
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSWindowController", elem, parent)
    ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)

    show_segue = elem.get("showSeguePresentationStyle")
    obj["showSeguePresentationStyle"] = 1 if show_segue == "single" else 0

    sb_id = elem.get("storyboardIdentifier")
    if sb_id:
        obj["explicitStoryboardIdentifier"] = NibString.intern(sb_id)

    parse_children(ctx, elem, obj)

    return obj
