from ..models import ArchiveContext, NibObject, XibObject, NibString
from ..parsers_base import parse_children
from xml.etree.ElementTree import Element

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = XibObject(ctx, "NSCustomObject", elem, parent)
    if obj.xibid is not None:
        ctx.addObject(obj.xibid, obj)
    if not obj.xibid.is_negative_id():
        ctx.extraNibObjects.append(obj)
    
    if elem.attrib.get("customClass"):
        pass
    elif obj.xibid.is_negative_id():
        obj["NSClassName"] = NibString.intern("NSApplication")
    else:
        obj["NSClassName"] = NibString.intern("NSObject")

    parse_children(ctx, elem, obj)
    return obj
