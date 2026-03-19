from ..models import ArchiveContext, NibObject, XibObject, NibString, XibId
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSCustomFormatter", elem, parent)
    if obj.xibid is not None:
        ctx.addObject(obj.xibid, obj)
    ctx.extraNibObjects.append(obj)

    return obj
