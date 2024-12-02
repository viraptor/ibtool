from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    obj = make_xib_object(ctx, "NSTableFieldCell", elem, parent)

    parse_children(ctx, elem, obj)
    
    return obj
