from ..models import ArchiveContext, NibObject, XibObject
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    children = parse_children(ctx, elem, parent)
    
    assert len(children) == 1, "Unexpected number of prototypes"

    parent.extraContext["prototypeCellView"] = children[0]
