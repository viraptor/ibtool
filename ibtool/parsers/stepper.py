from ..models import ArchiveContext, NibObject, XibObject, NibNil, NibMutableList
from xml.etree.ElementTree import Element
from .helpers import make_xib_object, handle_props, PropSchema, MAP_YES_NO
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: NibObject) -> XibObject:
    obj = make_xib_object(ctx, "NSStepper", elem, parent)

    parse_children(ctx, elem, obj)
    
    handle_props(ctx, elem, obj, [
    ])

    return obj
