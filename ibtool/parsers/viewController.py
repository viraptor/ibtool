from ..models import ArchiveContext, NibObject, NibString, XibObject
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSViewController", elem, parent)
    ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)
    obj["showSeguePresentationStyle"] = 0

    parse_children(ctx, elem, obj)

    return obj
