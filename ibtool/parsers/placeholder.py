from ..models import ArchiveContext, NibObject, NibProxyObject, XibId
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> NibProxyObject:
    placeholderid = elem.attrib["placeholderIdentifier"]
    obj = NibProxyObject(placeholderid)
    parse_children(ctx, elem, obj)
    ctx.addObject(XibId(elem.attrib["id"]), obj)
    return obj

