from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from .helpers import make_xib_object
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> XibObject:
    assert parent is not None

    key = elem.attrib["key"]

    obj = make_xib_object(ctx, "NSLevelIndicatorCell", elem, parent)
    parse_children(ctx, elem, obj)

    if key == "dataCell":
        parent["NSDataCell"] = obj

    else:
        raise Exception(f"Unknown key for levelIndicatorCell: {key}")
        

    return obj

