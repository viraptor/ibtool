from ..models import ArchiveContext, NibObject, NibMutableList
from xml.etree.ElementTree import Element
from typing import Optional
from ..parsers_base import parse_children

def parse(ctx: ArchiveContext, elem: Element, parent: Optional[NibObject]) -> None:
    assert parent is not None
    segments = parse_children(ctx, elem, parent)
    parent["NSSegmentImages"] = NibMutableList(segments)
    
