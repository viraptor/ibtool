from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object, __handle_view_chain
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTableCellView", elem, parent)

    identifier = elem.attrib.get("identifier")
    if identifier:
        obj.extraContext["identifier"] = identifier

    with __handle_view_chain(ctx, obj):
        parse_children(ctx, elem, obj)

    if obj.get("NSNextKeyView") is not None:
        del obj["NSNextKeyView"]

    return obj
